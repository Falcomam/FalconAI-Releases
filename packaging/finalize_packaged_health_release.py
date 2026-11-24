"""Finalize an already-validated packaged-health candidate as a 13.9.1 release candidate.

Does not publish, install, or touch user data. Fail closed on changed anchors.
Run only after prepare_packaged_health_candidate.py and its Windows CI gates.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_Health_Candidate"
RUNTIME = REPO / "build" / "falcon_app_health_runtime"

def replace_exact(path: Path, old: str, new: str):
    value = path.read_text(encoding="utf-8")
    if value.count(old) != 1:
        raise RuntimeError(f"Release identity anchor mismatch in {path.name}: {old!r}")
    path.write_text(value.replace(old, new, 1), encoding="utf-8")

def main():
    if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.9.0":
        raise RuntimeError("Expected post-13.9 verified candidate")
    required = ("falcon.py", "core_upgrade.py", "improve_cycle.py",
                "packaged_diagnostics.py", "project_search.py")
    for module in required:
        if not (SOURCE / module).is_file():
            raise RuntimeError("Required candidate module missing: " + module)
    entry = RUNTIME / "app_entry.py"
    if "sys.modules['diagnostics'] = packaged_diagnostics" not in entry.read_text(encoding="utf-8"):
        raise RuntimeError("Packaged diagnostics not wired into app entry")
    if "--falcon-diagnostics-self-test" not in entry.read_text(encoding="utf-8"):
        raise RuntimeError("Frozen diagnostics CI hook missing")
    improve = (SOURCE / "improve_cycle.py").read_text(encoding="utf-8")
    if "blocked: packaged source-upgrade unsupported" not in improve:
        raise RuntimeError("Self-upgrade frozen safety guard missing")
    # Check every anchor BEFORE writing anything.
    changes = [
        (SOURCE / "RELEASE_VERSION.txt", "13.9.0", "13.9.1"),
        (RUNTIME / "app_updates.py", "CURRENT_VERSION = (13, 9, 0)", "CURRENT_VERSION = (13, 9, 1)"),
        (RUNTIME / "Falcon_Ai.iss", '#define MyAppVersion "13.9.0"', '#define MyAppVersion "13.9.1"'),
        (entry, "CURRENT_VERSION != (13, 9, 0)", "CURRENT_VERSION != (13, 9, 1)"),
    ]
    for path, old, _ in changes:
        if path.read_text(encoding="utf-8").count(old) != 1:
            raise RuntimeError(f"Release version anchor mismatch: {path.name} -> {old!r}")
    for path, old, new in changes:
        replace_exact(path, old, new)
    (SOURCE / "README_FALCON_AI_V13_9_1.txt").write_text(
        "Falcon Ai V13.9.1 - packaged diagnostics repair\n"
        "- Replaces legacy loose .py/.bat self-checks with 13 packaged runtime checks.\n"
        "- Guards legacy Auto Improve from modifying an installed frozen EXE.\n"
        "- Adds a frozen EXE diagnostic self-test used by Windows release CI.\n"
        "- Includes post-13.9 project search and quieter internal updater shell.\n"
        "- Keeps local Ollama, one purple chat, STOP and permission boundaries.\n"
        "- Code changes are never installed without a verified released update.\n",
        encoding="utf-8",
    )
    print("13.9.1 health RELEASE CANDIDATE staged; NOT published or installed.")

if __name__ == "__main__":
    main()
