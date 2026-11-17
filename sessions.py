"""Session reads: authenticated Aside CLI status and messages.jsonl tracking.

두 소스를 쓴다:
  1) aside session list — the CLI handles daemon authentication for live status.
  2) ~/.aside/u/0/sessions/<날짜>_<id>/messages.jsonl — 실시간으로 쌓이는 대화 원본.
     `aside exec` 는 중간 과정을 stdout 에 안 뱉는다. 스트리밍의 유일한 소스가 이 파일이다.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlparse

import httpx

import config
import uploads
from daemon import ACCOUNT_ID, daemon

log = logging.getLogger("aside-relay.sessions")

_dir_index: dict[str, Path] = {}
_dir_index_at: float = 0.0

# --------------------------------------------------------------------- 디렉토리
def session_dir(session_id: str) -> Path | None:
    global _dir_index, _dir_index_at
    hit = _dir_index.get(session_id)
    if hit:
        if _safe_session_directory(hit):
            return hit
        _dir_index.pop(session_id, None)
    if time.time() - _dir_index_at > 2.0:
        _reindex()
    hit = _dir_index.get(session_id)
    return hit if hit and _safe_session_directory(hit) else None


def _reindex() -> None:
    global _dir_index, _dir_index_at
    idx: dict[str, Path] = {}
    if _safe_root(config.SESSIONS_DIR):
        for p in config.SESSIONS_DIR.iterdir():
            if _safe_session_directory(p) and "_" in p.name:
                idx[p.name.split("_", 1)[1]] = p
    _dir_index = idx
    _dir_index_at = time.time()


def snapshot_dirs() -> set[str]:
    """현재 존재하는 세션 디렉토리 이름 집합 (exec 스폰 전후 diff 용)."""
    if not _safe_root(config.SESSIONS_DIR):
        return set()
    return {p.name for p in config.SESSIONS_DIR.iterdir() if _safe_session_directory(p)}


def _safe_session_directory(path: Path) -> bool:
    if path.is_symlink():
        return False
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(config.SESSIONS_DIR.resolve(strict=True))
    except (OSError, ValueError):
        return False
    return resolved.is_dir()


def _safe_root(path: Path) -> bool:
    if path.is_symlink():
        return False
    try:
        return path.resolve(strict=True).is_dir()
    except OSError:
        return False


# --------------------------------------------------------------------- 미디어
def store_media(b64: str) -> dict:
    """base64 이미지를 캐시 파일로 떨구고 참조만 돌려준다. 폰으로 base64를 보내지 않는다."""
    if not _safe_root(config.MEDIA_DIR):
        raise ValueError("Media cache is unavailable")
    raw = base64.b64decode(b64)
    digest = hashlib.sha256(raw).hexdigest()[:32]
    kind = uploads.sniff(raw)
    mime, ext = kind if kind and kind[0].startswith("image/") else ("application/octet-stream", "bin")
    path = config.MEDIA_DIR / f"{digest}.{ext}"
    if path.is_symlink():
        raise ValueError("Media cache path is unsafe")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        if media_path(path.name) is None:
            raise ValueError("Media cache path is unsafe")
    else:
        with os.fdopen(descriptor, "wb") as file:
            file.write(raw)
    return {"type": "image", "mediaId": path.name, "mime": mime, "bytes": len(raw)}


def media_path(media_id: str) -> Path | None:
    if "/" in media_id or "\\" in media_id or ".." in media_id:
        return None
    if not _safe_root(config.MEDIA_DIR):
        return None
    p = config.MEDIA_DIR / media_id
    if p.is_symlink():
        return None
    try:
        resolved = p.resolve(strict=True)
        resolved.relative_to(config.MEDIA_DIR.resolve(strict=True))
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


# --------------------------------------------------------------------- 정규화
# 에이전트는 최종 답변에 로컬 절대경로를 그대로 박는다:
#   ![screenshot](/Users/<you>/.aside/u/0/sessions/<dir>/tmp/xxx.png)
#   ![screenshot](C:\Users\<you>\.aside\u\0\sessions\<dir>\tmp\xxx.png)   (Windows)
#   [Output too large ... saved to: /Users/.../tmp/repl-result-xxx.txt]
# 폰에서는 열 수 없으니 브리지가 서빙하는 URL 로 바꿔준다.
# 접두사 `file://` 를 반드시 함께 먹어야 한다. 안 그러면 경로만 바뀌어
#   ![샷](file:///api/sessions/<id>/file/tmp/x.png)
# 가 되고, https 페이지에서 file: 스킴은 브라우저가 차단해 깨진 이미지로 뜬다.
# (실제로 이 버그로 답변의 스크린샷이 alt 텍스트만 보였다.)
# Windows 경로는 드라이브 문자 + 역슬래시 구분자를 쓰므로 어느쪽이든 받아낸다.
_PATH_SEP = r"[\\/]"
_LOCAL_PATH_RE = re.compile(
    r"(?:file://)?"                                  # file:// 접두사(선택)
    r"/?"                                            # file:///C:/... 의 슬래시(선택)
    r"(?:[A-Za-z]:)?"                                # Windows 드라이브 문자(선택)
    + _PATH_SEP +
    r"Users" + _PATH_SEP +
    r"[^/\\\s]+" + _PATH_SEP + r"\.aside" + _PATH_SEP + r"u" + _PATH_SEP + r"\d+" + _PATH_SEP +
    r"sessions" + _PATH_SEP +
    r"(?P<dir>[^/\\\s)\]]+)" + _PATH_SEP +
    r"(?P<rel>[^\s)\]\"']+)"
)
# 첨부 업로드도 같은 문제를 겪는다. 이쪽은 파일명 하나가 곧 id 다.
_UPLOAD_PATH_RE = re.compile(
    r"(?:file://)?"
    r"/?"
    r"(?:[A-Za-z]:)?"
    + _PATH_SEP +
    r"Users" + _PATH_SEP +
    r"[^/\\\s]+" + _PATH_SEP + r"\.aside" + _PATH_SEP + r"u" + _PATH_SEP + r"\d+" + _PATH_SEP +
    r"uploads" + _PATH_SEP +
    r"(?P<fid>[^\s/\\)\]\"']+)"
)


def rewrite_local_paths(text: str) -> str:
    text = _LOCAL_PATH_RE.sub(
        lambda m: "/api/sessions/{}/file/{}".format(
            m.group("dir").split("_", 1)[-1],
            # Windows 경로의 역슬래시를 URL 세그먼트 구분자로 통일한다.
            m.group("rel").replace("\\", "/"),
        ),
        text,
    )
    return _UPLOAD_PATH_RE.sub(lambda m: f"/api/upload/{m.group('fid')}", text)


def session_file(session_id: str, rel: str) -> Path | None:
    """세션 디렉토리 안의 파일만 내준다. 경로 탈출 차단."""
    d = session_dir(session_id)
    if not d:
        return None
    relative = Path(rel)
    if relative.is_absolute() or "\\" in rel or ".." in relative.parts:
        return None
    try:
        root = d.resolve(strict=True)
        candidate = d / relative
        target = candidate.resolve(strict=True)
        target.relative_to(root)
    except (ValueError, OSError):
        return None
    current = candidate
    while current != d:
        if current.is_symlink():
            return None
        current = current.parent
    return target if target.is_file() else None


def _blocks(raw: object) -> list[dict]:
    out: list[dict] = []
    if isinstance(raw, str):
        return [{"type": "text", "text": rewrite_local_paths(raw)}] if raw.strip() else []
    if not isinstance(raw, list):
        return out
    for b in raw:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "text":
            text = b.get("text")
            if isinstance(text, str) and text:
                out.append({"type": "text", "text": rewrite_local_paths(text)})
        elif t == "thinking":
            thinking = b.get("thinking")
            txt = thinking.strip() if isinstance(thinking, str) else ""
            # thinkingSignature 는 암호화된 reasoning 원문이라 앱엔 무의미. 버린다.
            out.append({"type": "thinking", "text": txt})
        elif t == "toolCall":
            out.append({
                "type": "toolCall",
                "id": b.get("id"),
                "name": b.get("name"),
                "args": b.get("arguments"),
            })
        elif t == "image":
            data = b.get("data")
            if data:
                try:
                    out.append(store_media(data))
                except Exception:
                    log.exception("image block decode failed")
    return out


def _sources(raw: object) -> list[dict]:
    out: list[dict] = []
    for source in raw if isinstance(raw, list) else []:
        if not isinstance(source, dict):
            continue
        source_id = source.get("id")
        url = source.get("url")
        if not isinstance(source_id, str) or not isinstance(url, str):
            continue
        try:
            parsed = urlparse(url)
        except ValueError:
            continue
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        item = {"id": source_id, "url": url}
        if isinstance(source.get("title"), str):
            item["title"] = source["title"]
        out.append(item)
        if len(out) == 100:
            break
    return out


def normalize(line_obj: dict, seq: int) -> dict | None:
    role = line_obj.get("role")
    if role not in ("user", "assistant", "toolResult", "system-message"):
        return None
    msg = {
        "seq": seq,
        "role": "system" if role == "system-message" else role,
        "ts": line_obj.get("timestamp"),
        "blocks": _blocks(line_obj.get("content")),
    }
    for key in ("toolName", "toolCallId", "model", "provider", "stopReason", "responseId"):
        if line_obj.get(key) is not None:
            msg[key] = line_obj[key]
    if line_obj.get("isError"):
        msg["isError"] = True
    details = line_obj.get("details")
    sources = _sources(details.get("sources") if isinstance(details, dict) else None)
    if sources:
        msg["sources"] = sources
    usage = line_obj.get("usage")
    if isinstance(usage, dict) and usage:
        cost = usage.get("cost")
        msg["usage"] = {
            "input": usage.get("input"),
            "output": usage.get("output"),
            "total": usage.get("totalTokens"),
            "cost": cost.get("total") if isinstance(cost, dict) else None,
        }
    if not msg["blocks"] and role == "toolResult":
        msg["blocks"] = [{"type": "text", "text": ""}]
    return msg


def read_messages(session_id: str, *, tail: int | None = None) -> tuple[list[dict], int]:
    """(정규화된 메시지 목록, 파일 바이트 오프셋) 반환."""
    d = session_dir(session_id)
    if not d:
        return [], 0
    f = d / "messages.jsonl"
    if not f.exists():
        return [], 0
    try:
        data = f.read_bytes()
    except OSError:
        return [], 0
    if data and not data.endswith(b"\n"):
        trailing_start = data.rfind(b"\n") + 1
        try:
            json.loads(data[trailing_start:])
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = data[:trailing_start]
    msgs: list[dict] = []
    offset = seq = cursor = 0
    for raw in data.splitlines(keepends=True):
        cursor += len(raw)
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(obj, dict):
            seq += 1
            continue
        m = normalize(obj, seq)
        seq += 1
        if m:
            msgs.append(m)
            offset = cursor
    if tail:
        msgs = msgs[-tail:]
    return msgs, offset


async def tail_messages(session_id: str, start_offset: int = 0,
                        start_seq: int = 0) -> AsyncIterator[dict]:
    """messages.jsonl 에 새로 붙는 줄을 정규화해서 흘려보낸다."""
    d = session_dir(session_id)
    deadline = time.time() + 30
    while d is None and time.time() < deadline:
        await asyncio.sleep(0.3)
        d = session_dir(session_id)
    if d is None:
        return
    f = d / "messages.jsonl"
    offset, seq, buf = start_offset, start_seq, b""
    while True:
        try:
            if f.exists():
                size = f.stat().st_size
                if size < offset:      # 회전/재작성
                    offset, buf = 0, b""
                if size > offset:
                    with f.open("rb") as fh:
                        fh.seek(offset)
                        chunk = fh.read(size - offset)
                    offset = size
                    buf += chunk
                    *lines, buf = buf.split(b"\n")
                    for raw in lines:
                        if not raw.strip():
                            continue
                        try:
                            obj = json.loads(raw)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue
                        if not isinstance(obj, dict):
                            seq += 1
                            continue
                        m = normalize(obj, seq)
                        seq += 1
                        if m:
                            yield m
        except OSError:
            pass
        await asyncio.sleep(config.JSONL_POLL_SEC)


# --------------------------------------------------------------------- 데몬 프록시
async def live_sessions() -> list[dict]:
    args = [config.ASIDE_BIN, "session", "list"]
    if config.ASIDE_ACCOUNT:
        args += ["--account", config.ASIDE_ACCOUNT]
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
    except (TimeoutError, asyncio.CancelledError):
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        await proc.communicate()
        raise
    if proc.returncode != 0:
        raise RuntimeError("Aside session list failed")
    text = out.decode("utf-8", "replace").strip()
    if text == "No sessions.":
        return []
    items = []
    for line in text.splitlines():
        match = re.fullmatch(r"([A-Za-z0-9]{12,32})  (\S+)  (ephemeral|persistent)  (.*?)  (\S+)", line)
        if not match:
            raise RuntimeError("Unrecognized Aside session list output")
        sid, status, kind, title, updated = match.groups()
        items.append({"id": sid, "status": status, "ephemeral": kind == "ephemeral",
                      "title": title, "updatedAt": updated})
    return items


async def native_session_previews(*, limit: int = 50, cursor: int = 0,
                                  q: str | None = None,
                                  archived: str = "exclude",
                                  parent: str = "root",
                                  project_ids: list[str] | None = None,
                                  statuses: list[str] | None = None,
                                  order: str = "desc") -> dict:
    """Aside's native session index, including full-history search and filters."""
    value = {
        "accountId": ACCOUNT_ID,
        "limit": limit,
        "cursor": cursor,
        "order": order,
        "parent": parent,
        "archived": archived,
        "ephemeral": "exclude",
        "routines": "exclude",
        "coders": "exclude",
    }
    if q:
        value["q"] = q
    if project_ids:
        value["projectIds"] = project_ids
    if statuses:
        value["statuses"] = statuses
    items = await daemon.call("sessions.listPreviewItems", value)
    decorated = []
    for item in items:
        suspension = item.get("suspension") if isinstance(item.get("suspension"), dict) else None
        suspension_kind = suspension.get("kind") if suspension else None
        status = item.get("status") or "idle"
        status_label = {
            "approval": "Awaiting approval",
            "action-confirmation": "Awaiting confirmation",
            "ask-user-question": "Awaiting answer",
        }.get(suspension_kind) or {
            "running": "Running",
            "suspended": "Waiting",
            "interrupted": "Interrupted",
            "errored": "Task failed",
            "idle": "Idle",
        }.get(status, status.capitalize())
        decorated.append({
            **item,
            "statusLabel": status_label,
            "suspensionKind": suspension_kind,
        })
    return {
        "items": decorated,
        "nextCursor": cursor + limit if len(items) == limit else None,
    }


