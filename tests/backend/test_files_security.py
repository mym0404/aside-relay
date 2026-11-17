import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.backend import support
from fastapi import FastAPI
from fastapi.testclient import TestClient

import config
import native_files
import sessions

needs_symlinks = unittest.skipUnless(
    support.SYMLINKS_SUPPORTED,
    "symlink fixtures unavailable (Windows without Developer Mode/admin)",
)


class FilesSecurityTest(support.IsolatedBackendTest):
    def setUp(self):
        super().setUp()
        self.sessions_root = self.root / "sessions"
        self.uploads_root = self.root / "uploads"
        self.media_root = self.root / "media"
        for directory in (self.sessions_root, self.uploads_root, self.media_root):
            directory.mkdir()
        self.enterContext(patch.object(config, "SESSIONS_DIR", self.sessions_root))
        self.enterContext(patch.object(config, "UPLOAD_DIR", self.uploads_root))
        self.enterContext(patch.object(config, "MEDIA_DIR", self.media_root))
        sessions._dir_index = {}
        sessions._dir_index_at = 0
        sessions._index = []
        sessions._index_at = 0
        sessions._activity.clear()
        sessions._meta.clear()
        self.session_dir = self.sessions_root / f"20261011_{support.SESSION_ID}"
        self.session_dir.mkdir()
        app = FastAPI()
        app.include_router(native_files.router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    @needs_symlinks
    async def test_browse_only_exposes_visible_scoped_entries(self):
        (self.uploads_root / "notes.txt").write_text("hello")
        (self.uploads_root / ".env").write_text("secret")
        outside = self.root / "outside.txt"
        outside.write_text("outside")
        (self.uploads_root / "escape.txt").symlink_to(outside)

        roots = self.client.get("/api/native/files/roots")
        response = self.client.get("/api/native/files/browse", params={"root": "uploads"})

        self.assertEqual(roots.status_code, 200)
        self.assertEqual([(item["id"], item["path"]) for item in roots.json()["items"]], [
            ("uploads", str(self.uploads_root)),
        ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.json()["items"]], ["notes.txt"])
        self.assertEqual(response.json()["items"][0]["mime"], "text/plain")
        for path in ("../outside.txt", "/etc", "folder\\file"):
            denied = self.client.get("/api/native/files/browse", params={"root": "uploads", "path": path})
            self.assertIn(denied.status_code, (400, 404))
        self.assertEqual(self.client.get("/api/native/files/browse", params={"root": "unknown"}).status_code, 404)

    async def test_artifact_lifecycle_and_preview_headers(self):
        artifacts = self.session_dir / "artifacts"
        output = self.session_dir / "output"
        artifacts.mkdir()
        output.mkdir()
        (artifacts / "table.csv").write_text("name,value\nalpha,1\n")
        (artifacts / "page.html").write_text("<script>top.location='https://example.com'</script>")
        (output / "readme.ts").write_text("export const answer = 42\n")

        listing = self.client.get(f"/api/native/files/sessions/{support.SESSION_ID}/artifacts")
        self.assertEqual(listing.status_code, 200)
        paths = {item["path"]: item for item in listing.json()["items"]}
        self.assertEqual(set(paths), {"artifacts/page.html", "artifacts/table.csv", "output/readme.ts"})
        self.assertEqual(paths["artifacts/table.csv"]["kind"], "csv")
        self.assertEqual(paths["output/readme.ts"]["mime"], "text/typescript")

        preview = self.client.get(
            f"/api/native/files/sessions/{support.SESSION_ID}/artifact-preview",
            params={"path": "artifacts/table.csv"},
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["content"], "name,value\nalpha,1\n")

        html = self.client.get(
            f"/api/native/files/sessions/{support.SESSION_ID}/artifacts/artifacts/page.html"
        )
        self.assertEqual(html.status_code, 200)
        self.assertIn("sandbox", html.headers["content-security-policy"])
        self.assertEqual(html.headers["x-content-type-options"], "nosniff")

        renamed = self.client.patch(
            f"/api/native/files/sessions/{support.SESSION_ID}/artifacts/artifacts/table.csv",
            json={"name": "renamed.csv"},
        )
        self.assertEqual(renamed.status_code, 200)
        self.assertTrue((artifacts / "renamed.csv").is_file())
        deleted = self.client.delete(
            f"/api/native/files/sessions/{support.SESSION_ID}/artifacts/artifacts/renamed.csv"
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse((artifacts / "renamed.csv").exists())

    @needs_symlinks
    async def test_artifact_traversal_and_symlink_roots_are_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("do not expose")
        (self.session_dir / "artifacts").symlink_to(outside, target_is_directory=True)

        listing = self.client.get(f"/api/native/files/sessions/{support.SESSION_ID}/artifacts")
        self.assertEqual(listing.status_code, 404)
        traversal = self.client.get(
            f"/api/native/files/sessions/{support.SESSION_ID}/artifact-preview",
            params={"path": "artifacts/../../outside/secret.txt"},
        )
        self.assertIn(traversal.status_code, (400, 404))

    @needs_symlinks
    async def test_nested_symlink_and_hidden_parent_never_enter_artifact_listing(self):
        artifacts = self.session_dir / "artifacts"
        artifacts.mkdir()
        visible = artifacts / "visible"
        visible.mkdir()
        (visible / "note.txt").write_text("safe")
        hidden = artifacts / ".private"
        hidden.mkdir()
        (hidden / "secret.txt").write_text("hidden")
        (artifacts / "alias").symlink_to(visible, target_is_directory=True)

        response = self.client.get(f"/api/native/files/sessions/{support.SESSION_ID}/artifacts")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["path"] for item in response.json()["items"]], ["artifacts/visible/note.txt"])
        alias = self.client.get(
            f"/api/native/files/sessions/{support.SESSION_ID}/artifacts/artifacts/alias/note.txt"
        )
        self.assertEqual(alias.status_code, 404)

    @needs_symlinks
    async def test_session_and_media_file_helpers_reject_symlinks(self):
        safe_file = self.session_dir / "safe.txt"
        safe_file.write_text("safe")
        outside = self.root / "outside.txt"
        outside.write_text("outside")
        (self.session_dir / "escape.txt").symlink_to(outside)
        (self.media_root / "safe.png").write_bytes(b"png")
        (self.media_root / "escape.png").symlink_to(outside)

        self.assertEqual(sessions.session_file(support.SESSION_ID, "safe.txt"), safe_file.resolve())
        self.assertIsNone(sessions.session_file(support.SESSION_ID, "escape.txt"))
        self.assertIsNone(sessions.session_file(support.SESSION_ID, "../outside.txt"))
        self.assertEqual(sessions.media_path("safe.png"), (self.media_root / "safe.png").resolve())
        self.assertIsNone(sessions.media_path("escape.png"))

    @needs_symlinks
    async def test_session_listing_does_not_read_symlinked_logs(self):
        good_log = self.session_dir / "messages.jsonl"
        good_log.write_text(json.dumps({"timestamp": 1, "type": "user", "content": "safe"}) + "\n")
        outside = self.root / "external-session"
        outside.mkdir()
        (outside / "messages.jsonl").write_text(
            json.dumps({"timestamp": 9999999999, "type": "user", "content": "external secret"}) + "\n"
        )
        evil_id = "TESTSESSION000002"
        (self.sessions_root / f"20261011_{evil_id}").symlink_to(outside, target_is_directory=True)
        self.native_call.return_value = [
            {"id": support.SESSION_ID, "title": "Safe", "status": "idle"},
            {"id": evil_id, "title": "Native title", "status": "idle"},
        ]
        self.native_call.side_effect = None

        result = await sessions.list_sessions(None)

        by_id = {item["id"]: item for item in result["items"]}
        self.assertTrue(by_id[support.SESSION_ID]["hasLog"])
        self.assertFalse(by_id[evil_id]["hasLog"])
        self.assertNotIn("external secret", json.dumps(result))


if __name__ == "__main__":
    import unittest
    unittest.main()
