"""Prepare Falcon Ai V13.8.0 combined Windows release from verified 13.7.1.

This stage alone does not publish. CI must pass source unit/regression tests,
native EXE and Windows installer tests and real 13.7.1-to-13.8.0 upgrade.
Preserves the verified 13.7.1 source and the existing installer AppId.
"""
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_SingleChat_Candidate"
TARGET = REPO / "build" / "Falcon_Ai_App_V13_8_0"
RUNTIME_OLD = REPO / "build" / "falcon_app_1371_runtime"
RUNTIME = REPO / "build" / "falcon_app_1380_runtime"

if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.7.1":
    raise RuntimeError("Verified single-chat 13.7.1 candidate base required")
for stale in (TARGET, RUNTIME):
    if stale.exists():
        shutil.rmtree(stale)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
RUNTIME.mkdir(parents=True)
for icon in ("Falcon_Ai_Icon.ico", "Falcon_Ai_Icon.png"):
    shutil.copy2(RUNTIME_OLD / icon, RUNTIME / icon)


def change(path, old, new):
    dest = Path(path)
    raw = dest.read_text(encoding="utf-8")
    count = raw.count(old)
    if count != 1:
        raise RuntimeError(f"Version patch anchor changed: {dest}: {old!r}, count {count}")
    dest.write_text(raw.replace(old, new, 1), encoding="utf-8")


for old, new in (
    ("Falcon Ai V13.7.1 — Command Center", "Falcon Ai V13.8.0 — Command Center"),
    ("Falcon Ai V13.7.1 ready.", "Falcon Ai V13.8.0 ready."),
    ("V13.7.1  /  LOCAL JARVIS", "V13.8.0  /  LOCAL JARVIS"),
):
    change(TARGET / "falcon.py", old, new)
change(TARGET / "falcon_launcher.py", "Starting Falcon Ai V13.7.1",
       "Starting Falcon Ai V13.8.0")
change(TARGET / "release_updates.py", "CURRENT_VERSION = (13, 7, 1)",
       "CURRENT_VERSION = (13, 8, 0)")
(TARGET / "RELEASE_VERSION.txt").write_text("13.8.0\n", encoding="utf-8")
for marker in ("SINGLE_CHAT_DEV_ONLY.txt", "ENGINE_CANDIDATE_NOT_RELEASED.txt"):
    (TARGET / marker).unlink(missing_ok=True)

# Replace the old package-only runtime entry with V13.8.0, preserving the
# loaded installer updater and purple icon assertions from V13.7.1.
entry = (RUNTIME_OLD / "app_entry_engine_candidate.py").read_text(encoding="utf-8")
if entry.count("(13, 7, 1)") != 1:
    raise RuntimeError("Packaged entry version self-test anchor changed")
entry = entry.replace("(13, 7, 1)", "(13, 8, 0)")
entry = entry.replace("V13.7.1 PACKAGED", "V13.8.0 PACKAGED")
needle = "        import ollama_runtime\n"
if entry.count(needle) != 1:
    raise RuntimeError("Packaged entry module import anchor changed")
entry = entry.replace(
    needle,
    needle +
    "        import engine_manager\n"
    "        import developer_workspace\n"
    "        import developer_chat\n",
    1
)
(RUNTIME / "app_entry.py").write_text(entry, encoding="utf-8")

updates = (REPO / "packaging" / "app_updates.py").read_text(encoding="utf-8")
if updates.count("CURRENT_VERSION = (13, 7, 0)") != 1:
    raise RuntimeError("Updater version anchor changed")
updates = updates.replace("CURRENT_VERSION = (13, 7, 0)", "CURRENT_VERSION = (13, 8, 0)")
updates = updates.replace("FalconAi-WindowsUpdater/13.7", "FalconAi-WindowsUpdater/13.8")
(RUNTIME / "app_updates.py").write_text(updates, encoding="utf-8")

iss = (RUNTIME_OLD / "Falcon_Ai.iss").read_text(encoding="utf-8")
if iss.count('#define MyAppVersion "13.7.1"') != 1:
    raise RuntimeError("Installed-app identity version anchor changed")
iss = iss.replace('#define MyAppVersion "13.7.1"', '#define MyAppVersion "13.8.0"')
iss = iss.replace("build\\falcon_app_1371_runtime\\Falcon_Ai_Icon.ico",
                  "build\\falcon_app_1380_runtime\\Falcon_Ai_Icon.ico")
if "falcon_app_1380_runtime" not in iss:
    raise RuntimeError("Missing purple Falcon 13.8.0 installer icon path")
(RUNTIME / "Falcon_Ai.iss").write_text(iss, encoding="utf-8")

(TARGET / "README_V13_8_0.txt").write_text(
    "Falcon Ai 13.8.0 BUNDLED RELEASE\n\n"
    " - Local Ollama health check, offline status and explicit server launch\n"
    " - Select installed Qwen or Llama chat model without changing permissions\n"
    " - One conversation for local PC tools and multi-file Developer Mode\n"
    " - Review individual source files in chat, then explicitly approve saving\n"
    " - Python/website/Fabric starter file creation, syntax and path checks\n"
    " - Generated files are inert: no execution, deployment or installation\n"
    " - Existing purple icon, Windows installer update and STOP retained\n"
    " - Changes are not automatically tested on the user's own hardware\n",
    encoding="utf-8",
)
print("Prepared Falcon Ai V13.8.0 combined-release staging (not published)")
