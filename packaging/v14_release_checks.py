"""Fail-closed V14 source/runtime consistency gate for Windows staging.

Static only: does not execute model code, touch user data or publish release.
The Windows CI workflow must additionally run frozen tests, installer, upgrade.
"""
from __future__ import annotations

from pathlib import Path
import re

VERSION = "14.0.0"
UPDATE_TUPLE = "(14, 0, 0)"
REQUIRED = (
    "falcon.py", "falcon_launcher.py", "release_updates.py",
    "falcon_foundation.py", "developer_chat.py", "developer_workspace.py",
    "developer_generation.py", "engine_manager.py",
    "gaming_mode.py", "site_design_check.py", "html_quality.py",
    "project_browser.py", "project_revision.py", "project_targeted_edits.py",
    "project_static_check.py", "packaged_diagnostics.py", "core_upgrade.py",
    "improve_cycle.py", "RELEASE_VERSION.txt",
)


class ContractError(RuntimeError):
    pass


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def installer_id(text):
    fields = re.findall(r"^\s*AppId\s*=\s*(.+?)\s*$", text, re.M)
    if len(fields) != 1:
        raise ContractError("Windows installer AppId missing or ambiguous")
    return fields[0]


def verify(source, runtime, *, previous_installer=None):
    """Reject absent files, inconsistent versions, regressions and staging markers."""
    source = Path(source)
    runtime = Path(runtime)
    missing = [name for name in REQUIRED if not (source / name).is_file()]
    if missing:
        raise ContractError("Incomplete V14 source: " + ", ".join(missing))
    if _read(source / "RELEASE_VERSION.txt").strip() != VERSION:
        raise ContractError("V14 release metadata does not match")
    if 'VERSION = "14.0.0"' not in _read(source / "falcon_foundation.py"):
        raise ContractError("Foundation module version mismatched")
    gui = _read(source / "falcon.py")
    launcher = _read(source / "falcon_launcher.py")
    chat = _read(source / "developer_chat.py")
    planner = _read(source / "agent.py")
    improve = _read(source / "improve_cycle.py")
    if ("V14.0.0" not in gui or "Starting Falcon Ai V14.0.0" not in launcher):
        raise ContractError("UI or startup-log version still stale")
    if any(old in gui or old in launcher for old in ("V13.9.0", "V13.9.1")):
        raise ContractError("Previous UI identity is still visible")
    if ("CURRENT_VERSION = (14, 0, 0)" not in _read(source / "release_updates.py")):
        raise ContractError("Source update version mismatch")
    if ("import falcon_foundation" not in chat or
        'return "foundation", ""' not in chat or
        "gaming_mode.enabled()" not in chat):
        raise ContractError("Foundation/Gaming Mode chat routing missing")
    if "import gaming_mode" not in planner or "gaming_mode.enabled()" not in planner:
        raise ContractError("AI planner does not honor Gaming Mode")
    if "blocked: packaged source-upgrade unsupported" not in improve:
        raise ContractError("Frozen EXE self-modification guard missing")
    if "site_design_check.inspect" not in _read(source / "developer_workspace.py"):
        raise ContractError("Website design benchmark signals missing")
    if "falcon_foundation.py" not in REQUIRED:
        raise ContractError("Required V14 foundation missing")
    for filename in ("app_updates.py", "app_entry.py", "Falcon_Ai.iss",
                     "Falcon_Ai_Icon.ico", "Falcon_Ai_Icon.png"):
        if not (runtime / filename).is_file():
            raise ContractError("Missing Windows installer runtime file: " + filename)
    updates = _read(runtime / "app_updates.py")
    entry = _read(runtime / "app_entry.py")
    iss = _read(runtime / "Falcon_Ai.iss")
    if "CURRENT_VERSION = " + UPDATE_TUPLE not in updates:
        raise ContractError("Windows updater version mismatch")
    if "CURRENT_VERSION != " + UPDATE_TUPLE not in entry:
        raise ContractError("Frozen runtime self-test version mismatch")
    if '#define MyAppVersion "14.0.0"' not in iss:
        raise ContractError("Inno Setup installer version mismatch")
    if "falcon_app_v14_runtime\\Falcon_Ai_Icon.ico" not in iss:
        raise ContractError("Installer icon path no longer points to V14 runtime")
    if "--falcon-diagnostics-self-test" not in entry:
        raise ContractError("13/13 frozen diagnostics self-test missing")
    if "sys.modules['diagnostics'] = packaged_diagnostics" not in entry:
        raise ContractError("Packaged diagnostics import not connected")
    if previous_installer is not None and installer_id(iss) != installer_id(_read(previous_installer)):
        raise ContractError("Installer AppId changed; previous installations would not upgrade")
    unsafe = [p.name for p in source.glob("*.txt")
              if p.name.endswith(("_DEV_ONLY.txt", "_CANDIDATE_ONLY.txt",
                                  "_NOT_RELEASED.txt"))]
    if unsafe:
        raise ContractError("Development markers not removed: " + ", ".join(unsafe))
    return {
        "version": VERSION,
        "required_source_files": len(REQUIRED),
        "previous_installer_id_preserved": previous_installer is not None,
        "source_checks_passed": True,
        "frozen_exe_tested": False,
        "installed_on_user_pc": False,
    }
