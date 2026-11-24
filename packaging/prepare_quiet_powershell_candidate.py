"""Post-13.9 development: minimize internal PowerShell installer handoffs.

Only modifies staging under build/. The released v13.9.0 stays unchanged.
Separate GUI/test candidate retains all published features plus project search.
"""
from __future__ import annotations

from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / "build" / "Falcon_Ai_ProjectSearch_Candidate"
RUNTIME_BASE = REPO / "build" / "falcon_app_next_bundle_candidate_runtime"
TARGET = REPO / "build" / "Falcon_Ai_QuietPowerShell_Candidate"
RUNTIME = REPO / "build" / "falcon_app_quiet_powershell_runtime"

if (BASE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.9.0":
    raise RuntimeError("Post-13.9.0 source baseline required")
if "CURRENT_VERSION = (13, 9, 0)" not in (RUNTIME_BASE / "app_updates.py").read_text():
    raise RuntimeError("Existing published-version runtime required")
for dest in (TARGET, RUNTIME):
    if dest.exists():
        shutil.rmtree(dest)
shutil.copytree(BASE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copytree(RUNTIME_BASE, RUNTIME, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(REPO / "packaging" / "quiet_powershell.py", TARGET / "quiet_powershell.py")


def replace_exact(path, old, new):
    file = Path(path)
    body = file.read_text(encoding="utf-8")
    if body.count(old) != 1:
        raise RuntimeError(f"Changed packaged update-launch anchor: {file}, count={body.count(old)}")
    file.write_text(body.replace(old, new, 1), encoding="utf-8")


app_updates = RUNTIME / "app_updates.py"
replace_exact(app_updates, "import subprocess\n", "import subprocess\nimport quiet_powershell\n")
replace_exact(app_updates,
              """    args = ['powershell.exe', '-NoProfile', '-NonInteractive',
            '-ExecutionPolicy', 'Bypass', '-File', str(copied_helper),
            '-WaitPid', str(process_id or os.getpid()),
            '-Installer', str(exe), '-AppExe', str(installed_exe)]
""",
              """    # Windows should not bring the internal update shell in front of Falcon.
    # The script remains visible if the user intentionally restores it, and
    # all helper results/errors are preserved in app_installer_update.log.
    args = quiet_powershell.powershell_minimized_args(str(copied_helper))
    args += ['-WaitPid', str(process_id or os.getpid()),
             '-Installer', str(exe), '-AppExe', str(installed_exe)]
""")
replace_exact(app_updates,
              """    flags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    with open(os.devnull, 'wb') as sink:
        subprocess.Popen(args, cwd=str(exe.parent), creationflags=flags,
                         stdin=subprocess.DEVNULL, stdout=sink, stderr=sink,
                         close_fds=True)
""",
              """    flags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    startup = quiet_powershell.minimized_startupinfo()
    with open(os.devnull, 'wb') as sink:
        subprocess.Popen(args, cwd=str(exe.parent), creationflags=flags,
                         startupinfo=startup,
                         stdin=subprocess.DEVNULL, stdout=sink, stderr=sink,
                         close_fds=True)
""")

# The existing installer launcher remains a windowed GUI EXE. We do not alter
# the desktop shortcut, Ollama permission model, or user-command PowerShell.
(TARGET / "POST_139_MINIMIZED_POWERSHELL_DEV_ONLY.txt").write_text(
    "Next update development: internal PowerShell updater helper launches "
    "minimized; user-requested terminals are unchanged. Test on actual "
    "Windows before any package publication.\n", encoding="utf-8")
print("Prepared post-13.9.0 minimized internal updater PowerShell candidate")
