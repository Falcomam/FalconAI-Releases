"""Internal Falcon updater should minimize its own PowerShell, not user shells."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import quiet_powershell as quiet


class QuietPowerShellTests(unittest.TestCase):
    def test_uses_file_arg_not_shell_command(self):
        args = quiet.powershell_minimized_args(
            r"C:\FalconUpdater\app_update_restart.ps1")
        self.assertEqual(args[:4],
                         ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive"])
        self.assertIn("-WindowStyle", args)
        self.assertEqual(args[args.index("-WindowStyle") + 1], "Minimized")
        self.assertIn("-File", args)
        self.assertNotIn("-Command", args)
        self.assertEqual(args[-1], r"C:\FalconUpdater\app_update_restart.ps1")

    def test_never_accepts_scriptless_shell_command(self):
        for x in ("", "whoami", "ping 8.8.8.8", "hello.bat", "x.ps1 & calc", None):
            with self.subTest(x=x), self.assertRaises((ValueError, TypeError)):
                quiet.powershell_minimized_args(x)

    def test_other_platforms_do_not_get_windows_startupinfo(self):
        self.assertIsNone(quiet.minimized_startupinfo(platform="linux"))
        self.assertIsNone(quiet.minimized_startupinfo(platform="darwin"))

    @unittest.skipUnless(sys.platform == "win32", "Windows-only STARTUPINFO")
    def test_windows_minimized_no_activation(self):
        info = quiet.minimized_startupinfo(platform="win32")
        self.assertIsInstance(info, subprocess.STARTUPINFO)
        self.assertTrue(info.dwFlags & subprocess.STARTF_USESHOWWINDOW)
        self.assertEqual(info.wShowWindow, 7)

    @unittest.skipUnless(sys.platform == "win32", "Requires native Windows")
    def test_packaged_update_handoff_stays_minimized_and_noninteractive(self):
        module_path = (ROOT.parents[0] / "build" /
                       "falcon_app_quiet_powershell_runtime" / "app_updates.py")
        spec = importlib.util.spec_from_file_location("falcon_quiet_app_updates", module_path)
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
        with tempfile.TemporaryDirectory() as temp:
            tmp = Path(temp)
            exe = tmp / "Falcon Ai.exe"
            exe.write_bytes(b"MZfake-installed-executable")
            helper = tmp / "bundled" / "app_update_restart.ps1"
            helper.parent.mkdir()
            helper.write_text("exit 0", encoding="utf-8")
            stage = tmp / "falcon_ai_temp" / "Falcon_Ai_Setup.exe"
            stage.parent.mkdir()
            stage.write_bytes(b"MZfake-installer")
            # No real child process is started, no GUI is closed, and no
            # staged installer is ever executed by this regression test.
            with patch.object(runtime, "_trusted_stage", return_value=stage), \
                 patch.object(runtime.sys, "frozen", True, create=True), \
                 patch.object(runtime.sys, "executable", str(exe)), \
                 patch.object(runtime.sys, "_MEIPASS", str(helper.parent), create=True), \
                 patch.object(runtime.subprocess, "Popen") as popen:
                self.assertTrue(runtime.schedule_install(stage, process_id=12345))
                popen.assert_called_once()
                args, kwargs = popen.call_args
                self.assertEqual(args[0][0], "powershell.exe")
                self.assertEqual(args[0][args[0].index("-WindowStyle")+1],
                                 "Minimized")
                self.assertEqual(args[0][args[0].index("-File")+1],
                                 str(stage.parent / "app_update_restart.ps1"))
                self.assertIn("12345", args[0])
                self.assertEqual(kwargs["startupinfo"].wShowWindow, 7)
                self.assertTrue(kwargs["creationflags"] &
                                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
                self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
                self.assertTrue((stage.parent / "app_update_restart.ps1").is_file())


if __name__ == "__main__":
    unittest.main()
