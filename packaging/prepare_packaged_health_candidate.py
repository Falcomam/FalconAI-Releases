"""Stage corrected packaged diagnostics and legacy source-upgrade safety.

Based on post-13.9 development source, NOT a published installer. Existing
user-generated projects and Windows data are never modified by staging.
"""
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_QuietPowerShell_Candidate"
RUN_BASE = REPO / "build" / "falcon_app_quiet_powershell_runtime"
TARGET = REPO / "build" / "Falcon_Ai_Health_Candidate"
RUNTIME = REPO / "build" / "falcon_app_health_runtime"

if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.9.0":
    raise RuntimeError("Expected verified Falcon 13.9.0-based source")
for dest in (TARGET, RUNTIME):
    if dest.exists():
        shutil.rmtree(dest)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copytree(RUN_BASE, RUNTIME, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(REPO / "packaging" / "packaged_diagnostics.py",
             TARGET / "packaged_diagnostics.py")


def patch(path, old, new):
    file = Path(path)
    body = file.read_text(encoding="utf-8")
    count = body.count(old)
    if count != 1:
        raise RuntimeError(f"Health patch anchor changed: {file.name}, count={count}, {old[:65]!r}")
    file.write_text(body.replace(old, new, 1), encoding="utf-8")


# The frozen app resolves 'diagnostics' to its packaged health-check module.
# Source-based/legacy CLI Falcon still retains its own original diagnostics.
patch(RUNTIME / "app_entry.py",
      "sys.modules['release_updates'] = app_updates\n",
      """sys.modules['release_updates'] = app_updates
import packaged_diagnostics
sys.modules['diagnostics'] = packaged_diagnostics
""")

# The original Docker-based self-upgrader edits live loose .py files. It must
# not attempt to edit a frozen PyInstaller installation, even if diagnostics
# pass. User-facing Improve explains what is unsupported and why.
patch(TARGET / "improve_cycle.py",
      """        if 'Failed: none' not in str(summary):
            note('Core file checks failed. Improve cycle stopped; no patch generated.')
            finish('blocked: diagnostics')
            return last_goal,None
""",
      """        if 'Failed: none' not in str(summary):
            note('Core file checks failed. Improve cycle stopped; no patch generated.')
            finish('blocked: diagnostics')
            return last_goal,None
        import sys
        if getattr(sys, 'frozen', False):
            note('The packaged Falcon EXE passed runtime checks, but the legacy '
                 'source-file Docker Improve feature cannot safely patch the '
                 'installed EXE. No code has changed. Use /project for code '
                 'proposals or Check Updates for verified bundled app releases.')
            finish('blocked: packaged source-upgrade unsupported')
            return last_goal, None
""")

# Source edits must never silently target bundled read-only .py pseudo-paths.
patch(TARGET / "core_upgrade.py",
      """    emit=log or (lambda text: None)
    if not isinstance(goal,str) or not 10<=len(goal.strip())<=750:
""",
      """    if getattr(sys, 'frozen', False):
        raise UpgradeError('Source-file self-upgrade is unavailable in packaged Falcon Ai. '
                           'Use Developer Mode or verified installer updates.')
    emit=log or (lambda text: None)
    if not isinstance(goal,str) or not 10<=len(goal.strip())<=750:
""")
patch(TARGET / "core_upgrade.py",
      """def install_approved(folder):
    """ + '"""Call ONLY after explicit UI approval AND preview. User must restart."""' + """
    _, manifest, newer, old = _load_draft(folder)
""",
      """def install_approved(folder):
    """ + '"""Call ONLY after explicit UI approval AND preview. User must restart."""' + """
    if getattr(sys, 'frozen', False):
        raise UpgradeError('Cannot install source patches into a frozen Falcon EXE')
    _, manifest, newer, old = _load_draft(folder)
""")
patch(TARGET / "core_upgrade.py",
      """def rollback_last():
    history=_history()
""",
      """def rollback_last():
    if getattr(sys, 'frozen', False):
        raise UpgradeError('Legacy source rollback is unavailable in the packaged Falcon EXE')
    history=_history()
""")

# Add a direct frozen self-test hook so Windows CI checks THE SAME diagnostics
# path the user invokes, not only imports. Never opens the UI or installs code.
patch(RUNTIME / "app_entry.py",
      "def main():\n",
      """def main():
    if '--falcon-diagnostics-self-test' in sys.argv:
        import pathlib
        report, summary = packaged_diagnostics.run()
        if "13/13" not in summary or "Failed: none" not in summary:
            raise RuntimeError('Frozen runtime diagnostics failed: ' + summary)
        print("FALCON PACKAGED DIAGNOSTICS PASSED: " + summary)
        return 0
""")
(TARGET / "POST_139_PACKAGED_DIAGNOSTICS_DEV_ONLY.txt").write_text(
    "Fixes 0/13 legacy self-check when installed as a frozen Windows EXE. "
    "11 bundled module-loader checks + GUI EXE + updater helper. Legacy "
    "source-editing Improve is explicitly blocked for EXE installs. "
    "No source patch runs or self-installs. Not yet released.\n",
    encoding="utf-8",
)
print("Staged bundled Falcon health check, explicit frozen-EXE Improve limit, no install")
