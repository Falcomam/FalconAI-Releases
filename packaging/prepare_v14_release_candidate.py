"""Stage Falcon AI V14.0.0 from the verified V13.9.1 health candidate.

This script writes ONLY build/ staging folders and never publishes, installs,
runs model-generated code, modifies existing app installations or local data.
The caller must have reconstructed and finalized 13.9.1 source/runtime first.
"""
from __future__ import annotations

from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / "build" / "Falcon_Ai_Health_Candidate"
BASE_RUNTIME = REPO / "build" / "falcon_app_health_runtime"
TARGET = REPO / "build" / "Falcon_Ai_V14_Candidate"
RUNTIME = REPO / "build" / "falcon_app_v14_runtime"
PREVIOUS = "13.9.1"
VERSION = "14.0.0"


def replace_exact(file: Path, old: str, new: str, count: int = 1):
    data = file.read_text(encoding="utf-8")
    if data.count(old) != count:
        raise RuntimeError(
            f"V14 release staging anchor changed: {file.name}: {old!r}, "
            f"expected {count} actual {data.count(old)}"
        )
    file.write_text(data.replace(old, new), encoding="utf-8")


def replace_visible_versions(path: Path):
    raw = path.read_text(encoding="utf-8")
    if "V13.9.0" not in raw:
        raise RuntimeError("Expected previous Falcon UI/launcher version in " + path.name)
    path.write_text(raw.replace("V13.9.0", "V14.0.0"), encoding="utf-8")


def app_id(path: Path):
    ids = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
           if line.lstrip().startswith("AppId=")]
    if len(ids) != 1:
        raise RuntimeError("Installer AppId is missing or ambiguous")
    return ids[0]


