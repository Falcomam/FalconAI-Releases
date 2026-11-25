"""Safe browser-preview tests: no generic file, URL or command launching."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import developer_workspace as dev
import website_preview as preview


class WebsitePreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / "projects"
        website = {
            "name": "lostfalcon_site", "kind": "website",
            "files": {"index.html": (
                "<!DOCTYPE html><html><head><meta charset="UTF-8"><title>LostFalcon</title>"
                "</head><body><main><h1>Hi</h1></main></body></html>"),
                "README.md": "Local preview"},
        }
        dev.save_approved(website, dev.review_proposal(website)["fingerprint"],
                          workspace=self.workspace)
        code = {"name": "python_tool", "kind": "python",
                "files": {"main.py": "print('test')", "README.md": "test"}}
        dev.save_approved(code, dev.review_proposal(code)["fingerprint"],
                          workspace=self.workspace)

    def test_preview_opens_exact_saved_index_without_approval(self):
        open_browser = Mock(return_value=True)
        url = preview.open_website("lostfalcon_site", workspace=self.workspace,
                                   opener=open_browser)
        self.assertTrue(url.startswith("file:///"))
        self.assertTrue(url.endswith("/lostfalcon_site/index.html"))
        open_browser.assert_called_once_with(url, new=2)

    def test_nonwebsite_and_traversal_rejected_before_browser(self):
        open_browser = Mock(return_value=True)
        for name in ("python_tool", "../escape", "https://example.com",
                     "lostfalcon_site/index.html", "missing"):
            with self.subTest(name=name), self.assertRaises(dev.ProjectError):
                preview.open_website(name, workspace=self.workspace, opener=open_browser)
        open_browser.assert_not_called()

    def test_missing_index_and_browser_failure(self):
        target = self.workspace / "lostfalcon_site/index.html"
        original = target.read_text(encoding="utf-8")
        target.unlink()
        with self.assertRaises(dev.ProjectError):
            preview.preview_url("lostfalcon_site", workspace=self.workspace)
        target.write_text(original, encoding="utf-8")
        with self.assertRaisesRegex(dev.ProjectError, "Default browser"):
            preview.open_website("lostfalcon_site", workspace=self.workspace,
                                 opener=Mock(return_value=False))

    def test_symlink_index_refused(self):
        target = self.workspace / "lostfalcon_site/index.html"
        target.unlink()
        outside = Path(self.tmp.name) / "outside.html"
        outside.write_text("<html>outside</html>", encoding="utf-8")
        try:
            target.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks not available")
        opener = Mock(return_value=True)
        with self.assertRaises(dev.ProjectError):
            preview.open_website("lostfalcon_site", workspace=self.workspace,
                                 opener=opener)
        opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
