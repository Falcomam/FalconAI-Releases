"""Honest, read-only health checks for Falcon's frozen Windows EXE.

The legacy loose-source diagnostic assumes falcon.py and START_HERE.bat exist
beside diagnostics.py. That layout no longer exists in the Windows installer.
In frozen mode, validate the 11 required bundled import loaders and the
installed GUI executable plus update helper. This does not claim Python source
syntax was recompiled; full EXE self-tests remain the CI release gate.

Never runs source, model output, Docker, shell commands, or auto-upgrades.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "FalconAI" / "v13_5_diagnostics"
SOURCES = ("falcon.py", "unified.py", "agent.py", "core_upgrade.py", "research.py",
           "studio.py", "notifications.py", "voice.py", "collab.py",
           "progress.py", "ollama_runtime.py")
REQUIRED_FILES = ("Falcon Ai.exe", "app_update_restart.ps1")


def _inside(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except (ValueError, OSError, TypeError):
        return False


def _module_present(filename, bundle):
    """Check the frozen Python loader, not nonexistent loose .py sources.

    find_spec does not import the module for these top-level names. We accept
    only module origins within the application's own verified runtime folder.
    """
    name = filename[:-3]
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError, AttributeError):
        return False
    if spec is None or spec.loader is None or not spec.origin:
        return False
    return _inside(spec.origin, bundle)


def inspect(*, frozen=None, bundle=None, executable=None):
    """Return 13 semantically accurate packaged-runtime check statuses."""
    if frozen is None:
        frozen = getattr(sys, "frozen", False)
    if not frozen:
        raise RuntimeError("Packaged diagnostics require the Falcon Windows EXE")
    bundle = Path(bundle if bundle is not None else getattr(sys, "_MEIPASS", ""))
    executable = Path(executable if executable is not None else sys.executable)
    if not bundle.is_dir() or not executable.is_file():
        raise RuntimeError("Packaged Falcon runtime or EXE could not be located")
    # The Windows one-folder app should keep _internal as a child of the
    # installation directory. No arbitrary attacker-controlled source folders.
    if not _inside(bundle, executable.parent) or bundle == executable.parent:
        raise RuntimeError("Packaged runtime is outside the Falcon EXE directory")
    checks = {
        name: ("present" if _module_present(name, bundle) else "missing")
        for name in SOURCES
    }
    checks["Falcon Ai.exe"] = (
        "present" if executable.name.casefold() == "falcon ai.exe"
        and executable.stat().st_size >= 100000 else "missing"
    )
    helper = bundle / "app_update_restart.ps1"
    checks["app_update_restart.ps1"] = (
        "present" if helper.is_file() and not helper.is_symlink()
        and helper.stat().st_size > 100 else "missing"
    )
    return checks


def run():
    """Write a minimal local status report without reading user content."""
    checks = inspect()
    ROOT.mkdir(parents=True, exist_ok=True)
    report = ROOT / (
        "check_" + time.strftime("%Y%m%d_%H%M%S", time.gmtime()) +
        "_" + uuid.uuid4().hex[:6] + ".json"
    )
    tmp = report.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps({
            "version": "packaged Windows",
            "mode": "frozen module-loader and installer-file availability",
            "checks": checks,
            "note": "No source syntax compilation or self-modifying patch was performed.",
        }, indent=2), encoding="utf-8")
        os.replace(tmp, report)
    finally:
        tmp.unlink(missing_ok=True)
    passed = sum(value == "present" for value in checks.values())
    failed = [name for name, state in checks.items() if state != "present"]
    summary = (f"{passed}/{len(checks)} packaged module/installer checks passed. "
               "Failed: " + (", ".join(failed) if failed else "none"))
    return report, summary
