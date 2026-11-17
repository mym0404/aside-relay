"""aside-relay — Aside 를 폰에서 쓰기 위한 로컬 브리지.

  Android ──HTTPS/WSS──> Cloudflare Access ──> cloudflared ──> 여기(127.0.0.1:8799)
                                                                 ├ aside mcp  (브라우저/탭)
                                                                 ├ aside exec (에이전트 실행)
                                                                 ├ messages.jsonl tail (스트리밍)
                                                                 └ daemon :21420 (세션 목록)

설계 제약 (CF 때문에 반드시 지켜야 하는 것):
  · 모든 실행 API 는 즉시 반환한다. CF 엣지 HTTP 타임아웃이 100초라 블로킹하면 504.
  · WS 는 20초 하트비트. CF Free/Pro 는 100초 idle 이면 끊는다.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import secrets
import subprocess
import time
import uuid
from urllib.parse import urlsplit

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response

import browser
import cfaccess
import config
import daemondb
import fonts
import followups
import uploads
import runner
import sessions
import web_push
import native_sessions
import native_files
import native_browser
import native_queue
import native_workspace
from daemon import ACCOUNT_ID, daemon
from mcp_client import ReplError, mcp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)


class _StripQuery(logging.Filter):
    """uvicorn 접근로그는 전체 경로를 찍는다. 쿼리스트링에 토큰이 실릴 수 있어 잘라낸다."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[1], str):
            path = args[1].split("?", 1)
            if len(path) == 2:
                record.args = (args[0], path[0] + "?…", *args[2:])
        return True


logging.getLogger("uvicorn.access").addFilter(_StripQuery())
log = logging.getLogger(config.APP_NAME)

STARTED_AT = time.time()
app = FastAPI(title=config.APP_NAME, docs_url=None, redoc_url=None)
_http: httpx.AsyncClient | None = None
push_notifications = web_push.WebPushStore(config.WEB_PUSH_DIR)


# ------------------------------------------------------------------ 인증
COOKIE = "ar_token"


