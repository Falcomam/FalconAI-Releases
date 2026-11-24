"""Saved-project catalog: read-only, restricted, bounded, never executes code."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import developer_workspace as dev
import project_browser as browser


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "developer_projects"
        self.base.mkdir()

    def add(self, name, text="print('hello')\n"):
        plan = {"name": name, "kind": "python",
                "files": {"main.py": text, "README.md": "Demo\n"}}
        dev.save_approved(plan, dev.review_proposal(plan)["fingerprint"],
                          workspace=self.base)
        return self.base / name

    def test_empty_and_missing_workspace_are_read_only(self):
        missing = self.base / "not_present"
        self.assertEqual(browser.list_saved_projects(workspace=missing), ())
        self.assertFalse(missing.exists())
        self.assertEqual(browser.list_saved_projects(workspace=self.base), ())

    def test_sorted_catalog_filters_files_and_hidden_backups(self):
        self.add("zulu")
        self.add("Alpha")
        self.add("bravo")
        (self.base / ".falcon_revision_backups").mkdir()
        (self.base / "not_a_project.txt").write_text("a file")
        (self.base / "README.md").write_text("a file")
        self.assertEqual(browser.list_saved_projects(workspace=self.base),
                         ("Alpha", "bravo", "zulu"))
        self.assertEqual(browser.list_saved_projects(workspace=self.base, limit=2),
                         ("Alpha", "bravo"))

    def test_open_and_show_existing_source(self):
        self.add("website", "print('🦅 Falcon')\n")
        opened = browser.open_saved_project("website", workspace=self.base)
        self.assertEqual(opened["plan"]["name"], "website")
        self.assertEqual(len(opened["fingerprint"]), 64)
        preview = browser.show_saved_file(
            "website", "main.py", opened["fingerprint"], workspace=self.base)
        self.assertEqual(preview["text"], "print('🦅 Falcon')\n")
        self.assertFalse(preview["truncated"])

    def test_reject_stale_snapshot_if_user_changed_file(self):
        target = self.add("sample")
        opened = browser.open_saved_project("sample", workspace=self.base)
        (target / "README.md").write_text("user edited file\n")
        with self.assertRaisesRegex(dev.ProjectError, "changed"):
            browser.show_saved_file("sample", "main.py",
                                    opened["fingerprint"], workspace=self.base)
        self.assertEqual((target / "README.md").read_text(), "user edited file\n")

    def test_reject_unlisted_and_path_traversal(self):
        self.add("safe")
        snapshot = browser.open_saved_project("safe", workspace=self.base)
        for path in ("../outside.py", "C:\\secrets.txt", "/windows/file.txt"):
            with self.subTest(path=path), self.assertRaises(dev.ProjectError):
                browser.show_saved_file("safe", path, snapshot["fingerprint"],
                                        workspace=self.base)
        with self.assertRaisesRegex(dev.ProjectError, "not in the saved"):
            browser.show_saved_file("safe", "other.py", snapshot["fingerprint"],
                                    workspace=self.base)

    def test_preview_is_bounded_and_nonmutating(self):
        source = self.add("long", text="a=1\n" * 4000)
        opened = browser.open_saved_project("long", workspace=self.base)
        result = browser.show_saved_file("long", "main.py", opened["fingerprint"],
                                         workspace=self.base, preview_limit=125)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["text"]), 125)
        self.assertEqual((source / "main.py").read_text(), "a=1\n" * 4000)
        for bound in (0, -1, 18001):
            with self.assertRaises(dev.ProjectError):
                browser.show_saved_file("long", "main.py", opened["fingerprint"],
                                        workspace=self.base, preview_limit=bound)

    def test_hidden_unsafe_directory_is_not_listed(self):
        self.add("visible")
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        target = self.base / "link"
        try:
            target.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        self.assertEqual(browser.list_saved_projects(workspace=self.base), ("visible",))

    def test_list_boundaries_and_no_execution(self):
        self.add("demo")
        for bound in (0, 51, -1, 1.1, "5"):
            with self.assertRaises(dev.ProjectError):
                browser.list_saved_projects(workspace=self.base, limit=bound)
        self.assertEqual(browser.list_saved_projects(workspace=self.base, limit=1),
                         ("demo",))


if __name__ == "__main__":
    unittest.main()
