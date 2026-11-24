"""Developer Mode review-only project tests: no AI code execution."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import developer_workspace as dev


def proposal(files=None, kind="python", name="test_project"):
    return {"name": name, "kind": kind,
            "files": files if files is not None else
                {"main.py": "print('Hello from Falcon')\n",
                 "README.md": "# Project\n"}}


class DeveloperWorkspaceTests(unittest.TestCase):
    def test_review_never_creates_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "projects"
            result = dev.review_proposal(proposal())
            self.assertEqual(result["file_count"], 2)
            self.assertFalse(result["execution_allowed"])
            self.assertFalse(root.exists())

    def test_json_proposal_and_digest(self):
        raw = json.dumps(proposal(), separators=(",", ":"))
        result = dev.parse_proposal(raw)
        self.assertEqual(len(result["fingerprint"]), 64)
        self.assertEqual(result["fingerprint"], dev.review_proposal(proposal())["fingerprint"])

    def test_saves_only_approved_new_project(self):
        with tempfile.TemporaryDirectory() as directory:
            p = proposal()
            digest = dev.review_proposal(p)["fingerprint"]
            root = Path(directory) / "projects"
            result = dev.save_approved(p, digest, workspace=root)
            self.assertEqual(Path(result["path"]), root / "test_project")
            self.assertFalse(result["executed"])
            self.assertEqual((root/"test_project"/"main.py").read_text(), p["files"]["main.py"])
            with self.assertRaises(dev.ProjectError):
                dev.save_approved(p, digest, workspace=root)

    def test_stale_approval_refused_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            p = proposal()
            digest = dev.review_proposal(p)["fingerprint"]
            p["files"]["main.py"] = "print('tampered')\n"
            root = Path(directory) / "projects"
            with self.assertRaises(dev.ProjectError):
                dev.save_approved(p, digest, workspace=root)
            self.assertFalse(root.exists())

    def test_invalid_approval_refused_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "projects"
            with self.assertRaises(dev.ProjectError):
                dev.save_approved(proposal(), "not-approved", workspace=root)
            self.assertFalse(root.exists())

    def test_folder_traversal_windows_devices_and_scripts_blocked(self):
        paths = [
            "../attack.py", "src/../../attack.py", "/tmp/attack.py",
            r"C:\evil.py", r"src\file.py", "C:attack.py",
            "folder//attack.py", "folder/./attack.py",
            "CON.py", "COM1.py", "LPT9.txt",
            ".github/workflows/run.yml", ".git/config.txt", "src/.venv/file.py",
            "bad.exe", "bad.ps1", "bad.cmd", "bad.sh", "bad.bat",
        ]
        for path in paths:
            with self.subTest(path=path), self.assertRaises(dev.ProjectError):
                dev.review_proposal(proposal({path: "Hi\n"}))

    def test_windows_case_conflict_and_parent_file_blocked(self):
        with self.assertRaises(dev.ProjectError):
            dev.review_proposal(proposal({"A.py": "pass", "a.PY": "pass"}))
        with self.assertRaises(dev.ProjectError):
            dev.review_proposal(proposal({"src.py": "pass", "src.py/main.py": "pass"}))

    def test_invalid_python_json_and_malformed_kinds(self):
        for files in [
            {"a.py": "def function(:\n"},
            {"a.json": "{not json}"},
        ]:
            with self.assertRaises(dev.ProjectError):
                dev.review_proposal(proposal(files))
        for kind in (None, 4, [], {}, "executable"):
            with self.subTest(kind=kind), self.assertRaises(dev.ProjectError):
                dev.review_proposal(proposal(kind=kind))

    def test_website_and_fabric_starters_supported_as_inert_files(self):
        for kind, files in [
            ("website", {"index.html": "<!doctype html><html><head><meta charset=\"UTF-8\"><title>Falcon</title></head><body><h1>Hi</h1></body></html>",
                         "styles/main.css": "body {font-family: sans-serif;}"}),
            ("fabric_mod", {"build.gradle": "plugins { id 'fabric-loom' version '1.8' }",
                            "src/main/java/example/Falcon.java":
                            "package example; public class Falcon {}",
                            "src/main/resources/fabric.mod.json": "{\"id\":\"falcon\",\"version\":\"1.0.0\"}"}),
        ]:
            with self.subTest(kind=kind):
                result = dev.review_proposal(proposal(files, kind=kind))
                self.assertEqual(result["kind"], kind)

    def test_website_bad_meta_blocked_before_any_files_written(self):
        malformed = (
            '<!DOCTYPE html>\\n<html lang="en"><head>\\n'
            '<meta charset="UTF-\\n'
            '<meta name="viewport" content="width=device-width">\\n'
            '<title>Broken</title></head><body>hi</body></html>'
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "projects"
            p = proposal({"index.html": malformed}, kind="website")
            with self.assertRaisesRegex(dev.ProjectError, "Website HTML validation failed"):
                dev.save_approved(p, "unapproved", workspace=root)
            self.assertFalse(root.exists())

    def test_website_missing_closing_tag_or_charset_blocked(self):
        for content in (
            '<html><head><meta charset="UTF-8"><title>Missing</title></head><body>Hi',
            '<html><head><title>Missing charset</title></head><body>Hi</body></html>',
            '<html><head><meta charset="UTF-8"></head><body>Hi</body></html>',
        ):
            with self.subTest(content=content), self.assertRaises(dev.ProjectError):
                dev.review_proposal(proposal({"index.html": content}, kind="website"))

    def test_website_missing_nav_target_is_warning_not_saved_code(self):
        content = ('<!doctype html><html><head><meta charset="UTF-8"><title>Test</title></head>'
                   '<body><nav><a href="#about">About</a></nav></body></html>')
        result = dev.review_proposal(proposal({"index.html": content}, kind="website"))
        self.assertTrue(any("about" in warning for warning in result["quality_warnings"]))
        self.assertFalse(result["execution_allowed"])

    def test_file_caps_and_bad_model_output(self):
        with self.assertRaises(dev.ProjectError):
            dev.review_proposal(proposal({"a.txt": "x" * (dev.MAX_BYTES_PER_FILE + 1)}))
        with self.assertRaises(dev.ProjectError):
            dev.review_proposal(proposal({f"{n}.py": "pass" for n in range(dev.MAX_FILES + 1)}))
        for raw in ("markdown fenced JSON", "not json", "[]"):
            with self.assertRaises(dev.ProjectError):
                dev.parse_proposal(raw)

    def test_linked_workspace_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real"
            real.mkdir()
            link = root / "projects"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                return
            p = proposal()
            digest = dev.review_proposal(p)["fingerprint"]
            with self.assertRaises(dev.ProjectError):
                dev.save_approved(p, digest, workspace=link)
            self.assertFalse((real / "test_project").exists())


if __name__ == "__main__":
    unittest.main()
