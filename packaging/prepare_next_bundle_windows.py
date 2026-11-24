"""Freeze the source and installer metadata for Falcon's NEXT Windows test candidate.

Not a release: this script stages files in build/ only. Windows CI must prove
frozen EXE, clean installer, and real 13.8.0 -> candidate upgrade/relaunch
with local data preserved. It must NEVER publish or replace a GitHub Release.
"""
from __future__ import annotations

from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_Browser_Candidate"
BASE_RUNTIME = REPO / "build" / "falcon_app_1380_runtime"
TARGET = REPO / "build" / "Falcon_Ai_NextBundle_Candidate"
RUNTIME = REPO / "build" / "falcon_app_next_bundle_candidate_runtime"
OLD_VERSION = "13.8.0"
TEST_VERSION = "13.9.0"

if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != OLD_VERSION:
    raise RuntimeError("Expected the tested 13.8.0-based combined Falcon source")
if not BASE_RUNTIME.is_dir():
    raise RuntimeError("Expected the verified 13.8.0 installer runtime")
for dest in (TARGET, RUNTIME):
    if dest.exists():
        shutil.rmtree(dest)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copytree(BASE_RUNTIME, RUNTIME, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))


def replace_exact(file, old, new, count=1):
    file = Path(file)
    data = file.read_text(encoding="utf-8")
    actual = data.count(old)
    if actual != count:
        raise RuntimeError(f"Changed next-bundle staging anchor {file}: "
                           f"expected {count} got {actual}: {old!r}")
    file.write_text(data.replace(old, new), encoding="utf-8")


def replace_gui_version(file):
    file = TARGET / file
    raw = file.read_text(encoding="utf-8")
    if f"V{OLD_VERSION}" not in raw:
        raise RuntimeError(f"Missing source-facing version in {file}")
    file.write_text(raw.replace(f"V{OLD_VERSION}", f"V{TEST_VERSION}"),
                    encoding="utf-8")


replace_gui_version("falcon.py")
replace_gui_version("falcon_launcher.py")
replace_exact(TARGET / "release_updates.py",
              "CURRENT_VERSION = (13, 8, 0)",
              "CURRENT_VERSION = (13, 9, 0)")
(TARGET / "RELEASE_VERSION.txt").write_text(TEST_VERSION + "\n", encoding="utf-8")

replace_exact(RUNTIME / "app_updates.py",
              "CURRENT_VERSION = (13, 8, 0)",
              "CURRENT_VERSION = (13, 9, 0)")
replace_exact(RUNTIME / "app_updates.py",
              "FalconAi-WindowsUpdater/13.8",
              "FalconAi-WindowsUpdater/13.9", count=2)
replace_exact(RUNTIME / "app_entry.py",
              "if app_updates.CURRENT_VERSION != (13, 8, 0):",
              "if app_updates.CURRENT_VERSION != (13, 9, 0):")
replace_exact(RUNTIME / "app_entry.py",
              "        import developer_chat\n",
              "        import developer_chat\n"
              "        import message_copy\n"
              "        import command_palette\n"
              "        import html_quality\n"
              "        import project_revision\n"
              "        import project_browser\n")
replace_exact(RUNTIME / "Falcon_Ai.iss",
              '#define MyAppVersion "13.8.0"',
              '#define MyAppVersion "13.9.0"')
replace_exact(RUNTIME / "Falcon_Ai.iss",
              "build\\falcon_app_1380_runtime\\Falcon_Ai_Icon.ico",
              "build\\falcon_app_next_bundle_candidate_runtime\\Falcon_Ai_Icon.ico")
# Ensure an old install's identity/AppId remains unchanged when incrementing.
old_installer = (BASE_RUNTIME / "Falcon_Ai.iss").read_text(encoding="utf-8")
new_installer = (RUNTIME / "Falcon_Ai.iss").read_text(encoding="utf-8")
old_id = [line.strip() for line in old_installer.splitlines()
          if line.strip().startswith("AppId=")]
new_id = [line.strip() for line in new_installer.splitlines()
          if line.strip().startswith("AppId=")]
if not old_id or old_id != new_id:
    raise RuntimeError("Windows installer AppId changed: upgrade unsafe")

required = {
    "developer_chat.py", "developer_workspace.py", "engine_manager.py",
    "message_copy.py", "command_palette.py", "html_quality.py",
    "project_revision.py", "project_browser.py", "falcon.py",
}
missing = sorted(x for x in required if not (TARGET / x).is_file())
if missing:
    raise RuntimeError(f"Missing bundled modules: {missing}")
gui = (TARGET / "falcon.py").read_text(encoding="utf-8")
chat = (TARGET / "developer_chat.py").read_text(encoding="utf-8")
if ("message_copy.attach_copy_reply(" not in gui
        or "command_palette.EntryController(" not in gui
        or "self._open_saved(payload)" not in chat
        or "revisions.save_revision_approved(" not in chat):
    raise RuntimeError("The next-bundle app lost a verified feature")

(TARGET / "NEXT_BUNDLE_TEST_CANDIDATE_ONLY.txt").write_text(
    "Development test candidate ONLY. Version 13.9.0 is RESERVED FOR "
    "WINdows packaging tests; it is NOT a public Falcon release. "
    "Do not hand to user before installer and upgrade/relaunch/data tests "
    "pass and a deliberate release gate is reviewed.\n",
    encoding="utf-8",
)
print("Staged Falcon next bundle version 13.9.0 source + matching installer "
      "metadata for Windows TESTING ONLY; no release, no installer published")
