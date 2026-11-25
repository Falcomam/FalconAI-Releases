"""V14 candidate integrity tests using only synthetic source files and metadata.

No real installers, generated programs or local user files are executed.
"""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v14_release_checks as checks


class V14ReleaseContractTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory()
        self.addCleanup(self.sandbox.cleanup)
        root = Path(self.sandbox.name)
        self.source = root / "app"
        self.runtime = root / "runtime"
        self.source.mkdir()
        self.runtime.mkdir()
        for file in checks.REQUIRED:
            (self.source / file).write_text("placeholder\n", encoding="utf-8")
        self._source("RELEASE_VERSION.txt", "14.0.0\n")
        self._source("falcon_foundation.py", 'VERSION = "14.0.0"\n')
        self._source("falcon.py", "Falcon Ai V14.0.0 — Command Center\n")
        self._source("falcon_launcher.py", "Starting Falcon Ai V14.0.0\n")
        self._source("agent.py", "import gaming_mode\nif gaming_mode.enabled(): pass\n")
        self._source("developer_chat.py",
                     'import falcon_foundation\nreturn "foundation", ""\n'
                     "gaming_mode.enabled()\n")
        self._source("developer_workspace.py", "site_design_check.inspect(files)\n")
        self._source("release_updates.py", "CURRENT_VERSION = (14, 0, 0)\n")
        self._source("improve_cycle.py", "blocked: packaged source-upgrade unsupported\n")
        self._runtime("app_updates.py", "CURRENT_VERSION = (14, 0, 0)\n")
        self._runtime("app_entry.py", "CURRENT_VERSION != (14, 0, 0)\n"
                      "--falcon-foundation-self-test\n"
                      "--falcon-diagnostics-self-test\n"
                      "sys.modules['diagnostics'] = packaged_diagnostics\n")
        self._runtime("Falcon_Ai.iss", '#define MyAppVersion "14.0.0"\n'
                      "AppId={{FALCON-STABLE-ID}}\n"
                      r"icon=build\falcon_app_v14_runtime\Falcon_Ai_Icon.ico" + "\n")
        for icon in ("Falcon_Ai_Icon.ico", "Falcon_Ai_Icon.png"):
            (self.runtime / icon).write_bytes(b"synthetic-icon")
        self.previous = root / "old.iss"
        self.previous.write_text("AppId={{FALCON-STABLE-ID}}\n", encoding="utf-8")

    def _source(self, name, value):
        (self.source / name).write_text(value, encoding="utf-8")

    def _runtime(self, name, value):
        (self.runtime / name).write_text(value, encoding="utf-8")

    def _validate(self):
        return checks.verify(self.source, self.runtime,
                             previous_installer=self.previous)

    def test_good_candidate_explicitly_does_not_claim_install(self):
        result = self._validate()
        self.assertEqual(result["version"], "14.0.0")
        self.assertTrue(result["source_checks_passed"])
        self.assertFalse(result["frozen_exe_tested"])
        self.assertFalse(result["installed_on_user_pc"])

    def test_refuses_old_version_in_ui_and_updater(self):
        self._source("falcon.py", "Falcon Ai V13.9.0\n")
        with self.assertRaises(checks.ContractError):
            self._validate()
        self._source("falcon.py", "Falcon Ai V14.0.0\n")
        self._runtime("app_updates.py", "CURRENT_VERSION = (13, 9, 1)\n")
        with self.assertRaises(checks.ContractError):
            self._validate()

    def test_refuses_missing_agent_or_gaming_guard(self):
        (self.source / "agent.py").unlink()
        with self.assertRaises(checks.ContractError):
            self._validate()
        self._source("agent.py", "import agent\n")
        with self.assertRaises(checks.ContractError):
            self._validate()

    def test_refuses_changed_installer_appid(self):
        self._runtime("Falcon_Ai.iss", '#define MyAppVersion "14.0.0"\n'
                      "AppId={{NOT-SAME}}\n" +
                      r"icon=build\falcon_app_v14_runtime\Falcon_Ai_Icon.ico" + "\n")
        with self.assertRaises(checks.ContractError):
            self._validate()

    def test_refuses_development_markers(self):
        (self.source / "TEST_CANDIDATE_ONLY.txt").write_text("internal")
        with self.assertRaises(checks.ContractError):
            self._validate()

    def test_refuses_missing_diagnostics_hook(self):
        self._runtime("app_entry.py", "CURRENT_VERSION != (14, 0, 0)\n")
        with self.assertRaises(checks.ContractError):
            self._validate()


if __name__ == "__main__":
    unittest.main()
