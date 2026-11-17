import hashlib
import io
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tests.backend import support
from fastapi.testclient import TestClient

import config
import server
import uploads

needs_symlinks = unittest.skipUnless(
    support.SYMLINKS_SUPPORTED,
    "symlink fixtures unavailable (Windows without Developer Mode/admin)",
)


class UploadsTest(support.IsolatedBackendTest):
    def setUp(self):
        super().setUp()
        self.uploads_root = self.root / "uploads"
        self.uploads_root.mkdir()
        self.enterContext(patch.object(config, "UPLOAD_DIR", self.uploads_root))
        self.client = TestClient(server.app)
        self.addCleanup(self.client.close)
        self.auth = {"Authorization": f"Bearer {support.TEST_TOKEN}"}

    async def test_sniff_uses_file_content_and_code_extension(self):
        samples = [
            (b"\xff\xd8\xffbody", "photo.txt", ("image/jpeg", "jpg")),
            (b"%PDF-1.7\n%%EOF", "wrong.png", ("application/pdf", "pdf")),
            (b"\x1aE\xdf\xa3body", "clip.bin", ("video/webm", "webm")),
            (b"\x00\x00\x00\x18ftypisombody", "clip.mov", ("video/mp4", "mp4")),
            (b"\x00\x00\x00\x18ftypqt  body", "clip.mp4", ("video/quicktime", "mov")),
            (b"export const answer = 42\n", "source.ts", ("text/typescript", "ts")),
        ]
        for raw, name, expected in samples:
            with self.subTest(name=name):
                self.assertEqual(uploads.sniff(raw, name), expected)
        self.assertIsNone(uploads.sniff(b"RIFFxxxxNOTW", "fake.webp"))
        self.assertIsNone(uploads.sniff(b"\xff\xfe\x00", "fake.ts"))
        self.assertIsNone(uploads.sniff(b"arbitrary binary", "file.bin"))

    async def test_office_archives_require_expected_package_markers(self):
        def archive(*names: str) -> bytes:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as output:
                for name in names:
                    output.writestr(name, "content")
            return buffer.getvalue()

        docx = archive("[Content_Types].xml", "word/document.xml")
        random_zip = archive("word/document.xml")

        self.assertEqual(
            uploads.sniff(docx, "document.docx"),
            ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
        )
        self.assertIsNone(uploads.sniff(random_zip, "document.docx"))

    async def test_save_is_bounded_deduplicated_and_metadata_is_canonical(self):
        raw = b"console.log('safe')\n"
        first = uploads.save(raw, "folder/source.js")
        second = uploads.save(raw, "folder/source.js")

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(list(self.uploads_root.iterdir())), 1)
        self.assertEqual(uploads.metadata(first["id"], "renamed.ts")["mime"], "text/typescript")
        self.assertEqual(first["name"], "folder/source.js")
        with patch.object(config, "UPLOAD_MAX_BYTES", len(raw) - 1):
            with self.assertRaises(ValueError):
                uploads.save(raw, "source.js")

    @needs_symlinks
    async def test_save_rejects_candidate_and_root_symlink_writes(self):
        raw = b"hello\n"
        fid = f"{hashlib.sha256(raw).hexdigest()[:16]}.txt"
        outside = self.root / "outside.txt"
        outside.write_bytes(b"unchanged")
        (self.uploads_root / fid).symlink_to(outside)

        with self.assertRaises(ValueError):
            uploads.save(raw, "message.txt")
        self.assertEqual(outside.read_bytes(), b"unchanged")

        linked_root = self.root / "linked-uploads"
        linked_root.symlink_to(self.root, target_is_directory=True)
        escaped_content = b"root escape\n"
        with patch.object(config, "UPLOAD_DIR", linked_root):
            with self.assertRaises(ValueError):
                uploads.save(escaped_content, "message.txt")
        escaped_name = f"{hashlib.sha256(escaped_content).hexdigest()[:16]}.txt"
        self.assertFalse((self.root / escaped_name).exists())

    async def test_upload_api_serves_active_content_as_attachment(self):
        uploaded = self.client.post(
            "/api/upload",
            headers={**self.auth, "X-Filename": "page.html"},
            content=b"<script>top.location='https://example.com'</script>",
        )
        self.assertEqual(uploaded.status_code, 200, uploaded.text)

        response = self.client.get(f"/api/upload/{uploaded.json()['id']}", headers=self.auth)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertIn("sandbox", response.headers["content-security-policy"])
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertEqual(response.headers["content-type"].split(";")[0], "text/html")

    async def test_upload_api_rejects_oversized_and_unsupported_content(self):
        with patch.object(config, "UPLOAD_MAX_BYTES", 4):
            oversized = self.client.post(
                "/api/upload", headers={**self.auth, "X-Filename": "note.txt"}, content=b"12345"
            )
        unsupported = self.client.post(
            "/api/upload", headers={**self.auth, "X-Filename": "payload.bin"}, content=b"binary"
        )

        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(unsupported.status_code, 415)


if __name__ == "__main__":
    import unittest
    unittest.main()