async def native_child_sessions(session_id: str) -> list[dict]:
    return await daemon.call("sessions.childSessions", {
        "accountId": ACCOUNT_ID,
        "parentId": session_id,
        "archived": "exclude",
    })


async def native_projects() -> list[dict]:
    return await daemon.call("projects.list", {"accountId": ACCOUNT_ID})


def _texts(node) -> list[str]:
    """content 가 문자열이기도 하고 블록 배열이기도 해서 둘 다 받는다."""
    if node is None:
        return []
    if isinstance(node, str):
        return [node] if node.strip() else []
    if isinstance(node, dict):
        text = node.get("text")
        if node.get("type") == "text" and isinstance(text, str) and text:
            return [text]
        return _texts(node.get("content"))
    if isinstance(node, list):
        out: list[str] = []
        for item in node:
            out.extend(_texts(item))
        return out
    return []


def _final_text(run: dict | None) -> str:
    if not run:
        return ""
    return " ".join(_texts(run.get("finalAssistantMessage"))).strip()


def _first_user_text(run: dict | None) -> str:
    if not run:
        return ""
    parts = _texts(run.get("userMessage"))
    return parts[0] if parts else ""


_status_cache: tuple[float, dict] = (0.0, {})


async def session_status(client: httpx.AsyncClient, session_id: str) -> str | None:
    """데몬이 보는 세션 상태. 브리지가 재기동돼도 살아있는 유일한 권위 소스다.

    브리지의 in-memory `_runs` 는 프로세스가 죽으면 사라지지만 실행 자체는 계속된다
    (aside exec 은 데몬에 직접 붙고 프로세스 그룹도 분리돼 있다).
    그래서 '실행 중' 판정은 여기서 가져와야 맞다.
    """
    global _status_cache
    ts, cache = _status_cache
    if time.time() - ts > 2.0:
        try:
            raw = await live_sessions()
            cache = {s.get("id"): s.get("status") for s in raw}
            _status_cache = (time.time(), cache)
        except Exception:
            pass
    return cache.get(session_id)


