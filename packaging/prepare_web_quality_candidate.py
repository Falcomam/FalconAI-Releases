"""Stage HTML-quality gate atop the existing v13.8 next-bundle candidate.

Not a public release. All generated project files remain inert until a user
reviews them and explicitly approves saving to Falcon-owned workspace.
"""
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_CommandPalette_Candidate"
TARGET = REPO / "build" / "Falcon_Ai_WebQuality_Candidate"

if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.8.0":
    raise SystemExit("Verified 13.8.0 next-bundle candidate required")
if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(REPO / "packaging" / "html_quality.py", TARGET / "html_quality.py")


def replace_once(path, old, new):
    file = TARGET / path
    data = file.read_text(encoding="utf-8")
    if data.count(old) != 1:
        raise RuntimeError(f"Changed Falcon source anchor {path}: count={data.count(old)}: {old[:90]}")
    file.write_text(data.replace(old, new, 1), encoding="utf-8")


# The base v13.8 staging script may already use the latest packaged
# developer_workspace.py and developer_chat.py sources. Do not double-patch
# a module that has already been updated on main by another development sprint.
workspace = (TARGET / "developer_workspace.py").read_text(encoding="utf-8")
if "import html_quality" not in workspace:
    replace_once("developer_workspace.py", "import stat\n",
                 "import stat\nimport html_quality\n")
    workspace = (TARGET / "developer_workspace.py").read_text(encoding="utf-8")
if "quality_warnings" not in workspace:
    replace_once("developer_workspace.py",
                 "        clean[path] = contents\n    canonical = json.dumps(",
                 """        clean[path] = contents
    quality_warnings = ()
    if kind == "website":
        try:
            quality_warnings = tuple(html_quality.check_website(clean))
        except html_quality.WebsiteQualityError as exc:
            raise ProjectError("Website HTML validation failed: " + str(exc)) from exc
    canonical = json.dumps(""")
    replace_once("developer_workspace.py",
                 '        "execution_allowed": False,\n',
                 '        "execution_allowed": False,\n'
                 '        "quality_warnings": quality_warnings,\n')
chat = (TARGET / "developer_chat.py").read_text(encoding="utf-8")
if "For website projects, always include index.html" not in chat:
    replace_once("developer_chat.py",
                 '    "Minecraft Fabric projects are uncompiled starters, not working built mods. "\n',
                 '    "For website projects, always include index.html with complete HTML, "\n'
                 '    "a valid UTF-8 meta charset, correct links and no fake functionality. "\n'
                 '    "Minecraft Fabric projects are uncompiled starters, not working built mods. "\n')
# Always require the actual integration outcome; neither a skip nor a partial
# patch should allow invalid website source to be offered to the user.
workspace = (TARGET / "developer_workspace.py").read_text(encoding="utf-8")
chat = (TARGET / "developer_chat.py").read_text(encoding="utf-8")
assert "import html_quality" in workspace
assert "quality_warnings" in workspace
assert "check_website(clean)" in workspace
assert "website projects" in chat or "For websites" in chat

(TARGET / "WEB_QUALITY_CANDIDATE_ONLY.txt").write_text(
    "Conservative static website checking and quality-oriented prompts. "
    "No code execution and no released installer. Bundle after native Windows "
    "runtime and upgrade testing.\n",
    encoding="utf-8",
)
print("Prepared full HTML-quality next-bundle candidate (not released)")
