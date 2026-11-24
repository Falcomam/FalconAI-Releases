"""No-execution AST risk hints, including explicit known blind spots."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import self_improve_risk_hints as hints


class RiskHintTests(unittest.TestCase):
    def test_process_and_dynamic_code_flags(self):
        source = "import subprocess\nsubprocess.Popen(['echo', 'hi'])\nexec('pass')\n"
        found = hints.inspect_python(source)
        indicators = [x["indicator"] for x in found["indicators"]]
        self.assertIn("watched_import:subprocess", indicators)
        self.assertIn("high_impact_call:subprocess.Popen", indicators)
        self.assertIn("high_impact_call:exec", indicators)
        self.assertTrue(found["advisory_only"])

    def test_file_write_mode_is_flagged(self):
        found = hints.inspect_python("open('a.txt', mode='w')\n")
        self.assertTrue(found["manual_review_required"])
        self.assertIn("possible_file_write:open", found["indicators"][0]["indicator"])

    def test_normal_code_no_flags_but_not_certified_safe(self):
        found = hints.inspect_python("def sum_two(a, b):\n    return a+b\n")
        self.assertFalse(found["manual_review_required"])
        self.assertTrue(found["advisory_only"])

    def test_common_aliases_and_path_writes_are_flagged(self):
        source = ("import subprocess as sp\n"
                  "from subprocess import Popen as launch\n"
                  "sp.run(['echo'])\n"
                  "launch(['echo'])\n"
                  "from pathlib import Path\n"
                  "Path('output').write_text('data')\n")
        findings = hints.inspect_python(source)["indicators"]
        labels = [entry["indicator"] for entry in findings]
        self.assertIn("high_impact_call:subprocess.run", labels)
        self.assertIn("high_impact_call:subprocess.Popen", labels)
        self.assertTrue(any("write_text" in label for label in labels))

    def test_bounded_findings(self):
        found = hints.inspect_python("exec('pass')\n" * 60)
        self.assertEqual(len(found["indicators"]), 40)
        self.assertTrue(found["indicators_truncated"])


if __name__ == "__main__":
    unittest.main()
