"""Falcon V13.6.3: deliberate restart button and valid updater helper syntax."""
from pathlib import Path
import shutil

repo = Path(__file__).resolve().parents[2]
source = repo / "build" / "Falcon_AI_V13_6_2"
target = repo / "build" / "Falcon_AI_V13_6_3"
assert (source / "RELEASE_VERSION.txt").read_text().strip() == "13.6.2"
if target.exists():
    shutil.rmtree(target)
shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

def replace(rel, old, new):
    p = target / rel
    data = p.read_text(encoding="utf-8")
    count = data.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one exact anchor in {rel}; got {count}: {old[:80]!r}")
    p.write_text(data.replace(old, new, 1), encoding="utf-8")

# The previous patch emitted two literal characters (\ and n) into a PowerShell
# statement, making that part of the update helper invalid PowerShell.
script = target / "APPLY_RELEASE_UPDATE.ps1"
ps = script.read_text(encoding="utf-8")
bad = "\\n    Log ('Startup status log: ' + $bootLog)"
assert ps.count(bad) == 1, ("Invalid V13.6.2 PowerShell anchor", ps.count(bad))
ps = ps.replace(bad, "\n    Log ('Startup status log: ' + $bootLog)")
# Avoid relying on one fragile log message to establish process availability.
assert "Log ('Updater helper started" in ps
assert "Start-Process -FilePath $pythonw" in ps
script.write_text(ps, encoding="utf-8")

# A separately launched helper survives closure of the current GUI and starts
# the same checked launcher after the existing process fully exits.
(target / "restart_helper.py").write_text(r'''"""Falcon user-requested restart. No remote execution or privilege escalation."""
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
LOG = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "FalconAI" / "logs" / "restart.log"

def log(msg):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat() + " " + msg + "\n")
    except OSError:
        pass

def wait_for_pid(pid, timeout_ms=20000):
    if os.name != "nt":
        time.sleep(1.5)
        return True
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = (ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong)
    kernel.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_ulong)
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
    SYNCHRONIZE = 0x00100000
    h = kernel.OpenProcess(SYNCHRONIZE, False, pid)
    if not h:
        # Already exited, or unavailable. The launcher mutex still prevents duplicates.
        time.sleep(0.6)
        return True
    try:
        outcome = kernel.WaitForSingleObject(h, timeout_ms)
        return outcome == 0  # WAIT_OBJECT_0
    finally:
        kernel.CloseHandle(h)

def main():
    if len(sys.argv) != 2:
        return 2
    try:
        old_pid = int(sys.argv[1])
    except ValueError:
        return 2
    if old_pid <= 0 or old_pid == os.getpid():
        return 2
    log("Manual restart requested, waiting for PID " + str(old_pid))
    if not wait_for_pid(old_pid):
        log("ERROR: previous Falcon did not exit within 20 seconds; launch cancelled")
        return 1
    launcher = ROOT / "falcon_launcher.py"
    if not launcher.is_file():
        log("ERROR: falcon_launcher.py not found")
        return 1
    env = os.environ.copy()
    env.pop("FALCON_RESTART_MINIMIZED", None)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        child = subprocess.Popen(
            [sys.executable, str(launcher)], cwd=str(ROOT), env=env,
            creationflags=flags, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("Restart spawned new launcher PID " + str(child.pid))
        time.sleep(2)
        if child.poll() is not None:
            log("ERROR: new launcher exited early, exit code " + str(child.returncode))
            return 1
        return 0
    except Exception as exc:
        log("ERROR: failed to launch Falcon: " + repr(exc))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
''', encoding="utf-8")

replace("falcon.py",
        "import base64, io, json, os, re, threading, urllib.error, urllib.request, tkinter as tk",
        "import base64, io, json, os, re, threading, urllib.error, urllib.request, tkinter as tk\nimport subprocess, sys")
replace("falcon.py",
        "            ('⧉   Copy Report', self.copy_report),",
        "            ('⧉   Copy Report', self.copy_report),\n            ('↻   Restart Falcon', self.restart_falcon),")