# --------------------------------------------------------------- 목록 (디스크가 권위)
# 데몬의 /session/recents 는 히스토리가 아니라 휘발성 최근 창이다. 데몬이 재시작되면
# 통째로 날아간다 (관측: 디스크 81건 vs recents 3건). 그래서 목록의 권위를 디스크로 옮기고,
# recents 는 "지금 running 인가 / 데몬이 붙인 제목" 을 덧칠하는 용도로만 병합한다.
#
# 비용 (실측, 1343 디렉토리):
#   scandir+stat 전수     콜드 159ms · 웜 3ms   → TTL 캐시 하나면 사실상 공짜
#   title+preview 추출    0.76ms/건            → 페이지(30건)만 하이드레이트하면 23ms
# messages.jsonl 없는 디렉토리 1262개는 `aside repl` 원샷 잔재라 목록에서 제외한다.

_INDEX_TTL = 4.0
_index: list[tuple[int, str, int, Path | None]] = []   # (activity_ns, id, size, dir) · 최신순
# mtime 은 정수 나노초로 둔다. float 초를 문자열 커서로 왕복시키면 반올림 때문에
# 커서가 실제값보다 커져 경계 항목이 다음 페이지에 다시 나온다 (실측: 81건 순회에 중복 1건).
_index_at = 0.0
_meta: dict[str, tuple[int, int, str, str]] = {}       # id -> (mtime_ns, size, title, preview)
_activity: dict[str, tuple[int, int, int]] = {}  # File metadata invalidates cached message timestamps.
_TAIL_BYTES = 96 * 1024

