"""Static Developer Mode checks are truthful and never execute generated files."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import project_static_check as check
import developer_workspace as workspace


class StaticCheckTests(unittest.TestCase):
    def test_python_and_json_report(self):
        plan = {"name": "demo", "kind": "python",
                "files": {"main.py": "print('hello')\n",
                          "config.json": '{"enabled": true}'}}
        fingerprint = workspace.review_proposal(plan)["fingerprint"]
        with patch("subprocess.run", side_effect=AssertionError("ran code")), \
             patch("subprocess.Popen", side_effect=AssertionError("ran code")):
            report = check.inspect(plan, fingerprint)
        self.assertEqual(report["file_count"], 2)
        self.assertFalse(report["code_executed"])
        self.assertFalse(report["tests_executed"])
        self.assertIn("Executed tests: NONE", check.render(report))
        self.assertTrue(any(f["static_gate"] == "python_ast_parsed" for f in report["files"]))

    def test_changed_draft_blocks_diagnostics(self):
        plan = {"name": "demo", "kind": "python",
                "files": {"main.py": "pass\n"}}
        saved_fingerprint = workspace.review_proposal(plan)["fingerprint"]
        plan["files"]["main.py"] = "print(99)\n"
        with self.assertRaisesRegex(workspace.ProjectError, "changed since"):
            check.inspect(plan, saved_fingerprint)

    def test_js_not_claimed_to_have_been_tested(self):
        plan = {"name": "site", "kind": "website",
                "files": {"index.html": ('<!doctype html><html><head><meta charset="UTF-8">'
                                          '<title>X</title></head><body>Hi</body></html>'),
                          "index.js": "alert('hi');"}}
        report = check.inspect(plan)
        self.assertTrue(any("approved isolated worker" in w for w in report["warnings"]))
        self.assertFalse(report["build_created"])

    def test_review_gate_invalid_syntax_blocks(self):
        plan = {"name": "demo", "kind": "python",
                "files": {"main.py": "def not_valid(:"}}
        with self.assertRaises(workspace.ProjectError):
            check.inspect(plan)


if __name__ == "__main__":
    unittest.main()
