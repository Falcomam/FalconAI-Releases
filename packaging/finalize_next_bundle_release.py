"""Finalize the tested Falcon 13.9.0 bundle metadata for a real Windows release.

Must run ONLY after prepare_next_bundle_windows.py. This does not publish.
Publication is a separately gated GitHub Windows workflow that must verify the
frozen EXE, clean install and upgrade/relaunch from the existing v13.8.0.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "build" / "Falcon_Ai_NextBundle_Candidate"
RUNTIME = REPO / "build" / "falcon_app_next_bundle_candidate_runtime"
VERSION = "13.9.0"

if (TARGET / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != VERSION:
    raise RuntimeError("Expected tested Falcon 13.9.0 candidate source")
iss = (RUNTIME / "Falcon_Ai.iss").read_text(encoding="utf-8")
if '#define MyAppVersion "13.9.0"' not in iss:
    raise RuntimeError("Expected matching Windows installer identity")
if "CURRENT_VERSION = (13, 9, 0)" not in (
        RUNTIME / "app_updates.py").read_text(encoding="utf-8"):
    raise RuntimeError("Expected matching installed updater version")
for module in (
    "developer_chat.py", "developer_workspace.py", "message_copy.py",
    "command_palette.py", "html_quality.py", "project_revision.py",
    "project_browser.py",
):
    if not (TARGET / module).is_file():
        raise RuntimeError("Bundled module missing: " + module)

marker = TARGET / "NEXT_BUNDLE_TEST_CANDIDATE_ONLY.txt"
if not marker.is_file():
    raise RuntimeError("Unreviewed candidate was not staged")
marker.unlink()
(TARGET / "README_FALCON_AI_V13_9_0.txt").write_text(
    "Falcon Ai 13.9.0 - BUNDLED UPDATE\n\n"
    " - Copy individual Falcon responses in the main chat.\n"
    " - Tab and Shift+Tab slash-command completion and grouped Commands menu.\n"
    " - Static website HTML validation before project save.\n"
    " - Open and inspect saved Falcon-owned developer projects in chat.\n"
    " - Review edits and additions to existing project source files with diffs.\n"
    " - Explicit approval, exact source fingerprints, backups and rollback.\n"
    " - Existing STOP and PC permission boundaries retained.\n"
    " - Generated project source is not run, built or installed automatically.\n"
    " - Optional editing may be limited by a small local model context size.\n"
    " - Local user data is kept outside the installed app directory.\n"
    " - Tested using Windows packaged build, clean install, and real upgrade.\n"
    " - User PC behavior still requires real user acceptance testing.\n"
    " - Unsigned Windows installer: SmartScreen warnings may appear.\n",
    encoding="utf-8",
)
print("Finalized reviewable Falcon Ai v13.9.0 bundled release metadata; "
      "this script does NOT publish or install anything.")