_ATT_BLOCK = re.compile(r"^\[첨부 (?:이미지|파일)\]\n(?:- .*\n)+위 (?:이미지|파일)을?를?[^\n]*\n\n?")


def _last_message_ns(path: Path, size: int) -> int:
    with path.open("rb") as fh:
        position = size
        partial = b""
        while position:
            start = max(0, position - _TAIL_BYTES)
            fh.seek(start)
            lines = (fh.read(position - start) + partial).split(b"\n")
            partial = lines[0] if start else b""
            for raw in reversed(lines[1:] if start else lines):
                try:
                    obj = json.loads(raw)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if not isinstance(obj, dict) or obj.get("role") not in ("user", "assistant"):
                    continue
                timestamp = obj.get("timestamp")
                if type(timestamp) in (int, float) and math.isfinite(timestamp) and timestamp > 0:
                    return int(timestamp * 1_000_000)
            position = start
    return 0


def _scan_index() -> list[tuple[int, str, int, Path | None]]:
    rows: list[tuple[int, str, int, Path | None]] = []
    base = config.SESSIONS_DIR
    if not _safe_root(base):
        return rows
    try:
        it = os.scandir(base)
    except OSError:
        return rows
    with it:
        for e in it:
            if "_" not in e.name:
                continue
            try:
                path = Path(e.path)
                if e.is_symlink() or not _safe_session_directory(path):
                    continue
                candidate = path / "messages.jsonl"
                if candidate.is_symlink():
                    continue
                file = candidate.resolve(strict=True)
                file.relative_to(path.resolve(strict=True))
                st = file.stat()
                sid = e.name.split("_", 1)[1]
                cached = _activity.get(sid)
                if cached and cached[:2] == (st.st_mtime_ns, st.st_size):
                    activity_ns = cached[2]
                else:
                    activity_ns = _last_message_ns(file, st.st_size) or st.st_mtime_ns
                    _activity[sid] = (st.st_mtime_ns, st.st_size, activity_ns)
            except OSError:
                continue
            rows.append((activity_ns, sid, st.st_size, path))
    if len(_activity) > 4000:
        _activity.clear()
    rows.sort(key=lambda r: (-r[0], r[1]))
    return rows