def _token_of(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    # cookie fallback: <img>/WS cannot attach headers. Never a query string —
    # tokens in URLs leak into access logs and Referer headers.
    return request.cookies.get(COOKIE, "")


def _is_valid_token(token: str) -> bool:
    return secrets.compare_digest(token.encode(), config.BEARER.encode())


async def require_auth(request: Request) -> None:
    if not config.BEARER:          # 토큰 미설정 = 로컬 개발 모드
        return
    if not _is_valid_token(_token_of(request)):
        raise HTTPException(status_code=401, detail="unauthorized")


Auth = Depends(require_auth)
app.include_router(native_sessions.router, dependencies=[Auth])
app.include_router(native_sessions.projects_router, dependencies=[Auth])
app.include_router(native_files.router, dependencies=[Auth])
app.include_router(native_browser.router, dependencies=[Auth])
app.include_router(native_workspace.router, dependencies=[Auth])


@app.exception_handler(native_queue.NativeQueueError)
async def native_queue_error(_request: Request, _error: native_queue.NativeQueueError):
    return JSONResponse({"detail": "Could not update the Aside queue. Review your queued messages and try again."}, status_code=502)


@app.get("/api/sessions/{session_id}/details", dependencies=[Auth])
async def api_session_details(session_id: str):
    if sessions.session_dir(session_id) is None:
        raise HTTPException(404, "unknown session")
    try:
        return await _session_details(session_id)
    except Exception:
        log.exception("conversation details failed session=%s", session_id)
        raise HTTPException(502, "Could not load conversation options.")


async def _session_details(session_id: str) -> dict:
    session = await daemon.call("sessions.get", {"accountId": ACCOUNT_ID, "sessionId": session_id})
    previews = await daemon.call("sessions.listPreviewItems", {"accountId": ACCOUNT_ID,
        "sessionIds": [session_id], "limit": 1, "archived": "include"})
    preview = previews[0] if previews else {}
    return {"id": session_id, "title": session.get("title") or "Conversation",
            "status": session["status"], "isPinned": bool(preview.get("pinned"))}


@app.patch("/api/sessions/{session_id}", dependencies=[Auth])
async def api_update_session(session_id: str, payload: dict):
    if not payload or not set(payload).issubset({"title", "isPinned"}):
        raise HTTPException(400, "invalid conversation settings")
    title = payload.get("title")
    if "title" in payload and (not isinstance(title, str) or not title.strip() or len(title.strip()) > 120):
        raise HTTPException(400, "Use a conversation name between 1 and 120 characters.")
    if "isPinned" in payload and not isinstance(payload["isPinned"], bool):
        raise HTTPException(400, "invalid pin setting")
    async with runner.session_lock:
        if sessions.session_dir(session_id) is None:
            raise HTTPException(404, "unknown session")
        try:
            if title is not None:
                await daemon.call("sessions.update", {"accountId": ACCOUNT_ID, "sessionId": session_id,
                    "title": title.strip()}, mutation=True)
            if "isPinned" in payload:
                await daemon.call("sessions.update", {"accountId": ACCOUNT_ID, "sessionId": session_id,
                    "pinned": payload["isPinned"]}, mutation=True)
            return await _session_details(session_id)
        except Exception:
            log.exception("conversation update failed session=%s", session_id)
            raise HTTPException(502, "Could not update the conversation.")


@app.get("/api/models", dependencies=[Auth])
async def api_models(session_id: str | None = None):
    try:
        available = await daemon.call("models.listAvailable", {"accountId": ACCOUNT_ID})
        if session_id:
            if sessions.session_dir(session_id) is None:
                raise HTTPException(404, "unknown session")
            session = await daemon.call("sessions.get", {"accountId": ACCOUNT_ID, "sessionId": session_id})
            current = session["model"]
        else:
            current = await daemon.call("settings.get", {"accountId": ACCOUNT_ID, "key": "defaultModel"})
        return {"items": [{"id": model["id"], "name": model["name"], "provider": model["provider"],
                           "thinkingLevels": model["availableThinkingLevels"],
                           "supportsFastMode": model["supportsFastMode"]} for model in available],
                "current": current}
    except HTTPException:
        raise
    except Exception:
        log.exception("model list failed")
        raise HTTPException(502, "Could not load models.")


@app.put("/api/sessions/{session_id}/model", dependencies=[Auth])
async def api_select_model(session_id: str, payload: dict):
    if not isinstance(payload.get("provider"), str) or not isinstance(payload.get("modelId"), str):
        raise HTTPException(400, "invalid model")
    try:
        available = await daemon.call("models.listAvailable", {"accountId": ACCOUNT_ID})
        selected = next((model for model in available if model["id"] == payload["modelId"]
                         and model["provider"] == payload["provider"]), None)
        if selected is None:
            raise HTTPException(400, "This model is not available.")
        levels = selected["availableThinkingLevels"]
        thinking_level = payload.get("thinkingLevel")
        if thinking_level is not None and thinking_level not in levels:
            raise HTTPException(400, "This reasoning effort is not available for this model.")
        async with runner.session_lock:
            if sessions.session_dir(session_id) is None:
                raise HTTPException(404, "unknown session")
            session = await daemon.call("sessions.get", {"accountId": ACCOUNT_ID, "sessionId": session_id})
            current = session["model"]
            model = {"provider": selected["provider"], "modelId": selected["id"],
                     "thinkingLevel": thinking_level if thinking_level is not None
                         else current["thinkingLevel"] if current["thinkingLevel"] in levels
                         else "high" if "high" in levels else levels[0],
                     "fastMode": bool(current["fastMode"] and selected["supportsFastMode"])}
            updated = await daemon.call("sessions.update", {"accountId": ACCOUNT_ID,
                "sessionId": session_id, "model": model}, mutation=True)
        return updated["model"]
    except HTTPException:
        raise
    except Exception:
        log.exception("model change failed session=%s", session_id)
        raise HTTPException(502, "Could not change the model.")


@app.exception_handler(browser.TooBusy)
async def _too_busy_handler(_request: Request, _exc: browser.TooBusy):
    """캡처 큐가 꽉 참. 클라이언트는 파비콘으로 폴백한다."""
    return JSONResponse({"error": "busy"}, status_code=503,
                        headers={"Retry-After": "3"})


@app.exception_handler(browser.TabAsleep)
async def _tab_asleep_handler(_request: Request, exc: browser.TabAsleep):
    """잠든 탭은 깨울 방법이 없다(chrome.tabs.update 차단). 앱은 openTab 으로 유도한다."""
    return JSONResponse({
        "error": "tab_asleep",
        "detail": "Chrome discarded this tab to save memory, so it cannot be captured or read.",
        "action": "open_url",
        "url": exc.tab.get("url"),
        "tab": exc.tab,
    }, status_code=409)


@app.exception_handler(browser.TabNotFound)
async def _tab_missing_handler(_request: Request, exc: browser.TabNotFound):
    return JSONResponse({"error": "tab_not_found", "targetId": str(exc)}, status_code=404)


@app.exception_handler(ReplError)
async def _repl_error_handler(_request: Request, exc: ReplError):
    log.error("browser REPL failed: %s", exc)
    return JSONResponse({"error": "repl_error", "detail": runner.safe_run_error(exc)},
                        status_code=502)


# ------------------------------------------------------------------ 수명주기
@app.on_event("startup")
async def _startup() -> None:
    global _http
    _http = httpx.AsyncClient()
    followup_queue.start()
    asyncio.create_task(_warm_mcp())
    log.info("%s up on %s:%s (auth=%s)", config.APP_NAME,
             config.HOST, config.PORT, "on" if config.BEARER else "OFF")


async def _warm_mcp() -> None:
    try:
        await mcp.ensure()
    except Exception:
        log.exception("mcp warmup failed (계속 진행 — 첫 요청 때 다시 시도)")


@app.on_event("shutdown")
async def _shutdown() -> None:
    await followup_queue.close()
    await mcp.close()
    if _http:
        await _http.aclose()


# ------------------------------------------------------------------ 웹 UI
WEB_DIR = config.BASE_DIR / "web"
WEB_DIST_DIR = WEB_DIR / "dist"


@app.get("/")
async def web_index():
    """웹 화면. 인증은 앞단 CF Access 가 막고, 브리지 토큰은 이 셸이 로드된 뒤 물어본다.

    HTML 자체에는 데이터가 없다 — 세션/탭/미디어는 전부 토큰이 붙은 API 호출로만 나간다.
    """
    f = WEB_DIST_DIR / "index.html"
    if not f.exists():
        raise HTTPException(503, "Web UI is not built. Run `npm run build`.")
    return FileResponse(f, media_type="text/html; charset=utf-8",
                        headers={"Cache-Control": "no-cache"})


@app.get("/assets/{path:path}")
async def web_asset(path: str):
    root = (WEB_DIST_DIR / "assets").resolve()
    asset = (root / path).resolve()
    try:
        asset.relative_to(root)
    except ValueError:
        raise HTTPException(404, "not found")
    if not asset.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(asset,
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/manifest.webmanifest")
async def web_manifest():
    return FileResponse(WEB_DIR / "manifest.webmanifest", media_type="application/manifest+json",
                        headers={"Cache-Control": "no-cache"})


@app.get("/sw.js")
async def service_worker():
    return FileResponse(WEB_DIR / "sw.js", media_type="text/javascript",
                        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


@app.get("/api/push/config", dependencies=[Auth])
async def push_config():
    return {"publicKey": push_notifications.public_key()}


@app.put("/api/push/subscriptions", dependencies=[Auth])
async def push_subscribe(payload: dict):
    try:
        subscription_id = push_notifications.subscribe(web_push.validate_subscription(payload))
    except ValueError as error:
        raise HTTPException(400, str(error))
    return {"id": subscription_id}


@app.delete("/api/push/subscriptions/{subscription_id}", dependencies=[Auth])
async def push_unsubscribe(subscription_id: str):
    push_notifications.unsubscribe(subscription_id)
    return {"ok": True}


@app.post("/api/push/presence", dependencies=[Auth])
async def push_presence(payload: dict):
    subscription_id = payload.get("subscriptionId")
    client_id = payload.get("clientId")
    revision = payload.get("revision")
    is_focused = payload.get("isFocused")
    if (not isinstance(subscription_id, str) or not re.fullmatch(r"[a-f0-9]{64}", subscription_id)
            or not isinstance(client_id, str) or not re.fullmatch(r"[a-f0-9-]{36}", client_id)
            or not isinstance(revision, int) or isinstance(revision, bool) or revision < 0
            or not isinstance(is_focused, bool)):
        raise HTTPException(400, "Invalid notification presence.")
    push_notifications.presence(subscription_id, client_id, revision, is_focused)
    return {"ok": True}


@app.get("/api/web-token")
async def web_token(request: Request):
    """웹 UI 부트스트랩: Access 를 통과한 브라우저에만 브리지 토큰을 내준다.

    헤더 문자열을 믿지 않고 `cf-access-jwt-assertion` 을 Cloudflare 공개키로 서명 검증한다.
    로컬(127.0.0.1)에서 직접 부르는 경우는 이미 이 맥 안이라 그대로 허용한다.
    """
    host = request.url.hostname or ""
    client_host = request.client.host if request.client else ""
    loopback_hosts = ("127.0.0.1", "localhost", "::1")
    if host in loopback_hosts and client_host in loopback_hosts:
        return _token_response(request, "loopback", None)

    assertion = request.headers.get("cf-access-jwt-assertion")
    if not assertion:
        raise HTTPException(401, "no Access assertion")
    try:
        email = await cfaccess.verify(
            _http, assertion, aud=config.ACCESS_AUD,
            allowed_emails=config.ACCESS_EMAILS, allowed_cns=config.ACCESS_SERVICE_CNS,
        )
    except (httpx.HTTPError, OSError, ValueError) as error:
        log.warning("Access verification unavailable: %s", error)
        raise HTTPException(503, "Access verification unavailable") from error
    if not email:
        raise HTTPException(403, "Access assertion rejected")
    log.info("web-token issued to %s", email)
    return _token_response(request, "cf-access", email)


@app.post("/api/auth", dependencies=[Auth])
async def api_auth(request: Request):
    """검증된 수동 bearer token 을 브라우저의 HttpOnly WebSocket 쿠키로 옮긴다."""
    return _token_response(request, "bearer", None)


def _token_response(request: Request, via: str, email: str | None) -> JSONResponse:
    body = {"token": config.BEARER, "via": via}
    if email:
        body["email"] = email
    r = JSONResponse(body, headers={"Cache-Control": "no-store"})
    r.set_cookie(
        COOKIE, config.BEARER,
        max_age=60 * 60 * 24 * 30, httponly=True, samesite="lax",
        secure=request.url.scheme == "https", path="/",
    )
    return r


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(WEB_DIR / "icons" / "favicon.ico",
                        headers={"Cache-Control": "public, max-age=86400"})


@app.get("/vendor/{name}")
async def vendor(name: str):
    """자체 호스팅 서드파티 자산(highlight.js). 런타임에 외부를 안 본다."""
    p = WEB_DIR / "vendor" / name
    if "/" in name or ".." in name or not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(p, media_type="image/svg+xml" if p.suffix == ".svg" else "application/javascript",
                        headers={"Cache-Control": "public, max-age=604800"})


@app.get("/icons/{name}")
async def icon(name: str):
    p = WEB_DIR / "icons" / name
    if "/" in name or ".." in name or not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(p, headers={"Cache-Control": "public, max-age=86400"})


# ------------------------------------------------------------------ 폰트
@app.get("/api/font/css/{font_id}")
async def font_css(font_id: str):
    """폰트 CSS. 폰트 파일 URL 은 브리지 경유로 치환되어 나간다 → 브라우저는 서드파티를 안 본다."""
    if font_id not in fonts.FAMILIES:
        raise HTTPException(404, "unknown font")
    try:
        text = await fonts.css(_http, font_id)
    except Exception as exc:
        log.warning("font css failed: %s", exc)
        raise HTTPException(502, "font fetch failed")
    return Response(text, media_type="text/css",
                    headers={"Cache-Control": "public, max-age=604800"})


@app.get("/api/font/file/{fid}")
async def font_file(fid: str):
    got = await fonts.file(_http, fid)
    if not got:
        raise HTTPException(404, "not found")
    data, ctype = got
    return Response(data, media_type=ctype,
                    headers={"Cache-Control": "public, max-age=31536000, immutable", "Access-Control-Allow-Origin": "*"})


# ------------------------------------------------------------------ 상태
def _windows_aside_app_running() -> bool:
    """True when the Aside *app* is running on Windows (not the CLI).

    stdlib ctypes (Toolhelp32 + QueryFullProcessImageNameW) — one health check
    doesn't justify a psutil dependency. Path-based because `aside` CLI
    processes share the image name with the app and must not count as
    "browser connected" (the bridge itself spawns the CLI constantly).
    """
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    TH32CS_SNAPPROCESS = 0x00000002
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        return False
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return False
        while True:
            # Image name alone can't tell app from CLI (tasklist even
            # normalizes case), so resolve the full path for aside.exe.
            if entry.szExeFile.lower() == "aside.exe":
                proc = kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION, False, entry.th32ProcessID)
                if proc:
                    try:
                        buf = ctypes.create_unicode_buffer(32768)
                        size = wintypes.DWORD(len(buf))
                        if kernel32.QueryFullProcessImageNameW(
                                proc, 0, buf, ctypes.byref(size)):
                            path = buf.value.lower().replace("/", "\\")
                            # App: ...\Aside\Application\Aside.exe
                            # CLI: ...\Aside\CLI\current\aside.exe
                            if path.endswith("\\application\\aside.exe"):
                                return True
                    finally:
                        kernel32.CloseHandle(proc)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                return False
    finally:
        kernel32.CloseHandle(snapshot)
    return False


def _aside_app_running() -> bool:
    try:
        if os.name == "nt":
            return _windows_aside_app_running()
        out = subprocess.run(["pgrep", "-f", "/Applications/Aside.app/Contents/MacOS/Aside"],
                             capture_output=True, timeout=5)
        return out.returncode == 0
    except Exception:
        return False


@app.get("/api/health")
async def health():
    daemon = None
    try:
        r = await _http.get(f"{config.DAEMON_URL}/health", timeout=5)
        daemon = r.json()
    except Exception as exc:
        daemon = {"error": str(exc)}
    return {
        "ok": True,
        "uptime": round(time.time() - STARTED_AT, 1),
        "daemon": daemon,
        "asideApp": _aside_app_running(),
        "mcp": {
            "alive": mcp.alive,
            "pwd": mcp.session_pwd,
            "restarts": mcp.restarts,
            "lastOk": mcp.last_ok,
        },
        "runningSessions": runner.running_ids(),
    }


@app.post("/api/aside/launch", dependencies=[Auth])
async def launch_aside():
    """Aside.app 이 꺼져 있으면 브라우저 툴이 전부 실패한다. 폰에서 깨울 수 있게."""
    if _aside_app_running():
        return {"ok": True, "already": True}
    if os.name == "nt":
        subprocess.Popen([config.ASIDE_APP])
    else:
        subprocess.Popen(["open", "-g", "-a", "Aside"])
    for _ in range(20):
        await asyncio.sleep(0.5)
        if _aside_app_running():
            return {"ok": True, "already": False}
    return JSONResponse({"ok": False, "error": "Could not launch Aside.app"}, status_code=503)


# ------------------------------------------------------------------ 세션
SESSION_RUNNING_MESSAGE = "Stop the run before deleting this conversation"


@app.get("/api/sessions", dependencies=[Auth])
async def api_sessions(
    limit: int = Query(30, ge=1, le=100),
    cursor: str | None = Query(None, description="Previous page's nextCursor, ordered by last message time and session ID"),
    q: str | None = Query(None, description="제목·미리보기 전체 검색 (로드된 페이지가 아니라 전 구간)"),
):
    return await sessions.list_sessions(_http, limit=limit, cursor=cursor, q=q)


@app.delete("/api/sessions/{session_id}", dependencies=[Auth])
async def api_delete_session(session_id: str):
    async with runner.session_lock:
        if not re.fullmatch(r"[A-Za-z0-9]{12,32}", session_id) or sessions.session_dir(session_id) is None:
            raise HTTPException(404, runner.SESSION_NOT_FOUND_MESSAGE)
        run = runner.get_run(session_id)
        if run and run.running:
            raise HTTPException(409, SESSION_RUNNING_MESSAGE)
        try:
            recents = await sessions.live_sessions()
        except (OSError, TimeoutError, RuntimeError):
            raise HTTPException(503, "Could not check the current Aside run status. Try again shortly.")
        if any(s.get("id") == session_id and s.get("status") == "running" for s in recents):
            raise HTTPException(409, SESSION_RUNNING_MESSAGE)
        try:
            is_deleted = await runner.delete_session(session_id)
        except TimeoutError:
            raise HTTPException(504, "The delete request timed out. Refresh the list to check the result.")
        except OSError:
            raise HTTPException(503, "Could not run the Aside CLI")
        if not is_deleted:
            raise HTTPException(502, "Aside could not delete the conversation. Refresh the list and try again.")
    await hub.forget_session(session_id)
    await followup_queue.clear(session_id)
    return {"deleted": True, "sessionId": session_id}


@app.get("/api/sessions/{session_id}/messages", dependencies=[Auth])
async def api_messages(session_id: str, tail: int = Query(400, ge=1, le=5000)):
    msgs, offset = sessions.read_messages(session_id, tail=tail)
    return {
        "sessionId": session_id,
        "messages": msgs,
        "offset": offset,
        "nextSeq": (msgs[-1]["seq"] + 1) if msgs else 0,
        "running": await _is_running(session_id),
    }


async def _is_running(session_id: str) -> bool:
    """브리지가 아는 실행 + 데몬이 보는 상태를 함께 본다."""
    run = runner.get_run(session_id)
    if run and run.running:
        return True
    return (await sessions.session_status(_http, session_id)) == "running"


@app.get("/api/sessions/{session_id}/status", dependencies=[Auth])
async def api_status(session_id: str):
    """가벼운 실행 여부 확인. run.done 을 놓쳤을 때 클라이언트가 스피너를 끄는 용도."""
    return {"sessionId": session_id, "running": await _is_running(session_id)}


def _with_attachments(payload: dict) -> str:
    """첨부가 있으면 프롬프트 앞에 경로 블록을 붙인다.

    `aside exec` 은 텍스트 프롬프트만 받는다 → 이미지는 "여기 있으니 읽어봐"로 전달하는 수밖에 없다.
    """
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise HTTPException(400, "invalid prompt")
    for name in ("model", "effort", "speed", "provider", "permission", "host"):
        value = payload.get(name)
        if value is not None and not isinstance(value, str):
            raise HTTPException(400, "invalid run options")
    if payload.get("mode", "default") not in ("default", "incognito"):
        raise HTTPException(400, "invalid conversation mode")
    project_id = payload.get("projectId")
    if project_id is not None and (not isinstance(project_id, str) or not project_id.strip()):
        raise HTTPException(400, "invalid project")
    prompt = prompt.strip()
    clean = [{"name": attachment["name"], "path": str(config.UPLOAD_DIR / attachment["id"])}
             for attachment in _validated_attachments(payload)]
    return (uploads.prompt_prefix(clean) + prompt) if clean else prompt


@app.post("/api/runs", dependencies=[Auth])
async def api_run(payload: dict):
    """새 실행. 절대 블로킹하지 않는다 — 세션 id 만 확정해서 즉시 반환."""
    prompt = _with_attachments(payload)
    if not prompt:
        raise HTTPException(400, "prompt required")
    try:
        run = await runner.start_run(
            prompt,
            model=payload.get("model"),
            effort=payload.get("effort"),
            speed=payload.get("speed"),
            provider=payload.get("provider"),
            permission=payload.get("permission"),
            host=payload.get("host"),
            incognito=payload.get("mode") == "incognito",
            project_id=payload.get("projectId"),
        )
    except Exception as exc:
        log.exception("conversation start failed")
        raise HTTPException(502, runner.safe_run_error(exc))
    if not run.session_id:
        raise HTTPException(502, runner.safe_run_error(run.error))
    hub.ensure_stream(run)
    asyncio.create_task(hub.watch_run(run))
    return JSONResponse({"sessionId": run.session_id, "runId": run.stream_id,
                         "running": run.running}, status_code=202)


@app.post("/api/sessions/{session_id}/messages", dependencies=[Auth])
async def api_continue(session_id: str, payload: dict):
    prompt = _with_attachments(payload)
    if not prompt:
        raise HTTPException(400, "prompt required")
    if sessions.session_dir(session_id) is None:
        raise HTTPException(404, "unknown session")
    existing = runner.get_run(session_id)
    if existing and existing.running:
        raise HTTPException(409, runner.RUN_ALREADY_RUNNING_MESSAGE)
    # `aside session resume` takes no model/effort/speed options — the session
    # keeps the settings it was created with.
    try:
        run = await runner.continue_run(session_id, prompt)
    except (FileNotFoundError, FileExistsError) as exc:
        log.exception("conversation continue failed session=%s", session_id)
        if str(exc) == runner.SESSION_NOT_FOUND_MESSAGE:
            raise HTTPException(404, runner.SESSION_NOT_FOUND_MESSAGE)
        if str(exc) == runner.RUN_ALREADY_RUNNING_MESSAGE:
            raise HTTPException(409, runner.RUN_ALREADY_RUNNING_MESSAGE)
        raise HTTPException(502, runner.safe_run_error(exc))
    except Exception as exc:
        log.exception("conversation continue failed session=%s", session_id)
        raise HTTPException(502, runner.safe_run_error(exc))
    hub.ensure_stream(run)
    asyncio.create_task(hub.watch_run(run))
    return JSONResponse({"sessionId": session_id, "runId": run.stream_id,
                         "running": run.running}, status_code=202)


@app.post("/api/sessions/{session_id}/abort", dependencies=[Auth])
async def api_abort(session_id: str):
    await followup_queue.pause(session_id)
    return {"aborted": await runner.abort(session_id)}


@app.get("/api/sessions/{session_id}/followups", dependencies=[Auth])
async def api_followups(session_id: str):
    _require_session(session_id)
    return await followup_queue.get(session_id)


@app.post("/api/sessions/{session_id}/followups", dependencies=[Auth])
async def api_followup_create(session_id: str, payload: dict):
    _require_session(session_id)
    item_id = _followup_id(payload.get("id"))
    item = _followup_content(payload)
    item["id"] = item_id
    delivery = payload.get("delivery", "queue")
    if delivery not in {"queue", "steer"}:
        raise HTTPException(400, "Invalid follow-up behavior.")
    state = await followup_queue.enqueue(session_id, item)
    if delivery == "steer" and any(queued["id"] == item_id for queued in state["items"]):
        return await followup_queue.steer(session_id, item_id, _deliver_steer)
    return state


@app.post("/api/sessions/{session_id}/followups/resume", dependencies=[Auth])
async def api_followup_resume(session_id: str):
    _require_session(session_id)
    if await sessions.session_status(_http, session_id) == "interrupted" and await native_followups.list(session_id):
        run = await runner.resume_queue(session_id)
        hub.ensure_stream(run)
        asyncio.create_task(hub.watch_run(run))
        await hub.broadcast(session_id, {"op": "run.started", "sessionId": session_id, "runId": run.stream_id})
    return await followup_queue.resume(session_id)


@app.patch("/api/sessions/{session_id}/followups/{item_id}", dependencies=[Auth])
async def api_followup_edit(session_id: str, item_id: str, payload: dict):
    _require_session(session_id)
    item_id = _followup_id(item_id)
    is_editing = payload.get("isEditing", False)
    if not isinstance(is_editing, bool):
        raise HTTPException(400, "isEditing must be a boolean")
    has_content = "prompt" in payload or "attachments" in payload
    if not has_content and "isEditing" not in payload:
        raise HTTPException(400, "message update required")
    update = None
    if has_content:
        update = {}
        if "prompt" in payload:
            if not isinstance(payload["prompt"], str):
                raise HTTPException(400, "invalid prompt")
            update["prompt"] = payload["prompt"].strip()
        if "attachments" in payload:
            update["attachments"] = _validated_attachments(payload)
    try:
        return await followup_queue.edit(session_id, item_id, update, is_editing)
    except followups.ItemNotFound:
        raise HTTPException(404, "Queued message not found")
    except followups.ItemSending:
        raise HTTPException(409, "This queued message is already being sent")
    except followups.EmptyItem:
        raise HTTPException(400, "prompt required")


@app.delete("/api/sessions/{session_id}/followups/{item_id}", dependencies=[Auth])
async def api_followup_delete(session_id: str, item_id: str):
    _require_session(session_id)
    item_id = _followup_id(item_id)
    try:
        return await followup_queue.delete(session_id, item_id)
    except followups.ItemNotFound:
        raise HTTPException(404, "Queued message not found")
    except followups.ItemSending:
        raise HTTPException(409, "This queued message is already being sent")


@app.post("/api/sessions/{session_id}/followups/{item_id}/steer", dependencies=[Auth])
async def api_followup_steer(session_id: str, item_id: str):
    _require_session(session_id)
    item_id = _followup_id(item_id)
    try:
        return await followup_queue.steer(session_id, item_id, _deliver_steer)
    except followups.ItemNotFound:
        raise HTTPException(404, "Queued message not found")
    except followups.ItemSending:
        raise HTTPException(409, "This queued message is already being sent")


def _require_session(session_id: str) -> None:
    if (not isinstance(session_id, str) or not re.fullmatch(r"[A-Za-z0-9]{12,32}", session_id)
            or sessions.session_dir(session_id) is None):
        raise HTTPException(404, runner.SESSION_NOT_FOUND_MESSAGE)


def _followup_id(value: object) -> str:
    if not isinstance(value, str):
        raise HTTPException(400, "valid message id required")
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        raise HTTPException(400, "valid message id required")
    if str(parsed) != value.lower():
        raise HTTPException(400, "valid message id required")
    return str(parsed)


def _followup_content(payload: dict) -> dict:
    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        prompt = ""
    prompt = prompt.strip()
    attachments = _validated_attachments(payload)
    if not prompt and not attachments:
        raise HTTPException(400, "prompt required")
    return {"prompt": prompt, "attachments": attachments}


def _validated_attachments(payload: dict) -> list[dict]:
    raw = payload.get("attachments", [])
    if not isinstance(raw, list):
        raise HTTPException(400, "invalid attachments")
    if len(raw) > 12:
        raise HTTPException(400, "Use no more than 12 attachments.")
    attachments = []
    for value in raw:
        if not isinstance(value, dict) or not isinstance(value.get("id"), str):
            raise HTTPException(400, "invalid attachment")
        attachment = uploads.metadata(value["id"], value.get("name"))
        if attachment is None:
            raise HTTPException(400, "attachment not found or unsupported")
        attachments.append(attachment)
    return attachments


# ------------------------------------------------------------------ 미디어
@app.get("/api/media/{media_id}", dependencies=[Auth])
async def api_media(media_id: str):
    p = sessions.media_path(media_id)
    if not p:
        raise HTTPException(404, "not found")
    return FileResponse(p, headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/api/sessions/{session_id}/file/{rel:path}", dependencies=[Auth])
async def api_session_file(session_id: str, rel: str):
    """에이전트가 답변에 박아 넣은 로컬 파일(스크린샷·긴 툴출력)을 폰에 내준다."""
    p = sessions.session_file(session_id, rel)
    if not p:
        raise HTTPException(404, "not found")
    return FileResponse(p, headers={"Cache-Control": "private", "X-Content-Type-Options": "nosniff",
                                   "Content-Security-Policy": "sandbox; default-src 'none'; img-src data:; style-src 'unsafe-inline'"})


# ------------------------------------------------------------------ 첨부
@app.post("/api/upload", dependencies=[Auth])
async def api_upload(request: Request):
    """이미지 원본 바이트를 그대로 받는다(멀티파트 파싱 의존성 없이).

    파일명은 X-Filename 헤더로 받는다. 저장 위치는 Aside 유저 루트 안이어야
    에이전트의 repl 이 읽을 수 있다 (uploads.py 주석 참조).
    """
    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > config.UPLOAD_MAX_BYTES:
            raise HTTPException(413, "File is too large.")
        chunks.append(chunk)
    raw = b"".join(chunks)
    if not raw:
        raise HTTPException(400, "empty body")
    if len(raw) > config.UPLOAD_MAX_BYTES:
        raise HTTPException(413, f"too large ({len(raw)}B)")
    name = request.headers.get("x-filename") or ""
    try:
        from urllib.parse import unquote
        name = unquote(name)
    except Exception:
        pass
    try:
        return uploads.save(raw, name)
    except ValueError as exc:
        raise HTTPException(415, str(exc))


@app.get("/api/upload/{fid}", dependencies=[Auth])
async def api_upload_get(fid: str):
    attachment = uploads.metadata(fid)
    p = uploads.path_of(fid)
    if not p or not attachment:
        raise HTTPException(404, "not found")
    is_active_content = attachment["mime"] in {"text/html", "image/svg+xml", "text/javascript", "application/javascript"}
    return FileResponse(p, media_type=attachment["mime"], filename=attachment["name"] if is_active_content else None,
                        headers={"Cache-Control": "private, max-age=31536000, immutable",
                                 "X-Content-Type-Options": "nosniff",
                                 "Content-Security-Policy": "sandbox; default-src 'none'"} if is_active_content else
                        {"Cache-Control": "private, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"})


# ------------------------------------------------------------------ 탭
@app.get("/api/tabs", dependencies=[Auth])
async def api_tabs(refresh: bool = False, session: str | None = None, all: bool = False):
    if session and sessions.session_dir(session) is None:
        raise HTTPException(404, "Conversation not found.")
    tabs = await browser.list_tabs(force=refresh, session_id=session, show_all=all)
    return {"count": len(tabs), "tabs": _public_tabs(tabs)}


def _public_tabs(tabs: list[dict]) -> list[dict]:
    fields = ("targetId", "title", "url", "favicon", "active", "loaded", "lastAccessed")
    return [{key: tab[key] for key in fields if key in tab} for tab in tabs]


@app.get("/api/tabs/{target_id}/shot", dependencies=[Auth])
async def api_tab_shot(target_id: str, full: bool = False, q: int = Query(62, ge=20, le=95),
                       fresh: bool = False, session: str | None = None, all: bool = False):
    if session:
        await browser.find_tab(target_id, session_id=session, show_all=all)
    path, _meta = await browser.screenshot(target_id, full=full, quality=q,
                                           max_age=0 if fresh else None, session_id=session, show_all=all)
    frame = await asyncio.to_thread(path.read_bytes)
    return Response(content=frame, media_type="image/jpeg",
                    headers={"Cache-Control": "no-cache"})


@app.get("/api/tabs/{target_id}/text", dependencies=[Auth])
async def api_tab_text(target_id: str, interactive: bool = False, session: str | None = None, all: bool = False):
    return await browser.tab_text(target_id, interactive=interactive, session_id=session, show_all=all)


@app.post("/api/tabs", dependencies=[Auth])
async def api_open_tab(payload: dict, session: str | None = None):
    url = payload.get("url")
    if not browser.is_web_url(url):
        raise HTTPException(400, "Use a full http:// or https:// address.")
    return await browser.open_tab(url.strip(), session_id=session)


@app.post("/api/tabs/{target_id}/focus", dependencies=[Auth])
async def api_focus(target_id: str, session: str | None = None, all: bool = False):
    return await browser.focus_tab(target_id, session_id=session, show_all=all)


@app.delete("/api/tabs/{target_id}", dependencies=[Auth])
async def api_close_tab(target_id: str, session: str | None = None, all: bool = False):
    return await browser.close_tab(target_id, session_id=session, show_all=all)


@app.post("/api/repl", dependencies=[Auth])
async def api_repl(payload: dict):
    """탈출구. 본인 전용이니까 남겨둔다."""
    code = payload.get("code")
    if not isinstance(code, str) or not code.strip():
        raise HTTPException(400, "code required")
    title = payload.get("title") or "Manual REPL"
    wrap = payload.get("wrap", True)
    if not isinstance(title, str) or not isinstance(wrap, bool):
        raise HTTPException(400, "invalid REPL options")
    out = await mcp.repl(code, title=title, wrap=wrap)
    return {"output": out}


# ------------------------------------------------------------------ WebSocket
class Hub:
    """세션별 tail 태스크를 소켓들이 공유한다."""

    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self._subs: dict[str, set[WebSocket]] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._subscription_locks: dict[str, asyncio.Lock] = {}
        self._stream_tasks: dict[str, asyncio.Task] = {}
        self._committed_assistants: dict[str, list[tuple[object, object]]] = {}

    async def subscribe(self, ws: WebSocket, session_id: str, from_seq: int, from_offset: int) -> None:
        is_dead = False
        lock = self._subscription_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            self._subs.setdefault(session_id, set()).add(ws)
            task = self._tasks.get(session_id)
            if task and not task.done():
                messages, offset = await asyncio.to_thread(sessions.read_messages, session_id)
                try:
                    for message in messages:
                        if message["seq"] >= from_seq:
                            await asyncio.wait_for(ws.send_text(json.dumps({
                                "op": "msg", "sessionId": session_id, "message": message,
                            }, ensure_ascii=False)), timeout=5)
                except Exception:
                    is_dead = True
                if task.done():
                    next_seq = messages[-1]["seq"] + 1 if messages else 0
                    self._tasks[session_id] = asyncio.create_task(
                        self._pump(session_id, offset, next_seq))
            else:
                self._tasks[session_id] = asyncio.create_task(
                    self._pump(session_id, from_offset, from_seq))
        if is_dead:
            self.unsubscribe(ws, session_id)

    def unsubscribe(self, ws: WebSocket, session_id: str | None = None) -> None:
        targets = [session_id] if session_id else list(self._subs)
        for sid in targets:
            subs = self._subs.get(sid)
            if not subs:
                continue
            subs.discard(ws)
            if not subs:
                task = self._tasks.pop(sid, None)
                if task:
                    task.cancel()
                self._subs.pop(sid, None)

    async def broadcast(self, session_id: str, payload: dict) -> None:
        dead = []
        lock = self._subscription_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            for ws in list(self._subs.get(session_id, ())):
                try:
                    await asyncio.wait_for(ws.send_text(json.dumps(payload, ensure_ascii=False)), timeout=5)
                except Exception:
                    dead.append(ws)
        for ws in dead:
            self.unsubscribe(ws)

    async def forget_session(self, session_id: str) -> None:
        for ws in list(self.clients):
            await _send(ws, {"op": "session.deleted", "sessionId": session_id})
        for ws in list(self._subs.get(session_id, ())):
            self.unsubscribe(ws, session_id)
        self._committed_assistants.pop(session_id, None)
        self._stream_tasks.pop(session_id, None)

    async def _pump(self, session_id: str, offset: int, seq: int) -> None:
        try:
            async for msg in sessions.tail_messages(session_id, offset, seq):
                if msg.get("role") in ("user", "assistant"):
                    sessions.invalidate_index()
                if msg.get("role") == "assistant":
                    committed = self._committed_assistants.setdefault(session_id, [])
                    committed.append((msg.get("ts"), msg.get("responseId")))
                    del committed[:-64]
                await self.broadcast(session_id, {"op": "msg", "sessionId": session_id,
                                                  "message": msg})
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("pump failed for %s", session_id)

    def _stream_is_committed(self, session_id: str, snapshot: dict) -> bool:
        message_ts = snapshot.get("messageTs")
        response_id = snapshot.get("responseId")
        return any(
            (message_ts is not None and message_ts == committed_ts)
            or (response_id is not None and response_id == committed_response_id)
            for committed_ts, committed_response_id in self._committed_assistants.get(session_id, ())
        )

    @staticmethod
    def _stream_payload(session_id: str, snapshot: dict) -> dict:
        payload = {"op": "msg.delta", "sessionId": session_id, **snapshot}
        text = payload.get("text")
        if isinstance(text, str):
            payload["text"] = sessions.rewrite_local_paths(text)
        return payload

    async def send_stream_snapshot(self, ws: WebSocket, session_id: str) -> None:
        run = runner.get_run(session_id)
        task = self._stream_tasks.get(session_id)
        if run and (task is None or task.done()):
            while not run.stream_queue.empty():
                try:
                    run.stream_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        snapshot = run.stream_snapshot if run else None
        if snapshot and not self._stream_is_committed(session_id, snapshot):
            await _send(ws, self._stream_payload(session_id, snapshot))

    def ensure_stream(self, run: "runner.Run") -> None:
        sid = run.session_id
        if not sid:
            return
        task = self._stream_tasks.get(sid)
        if task is None or task.done():
            self._stream_tasks[sid] = asyncio.create_task(self.watch_stream(run))

    async def watch_stream(self, run: "runner.Run") -> None:
        sid = run.session_id
        if not sid:
            return
        try:
            async for snapshot in runner.stream_events(run):
                if not self._stream_is_committed(sid, snapshot):
                    await self.broadcast(sid, self._stream_payload(sid, snapshot))
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("stream pump failed for %s", sid)

    async def watch_run(self, run: "runner.Run") -> None:
        """프로세스 종료를 기다렸다가 run.done 을 쏜다. jsonl 마지막 줄이 도착할 시간을 준다."""
        sid = run.session_id
        if not sid:
            return
        while run.running:
            await asyncio.sleep(0.4)
        await asyncio.sleep(config.JSONL_POLL_SEC * 3)
        sessions.invalidate_index()   # 목록 캐시(TTL 4s)를 기다리지 않고 즉시 반영
        payload = {
            "op": "run.done", "sessionId": sid, "runId": run.stream_id,
            "exitCode": run.exit_code,
        }
        if run.error or run.exit_code:
            payload["message"] = runner.safe_run_error(run.error or run.output)
        notifications = [push_ntfy(sid, run)]
        if not run.is_aborted:
            notifications.append(self._push_answer(sid, run))
        await asyncio.gather(self.broadcast(sid, payload), *notifications)
        log.info("run.done broadcast session=%s", sid)

    async def _push_answer(self, session_id: str, run: "runner.Run") -> None:
        try:
            deadline = time.monotonic() + 2
            while not run.stream_complete and time.monotonic() < deadline:
                await asyncio.sleep(0.05)
            snapshot = run.stream_snapshot
            text = sessions.rewrite_local_paths(snapshot["text"]) if snapshot and snapshot.get("done") is True else ""
            if not text:
                messages, _offset = await asyncio.to_thread(sessions.read_messages, session_id)
                text = next(("\n".join(block["text"] for block in message["blocks"] if block["type"] == "text")
                             for message in reversed(messages)
                             if message["role"] == "assistant" and message["seq"] >= run.canonical_start_seq
                             and type(message.get("ts")) in (int, float)
                             and message["ts"] <= run.finished_at * 1000), "")
            if not run.is_aborted:
                title = "New response"
                try:
                    session = await daemon.call("sessions.get", {"accountId": ACCOUNT_ID, "sessionId": session_id})
                    title = session.get("title") or title
                except Exception:
                    log.warning("notification title unavailable session=%s", session_id, exc_info=True)
                await push_notifications.complete(session_id, run.stream_id, text=text,
                                                  title=title,
                                                  has_error=bool(run.error or run.exit_code))
        except Exception:
            log.exception("Could not prepare response notification.")


async def push_ntfy(session_id: str, run: "runner.Run") -> None:
    """실행 완료 푸시. 실패해도 조용히 넘어간다 — 알림 때문에 본 기능이 막히면 안 된다.

    ntfy 는 헤더로도 받지만 HTTP 헤더는 latin-1 이라 한글 제목이 깨지거나 예외가 난다.
    루트 엔드포인트에 JSON 을 던지는 형식이 UTF-8 을 제대로 처리한다.
    """
    if not config.NTFY_ENABLED or not _http:
        return
    title = config.APP_NAME
    try:
        for s in (await sessions.list_sessions(_http, limit=20))["items"]:
            if s["id"] == session_id:
                title = s["title"] or title
                break
    except Exception:
        pass
    if run.error or run.exit_code:
        tail = runner.safe_run_error(run.error or run.output)
    else:
        body = [ln for ln in (run.output or "").strip().splitlines() if ln.strip()]
        tail = "\n".join(body[-6:])[:600] or "Complete"
    try:
        await _http.post(
            config.NTFY_URL,
            json={
                "topic": config.NTFY_TOPIC,
                "title": title[:120],
                "message": tail,
                "tags": ["white_check_mark"] if run.exit_code == 0 else ["x"],
            },
            timeout=10,
        )
    except Exception:
        log.warning("ntfy push failed", exc_info=True)


hub = Hub()


async def _queue_changed(session_id: str, state: dict) -> None:
    await hub.broadcast(session_id, {"op": "queue.changed", "sessionId": session_id, **state})


async def _queue_is_running(session_id: str) -> bool:
    run = runner.get_run(session_id)
    if run and run.running:
        return True
    status = await sessions.session_status(_http, session_id)
    if status is None:
        raise RuntimeError("Aside session status is unavailable")
    return status == "running"


async def _start_followup(session_id: str, item: dict, *, allow_paused: bool = False) -> bool:
    prompt = _with_attachments(item)
    if not prompt:
        return False
    next_seq, expected_text = await _ensure_acceptance_marker(session_id, item, prompt)
    if _has_user_message(session_id, next_seq, expected_text):
        return True
    async with followup_queue.launch(session_id, allow_paused=allow_paused):
        await asyncio.to_thread(daemondb.ensure_alive, session_id)
        try:
            run = await runner.continue_run(session_id, prompt)
        except FileExistsError as exc:
            if str(exc) == runner.RUN_ALREADY_RUNNING_MESSAGE:
                raise followups.RetryLater
            raise
        hub.ensure_stream(run)
        asyncio.create_task(hub.watch_run(run))
        await hub.broadcast(session_id, {
            "op": "run.started", "sessionId": session_id, "runId": run.stream_id,
        })
    return await _wait_for_user_message(session_id, next_seq, expected_text, run)


async def _ensure_acceptance_marker(session_id: str, item: dict,
                                    prompt: str) -> tuple[int, str]:
    expected_text = sessions.rewrite_local_paths(prompt).strip()
    next_seq = item.get("acceptanceSeq")
    if isinstance(next_seq, int):
        return next_seq, expected_text
    messages, _offset = sessions.read_messages(session_id)
    next_seq = messages[-1]["seq"] + 1 if messages else 0
    item_id = item.get("id")
    if isinstance(item_id, str):
        await followup_queue.set_acceptance(session_id, item_id, next_seq, expected_text)
        item["acceptanceSeq"] = next_seq
        item["acceptanceText"] = expected_text
    return next_seq, expected_text


def _has_user_message(session_id: str, next_seq: int, expected_text: str) -> bool:
    messages, _offset = sessions.read_messages(session_id)
    return any(
        message.get("role") == "user" and message.get("seq", -1) >= next_seq
        and "".join(block.get("text", "") for block in message.get("blocks", [])
                    if block.get("type") == "text").strip() == expected_text
        for message in messages
    )


async def _wait_for_user_message(session_id: str, next_seq: int, expected_text: str,
                                 run: "runner.Run") -> bool:
    while True:
        try:
            if _has_user_message(session_id, next_seq, expected_text):
                return True
        except OSError:
            pass
        if not run.running:
            break
        await asyncio.sleep(0.1)
    await asyncio.sleep(config.JSONL_POLL_SEC * 3)
    try:
        if _has_user_message(session_id, next_seq, expected_text):
            return True
    except OSError:
        pass
    return False


async def _deliver_steer(session_id: str, item: dict) -> bool:
    prompt = _with_attachments(item)
    if not prompt:
        return False
    await _ensure_acceptance_marker(session_id, item, prompt)
    if await _queue_is_running(session_id):
        if await runner.steer(session_id, prompt):
            return True
        if await _queue_is_running(session_id):
            return False
    try:
        return await _start_followup(session_id, item, allow_paused=True)
    except followups.RetryLater:
        return await runner.steer(session_id, prompt)


native_followups = native_queue.NativeQueue(_with_attachments)
followup_queue = followups.FollowupQueue(
    config.FOLLOWUPS_FILE,
    _queue_is_running,
    _start_followup,
    _queue_changed,
    native_followups,
)

_RUN_REQUEST_TTL_SEC = 10 * 60
_RUN_REQUEST_MAX = 256
_run_requests: dict[str, dict] = {}


def _prune_run_requests() -> None:
    cutoff = time.monotonic() - _RUN_REQUEST_TTL_SEC
    expired = [request_id for request_id, item in _run_requests.items()
               if item["status"] != "pending" and item["updatedAt"] < cutoff]
    for request_id in expired:
        _run_requests.pop(request_id, None)


def _begin_run_request(request_id: str) -> tuple[dict | None, bool]:
    _prune_run_requests()
    existing = _run_requests.get(request_id)
    if existing:
        return existing, False
    if len(_run_requests) >= _RUN_REQUEST_MAX:
        completed = sorted(
            ((item["updatedAt"], rid) for rid, item in _run_requests.items()
             if item["status"] != "pending"),
        )
        while len(_run_requests) >= _RUN_REQUEST_MAX and completed:
            _run_requests.pop(completed.pop(0)[1], None)
    if len(_run_requests) >= _RUN_REQUEST_MAX:
        return None, False
    item = {"status": "pending", "updatedAt": time.monotonic()}
    _run_requests[request_id] = item
    return item, True


def _finish_run_request(request_id: str, status: str, *, session_id: str | None = None,
                        run_id: str | None = None,
                        message: str | None = None) -> None:
    item = {"status": status, "updatedAt": time.monotonic()}
    if session_id:
        item["sessionId"] = session_id
    if run_id:
        item["runId"] = run_id
    if message:
        item["message"] = message
    _run_requests[request_id] = item


def _public_run_request(item: dict) -> dict:
    return {key: item[key] for key in ("status", "sessionId", "runId", "message") if key in item}


async def _send_run_request(ws: WebSocket, request_id: str, item: dict) -> None:
    status = item["status"]
    if status == "started":
        await _send(ws, {"op": "run.started", "requestId": request_id,
                         "sessionId": item["sessionId"], "runId": item["runId"]})
    elif status == "error":
        await _send(ws, {"op": "error", "requestId": request_id,
                         "message": item["message"]})
    else:
        await _send(ws, {"op": "run.pending", "requestId": request_id})


async def _claim_run_request(ws: WebSocket, request_id) -> tuple[str | None, bool]:
    if request_id is None:
        return None, True
    if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id):
        await _send(ws, {"op": "error", "requestId": request_id,
                         "message": "Invalid requestId"})
        return None, False
    item, is_new = _begin_run_request(request_id)
    if item is None:
        await _send(ws, {"op": "error", "requestId": request_id,
                         "message": "Too many run requests are pending. Try again shortly."})
        return None, False
    if not is_new:
        await _send_run_request(ws, request_id, item)
        return request_id, False
    return request_id, True


@app.get("/api/run-requests/{request_id}", dependencies=[Auth])
async def api_run_request(request_id: str):
    _prune_run_requests()
    item = _run_requests.get(request_id)
    if not item:
        raise HTTPException(404, "Unknown or expired run request")
    return _public_run_request(item)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    if config.BEARER:
        header = ws.headers.get("authorization", "")
        has_bearer = header.lower().startswith("bearer ")
        supplied = header[7:].strip() if has_bearer else ws.cookies.get(COOKIE, "")
        origin = ws.headers.get("origin")
        host = ws.headers.get("host", "")
        is_origin_allowed = True
        if not has_bearer and origin:
            try:
                is_origin_allowed = urlsplit(origin).netloc.lower() == host.lower()
            except ValueError:
                is_origin_allowed = False
        if not _is_valid_token(supplied) or not is_origin_allowed:
            await ws.close(code=4401)
            return
    await ws.accept()
    hub.clients.add(ws)
    hb = asyncio.create_task(_heartbeat(ws))
    try:
        await ws.send_text(json.dumps({"op": "hello", "running": runner.running_ids()}))
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(msg, dict):
                await _send(ws, {"op": "error", "message": "Invalid message"})
                continue
            try:
                await _handle_ws(ws, msg)
            except HTTPException as error:
                request_id = msg.get("requestId")
                pending = _run_requests.get(request_id) if isinstance(request_id, str) else None
                if msg.get("op") in ("run", "continue") and pending and pending["status"] == "pending":
                    _finish_run_request(request_id, "error", message=str(error.detail))
                await _send(ws, {"op": "error", "requestId": request_id, "message": error.detail})
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws error")
    finally:
        hb.cancel()
        hub.clients.discard(ws)
        hub.unsubscribe(ws)
        with contextlib.suppress(Exception):
            await ws.close()


async def _heartbeat(ws: WebSocket) -> None:
    """CF Free/Pro 는 100초 무통신이면 WS 를 끊는다. 20초마다 살아있다고 알린다."""
    try:
        while True:
            await asyncio.sleep(config.WS_HEARTBEAT_SEC)
            await ws.send_text(json.dumps({"op": "ping", "t": int(time.time())}))
    except (asyncio.CancelledError, Exception):
        return


async def _send(ws: WebSocket, payload: dict) -> None:
    with contextlib.suppress(Exception):
        await ws.send_text(json.dumps(payload, ensure_ascii=False))


async def _handle_ws(ws: WebSocket, msg: dict) -> None:
    op = msg.get("op")
    rid = msg.get("requestId")

    if op in ("pong", "ping"):
        return

    if op == "sub":
        sid = msg.get("sessionId")
        _require_session(sid)
        from_seq, from_offset = msg.get("fromSeq", 0), msg.get("fromOffset", 0)
        if any(type(value) is not int or value < 0 for value in (from_seq, from_offset)):
            raise HTTPException(400, "Invalid subscription position")
        await hub.subscribe(ws, sid, from_seq, from_offset)
        await _send(ws, {"op": "sub.ok", "sessionId": sid, "requestId": rid})
        await hub.send_stream_snapshot(ws, sid)
        run = runner.get_run(sid)
        if run:
            hub.ensure_stream(run)
        return

    if op == "unsub":
        sid = msg.get("sessionId")
        if sid is not None and not isinstance(sid, str):
            raise HTTPException(400, "Invalid sessionId")
        hub.unsubscribe(ws, sid)
        return

    if op == "run":
        run_request_id, should_execute = await _claim_run_request(ws, rid)
        if not should_execute:
            return
        prompt = _with_attachments(msg)
        if not prompt:
            message = "prompt required"
            if run_request_id:
                _finish_run_request(run_request_id, "error", message=message)
            await _send(ws, {"op": "error", "requestId": rid, "message": message})
            return
        try:
            run = await runner.start_run(prompt, model=msg.get("model"),
                                         effort=msg.get("effort"), speed=msg.get("speed"),
                                         provider=msg.get("provider"),
                                         permission=msg.get("permission"),
                                         host=msg.get("host"),
                                         incognito=msg.get("mode") == "incognito",
                                         project_id=msg.get("projectId"))
        except Exception as exc:
            log.exception("websocket conversation start failed")
            message = runner.safe_run_error(exc)
            if run_request_id:
                _finish_run_request(run_request_id, "error", message=message)
            await _send(ws, {"op": "error", "requestId": rid, "message": message})
            return
        if not run.session_id:
            message = runner.safe_run_error(run.error)
            if run_request_id:
                _finish_run_request(run_request_id, "error", message=message)
            await _send(ws, {"op": "error", "requestId": rid,
                             "message": message})
            return
        if run_request_id:
            _finish_run_request(run_request_id, "started", session_id=run.session_id,
                                run_id=run.stream_id)
        await hub.subscribe(ws, run.session_id, 0, 0)
        await _send(ws, {"op": "run.started", "requestId": rid,
                         "sessionId": run.session_id, "runId": run.stream_id})
        hub.ensure_stream(run)
        asyncio.create_task(hub.watch_run(run))
        return

    if op == "continue":
        run_request_id, should_execute = await _claim_run_request(ws, rid)
        if not should_execute:
            return
        sid = msg.get("sessionId")
        _require_session(sid)
        prompt = _with_attachments(msg)
        if not sid or not prompt:
            message = "sessionId/prompt required"
            if run_request_id:
                _finish_run_request(run_request_id, "error", message=message)
            await _send(ws, {"op": "error", "requestId": rid, "message": message})
            return
        existing = runner.get_run(sid)
        if existing and existing.running:
            message = runner.RUN_ALREADY_RUNNING_MESSAGE
            if run_request_id:
                _finish_run_request(run_request_id, "error", message=message)
            await _send(ws, {"op": "error", "requestId": rid,
                             "message": message})
            return
        # 데몬이 퍼지한 세션이면(재시작으로 잊음) 레지스트리 행을 재삽입해 되살린다.
        try:
            await asyncio.to_thread(daemondb.ensure_alive, sid)
            _msgs, offset = sessions.read_messages(sid)
            await hub.subscribe(ws, sid, len(_msgs), offset)
            run = await runner.continue_run(sid, prompt)
        except Exception as exc:
            log.exception("websocket conversation continue failed session=%s", sid)
            message = runner.safe_run_error(exc)
            if run_request_id:
                _finish_run_request(run_request_id, "error", message=message)
            await _send(ws, {"op": "error", "requestId": rid, "message": message})
            return
        if run_request_id:
            _finish_run_request(run_request_id, "started", session_id=sid,
                                run_id=run.stream_id)
        await _send(ws, {"op": "run.started", "requestId": rid,
                         "sessionId": sid, "runId": run.stream_id})
        hub.ensure_stream(run)
        asyncio.create_task(hub.watch_run(run))
        return

    if op == "abort":
        sid = msg.get("sessionId")
        if sid is not None:
            _require_session(sid)
            await followup_queue.pause(sid)
        await _send(ws, {"op": "abort.ok", "requestId": rid,
                         "aborted": (await runner.abort(sid)) if sid else False})
        return

    if op == "tabs":
        try:
            tabs = await browser.list_tabs(force=bool(msg.get("refresh")))
        except Exception as exc:
            log.exception("websocket browser tab listing failed")
            await _send(ws, {"op": "error", "requestId": rid,
                             "message": runner.safe_run_error(exc)})
            return
        await _send(ws, {"op": "tabs", "requestId": rid, "count": len(tabs), "tabs": _public_tabs(tabs)})
        return

    await _send(ws, {"op": "error", "requestId": rid, "message": f"unknown op: {op}"})


# ------------------------------------------------------------------ SPA 셸
# 클라이언트 라우팅용. 반드시 "맨 마지막"에 등록해야 한다 — FastAPI 는 선언 순서로
# 매칭하므로, 위에 두면 /api/* 를 전부 삼킨다.
# 느슨한 catch-all 대신 화이트리스트를 쓴다. /api 오타가 200 HTML 로 돌아오면
# 디버깅이 괴로워진다 — 없는 주소는 정직하게 404 여야 한다.
_SPA_PATHS = re.compile(r"tabs|settings|workspace|files|c/[A-Za-z0-9_-]{1,64}")


@app.get("/{path:path}")
async def spa_shell(path: str):
    if not _SPA_PATHS.fullmatch(path):
        raise HTTPException(404, "not found")
    return await web_index()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="info",
                ws_ping_interval=None, ws_ping_timeout=None)
