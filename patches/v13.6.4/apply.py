"""V13.6.4: Mini Monitor and use the proven restart helper after updates."""
from pathlib import Path
import re
import shutil

repo = Path(__file__).resolve().parents[2]
source = repo / "build" / "Falcon_AI_V13_6_3"
target = repo / "build" / "Falcon_AI_V13_6_4"
assert (source / "RELEASE_VERSION.txt").read_text().strip() == "13.6.3"
if target.exists():
    shutil.rmtree(target)
shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

def replace(rel, old, new):
    file = target / rel
    text = file.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"Anchor mismatch {rel}: {old[:85]!r}; found {text.count(old)}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")

# PowerShell variables are case-insensitive. $home conflicts with read-only $HOME,
# so replace EVERY reference, including the initial assignment and diagnostic logs.
updater = target / "APPLY_RELEASE_UPDATE.ps1"
ps = updater.read_text(encoding="utf-8")
matches = len(re.findall(r"\$home\b", ps, flags=re.IGNORECASE))
if matches < 3:
    raise RuntimeError(f"Expected $home in existing updater; found {matches}")
ps = re.sub(r"\$home\b", "$falconData", ps, flags=re.IGNORECASE)
# Use the ALREADY-TESTED, user-invoked restart helper. It outlives the
# GUI, waits for the old PID, launches Falcon, and writes its own log.
start = ps.index("    # Relaunch without a visible console or stealing focus from games.")
end = ps.index("    exit 0", start) + len("    exit 0")
ps = ps[:start] + """    # Launch the same helper used by the verified manual Restart button.
    # The helper runs without a console and records the actual launch result.
    $pythonw = Join-Path $Live '.venv\\Scripts\\pythonw.exe'
    $restartHelper = Join-Path $Live 'restart_helper.py'
    if (-not (Test-Path -LiteralPath $pythonw) -or
        -not (Test-Path -LiteralPath $restartHelper)) {
      throw 'Updated Falcon missing Python GUI interpreter or restart helper'
    }
    Log ('Starting verified restart helper: ' + $restartHelper)
    $restartProc = Start-Process -FilePath $pythonw -ArgumentList @('"' + $restartHelper + '"', [string]$WaitPid) -WorkingDirectory $Live -PassThru
    Log ('Restart helper started with PID ' + $restartProc.Id)
    Start-Sleep -Seconds 4
    $restartProc.Refresh()
    if ($restartProc.HasExited -and $restartProc.ExitCode -ne 0) {
      throw ('Restart helper failed with code ' + $restartProc.ExitCode)
    }
    Log 'Restart helper dispatched; see FalconAI\\logs\\restart.log for launcher results'
    exit 0""" + ps[end:]
if "$home" in ps.lower():
    raise RuntimeError("Read-only HOME variable remains")
updater.write_text(ps, encoding="utf-8")