def _get_index(force: bool = False) -> list[tuple[int, str, int, Path | None]]:
    global _index, _index_at
    if force or time.time() - _index_at > _INDEX_TTL:
        _index = _scan_index()
        _index_at = time.time()
    return _index


def invalidate_index() -> None:
    """실행 시작/종료처럼 목록이 즉시 바뀌어야 할 때 캐시를 버린다."""
    global _index_at, _dir_index_at, _status_cache
    _index_at = 0.0
    _meta.clear()
    _dir_index.clear()
    _dir_index_at = 0.0
    _status_cache = (0.0, {})


def _clean(t: str) -> str:
    t = _ATT_BLOCK.sub("", t or "")
    return re.sub(r"\s+", " ", t).strip()


def _head_user_text(f: str, lines: int = 10) -> str:
    """제목용. 첫 user 발화 = 파일 앞쪽 몇 줄만 읽으면 된다."""
    buf = []
    with open(f, "rb") as fh:
        for _ in range(lines):
            line = fh.readline()
            if not line:
                break
            buf.append(line)
    for raw in buf:
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("role") == "user":
            t = " ".join(_texts(obj.get("content")))
            if t.strip():
                return t
    return ""


def _tail_asst_text(f: str, size: int, win: int = _TAIL_BYTES) -> str:
    """미리보기용. 마지막 assistant 발화 = 파일 끝 96KB 만 읽는다 (최대 2.7MB 파일 대비)."""
    with open(f, "rb") as fh:
        if size > win:
            fh.seek(-win, 2)
        buf = fh.read()
    lines = buf.split(b"\n")
    if size > win and lines:
        lines = lines[1:]                      # seek 로 잘려나간 첫 줄은 버린다
    for raw in reversed(lines):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("role") == "assistant":
            t = " ".join(_texts(obj.get("content")))
            if t.strip():
                return t
    return ""


