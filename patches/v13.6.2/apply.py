"""Apply Falcon 13.6.2 restart reliability patch on top of the verified 13.6.1 tree."""
from pathlib import Path
import shutil

repo = Path(__file__).resolve().parents[2]
source = repo / "build" / "Falcon_AI_V13_6_1"
target = repo / "build" / "Falcon_AI_V13_6_2"
if (source / "RELEASE_VERSION.txt").read_text().strip() != "13.6.1":
    raise SystemExit("V13.6.1 base required")
if target.exists():
    shutil.rmtree(target)
shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

def change(rel, old, new):
    file = target / rel
    data = file.read_text(encoding="utf-8")
    if data.count(old) != 1:
        raise SystemExit(f"Unexpected {rel} anchor ({data.count(old)}): {old[:90]!r}")
    file.write_text(data.replace(old, new), encoding="utf-8")

# Include diagnostics at the very start of the out-of-process update helper.
change("APPLY_RELEASE_UPDATE.ps1",
       "try {\n  $Live = [System.IO.Path]::GetFullPath($Live).TrimEnd('\\')",
       "try {\n  Log ('Updater helper started (PID ' + $PID + ', waiting for Falcon PID ' + $WaitPid + ')')\n  $Live = [System.IO.Path]::GetFullPath($Live).TrimEnd('\\')")

# Reinforce both the startup and rollback path. The previous code verified a log,
# but did not attempt a second launch method if pythonw immediately exited.
change("APPLY_RELEASE_UPDATE.ps1",
       """    $child = Start-Process -FilePath $pythonw -ArgumentList ('"' + $launcher + '"') -WorkingDirectory $Live -PassThru
    $ready = $false""",
       """    Log ('Starting updated Falcon via pythonw.exe: ' + $launcher)
    $child = Start-Process -FilePath $pythonw -ArgumentList ('"' + $launcher + '"') -WorkingDirectory $Live -PassThru
    Log ('Updated Falcon process spawned: PID ' + $child.Id)
    $ready = $false""")
change("APPLY_RELEASE_UPDATE.ps1",
       """      if ($child.HasExited) {
        throw ('Updated Falcon closed during restart (exit code ' + $child.ExitCode + ')')
      }""",
       """      if ($child.HasExited) {
        Log ('pythonw.exe exited early with code ' + $child.ExitCode + '; retrying hidden python.exe')
        $python = Join-Path $Live '.venv\\Scripts\\python.exe'
        if (-not (Test-Path -LiteralPath $python)) {
          throw 'Updated Falcon exited; no fallback Python found'
        }
        $child = Start-Process -FilePath $python -ArgumentList ('"' + $launcher + '"') -WorkingDirectory $Live -WindowStyle Hidden -PassThru
        Log ('Fallback python.exe process spawned: PID ' + $child.Id)
        Start-Sleep -Seconds 2
        $child.Refresh()
        if ($child.HasExited) {
          throw ('Updated Falcon failed both launch methods (exit code ' + $child.ExitCode + ')')
        }
      }""")
change("APPLY_RELEASE_UPDATE.ps1",
       "    $bootLog = Join-Path $home 'logs\\v13_5_startup.log'",
       "    $bootLog = Join-Path $home 'logs\\v13_5_startup.log'\n    Log ('Startup status log: ' + $bootLog)")
change("APPLY_RELEASE_UPDATE.ps1",
       """      Log ('Falcon process running (PID ' + $child.Id + '), GUI startup still unconfirmed')""",
       """      Log ('WARNING: Falcon process running (PID ' + $child.Id + '), GUI readiness unconfirmed; see startup log')""")

change("release_updates.py", "CURRENT_VERSION = (13, 6, 1)", "CURRENT_VERSION = (13, 6, 2)")
for old, new in (
    ("Falcon AI V13.6.1 — Command Center", "Falcon AI V13.6.2 — Command Center"),
    ("Falcon V13.6.1 ready.", "Falcon V13.6.2 ready."),
    ("V13.6.1  /  LOCAL JARVIS", "V13.6.2  /  LOCAL JARVIS"),
):
    change("falcon.py", old, new)
(target / "RELEASE_VERSION.txt").write_text("13.6.2\n", encoding="utf-8")
for rel in ("tests/test_v135_permanent.py", "tests/test_v131_updates.py", "tests/test_v1361_restart.py"):
    p = target / rel
    data = p.read_text(encoding="utf-8")
    data = data.replace("(13,6,1)", "(13,6,2)").replace("(13, 6, 1)", "(13, 6, 2)")
    data = data.replace("13.6.1", "13.6.2").replace("Falcon_AI_V13_6_1/", "Falcon_AI_V13_6_2/")
    p.write_text(data, encoding="utf-8")
(target / "tests" / "test_v1362_restart.py").write_text(
    """import pathlib, unittest\nimport release_updates\n\nROOT = pathlib.Path(__file__).resolve().parents[1]\nclass V1362Restart(unittest.TestCase):\n    def test_version_and_logging(self):\n        self.assertEqual(release_updates.CURRENT_VERSION, (13, 6, 2))\n        self.assertEqual((ROOT/'RELEASE_VERSION.txt').read_text().strip(), '13.6.2')\n        ps = (ROOT/'APPLY_RELEASE_UPDATE.ps1').read_text()\n        for s in ('Updater helper started', 'Fallback python.exe process spawned', 'Startup status log:', 'Installed verified release', 'Move-Item -LiteralPath $backup -Destination $Live'):\n            self.assertIn(s, ps)\n        self.assertNotIn('Start-Process -FilePath \\'cmd.exe\\'', ps)\n""", encoding="utf-8")
(target / "README_V13_6_2.txt").write_text(
    "Falcon AI V13.6.2 - startup troubleshooting and restart fallback.\\n"
    "After approved update, log helper activation and Python GUI launch.\\n"
    "If pythonw.exe exits immediately, retry via hidden python.exe and check startup status.\\n"
    "Existing backup/rollback safeguards remain. Real Windows desktop verification is still required.\\n",
    encoding="utf-8")
print("Built V13.6.2 on the V13.6.1 source; no user data included")
