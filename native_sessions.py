"""Validated HTTP access to Aside's native session procedures."""
from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid

import httpx
from fastapi import APIRouter, HTTPException, Query

import sessions
from daemon import ACCOUNT_ID, daemon

log = logging.getLogger("aside-relay.native-sessions")

router = APIRouter(prefix="/api/native/sessions")
projects_router = APIRouter(prefix="/api/native/projects")

_SESSION_ID_RE = re.compile(r"[A-Za-z0-9]{12,32}")
_SESSION_FIELDS = (
    "id", "title", "status", "createdAt", "updatedAt", "readAt", "model",
    "projectId", "parentId", "trigger", "incognito", "ephemeral", "permissionMode",
    "queuedMessages", "steeringMessages", "toolState", "suspension", "transcriptRevision",
    "unread", "waiting", "pinned", "archivedAt",
)


def _require_session_id(session_id: str) -> None:
    if not _SESSION_ID_RE.fullmatch(session_id):
        raise HTTPException(404, "Unknown conversation.")


async def _call(procedure: str, value: dict, *, mutation: bool = False):
    try:
        return await daemon.call(procedure, value, mutation=mutation)
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        if status == 404:
            raise HTTPException(404, "Unknown conversation.") from error
        if status == 400:
            raise HTTPException(409, "Aside rejected the request in its current state.") from error
        log.exception("native session call failed procedure=%s", procedure)
        raise HTTPException(502, "Aside could not complete the request.") from error
    except (ConnectionError, TimeoutError, httpx.HTTPError) as error:
        log.exception("native session call failed procedure=%s", procedure)
        raise HTTPException(502, "Aside could not complete the request.") from error


async def _get_session(session_id: str) -> dict:
    _require_session_id(session_id)
    value = await _call("sessions.get", {
        "accountId": ACCOUNT_ID,
        "sessionId": session_id,
    })
    if not isinstance(value, dict):
        raise HTTPException(502, "Aside returned an invalid conversation.")
    return value


@router.get("")
async def list_native_sessions(
    limit: int = Query(50, ge=1, le=200),
    cursor: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=300),
    archived: str = Query("exclude", pattern="^(exclude|include|only)$"),
    parent: str = Query("root", pattern="^(root|all)$"),
    project_id: list[str] | None = Query(None, alias="projectId"),
    status: list[str] | None = Query(None),
    sort: str = Query("newest", pattern="^(newest|oldest)$"),
):
    if project_id and any(not item or len(item) > 128 for item in project_id):
        raise HTTPException(400, "Invalid project filter.")
    if status and any(item not in {"idle", "running", "suspended", "interrupted", "errored"}
                      for item in status):
        raise HTTPException(400, "Invalid status filter.")
    return await sessions.native_session_previews(
        limit=limit,
        cursor=cursor,
        q=q.strip() if q and q.strip() else None,
        archived=archived,
        parent=parent,
        project_ids=project_id,
        statuses=status,
        order="desc" if sort == "newest" else "asc",
    )


@projects_router.get("")
async def list_native_projects():
    return {"items": await sessions.native_projects()}


@router.get("/{session_id}")
async def get_native_session(session_id: str, brief: bool = Query(False)):
    session = await _get_session(session_id)
    tasks = [
        sessions.native_child_sessions(session_id),
        _call("sessions.files.list", {"accountId": ACCOUNT_ID, "sessionId": session_id}),
        _call("sessions.listPreviewItems", {
            "accountId": ACCOUNT_ID,
            "sessionIds": [session_id],
            "limit": 1,
            "archived": "include",
        }),
    ]
    if not brief:
        tasks.extend((
            _call("sessions.listRuns", {"accountId": ACCOUNT_ID, "sessionId": session_id}),
            _call("sessions.messageRows", {"accountId": ACCOUNT_ID, "sessionId": session_id}),
        ))
    pending = [asyncio.create_task(task) for task in tasks]
    try:
        results = await asyncio.gather(*pending)
    except BaseException:
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        raise
    children, outputs, preview_items = results[:3]
    runs, message_rows = results[3:] if not brief else ([], [])
    if isinstance(preview_items, list) and preview_items:
        session = {**session, **{
            key: preview_items[0][key]
            for key in ("unread", "waiting", "pinned", "projectId", "status", "updatedAt", "archivedAt")
            if key in preview_items[0]
        }}
    tool_state = session.get("toolState") if isinstance(session.get("toolState"), dict) else {}
    todo_state = tool_state.get("todo") if isinstance(tool_state.get("todo"), dict) else {}
    subagent_state = tool_state.get("subagent") if isinstance(tool_state.get("subagent"), dict) else {}
    return {
        "session": {key: session[key] for key in _SESSION_FIELDS if key in session},
        "suspension": session.get("suspension"),
        "children": children,
        "todos": todo_state.get("todos") if isinstance(todo_state.get("todos"), list) else [],
        "subagents": subagent_state.get("subagents")
        if isinstance(subagent_state.get("subagents"), list) else [],
        "outputs": outputs if isinstance(outputs, list) else [],
        "runs": runs if isinstance(runs, list) else [],
        "messageRows": message_rows if isinstance(message_rows, list) else [],
    }