(target / "mini_monitor.py").write_text(r'''"""Optional compact Falcon activity monitor. Uses real GUI status, not synthetic progress."""
import tkinter as tk

COLORS = {
    "base": "#151224", "panel": "#211b35", "accent": "#b69aff",
    "text": "#f6f1ff", "muted": "#b5a8cd", "danger": "#ff859f",
}

class MiniMonitor:
    def __init__(self, app):
        self.app = app
        self.window = tk.Toplevel(app.root)
        self.window.title("Falcon AI | Mini Monitor")
        self.window.geometry("340x230+64+70")
        self.window.minsize(300, 200)
        self.window.configure(bg=COLORS["base"])
        self.window.attributes("-topmost", True)
        self.window.protocol("WM_DELETE_WINDOW", self.hide)

        header = tk.Frame(self.window, bg=COLORS["base"])
        header.pack(fill="x", padx=16, pady=(13, 5))
        tk.Label(header, text="◆ FALCON  |  LIVE ACTIVITY", bg=COLORS["base"],
                 fg=COLORS["accent"], font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(header, text="—", command=self.hide, bg=COLORS["base"],
                  fg=COLORS["muted"], relief="flat", borderwidth=0).pack(side="right")

        body = tk.Frame(self.window, bg=COLORS["panel"], padx=13, pady=13)
        body.pack(fill="both", expand=True, padx=12, pady=7)
        tk.Label(body, text="CURRENT STATUS", bg=COLORS["panel"],
                 fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.status = tk.Label(body, text="Ready", bg=COLORS["panel"],
                               fg=COLORS["text"], font=("Segoe UI", 11, "bold"),
                               anchor="w", justify="left", wraplength=282)
        self.status.pack(fill="x", pady=(7, 5))
        self.hint = tk.Label(body, text="Shows Falcon's real status messages.",
                             bg=COLORS["panel"], fg=COLORS["muted"],
                             font=("Segoe UI", 9), justify="left", anchor="w",
                             wraplength=282)
        self.hint.pack(fill="x")

        bar = tk.Frame(self.window, bg=COLORS["base"])
        bar.pack(fill="x", padx=12, pady=(3, 12))
        tk.Button(bar, text="Open Falcon", command=self.open_main,
                  bg="#423064", fg=COLORS["text"], relief="flat", padx=10,
                  font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(bar, text="STOP", command=app.stop, bg="#593041",
                  fg=COLORS["danger"], relief="flat", padx=14,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=8)
        self.pinned = tk.BooleanVar(value=True)
        tk.Checkbutton(bar, text="Pin", variable=self.pinned,
                       command=self.toggle_pin, bg=COLORS["base"],
                       fg=COLORS["muted"], activebackground=COLORS["base"],
                       activeforeground=COLORS["text"], selectcolor=COLORS["panel"],
                       font=("Segoe UI", 9)).pack(side="right")
        self.update_status(app.status.cget("text"))
        self.window.withdraw()  # Optional: user must explicitly open it.

    def toggle_pin(self):
        if self.window.winfo_exists():
            self.window.attributes("-topmost", bool(self.pinned.get()))

    def update_status(self, msg):
        if not self.window.winfo_exists():
            return
        message = str(msg).lstrip("●  ").strip() or "Ready"
        self.status.configure(text=message[:170])
        if "error" in message.casefold() or "failed" in message.casefold():
            self.hint.configure(text="Falcon reported an error. Open the main window for details.")
        elif "ready" in message.casefold() or "stopped" in message.casefold():
            self.hint.configure(text="No active task reported.")
        else:
            self.hint.configure(text="Live status from Falcon. No estimated progress.")

    def show(self):
        if not self.window.winfo_exists():
            return
        self.update_status(self.app.status.cget("text"))
        self.window.deiconify()
        self.window.lift()

    def hide(self):
        if self.window.winfo_exists():
            self.window.withdraw()

    def open_main(self):
        root = self.app.root
        root.deiconify()
        root.lift()
        root.focus_force()

    def close(self):
        if self.window.winfo_exists():
            self.window.destroy()
''', encoding="utf-8")

replace("falcon.py",
        "            ('↻   Restart Falcon', self.restart_falcon),",
        "            ('↻   Restart Falcon', self.restart_falcon),\n            ('◇   Mini Monitor', self.open_mini_monitor),")
replace("falcon.py",
        "        updates.add_command(label='Restart Falcon', command=self.restart_falcon)",
        "        updates.add_command(label='Restart Falcon', command=self.restart_falcon)\n        updates.add_command(label='Mini Monitor', command=self.open_mini_monitor)")
replace("falcon.py",
        "    def restart_falcon(self):\n",
        """    def open_mini_monitor(self):
        if getattr(self, 'mini_monitor', None) is None:
            from mini_monitor import MiniMonitor
            self.mini_monitor = MiniMonitor(self)
        self.mini_monitor.show()

    def restart_falcon(self):
""")
replace("falcon.py",
        "        self.status.configure(text='●  ' + message, fg=color)",
        """        self.status.configure(text='●  ' + message, fg=color)
        monitor = getattr(self, 'mini_monitor', None)
        if monitor is not None:
            monitor.update_status(message)""")
