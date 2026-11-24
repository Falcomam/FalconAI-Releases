"""Regression coverage for frozen Falcon EXE health reporting and safety."""
from pathlib import Path
from types import SimpleNamespace
import importlib.machinery
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import packaged_diagnostics as diag


class PackagedHealthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.exe = self.base / "Falcon Ai.exe"
        self.exe.write_bytes(b"MZ" + b"\x00" * 110000)
        self.bundle = self.base / "_internal"
        self.bundle.mkdir()
        (self.bundle / "app_update_restart.ps1").write_text("Log('status')\n" * 30)
        self.spec = lambda name: SimpleNamespace(
            origin=str(self.bundle / (name + ".pyc")),
            loader=importlib.machinery.SourcelessFileLoader(
                name, str(self.bundle / (name + ".pyc"))),
        )

    def test_packaged_modules_do_not_require_loose_python_source_files(self):
        with patch.object(importlib.util, "find_spec", side_effect=self.spec):
            result = diag.inspect(frozen=True, bundle=self.bundle, executable=self.exe)
        self.assertEqual(len(result), 13)
        self.assertEqual(set(result.values()), {"present"})
        self.assertFalse((self.bundle / "falcon.py").exists())
        self.assertFalse((self.bundle / "START_HERE.bat").exists())

    def test_missing_module_reports_missing_and_blocks_improve(self):
        def one_missing(name):
            return None if name == "agent" else self.spec(name)
        with patch.object(importlib.util, "find_spec", side_effect=one_missing):
            result = diag.inspect(frozen=True, bundle=self.bundle, executable=self.exe)
        self.assertEqual(result["agent.py"], "missing")
        self.assertEqual(sum(v == "present" for v in result.values()), 12)

    def test_origin_must_be_within_packaged_runtime(self):
        external = self.base / "outside.pyc"
        with patch.object(importlib.util, "find_spec",
                          return_value=SimpleNamespace(
                              origin=str(external), loader=object())):
            checks = diag.inspect(frozen=True, bundle=self.bundle, executable=self.exe)
        self.assertEqual(checks["falcon.py"], "missing")

    def test_no_other_user_folder_or_untrusted_bundle_accepted(self):
        with self.assertRaises(RuntimeError):
            diag.inspect(frozen=False, bundle=self.bundle, executable=self.exe)
        another = self.base.parent / "elsewhere"
        another.mkdir(exist_ok=True)
        with self.assertRaises(RuntimeError):
            diag.inspect(frozen=True, bundle=another, executable=self.exe)

    def test_missing_update_helper_detected(self):
        (self.bundle / "app_update_restart.ps1").unlink()
        with patch.object(importlib.util, "find_spec", side_effect=self.spec):
            checks = diag.inspect(frozen=True, bundle=self.bundle, executable=self.exe)
        self.assertEqual(checks["app_update_restart.ps1"], "missing")

    def test_run_writes_local_metadata_without_secrets_or_execution(self):
        with patch.object(diag, "ROOT", self.base / "diagnostics"), \
             patch.object(diag, "inspect", return_value={s:"present" for s in
                          diag.SOURCES + diag.REQUIRED_FILES}):
            result_path, summary = diag.run()
        self.assertIn("13/13", summary)
        self.assertIn("Failed: none", summary)
        obj = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertEqual(obj["mode"], "frozen module-loader and installer-file availability")
        self.assertEqual(len(obj["checks"]), 13)
        self.assertFalse("api_key" in result_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