def _hydrate(mtime: int, sid: str, size: int, d: Path | None) -> tuple[str, str]:
    if d is not None:
        try:
            mtime = (d / "messages.jsonl").stat().st_mtime_ns
        except OSError:
            return "", ""
    hit = _meta.get(sid)
    if hit and hit[0] == mtime and hit[1] == size:
        return hit[2], hit[3]
    title = preview = ""
    if d is not None:
        f = str(d / "messages.jsonl")
        try:
            title = _clean(_head_user_text(f))[:120]
            preview = _clean(_tail_asst_text(f, size))[:280]
        except OSError:
            pass
    _meta[sid] = (mtime, size, title, preview)
    if len(_meta) > 4000:
        _meta.clear()
    return title, preview


def _cursor_enc(rank: int, mtime: int, sid: str) -> str:
    return f"{rank}~{mtime}~{sid}"


def _cursor_dec(c: str) -> tuple[int, int, str] | None:
    try:
        rank, mtime, sid = c.split("~", 2)
        return (int(rank), int(mtime), sid)
    except Exception:
        return None


def _iso(mtime_ns: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(mtime_ns / 1e9)) + "Z"


def _epoch_ns(iso: str | None) -> int:
    if not iso:
        return 0
    try:
        return int((time.mktime(time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone) * 1e9)
    except Exception:
        return 0


async def list_sessions(client: httpx.AsyncClient, *, limit: int = 30,
                        cursor: str | None = None, q: str | None = None) -> dict:
    """키셋 페이지네이션. offset 이 아니라 (mtime, id) 로 잘라서,
    페이지를 넘기는 사이에 새 세션이 위에 끼어들어도 항목이 밀리거나 중복되지 않는다."""
    async def fetch_live(search_query: str | None = None) -> dict[str, dict]:
        result: dict[str, dict] = {}
        page_size = 200
        while True:
            value = {
                "accountId": ACCOUNT_ID, "limit": page_size, "cursor": len(result),
                "order": "desc", "parent": "root", "archived": "exclude",
                "ephemeral": "exclude", "routines": "exclude", "coders": "exclude",
            }
            if search_query:
                value["q"] = search_query
            page = await daemon.call("sessions.listPreviewItems", value)
            result.update({item["id"]: item for item in page})
            if len(page) < page_size:
                return result

    all_live = await fetch_live()
    needle = q.strip() if q and q.strip() else None
    live = await fetch_live(needle) if needle else all_live
    rows = [row for row in _get_index() if row[1] in live]
    pins = {session_id for session_id, item in all_live.items() if item.get("pinned")}

    def sort_key(row):
        return (0 if row[1] in pins else 1, -row[0], row[1])

    # 방금 시작해 messages.jsonl 이 아직 없는 세션은 디스크에 안 보인다 → recents 로 메운다.
    known = {r[1] for r in rows}
    ghosts = [(_epoch_ns(s.get("updatedAt")), sid, 0, None)
              for sid, s in live.items() if sid not in known and not s.get("ephemeral")]
    if ghosts:
        rows = sorted(rows + ghosts, key=lambda r: (-r[0], r[1]))
    rows = sorted(rows, key=sort_key)

    total = len(all_live)
    matched = len(rows)

    cur = _cursor_dec(cursor) if cursor else None
    if cur:
        ck = (cur[0], -cur[1], cur[2])
        rows = [r for r in rows if sort_key(r) > ck]

    page = rows[:limit]
    nxt = _cursor_enc(sort_key(page[-1])[0], page[-1][0], page[-1][1]) if len(rows) > limit and page else None

    items = []
    for mtime, sid, size, d in page:
        title, preview = _hydrate(mtime, sid, size, d)
        s = live.get(sid) or {}
        run = s.get("latestRun") or {}
        usage = run.get("tokenUsage") or {}
        suspension = s.get("suspension") if isinstance(s.get("suspension"), dict) else None
        suspension_kind = suspension.get("kind") if suspension else None
        status = s.get("status") or "idle"
        status_label = {
            "approval": "Awaiting approval",
            "action-confirmation": "Awaiting confirmation",
            "ask-user-question": "Awaiting answer",
        }.get(suspension_kind) or {
            "running": "Running",
            "suspended": "Waiting",
            "interrupted": "Interrupted",
            "errored": "Task failed",
            "idle": "Idle",
        }.get(status, status.capitalize())
        items.append({
            "id": sid,
            "title": (s.get("title") or title or "Untitled conversation")[:120],
            "status": status,
            "statusLabel": status_label,
            "suspensionKind": suspension_kind,
            "unread": bool(s.get("unread")),
            "isPinned": sid in pins,
            "pinned": bool(s.get("pinned")),
            "projectId": s.get("projectId"),
            "updatedAt": _iso(mtime),
            "mtime": mtime / 1e9,
            "preview": (_final_text(run)[:280] if run else "") or preview,
            "lastPrompt": _first_user_text(run)[:280] if run else title,
            "cost": (usage.get("cost") or {}).get("total"),
            "tokens": usage.get("totalTokens"),
            "bytes": size,
            "hasLog": d is not None,
        })
    return {"items": items, "nextCursor": nxt, "total": total,
            "matched": matched, "q": (q or None)}
