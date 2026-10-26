"""Contract tests for the allowlisted native session bridge."""
from tests.backend import support

import copy
from unittest.mock import patch

from daemon import ACCOUNT_ID


SESSION_ID = support.SESSION_ID


class NativeSessionContractTests(support.IsolatedBackendTest):
    def setUp(self):
        super().setUp()
        self.session = {
            "id": SESSION_ID,
            "title": "Native chat",
            "status": "idle",
            "model": {
                "provider": "aside",
                "modelId": "gpt-test",
                "thinkingLevel": "low",
                "fastMode": False,
            },
            "projectId": "project-one",
            "browserBinding": {"profile": "test-profile"},
            "permissionMode": "default",
            "runtimeConfig": {
                "memoryExtractionDisabled": False,
                "proactiveMode": False,
                "finalConfirm": False,
                "workingDirs": [],
                "apiKey": "must-not-leak",
            },
            "incognito": False,
            "toolState": {
                "todo": {"todos": [{"id": "todo-1", "content": "Check", "status": "pending"}]},
                "subagent": {"subagents": [{"sessionId": "CHILDSESSION001", "isRunning": True}]},
            },
            "queuedMessages": [],
            "steeringMessages": [],
            "privateCredential": "must-not-leak",
        }

    def stub(self, responses):
        calls = []

        async def dispatch(procedure, value, *, mutation=False):
            calls.append((procedure, value, mutation))
            response = responses[procedure]
            if callable(response):
                response = response(value, mutation)
            if isinstance(response, Exception):
                raise response
            return copy.deepcopy(response)

        self.native_call.side_effect = dispatch
        return calls

    async def test_list_filters_search_cursor_pin_and_projects_contract(self):
        preview = {
            "id": SESSION_ID,
            "title": "Pinned result",
            "status": "running",
            "pinned": True,
            "projectId": "project-one",
            "unread": False,
        }
        calls = self.stub({
            "sessions.listPreviewItems": [
                {**preview, "id": f"TESTSESSION{i:06d}"} for i in range(17)
            ],
            "projects.list": [{"id": "project-one", "name": "One"}],
        })
        async with support.api_client() as client:
            response = await client.get(
                "/api/native/sessions",
                params=[
                    ("limit", "17"), ("cursor", "34"), ("q", " historical text "),
                    ("archived", "only"), ("parent", "all"),
                    ("projectId", "project-one"), ("projectId", "project-two"),
                    ("status", "running"), ("status", "suspended"), ("sort", "oldest"),
                ],
            )
            projects = await client.get("/api/native/projects")

        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertTrue(item["pinned"])
        self.assertEqual(item["statusLabel"], "Running")
        self.assertIsNone(item["suspensionKind"])
        self.assertEqual(response.json()["nextCursor"], 51)
        self.assertEqual(projects.json(), {"items": [{"id": "project-one", "name": "One"}]})
        self.assertEqual(calls[0], (
            "sessions.listPreviewItems",
            {
                "accountId": ACCOUNT_ID,
                "limit": 17,
                "cursor": 34,
                "order": "asc",
                "parent": "all",
                "archived": "only",
                "ephemeral": "exclude",
                "routines": "exclude",
                "coders": "exclude",
                "q": "historical text",
                "projectIds": ["project-one", "project-two"],
                "statuses": ["running", "suspended"],
            },
            False,
        ))
        self.assertEqual(calls[1], ("projects.list", {"accountId": ACCOUNT_ID}, False))

    async def test_list_rejects_invalid_filters_before_native_call(self):
        async with support.api_client() as client:
            invalid_status = await client.get("/api/native/sessions", params={"status": "unknown"})
            invalid_archive = await client.get("/api/native/sessions", params={"archived": "trash"})
            invalid_cursor = await client.get("/api/native/sessions", params={"cursor": -1})
        self.assertEqual(
            [invalid_status.status_code, invalid_archive.status_code, invalid_cursor.status_code],
            [400, 422, 422],
        )
        self.native_call.assert_not_awaited()

    async def test_detail_filters_private_fields_and_brief_skips_heavy_calls(self):
        preview = {
            "id": SESSION_ID,
            "status": "suspended",
            "unread": True,
            "waiting": True,
            "pinned": True,
            "projectId": "project-two",
        }
        calls = self.stub({
            "sessions.get": self.session,
            "sessions.childSessions": [{"id": "CHILDSESSION001", "trigger": {"type": "sidechat"}}],
            "sessions.files.list": ["/tmp/output.png"],
            "sessions.listPreviewItems": [preview],
            "sessions.listRuns": [{"id": "run-1"}],
            "sessions.messageRows": [{"id": "message-1", "role": "user"}],
        })
        async with support.api_client() as client:
            full = await client.get(f"/api/native/sessions/{SESSION_ID}")
            brief = await client.get(f"/api/native/sessions/{SESSION_ID}", params={"brief": "true"})

        self.assertEqual(full.status_code, 200)
        body = full.json()
        self.assertNotIn("runtimeConfig", body["session"])
        self.assertNotIn("browserBinding", body["session"])
        self.assertNotIn("privateCredential", body["session"])
        self.assertEqual(body["session"]["projectId"], "project-two")
        self.assertTrue(body["session"]["pinned"])
        self.assertEqual(body["todos"][0]["id"], "todo-1")
        self.assertEqual(body["subagents"][0]["sessionId"], "CHILDSESSION001")
        self.assertEqual(body["outputs"], ["/tmp/output.png"])
        self.assertEqual(body["runs"], [{"id": "run-1"}])
        self.assertEqual(body["messageRows"][0]["id"], "message-1")
        self.assertEqual(brief.json()["runs"], [])
        self.assertEqual(brief.json()["messageRows"], [])
        procedures = [procedure for procedure, _, _ in calls]
        self.assertEqual(procedures.count("sessions.listRuns"), 1)
        self.assertEqual(procedures.count("sessions.messageRows"), 1)

    async def test_read_archive_share_and_unarchive_mutations(self):
        action_procedures = {
            "read": "sessions.markRead",
            "unread": "sessions.markUnread",
            "archive": "sessions.archive",
            "unarchive": "sessions.unarchive",
            "share": "sessions.share",
        }
        for action, procedure in action_procedures.items():
            with self.subTest(action=action):
                calls = self.stub({"sessions.get": self.session, procedure: {"ok": action}})
                async with support.api_client() as client:
                    response = await client.post(f"/api/native/sessions/{SESSION_ID}/{action}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"result": {"ok": action}})
                self.assertEqual(calls, [
                    ("sessions.get", {"accountId": ACCOUNT_ID, "sessionId": SESSION_ID}, False),
                    (procedure, {"accountId": ACCOUNT_ID, "sessionId": SESSION_ID}, True),
                ])

    async def test_metadata_pin_and_move_to_project_contract(self):
        calls = self.stub({
            "sessions.get": self.session,
            "sessions.update": {"title": "Renamed", "pinned": True},
            "sessions.moveToProject": {"projectId": "project-two"},
        })
        async with support.api_client() as client:
            response = await client.patch(
                f"/api/native/sessions/{SESSION_ID}",
                json={"title": "  Renamed  ", "pinned": True, "projectId": "project-two"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls[1], (
            "sessions.update",
            {"accountId": ACCOUNT_ID, "sessionId": SESSION_ID, "title": "Renamed", "pinned": True},
            True,
        ))
        self.assertEqual(calls[2], (
            "sessions.moveToProject",
            {"accountId": ACCOUNT_ID, "sessionId": SESSION_ID, "projectId": "project-two"},
            True,
        ))

    async def test_message_sequence_maps_to_native_ids_for_edit_and_branch(self):
        messages = [
            {"seq": 4, "role": "user", "ts": 1000},
            {"seq": 8, "role": "assistant", "ts": 2000},
        ]
        rows = [
            {"id": "native-user", "role": "user", "timestamp": 1000},
            {"id": "native-assistant", "role": "assistant", "timestamp": 2000},
        ]
        calls = self.stub({
            "sessions.get": self.session,
            "sessions.messageRows": rows,
            "sessions.editUserMessage": {"edited": True},
            "sessions.branch": {"id": "BRANCHSESSION001"},
        })
        with patch("native_sessions.sessions.read_messages", return_value=(messages, 222)):
            async with support.api_client() as client:
                edited = await client.post(
                    f"/api/native/sessions/{SESSION_ID}/command",
                    json={"command": "edit-user-message", "seq": 4, "content": "  revised  "},
                )
                branched = await client.post(
                    f"/api/native/sessions/{SESSION_ID}/command",
                    json={"command": "branch", "seq": 8},
                )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(branched.status_code, 200)
        self.assertIn((
            "sessions.editUserMessage",
            {
                "accountId": ACCOUNT_ID,
                "sessionId": SESSION_ID,
                "messageId": "native-user",
                "content": "revised",
            },
            True,
        ), calls)
        self.assertIn((
            "sessions.branch",
            {"accountId": ACCOUNT_ID, "sessionId": SESSION_ID, "messageId": "native-assistant"},
            True,
        ), calls)

    async def test_sidechat_uses_native_selection_metadata_and_parent_settings(self):
        calls = self.stub({
            "sessions.get": self.session,
            "sessions.createAndPrompt": {"id": "SIDECHATSESSION1"},
        })
        with (
            patch("native_sessions.time.time", return_value=1234.5),
            patch("native_sessions.uuid.uuid4", side_effect=["attachment-id", "request-key"]),
        ):
            async with support.api_client() as client:
                response = await client.post(
                    f"/api/native/sessions/{SESSION_ID}/command",
                    json={"command": "sidechat", "prompt": "  Explain this  ", "quote": "  selected text  "},
                )
        self.assertEqual(response.json(), {"result": {"id": "SIDECHATSESSION1"}})
        payload = calls[1][1]
        self.assertEqual(calls[1][0], "sessions.createAndPrompt")
        self.assertTrue(calls[1][2])
        self.assertEqual(payload["parentId"], SESSION_ID)
        self.assertEqual(payload["trigger"], {"type": "sidechat"})
        self.assertEqual(payload["projectId"], self.session["projectId"])
        self.assertEqual(payload["browserBinding"], self.session["browserBinding"])
        self.assertEqual(payload["model"], self.session["model"])
        self.assertEqual(payload["permissionMode"], self.session["permissionMode"])
        self.assertEqual(payload["runtimeConfig"], self.session["runtimeConfig"])
        metadata, message = payload["message"]
        self.assertEqual(metadata["role"], "user-message-metadata")
        self.assertEqual(metadata["timestamp"], 1234499)
        self.assertEqual(metadata["attachments"], [{
            "id": "attachment-id",
            "type": "selection",
            "name": "selected text",
            "selectionKind": "text",
            "text": "selected text",
            "sourceKind": "chat",
            "requestKey": "chat:request-key",
        }])
        self.assertEqual(message, {"role": "user", "content": "Explain this", "timestamp": 1234500})

    async def test_suspension_response_contracts_and_child_approval_policy(self):
        cases = [
            (
                "approval", {"verdict": "allow", "always": True}, {},
                {"verdict": "allow", "always": True}, True,
            ),
            (
                "approval", {"verdict": "allow", "always": True}, {"source": {"taskId": "agent-1"}},
                {"verdict": "allow", "always": False}, True,
            ),
            (
                "action-confirmation", {"verdict": "cancel", "instruction": "  use another file  "}, {},
                {"verdict": "cancel", "instruction": "use another file"}, True,
            ),
            (
                "ask-user-question", {"answers": [{"header": " Color ", "answer": " Blue "}]}, {},
                {"answers": [{"header": "Color", "answer": "Blue"}]}, False,
            ),
        ]
        for kind, response_body, request, expected_response, has_suspension_id in cases:
            with self.subTest(kind=kind, request=request):
                session = {
                    **self.session,
                    "suspension": {
                        "id": "suspension-1",
                        "kind": kind,
                        "toolCallId": "tool-1",
                        "request": request,
                    },
                }
                calls = self.stub({"sessions.get": session, "sessions.resolveSuspension": {"status": "running"}})
                async with support.api_client() as client:
                    response = await client.post(
                        f"/api/native/sessions/{SESSION_ID}/command",
                        json={"command": "resolve-suspension", "response": response_body},
                    )
                self.assertEqual(response.status_code, 200)
                payload = calls[1][1]
                self.assertEqual(payload["response"], expected_response)
                self.assertEqual("suspensionId" in payload, has_suspension_id)
                self.assertEqual(payload["toolCallId"], "tool-1")

    async def test_cancel_question_interrupts_and_invalid_state_does_not_mutate(self):
        waiting = {
            **self.session,
            "suspension": {"kind": "ask-user-question", "toolCallId": "tool-1"},
        }
        calls = self.stub({"sessions.get": waiting, "sessions.interrupt": {"status": "interrupted"}})
        async with support.api_client() as client:
            response = await client.post(
                f"/api/native/sessions/{SESSION_ID}/command", json={"command": "cancel-question"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls[1], (
            "sessions.interrupt",
            {"accountId": ACCOUNT_ID, "sessionId": SESSION_ID},
            True,
        ))

        calls = self.stub({"sessions.get": self.session})
        async with support.api_client() as client:
            rejected = await client.post(
                f"/api/native/sessions/{SESSION_ID}/command", json={"command": "cancel-question"},
            )
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(len(calls), 1)

    async def test_incognito_requires_empty_conversation(self):
        calls = self.stub({"sessions.get": self.session, "sessions.update": {"incognito": True}})
        with patch("native_sessions.sessions.read_messages", return_value=([], 0)):
            async with support.api_client() as client:
                response = await client.post(
                    f"/api/native/sessions/{SESSION_ID}/command",
                    json={"command": "set-incognito", "incognito": True},
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls[1], (
            "sessions.update",
            {"accountId": ACCOUNT_ID, "sessionId": SESSION_ID, "incognito": True},
            True,
        ))

        calls = self.stub({"sessions.get": self.session})
        with patch(
            "native_sessions.sessions.read_messages",
            return_value=([{"role": "user", "seq": 0, "ts": 1}], 1),
        ):
            async with support.api_client() as client:
                rejected = await client.post(
                    f"/api/native/sessions/{SESSION_ID}/command",
                    json={"command": "set-incognito", "incognito": True},
                )
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(len(calls), 1)

    async def test_clear_messages_and_compact_commands(self):
        calls = self.stub({"sessions.get": self.session, "sessions.clearMessages": {"ok": True}})
        async with support.api_client() as client:
            response = await client.post(
                f"/api/native/sessions/{SESSION_ID}/command", json={"command": "clear-messages"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls[1], (
            "sessions.clearMessages",
            {"accountId": ACCOUNT_ID, "sessionId": SESSION_ID},
            True,
        ))

        calls = self.stub({"sessions.get": self.session, "sessions.compact": {"ok": True}})
        async with support.api_client() as client:
            response = await client.post(
                f"/api/native/sessions/{SESSION_ID}/command",
                json={"command": "compact", "instructions": " Keep decisions "},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls[1], (
            "sessions.compact",
            {"accountId": ACCOUNT_ID, "sessionId": SESSION_ID, "instructions": "Keep decisions"},
            True,
        ))

    async def test_command_validation_rejects_unsupported_and_malformed_payloads(self):
        cases = [
            ({"command": "unknown"}, 400),
            ({"command": "sidechat", "prompt": "", "quote": "text"}, 400),
            ({"command": "branch", "messageId": "missing"}, 400),
            ({"command": "resolve-suspension", "response": {"verdict": "allow"}}, 409),
            ({"command": "clear-messages", "extra": True}, 400),
            ({"command": "compact", "instructions": ""}, 400),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload):
                responses = {"sessions.get": self.session, "sessions.messageRows": []}
                calls = self.stub(responses)
                async with support.api_client() as client:
                    response = await client.post(
                        f"/api/native/sessions/{SESSION_ID}/command", json=payload,
                    )
                self.assertEqual(response.status_code, expected)
                self.assertFalse(any(mutation for _, _, mutation in calls))
