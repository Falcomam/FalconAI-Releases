"""Tests for safely revising previously saved Falcon projects, without executing code."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import developer_workspace as dev
import project_revision as edits

VALID_HTML = ('<!doctype html><html><head><meta charset="UTF-8">'
              '<title>Falcon</title></head><body><h1>Hi</h1></body></html>')


class ProjectRevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / "developer_projects"
        self.workspace.mkdir()
        p = {"name": "myapp", "kind": "python",
             "files": {"main.py": "print('old')\n", "README.md": "Old README\n"}}
        dev.save_approved(p, dev.review_proposal(p)["fingerprint"],
                          workspace=self.workspace)
        self.original = p

    def modified(self, *, name="myapp"):
        p = copy.deepcopy(self.original)
        p["name"] = name
        p["files"]["main.py"] = "print('new')\n"
        return p

    def test_readonly_snapshot(self):
        s = edits.load_project("myapp", workspace=self.workspace)
        self.assertEqual(s["plan"], self.original)
        self.assertEqual(len(s["fingerprint"]), 64)
        self.assertFalse((self.workspace / edits.BACKUPS_FOLDER).exists())

    def test_review_diff_without_writing(self):
        s = edits.load_project("myapp", workspace=self.workspace)
        new = self.modified()
        revision = edits.review_revision(s, new)
        self.assertEqual(revision["changed"], ("main.py",))
        self.assertIn("-print('old')", revision["diff"])
        self.assertIn("+print('new')", revision["diff"])
        self.assertFalse((self.workspace / edits.BACKUPS_FOLDER).exists())
        self.assertEqual((self.workspace / "myapp" / "main.py").read_text(),
                         "print('old')\n")

    def test_review_rejects_missing_renamed_or_changed_kind(self):
        s = edits.load_project("myapp", workspace=self.workspace)
        for change in ("delete", "rename", "kind"):
            new = self.modified()
            if change == "delete":
                del new["files"]["README.md"]
            elif change == "rename":
                new["name"] = "different"
            else:
                new["kind"] = "website"
            with self.subTest(change=change), self.assertRaises(dev.ProjectError):
                edits.review_revision(s, new)

    def test_review_rejects_bad_code_and_invalid_digest(self):
        s = edits.load_project("myapp", workspace=self.workspace)
        new = self.modified()
        new["files"]["main.py"] = "def fail(:\n"
        with self.assertRaisesRegex(dev.ProjectError, "Python syntax"):
            edits.review_revision(s, new)
        new = self.modified()
        with self.assertRaisesRegex(dev.ProjectError, "approval"):
            edits.save_revision_approved(s, new, "bad", workspace=self.workspace)
        self.assertEqual((self.workspace / "myapp" / "main.py").read_text(),
                         "print('old')\n")

    def test_saving_creates_backup_and_can_rollback(self):
        original = edits.load_project("myapp", workspace=self.workspace)
        new = self.modified()
        reviewed = edits.review_revision(original, new)
        out = edits.save_revision_approved(original, new,
                         reviewed["new_fingerprint"], workspace=self.workspace)
        self.assertFalse(out["executed"])
        self.assertEqual(out["changed"], ("main.py",))
        saved = self.workspace / "myapp" / "main.py"
        self.assertEqual(saved.read_text(), "print('new')\n")
        backup = (self.workspace / edits.BACKUPS_FOLDER / "myapp" /
                  out["backup_id"])
        self.assertEqual((backup / "main.py").read_text(), "print('old')\n")
        meta = json.loads((backup / "revision.json").read_text())
        self.assertEqual(meta["base_fingerprint"], original["fingerprint"])
        restored = edits.rollback_revision("myapp", out["backup_id"],
                                           workspace=self.workspace)
        self.assertFalse(restored["executed"])
        self.assertEqual(saved.read_text(), "print('old')\n")
        self.assertEqual((backup / "main.py").read_text(), "print('old')\n")

    def test_add_new_source_file_and_rollback(self):
        original = edits.load_project("myapp", workspace=self.workspace)
        new = self.modified()
        new["files"]["src/feature.py"] = "def hello():\\n    return 'falcon'\\n".replace("\\n", "\n")
        reviewed = edits.review_revision(original, new)
        self.assertEqual(reviewed["added"], ("src/feature.py",))
        self.assertEqual(reviewed["updated"], ("main.py",))
        self.assertIn("src/feature.py", reviewed["diff"])
        self.assertIn("/dev/null", reviewed["diff"])
        newfile = self.workspace / "myapp/src/feature.py"
        self.assertFalse(newfile.exists())
        out = edits.save_revision_approved(original, new, reviewed["new_fingerprint"],
                                          workspace=self.workspace)
        self.assertEqual(out["added"], ("src/feature.py",))
        self.assertEqual(newfile.read_text(), new["files"]["src/feature.py"])
        self.assertEqual((self.workspace / "myapp/main.py").read_text(), "print('new')\n")
        restored = edits.rollback_revision("myapp", out["backup_id"],
                                           workspace=self.workspace)
        self.assertIn("src/feature.py", restored["removed_added"])
        self.assertFalse(newfile.exists())
        self.assertFalse(newfile.parent.exists())
        self.assertEqual((self.workspace / "myapp/main.py").read_text(), "print('old')\n")

    def test_add_only_revision_is_reviewable_and_reversible(self):
        original = edits.load_project("myapp", workspace=self.workspace)
        new = copy.deepcopy(original["plan"])
        new["files"]["settings.json"] = '{"enabled":true}'
        rev = edits.review_revision(original, new)
        self.assertEqual(rev["updated"], ())
        self.assertEqual(rev["added"], ("settings.json",))
        out = edits.save_revision_approved(original, new, rev["new_fingerprint"],
                                          workspace=self.workspace)
        self.assertTrue((self.workspace / "myapp/settings.json").exists())
        self.assertEqual((self.workspace / "myapp/main.py").read_text(), "print('old')\n")
        edits.rollback_revision("myapp", out["backup_id"], workspace=self.workspace)
        self.assertFalse((self.workspace / "myapp/settings.json").exists())

    def test_rollback_keeps_preexisting_empty_project_directory(self):
        existing = self.workspace / "myapp/src"
        existing.mkdir()
        initial = edits.load_project("myapp", workspace=self.workspace)
        proposal = self.modified()
        proposal["files"]["src/new.py"] = "pass\n"
        review = edits.review_revision(initial, proposal)
        out = edits.save_revision_approved(initial, proposal, review["new_fingerprint"],
                                          workspace=self.workspace)
        record = json.loads((self.workspace / edits.BACKUPS_FOLDER / "myapp" /
                             out["backup_id"] / "revision.json").read_text())
        self.assertEqual(record["created_dirs"], [])
        edits.rollback_revision("myapp", out["backup_id"], workspace=self.workspace)
        self.assertTrue(existing.is_dir())
        self.assertFalse((existing / "new.py").exists())

    def test_added_file_not_silently_overwritten_if_existing(self):
        original = edits.load_project("myapp", workspace=self.workspace)
        new = self.modified()
        new["files"]["settings.json"] = "{}"
        reviewed = edits.review_revision(original, new)
        (self.workspace / "myapp/settings.json").write_text("user contents")
        with self.assertRaisesRegex(dev.ProjectError, "changed since review"):
            edits.save_revision_approved(original, new, reviewed["new_fingerprint"],
                                          workspace=self.workspace)
        self.assertEqual((self.workspace / "myapp/settings.json").read_text(),
                         "user contents")

    def test_added_file_with_bad_syntax_or_forbidden_path_rejected(self):
        original = edits.load_project("myapp", workspace=self.workspace)
        for path, body in (("src/bad.py", "def fail(:\\n"),
                           ("src/task.exe", "bad"),
                           ("../escape.py", "print('bad')"),
                           ("README.md/new.py", "pass")):
            new = self.modified()
            new["files"][path] = body
            with self.subTest(path=path), self.assertRaises(dev.ProjectError):
                edits.review_revision(original, new)

    def test_cannot_add_file_that_changes_project_kind(self):
        base = edits.load_project("myapp", workspace=self.workspace)
        new = self.modified()
        new["files"]["index.html"] = VALID_HTML
        with self.assertRaisesRegex(dev.ProjectError, "project type"):
            edits.review_revision(base, new)

    def test_new_folder_symlink_attack_is_blocked(self):
        original = edits.load_project("myapp", workspace=self.workspace)
        new = self.modified()
        new["files"]["outside/attack.py"] = "pass"
        rev = edits.review_revision(original, new)
        outside = Path(self.tmp.name) / "foreign"
        outside.mkdir()
        link = self.workspace / "myapp/outside"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable")
        with self.assertRaises(dev.ProjectError):
            edits.save_revision_approved(original, new, rev["new_fingerprint"],
                                          workspace=self.workspace)
        self.assertFalse((outside / "attack.py").exists())

    def test_added_file_rollback_refuses_later_changes(self):
        original = edits.load_project("myapp", workspace=self.workspace)
        new = self.modified()
        new["files"]["src/feature.py"] = "print('added')\\n".replace("\\n", "\n")
        reviewed = edits.review_revision(original, new)
        out = edits.save_revision_approved(original, new, reviewed["new_fingerprint"],
                                          workspace=self.workspace)
        target = self.workspace / "myapp/src/feature.py"
        target.write_text("print('user changed')\n")
        with self.assertRaisesRegex(dev.ProjectError, "changed since review"):
            edits.rollback_revision("myapp", out["backup_id"], workspace=self.workspace)
        self.assertEqual(target.read_text(), "print('user changed')\n")

    def test_edit_does_not_overwrite_user_changes_since_preview(self):
        original = edits.load_project("myapp", workspace=self.workspace)
        new = self.modified()
        reviewed = edits.review_revision(original, new)
        (self.workspace / "myapp" / "README.md").write_text("User changed this\n")
        with self.assertRaisesRegex(dev.ProjectError, "changed since review"):
            edits.save_revision_approved(original, new, reviewed["new_fingerprint"],
                                         workspace=self.workspace)
        self.assertEqual((self.workspace / "myapp" / "main.py").read_text(),
                         "print('old')\n")

    def test_rollback_refuses_later_user_changes(self):
        base = edits.load_project("myapp", workspace=self.workspace)
        rev = self.modified()
        fingerprint = edits.review_revision(base, rev)["new_fingerprint"]
        done = edits.save_revision_approved(base, rev, fingerprint, workspace=self.workspace)
        (self.workspace / "myapp" / "main.py").write_text("print('my edit')\n")
        with self.assertRaisesRegex(dev.ProjectError, "changed since review"):
            edits.rollback_revision("myapp", done["backup_id"],
                                    workspace=self.workspace)
        self.assertEqual((self.workspace / "myapp" / "main.py").read_text(),
                         "print('my edit')\n")

    def test_rollback_refuses_corrupted_backup_before_any_writes(self):
        base = edits.load_project("myapp", workspace=self.workspace)
        rev = self.modified()
        approved = edits.review_revision(base, rev)["new_fingerprint"]
        result = edits.save_revision_approved(base, rev, approved,
                                              workspace=self.workspace)
        backup_file = (self.workspace / edits.BACKUPS_FOLDER /
                       "myapp" / result["backup_id"] / "main.py")
        backup_file.write_text("print('corrupt backup')\n")
        current = self.workspace / "myapp" / "main.py"
        with self.assertRaisesRegex(dev.ProjectError, "integrity"):
            edits.rollback_revision("myapp", result["backup_id"],
                                    workspace=self.workspace)
        self.assertEqual(current.read_text(), "print('new')\n")

    def test_rollback_id_path_injection_fails(self):
        for value in ("../", "a" * 40, ".." + "a" * 30, "A" * 32):
            with self.subTest(value=value), self.assertRaises(dev.ProjectError):
                edits.rollback_revision("myapp", value, workspace=self.workspace)

    def test_corrupted_or_foreign_project_files_refused(self):
        folder = self.workspace / "myapp"
        (folder / "unsafe.exe").write_bytes(b"data")
        with self.assertRaises(dev.ProjectError):
            edits.load_project("myapp", workspace=self.workspace)
        (folder / "unsafe.exe").unlink()
        (folder / "main.py").write_bytes(b"\xff")
        with self.assertRaisesRegex(dev.ProjectError, "UTF-8"):
            edits.load_project("myapp", workspace=self.workspace)

    def test_old_invalid_website_can_be_repaired(self):
        broken = ('<!doctype html><html><head><meta charset="UTF-\n'
                  '<title>Falcon</title></head><body>Hi</body></html>')
        site = self.workspace / "oldsite"
        site.mkdir()
        (site / "index.html").write_text(broken)
        initial = edits.load_project("oldsite", workspace=self.workspace)
        self.assertEqual(initial["plan"]["kind"], "website")
        updated = {"name": "oldsite", "kind": "website",
                   "files": {"index.html": VALID_HTML}}
        check = edits.review_revision(initial, updated)
        result = edits.save_revision_approved(initial, updated,
                       check["new_fingerprint"], workspace=self.workspace)
        self.assertEqual((site / "index.html").read_text(), VALID_HTML)
        edits.rollback_revision("oldsite", result["backup_id"],
                                workspace=self.workspace)
        self.assertEqual((site / "index.html").read_text(), broken)

    def test_symlinked_project_file_refused(self):
        p = self.workspace / "myapp"
        outside = Path(self.tmp.name) / "outside.txt"
        outside.write_text("secret")
        try:
            (p / "main.py").unlink()
            (p / "main.py").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Windows symlink support unavailable")
        with self.assertRaisesRegex(dev.ProjectError, "redirected"):
            edits.load_project("myapp", workspace=self.workspace)


if __name__ == "__main__":
    unittest.main()