@router.post("/{session_id}/read")
async def mark_native_session_read(session_id: str):
    await _get_session(session_id)
    result = await _call("sessions.markRead", {
        "accountId": ACCOUNT_ID,
        "sessionId": session_id,
    }, mutation=True)
    return {"result": result}


@router.post("/{session_id}/unread")
async def mark_native_session_unread(session_id: str):
    await _get_session(session_id)
    result = await _call("sessions.markUnread", {
        "accountId": ACCOUNT_ID,
        "sessionId": session_id,
    }, mutation=True)
    return {"result": result}


@router.post("/{session_id}/archive")
async def archive_native_session(session_id: str):
    await _get_session(session_id)
    result = await _call("sessions.archive", {
        "accountId": ACCOUNT_ID,
        "sessionId": session_id,
    }, mutation=True)
    return {"result": result}


@router.post("/{session_id}/unarchive")
async def unarchive_native_session(session_id: str):
    await _get_session(session_id)
    result = await _call("sessions.unarchive", {
        "accountId": ACCOUNT_ID,
        "sessionId": session_id,
    }, mutation=True)
    return {"result": result}


@router.post("/{session_id}/share")
async def share_native_session(session_id: str):
    await _get_session(session_id)
    result = await _call("sessions.share", {
        "accountId": ACCOUNT_ID,
        "sessionId": session_id,
    }, mutation=True)
    return {"result": result}


@router.patch("/{session_id}")
async def update_native_session(session_id: str, payload: dict):
    await _get_session(session_id)
    if not payload or not set(payload).issubset({"title", "pinned", "projectId"}):
        raise HTTPException(400, "Invalid conversation settings.")
    project_id = payload.get("projectId")
    if "projectId" in payload and (project_id is not None and (
            not isinstance(project_id, str) or not project_id or len(project_id) > 128)):
        raise HTTPException(400, "Invalid project.")
    update = {"accountId": ACCOUNT_ID, "sessionId": session_id}
    if "title" in payload:
        title = payload["title"]
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 120:
            raise HTTPException(400, "Use a conversation name between 1 and 120 characters.")
        update["title"] = title.strip()
    if "pinned" in payload:
        if not isinstance(payload["pinned"], bool):
            raise HTTPException(400, "Invalid pin setting.")
        update["pinned"] = payload["pinned"]
    result = None
    if len(update) > 2:
        result = await _call("sessions.update", update, mutation=True)
    if "projectId" in payload:
        result = await _call("sessions.moveToProject", {
            "accountId": ACCOUNT_ID,
            "sessionId": session_id,
            "projectId": project_id,
        }, mutation=True)
    return {"result": result}


@router.post("/{session_id}/command")
async def command_native_session(session_id: str, payload: dict):
    session = await _get_session(session_id)
    command = payload.get("command")
    if command == "resolve-suspension":
        result = await _resolve_suspension(session, payload)
    elif command == "cancel-question":
        result = await _cancel_question(session, payload)
    elif command in ("branch", "edit-user-message"):
        result = await _message_command(session_id, command, payload)
    elif command == "set-incognito":
        result = await _set_incognito(session, payload)
    elif command == "sidechat":
        result = await _create_sidechat(session, payload)
    elif command == "clear-messages":
        result = await _clear_messages(session_id, payload)
    elif command == "compact":
        result = await _compact_session(session_id, payload)
    else:
        raise HTTPException(400, "Unsupported conversation command.")
    return {"result": result}


