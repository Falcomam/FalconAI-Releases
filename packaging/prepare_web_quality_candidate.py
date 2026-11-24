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


replace_once("developer_workspace.py",
             "import stat\n",
             "import stat\nimport html_quality\n")
replace_once("developer_workspace.py",
             "        clean[path] = contents\n    canonical = json.dumps(",
             """        clean[path] = contents
    # Check browser markup WITHOUT running HTML, CSS or JavaScript. Generated
    # website source must pass this gate before the user can review/save it.
    quality_warnings = ()
    if kind == "website":
        try:
            quality_warnings = tuple(html_quality.check_website(clean))
        except html_quality.WebsiteQualityError as exc:
            raise ProjectError("Website quality check failed: " + str(exc)) from exc
    canonical = json.dumps(""")
replace_once("developer_workspace.py",
             '        "execution_allowed": False,\n',
             '        "execution_allowed": False,\n'
             '        "quality_warnings": quality_warnings,\n')
replace_once("developer_chat.py",
             '    "Minecraft Fabric projects are uncompiled starters, not working built mods. "\n',
             '    "For websites, include index.html with complete html, head, title and body tags, "\n'
             '    \'a complete <meta charset="UTF-8"> element, and working HTML structure. \'\n'
             '    "Every internal navigation href beginning with # must match an actual element id. "\n'
             '    "Do not invent real subscriptions: a subscribe button needs a real user-supplied "\n'
             '    "destination URL or must be clearly labeled as a demo button. "\n'
             '    "Do not include broken links, incomplete tags or placeholder content masquerading "\n'
             '    "as functional features. "\n'
             '    "Minecraft Fabric projects are uncompiled starters, not working built mods. "\n')
(TARGET / "WEB_QUALITY_CANDIDATE_ONLY.txt").write_text(
    "Conservative static website checking and quality-oriented prompts. "
    "No code execution and no released installer. Bundle after native Windows "
    "runtime and upgrade testing.\n",
    encoding="utf-8",
)
print("Prepared full HTML-quality next-bundle candidate (not released)")
