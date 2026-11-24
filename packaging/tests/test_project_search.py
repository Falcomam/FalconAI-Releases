"""Safety and functionality of saved-project source search."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import developer_workspace as dev
import project_browser as browser
import project_search as source_search


class ProjectSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "developer_projects"
        p = {
            "name": "falcon_search", "kind": "python",
            "files": {
                "main.py": "# TODO: improve Falcon search\nprint('Falcon ready')\n",
                "src/helper.py": "# Falcon helper\nVALUE = '🦅'\n",
                "README.md": "This is a Falcon project\n",
            },
        }
        dev.save_approved(p, dev.review_proposal(p)["fingerprint"], workspace=self.root)
        self.saved = self.root / "falcon_search"
        self.snapshot = browser.open_saved_project("falcon_search", workspace=self.root)

    def find(self, needle, **kwargs):
        return source_search.find_source(
            "falcon_search", needle, self.snapshot["fingerprint"],
            workspace=self.root, **kwargs)

    def test_find_ordered_files_lines_and_unicode(self):
        r = self.find("falcon")
        self.assertEqual([(x["path"], x["line"]) for x in r["matches"]],
                         [("README.md", 1), ("main.py", 1),
                          ("main.py", 2), ("src/helper.py", 1)])
        self.assertFalse(r["limited"])
        emoji = self.find("🦅")
        self.assertEqual(emoji["matches"][0]["line"], 2)
        self.assertEqual(emoji["matches"][0]["path"], "src/helper.py")

    def test_no_match_and_result_limit(self):
        self.assertEqual(self.find("no-such-string")["matches"], ())
        limited = self.find("falcon", max_matches=2)
        self.assertEqual(len(limited["matches"]), 2)
        self.assertTrue(limited["limited"])

    def test_stale_disk_content_is_not_searched(self):
        (self.saved / "main.py").write_text("print('changed')\n", encoding="utf-8")
        with self.assertRaisesRegex(dev.ProjectError, "changed"):
            self.find("falcon")
        self.assertEqual((self.saved / "main.py").read_text(), "print('changed')\n")

    def test_search_cannot_choose_other_directories(self):
        outside = Path(self.temp.name) / "outside.py"
        outside.write_text("secret-value")
        with self.assertRaises(dev.ProjectError):
            source_search.find_source("../outside", "secret", self.snapshot["fingerprint"],
                                      workspace=self.root)
        self.assertFalse(any("secret" in result["excerpt"]
                             for result in self.find("falcon")["matches"]))

    def test_bad_query_and_fingerprint_are_rejected(self):
        for needle in ("", " ", "x", "a" * 81, "a\nb", "a\rb", "a\x00b"):
            with self.subTest(needle=needle), self.assertRaises(dev.ProjectError):
                self.find(needle)
        for fingerprint in ("", None, "a" * 20):
            with self.assertRaises(dev.ProjectError):
                source_search.find_source("falcon_search", "Falcon", fingerprint,
                                          workspace=self.root)
        for limit in (0, 26, True, "5"):
            with self.assertRaises(dev.ProjectError):
                self.find("Falcon", max_matches=limit)

    def test_preview_is_bounded_and_never_modifies_code(self):
        before = (self.saved / "main.py").read_bytes()
        (self.saved / "README.md").write_text("Falcon " + "x" * 300 + "\n", encoding="utf-8")
        reopened = browser.open_saved_project("falcon_search", workspace=self.root)
        r = source_search.find_source("falcon_search", "Falcon", reopened["fingerprint"],
                                      workspace=self.root)
        excerpt = r["matches"][0]["excerpt"]
        self.assertLessEqual(len(excerpt), source_search.MAX_PREVIEW_CHARS)
        self.assertTrue(excerpt.endswith("…"))
        self.assertEqual((self.saved / "main.py").read_bytes(), before)

    def test_redirected_project_is_not_scanned(self):
        folder = self.saved / "src"
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (folder / "helper.py").unlink()
        folder.rmdir()
        try:
            folder.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable")
        with self.assertRaisesRegex(dev.ProjectError, "redirected"):
            self.find("Falcon")


if __name__ == "__main__":
    unittest.main()
