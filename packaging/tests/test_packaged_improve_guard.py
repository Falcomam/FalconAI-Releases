"""Frozen Falcon must not auto-patch read-only PyInstaller module pseudo-paths."""
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

CANDIDATE = Path(__file__).resolve().parents[2] / "build" / "Falcon_Ai_Health_Candidate"
sys.path.insert(0, str(CANDIDATE.resolve()))
import core_upgrade
import improve_cycle


class FrozenImproveGuardTests(unittest.TestCase):
    def test_packaged_improve_runs_health_but_not_source_patch(self):
        messages = []
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "improve.json"
            with patch.object(sys, "frozen", True, create=True):
                result = improve_cycle.run(
                    "notifications", messages.append, threading.Event(),
                    diagnose=lambda: ("local-report", "13/13 packaged checks passed. Failed: none"),
                    researcher=lambda *args, **kwargs:
                        self.fail("Research must never run if packaged self-upgrade unavailable"),
                    upgrader=lambda *args, **kwargs:
                        self.fail("No model/source patch should run on installed frozen EXE"),
                    store=report,
                )
            state = improve_cycle.latest(store=report)
            self.assertEqual(state["result"], "blocked: packaged source-upgrade unsupported")
        self.assertIsNone(result[1])
        self.assertTrue(any("installed EXE" in msg for msg in messages))
        self.assertTrue(any("No code has changed" in msg for msg in messages))

    def test_frozen_core_source_patching_install_and_rollback_are_guarded(self):
        with patch.object(sys, "frozen", True, create=True):
            for fn in (
                lambda: core_upgrade.auto_upgrade("Improve Falcon notifications safely"),
                lambda: core_upgrade.install_approved("fake-folder"),
                core_upgrade.rollback_last,
            ):
                with self.subTest(fn=fn), self.assertRaisesRegex(
                    core_upgrade.UpgradeError, "packaged|frozen"):
                    fn()


if __name__ == "__main__":
    unittest.main()