async def _resolve_suspension(session: dict, payload: dict):
    if set(payload) != {"command", "response"} or not isinstance(payload.get("response"), dict):
        raise HTTPException(400, "Invalid suspension response.")
    suspension = session.get("suspension")
    if not isinstance(suspension, dict):
        raise HTTPException(409, "This conversation is not waiting for a response.")
    kind = suspension.get("kind")
    response = payload["response"]
    if kind == "approval":
        if not set(response).issubset({"verdict", "always"}) or response.get("verdict") not in ("allow", "deny"):
            raise HTTPException(400, "Invalid approval response.")
        if "always" in response and not isinstance(response["always"], bool):
            raise HTTPException(400, "Invalid approval response.")
        request = suspension.get("request") if isinstance(suspension.get("request"), dict) else {}
        source = request.get("source") if isinstance(request.get("source"), dict) else {}
        response = {
            "verdict": response["verdict"],
            "always": False if source.get("taskId") else bool(response.get("always", False)),
        }
    elif kind == "action-confirmation":
        if not set(response).issubset({"verdict", "instruction"}) or response.get("verdict") not in ("confirm", "cancel"):
            raise HTTPException(400, "Invalid confirmation response.")
        instruction = response.get("instruction")
        if instruction is not None and (not isinstance(instruction, str) or not instruction.strip()
                                        or len(instruction) > 10_000):
            raise HTTPException(400, "Invalid confirmation instruction.")
        response = {"verdict": response["verdict"]}
        if instruction is not None:
            response["instruction"] = instruction.strip()
    elif kind == "ask-user-question":
        if (set(response) != {"answers"} or not isinstance(response["answers"], list)
                or not response["answers"] or len(response["answers"]) > 20):
            raise HTTPException(400, "Invalid question response.")
        answers = []
        for answer in response["answers"]:
            if not isinstance(answer, dict) or set(answer) != {"header", "answer"}:
                raise HTTPException(400, "Invalid question response.")
            if not all(isinstance(answer[key], str) and answer[key].strip()
                       and len(answer[key]) <= 10_000 for key in ("header", "answer")):
                raise HTTPException(400, "Invalid question response.")
            answers.append({"header": answer["header"].strip(), "answer": answer["answer"].strip()})
        response = {"answers": answers}
    else:
        raise HTTPException(409, "This response type is not supported.")
    tool_call_id = suspension.get("toolCallId")
    if not isinstance(tool_call_id, str) or not tool_call_id:
        raise HTTPException(502, "Aside returned an invalid suspension.")
    value = {
        "accountId": ACCOUNT_ID,
        "sessionId": session["id"],
        "toolCallId": tool_call_id,
        "response": response,
    }
    if kind != "ask-user-question":
        suspension_id = suspension.get("id")
        if not isinstance(suspension_id, str) or not suspension_id:
            raise HTTPException(502, "Aside returned an invalid suspension.")
        value["suspensionId"] = suspension_id
    return await _call("sessions.resolveSuspension", value, mutation=True)


async def _cancel_question(session: dict, payload: dict):
    if set(payload) != {"command"}:
        raise HTTPException(400, "Invalid question command.")
    suspension = session.get("suspension")
    if not isinstance(suspension, dict) or suspension.get("kind") != "ask-user-question":
        raise HTTPException(409, "This conversation is not waiting for an answer.")
    return await _call("sessions.interrupt", {
        "accountId": ACCOUNT_ID,
        "sessionId": session["id"],
    }, mutation=True)


async def _message_command(session_id: str, command: str, payload: dict):
    allowed = {"command", "messageId", "seq", "content"}
    if not set(payload).issubset(allowed):
        raise HTTPException(400, "Invalid message command.")
    rows = await _call("sessions.messageRows", {
        "accountId": ACCOUNT_ID,
        "sessionId": session_id,
    })
    message_id = payload.get("messageId")
    row = next((item for item in rows if item.get("id") == message_id), None) if isinstance(message_id, str) else None
    if row is None and isinstance(payload.get("seq"), int):
        messages, _ = await asyncio.to_thread(sessions.read_messages, session_id)
        message = next((item for item in messages if item.get("seq") == payload["seq"]), None)
        if message:
            role = "user" if message.get("role") == "user" else "assistant"
            row = next((item for item in rows if item.get("role") == role
                        and item.get("timestamp") == message.get("ts")), None)
    expected_role = "assistant" if command == "branch" else "user"
    if not isinstance(row, dict) or row.get("role") != expected_role:
        raise HTTPException(400, "The message cannot be used for this command.")
    if command == "branch":
        return await _call("sessions.branch", {
            "accountId": ACCOUNT_ID,
            "sessionId": session_id,
            "messageId": row["id"],
        }, mutation=True)
    content = payload.get("content")
    if not isinstance(content, str) or not content.strip() or len(content) > 100_000:
        raise HTTPException(400, "Use a message between 1 and 100,000 characters.")
    return await _call("sessions.editUserMessage", {
        "accountId": ACCOUNT_ID,
        "sessionId": session_id,
        "messageId": row["id"],
        "content": content.strip(),
    }, mutation=True)