def main():
    if (BASE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != PREVIOUS:
        raise RuntimeError("Expected exact verified 13.9.1 base source")
    if "CURRENT_VERSION = (13, 9, 1)" not in (BASE_RUNTIME / "app_updates.py").read_text(encoding="utf-8"):
        raise RuntimeError("Expected exact verified 13.9.1 updater")
    if "CURRENT_VERSION != (13, 9, 1)" not in (BASE_RUNTIME / "app_entry.py").read_text(encoding="utf-8"):
        raise RuntimeError("Expected exact verified 13.9.1 runtime entry")
    if '#define MyAppVersion "13.9.1"' not in (BASE_RUNTIME / "Falcon_Ai.iss").read_text(encoding="utf-8"):
        raise RuntimeError("Expected verified prior installer version")
    required = (
        "falcon_foundation.py", "gaming_mode.py", "site_design_check.py",
        "developer_chat.py", "developer_workspace.py", "project_static_check.py",
        "engine_manager.py", "project_targeted_edits.py",
        "project_browser.py", "project_revision.py", "release_updates.py",
        "packaged_diagnostics.py", "core_upgrade.py", "improve_cycle.py",
    )
    absent = [name for name in required if not (BASE / name).is_file()]
    if absent:
        raise RuntimeError("Missing V14 core stage modules: " + ", ".join(absent))
    imported = (BASE / "developer_chat.py").read_text(encoding="utf-8")
    if ("import falcon_foundation" not in imported or
            'return "foundation", ""' not in imported or
            "gaming_mode.enabled()" not in imported):
        raise RuntimeError("V14 foundation command or Gaming Mode integration missing")

    for directory in (TARGET, RUNTIME):
        if directory.exists():
            shutil.rmtree(directory)
    shutil.copytree(BASE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
    shutil.copytree(BASE_RUNTIME, RUNTIME,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))

    from stage_shorts import stage_shorts
    stage_shorts(REPO / "packaging", TARGET)

    replace_visible_versions(TARGET / "falcon.py")
    replace_visible_versions(TARGET / "falcon_launcher.py")
    replace_exact(TARGET / "release_updates.py",
                  "CURRENT_VERSION = (13, 9, 0)", "CURRENT_VERSION = (14, 0, 0)")
    replace_exact(TARGET / "RELEASE_VERSION.txt", PREVIOUS, VERSION)
    replace_exact(RUNTIME / "app_updates.py",
                  "CURRENT_VERSION = (13, 9, 1)", "CURRENT_VERSION = (14, 0, 0)")
    replace_exact(RUNTIME / "app_entry.py",
                  "CURRENT_VERSION != (13, 9, 1)", "CURRENT_VERSION != (14, 0, 0)")
    # Frozen self-test checks the actual V14 packaged foundation, not merely a
    # loose source file. Does not launch GUI, make model requests or write data.
    entry_path = RUNTIME / "app_entry.py"
    entry_text = entry_path.read_text(encoding="utf-8")
    gate = "    if '--falcon-diagnostics-self-test' in sys.argv:\n"
    if entry_text.count(gate) != 1:
        raise RuntimeError("Missing unique frozen health self-test entry anchor")
    foundation_gate = (
        "    if '--falcon-foundation-self-test' in sys.argv:\n"
        "        import falcon_foundation\n"
        "        from pathlib import Path\n"
        "        version_file = Path(getattr(sys, '_MEIPASS', '')) / 'RELEASE_VERSION.txt'\n"
        "        if (not falcon_foundation.check_contract() or\n"
        "                version_file.read_text(encoding='utf-8').strip() != '14.0.0'):\n"
        "            raise RuntimeError('V14 packaged foundation contract mismatch')\n"
        "        print('FALCON V14 FOUNDATION PACKAGED CHECK PASSED')\n"
        "        return 0\n"
    )
    entry_path.write_text(entry_text.replace(gate, foundation_gate + gate, 1),
                          encoding="utf-8")
    replace_exact(RUNTIME / "Falcon_Ai.iss",
                  '#define MyAppVersion "13.9.1"',
                  '#define MyAppVersion "14.0.0"')
    iss = RUNTIME / "Falcon_Ai.iss"
    raw = iss.read_text(encoding="utf-8")
    old_icon = r"build\falcon_app_next_bundle_candidate_runtime\Falcon_Ai_Icon.ico"
    if old_icon not in raw:
        raise RuntimeError("V14 installer icon runtime path changed")
    iss.write_text(raw.replace(old_icon, r"build\falcon_app_v14_runtime\Falcon_Ai_Icon.ico"), encoding="utf-8")
    if app_id(iss) != app_id(BASE_RUNTIME / "Falcon_Ai.iss"):
        raise RuntimeError("V14 installer changed Windows AppId; in-place upgrade is unsafe")
    # No historical development-only markers should ship inside a public app.
    for file in TARGET.glob("*.txt"):
        if file.name.endswith(("_CANDIDATE_ONLY.txt", "_DEV_ONLY.txt",
                               "_NOT_RELEASED.txt")):
            file.unlink()
    (TARGET / "README_FALCON_AI_V14.txt").write_text(
        "Falcon AI V14.0.0 — Foundation Release\n"
        "One purple chat, honest /foundation status, independent coding model,\n"
        "explicit Gaming Mode, reviewed source projects, static design warnings,\n"
        "safe source revisions, STOP, 13 packaged health checks and trusted updates.\n"
        "Generated code is NOT executed or installed automatically.\n"
        "Browser screenshot critic, isolated project test execution and full\n"
        "autonomous app/mod packaging are not implemented.\n"
        "Gaming Mode unload is best effort; game FPS is not guaranteed.\n"
        "Changes require a verified release and Windows user approval.\n",
        encoding="utf-8"
    )
    import v14_release_checks
    v14_release_checks.verify(TARGET, RUNTIME, previous_installer=BASE_RUNTIME / "Falcon_Ai.iss")
    print("Staged Falcon AI V14.0.0 Windows source and installer metadata. NO INSTALL OR PUBLISH.")


if __name__ == "__main__":
    main()
