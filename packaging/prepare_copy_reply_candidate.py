"""Stage optional per-message copy UI on the released v13.8.0 source.

No version bump, installer or GitHub Release: consolidate with the next larger
Falcon Ai update only after native Windows testing.
"""
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_App_V13_8_0"
TARGET = REPO / "build" / "Falcon_Ai_CopyReply_Candidate"

if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.8.0":
    raise SystemExit("Verified v13.8.0 source required")
if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(REPO / "packaging" / "message_copy.py", TARGET / "message_copy.py")


def replace_one(path, original, replacement):
    file = TARGET / path
    source = file.read_text(encoding="utf-8")
    if source.count(original) != 1:
        raise RuntimeError(f"Unexpected source anchor: {path}: {original!r}, count={source.count(original)}")
    file.write_text(source.replace(original, replacement, 1), encoding="utf-8")


replace_one("falcon.py",
            "from ollama_runtime import local_model_answer\n",
            "from ollama_runtime import local_model_answer\nimport message_copy\n")

replace_one(
    "falcon.py",
    "        self.log.insert('end', body, 'message_' + role)\n"
    "        self.log.insert('end', '\\n', 'message_gap')",
    "        self.log.insert('end', body, 'message_' + role)\n"
    "        if role == 'falcon':\n"
    "            message_copy.attach_copy_reply(\n"
    "                self.log, self.root, plain,\n"
    "                accent=self.ui_colors['purple'],\n"
    "                success=self.ui_colors['success'],\n"
    "                on_error=lambda err: self.append('Error', 'Could not copy reply: ' + err))\n"
    "        self.log.insert('end', '\\n', 'message_gap')"
)

(TARGET / "COPY_REPLY_CANDIDATE_ONLY.txt").write_text(
    "Prototype of per-Falcon-message Copy reply links. Not published. "
    "User v13.8.0 remains unchanged. Do not use as release without packaging tests.\n",
    encoding="utf-8",
)
print("Staged per-Falcon-reply copy links for next bundled release (no installation)")