replace("falcon.py",
        "    def on_close(self):\n",
        '''    def restart_falcon(self):
        """User-approved, deliberate restart without another installed copy."""
        if not messagebox.askyesno('Restart Falcon',
                'Close Falcon and reopen it now? Running tasks will be stopped.',
                parent=self.root):
            return
        helper = Path(__file__).resolve().parent / 'restart_helper.py'
        if not helper.is_file():
            messagebox.showerror('Restart unavailable', 'Restart helper was not installed.', parent=self.root)
            return
        try:
            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            subprocess.Popen(
                [sys.executable, str(helper), str(os.getpid())],
                cwd=str(helper.parent), creationflags=flags,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
        except OSError as exc:
            messagebox.showerror('Restart failed', str(exc), parent=self.root)
            return
        self.on_close()

    def on_close(self):
''')
replace("falcon.py",
        "        updates.add_command(label='Check for updates', command=self.check_release_updates)",
        "        updates.add_command(label='Check for updates', command=self.check_release_updates)\n        updates.add_command(label='Restart Falcon', command=self.restart_falcon)")
replace("release_updates.py", "CURRENT_VERSION = (13, 6, 2)", "CURRENT_VERSION = (13, 6, 3)")
for old, new in [
    ("Falcon AI V13.6.2 — Command Center", "Falcon AI V13.6.3 — Command Center"),
    ("Falcon V13.6.2 ready.", "Falcon V13.6.3 ready."),
    ("V13.6.2  /  LOCAL JARVIS", "V13.6.3  /  LOCAL JARVIS"),
]:
    replace("falcon.py", old, new)
(target / "RELEASE_VERSION.txt").write_text("13.6.3\n", encoding="utf-8")
for rel in ("tests/test_v135_permanent.py", "tests/test_v131_updates.py", "tests/test_v1361_restart.py", "tests/test_v1362_restart.py"):
    p = target / rel
    s = p.read_text(encoding="utf-8")
    s = s.replace("(13,6,2)", "(13,6,3)").replace("(13, 6, 2)", "(13, 6, 3)").replace("13.6.2", "13.6.3").replace("Falcon_AI_V13_6_2/", "Falcon_AI_V13_6_3/")
    p.write_text(s, encoding="utf-8")
(target / "tests" / "test_v1363_restart_button.py").write_text(
    """from pathlib import Path
import unittest
import release_updates

ROOT = Path(__file__).resolve().parents[1]
class RestartButtonTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(release_updates.CURRENT_VERSION, (13, 6, 3))
        self.assertEqual((ROOT/'RELEASE_VERSION.txt').read_text().strip(), '13.6.3')
    def test_button_and_confirmation(self):
        ui=(ROOT/'falcon.py').read_text(encoding='utf-8')
        self.assertIn('Restart Falcon', ui)
        self.assertIn('def restart_falcon(self):', ui)
        self.assertIn('messagebox.askyesno', ui)
        self.assertIn('restart_helper.py', ui)
        self.assertIn('self.on_close()', ui)
    def test_helper_and_updater_syntax(self):
        helper=(ROOT/'restart_helper.py').read_text(encoding='utf-8')
        self.assertIn('wait_for_pid(', helper)
        self.assertIn('falcon_launcher.py', helper)
        ps=(ROOT/'APPLY_RELEASE_UPDATE.ps1').read_text(encoding='utf-8')
        self.assertNotIn(chr(11), ps)
        self.assertNotIn(\"\\\\n    Log ('Startup status log:\", ps)
        self.assertIn(\"\\n    Log ('Startup status log:\", ps)
        self.assertIn('Move-Item -LiteralPath $backup -Destination $Live', ps)
""", encoding="utf-8")
(target / "FOLDER_GUIDE.txt").write_text(
    "FALCON AI | FILES AND FOLDERS\n"
    "START_HERE.bat             Manual launcher\n"
    "falcon.py                  Main purple GUI\n"
    "falcon_launcher.py         GUI bootstrap and duplicate guard\n"
    "restart_helper.py          Button restart helper (hidden)\n"
    "APPLY_RELEASE_UPDATE.ps1   Verified GitHub release installer\n"
    "release_updates.py         Update download/verification\n"
    "tests/                     Bundled checks\n"
    "LOCALAPPDATA/FalconAI/logs/  Diagnostic logs outside app\n"
    "FalconAI.previous          One recovery backup, next to install\n"
    "Do not move core files or delete recovery backup while updating.\n",
    encoding="utf-8")
print("Falcon 13.6.3 source ready: restart button, helper and syntax repair")