replace("falcon.py",
        "    def on_close(self):\n        self.stop()",
        """    def on_close(self):
        if getattr(self, 'mini_monitor', None) is not None:
            self.mini_monitor.close()
        self.stop()""")
replace("release_updates.py", "CURRENT_VERSION = (13, 6, 3)", "CURRENT_VERSION = (13, 6, 4)")
for old, new in (
    ("Falcon AI V13.6.3 — Command Center", "Falcon AI V13.6.4 — Command Center"),
    ("Falcon V13.6.3 ready.", "Falcon V13.6.4 ready."),
    ("V13.6.3  /  LOCAL JARVIS", "V13.6.4  /  LOCAL JARVIS"),
):
    replace("falcon.py", old, new)
(target / "RELEASE_VERSION.txt").write_text("13.6.4\n", encoding="utf-8")
for rel in ("tests/test_v135_permanent.py", "tests/test_v131_updates.py",
            "tests/test_v1361_restart.py", "tests/test_v1362_restart.py",
            "tests/test_v1363_restart_button.py"):
    path = target / rel
    text = path.read_text(encoding="utf-8")
    text = text.replace("(13,6,3)", "(13,6,4)").replace("(13, 6, 3)", "(13, 6, 4)")
    text = text.replace("13.6.3", "13.6.4").replace("Falcon_AI_V13_6_3/", "Falcon_AI_V13_6_4/")
    path.write_text(text, encoding="utf-8")
(target / "tests" / "test_v1364_monitor.py").write_text(
    """from pathlib import Path
import unittest
import release_updates

ROOT = Path(__file__).resolve().parents[1]
class MonitorTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(release_updates.CURRENT_VERSION,(13,6,4))
        self.assertEqual((ROOT/'RELEASE_VERSION.txt').read_text().strip(),'13.6.4')
    def test_monitor(self):
        ui=(ROOT/'falcon.py').read_text(encoding='utf-8')
        mini=(ROOT/'mini_monitor.py').read_text(encoding='utf-8')
        self.assertIn('def open_mini_monitor(', ui)
        self.assertIn('monitor.update_status(message)', ui)
        self.assertIn('window.withdraw()', mini)
        self.assertIn('command=app.stop', mini)
        self.assertIn('attributes("-topmost"', mini)
    def test_restart_uses_existing_helper(self):
        ps=(ROOT/'APPLY_RELEASE_UPDATE.ps1').read_text(encoding='utf-8')
        self.assertNotIn('$home', ps.lower())
        self.assertIn('restart_helper.py', ps)
        self.assertIn("Start-Process -FilePath $pythonw", ps)
        self.assertIn('Move-Item -LiteralPath $backup -Destination $Live', ps)
        self.assertIn('Log ', ps)
""", encoding="utf-8")
(target / "FOLDER_GUIDE.txt").write_text(
    "PROJECT FALCON - APP LAYOUT\n"
    "START_HERE.bat             Manual launcher\n"
    "falcon.py                  Main purple UI\n"
    "mini_monitor.py            Optional floating live status\n"
    "falcon_launcher.py         GUI bootstrap + duplicate guard\n"
    "restart_helper.py          Proven button and update relaunch helper\n"
    "APPLY_RELEASE_UPDATE.ps1   Approved update installer (backup/rollback)\n"
    "release_updates.py         GitHub release verification\n"
    "tests/                     Regression suite\n"
    "LOCALAPPDATA/FalconAI/logs/  Local diagnostics, separate from app\n"
    "FalconAI.previous          Single backup next to installation\n"
    "Do not move launcher, helper, or files until Falcon is closed.\n",
    encoding="utf-8")
print("Built 13.6.4 with optional mini monitor and shared restart helper")