async def _set_incognito(session: dict, payload: dict):
    if set(payload) != {"command", "incognito"} or not isinstance(payload.get("incognito"), bool):
        raise HTTPException(400, "Invalid incognito setting.")
    messages, _ = await asyncio.to_thread(sessions.read_messages, session["id"])
    if any(message.get("role") in ("user", "assistant") for message in messages):
        raise HTTPException(409, "Incognito mode can only change before the first message.")
    return await _call("sessions.update", {
        "accountId": ACCOUNT_ID,
        "sessionId": session["id"],
        "incognito": payload["incognito"],
    }, mutation=True)


async def _create_sidechat(session: dict, payload: dict):
    if set(payload) != {"command", "prompt", "quote"}:
        raise HTTPException(400, "Invalid side chat command.")
    prompt = payload.get("prompt")
    quote = payload.get("quote")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 100_000:
        raise HTTPException(400, "Use a prompt between 1 and 100,000 characters.")
    if not isinstance(quote, str) or not quote.strip() or len(quote) > 100_000:
        raise HTTPException(400, "Use a quote between 1 and 100,000 characters.")
    model = session.get("model")
    runtime_config = session.get("runtimeConfig")
    permission_mode = session.get("permissionMode")
    if not isinstance(model, dict) or not isinstance(runtime_config, dict) or not isinstance(permission_mode, str):
        raise HTTPException(409, "This conversation cannot start a side chat.")
    quote = quote.strip()
    normalized_name = " ".join(quote.split())
    name = normalized_name if len(normalized_name) <= 72 else f"{normalized_name[:69].rstrip()}..."
    attachment_id = str(uuid.uuid4())
    timestamp = int(time.time() * 1000)
    message = [
        {
            "role": "user-message-metadata",
            "attachments": [{
                "id": attachment_id,
                "type": "selection",
                "name": name or "Selected text",
                "selectionKind": "text",
                "text": quote,
                "sourceKind": "chat",
                "requestKey": f"chat:{uuid.uuid4()}",
            }],
            "timestamp": timestamp - 1,
        },
        {"role": "user", "content": prompt.strip(), "timestamp": timestamp},
    ]
    return await _call("sessions.createAndPrompt", {
        "accountId": ACCOUNT_ID,
        "projectId": session.get("projectId"),
        "browserBinding": session.get("browserBinding"),
        "model": model,
        "permissionMode": permission_mode,
        "runtimeConfig": runtime_config,
        "incognito": bool(session.get("incognito")),
        "parentId": session["id"],
        "trigger": {"type": "sidechat"},
        "message": message,
    }, mutation=True)


async def _clear_messages(session_id: str, payload: dict):
    if set(payload) != {"command"}:
        raise HTTPException(400, "Invalid clear command.")
    return await _call("sessions.clearMessages", {
        "accountId": ACCOUNT_ID,
        "sessionId": session_id,
    }, mutation=True)


async def _compact_session(session_id: str, payload: dict):
    allowed = {"command", "instructions"}
    if not set(payload).issubset(allowed) or "command" not in payload:
        raise HTTPException(400, "Invalid compact command.")
    instructions = payload.get("instructions")
    if instructions is not None and (
            not isinstance(instructions, str) or not instructions.strip() or len(instructions) > 10_000):
        raise HTTPException(400, "Use compact instructions between 1 and 10,000 characters.")
    request = {"accountId": ACCOUNT_ID, "sessionId": session_id}
    if isinstance(instructions, str):
        request["instructions"] = instructions.strip()
    return await _call("sessions.compact", request, mutation=True)
