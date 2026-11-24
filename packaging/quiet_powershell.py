"""Windows window policy for Falcon's own PowerShell update helper.

Do not affect user-requested terminals or arbitrary /do PC actions.
Only internal, verified installer-update PowerShell handoffs are minimized.
"""
from __future__ import annotations

import subprocess
import sys


def powershell_minimized_args(script, *, powershell="powershell.exe"):
    """Return explicit, noninteractive PowerShell arguments.

    The helper's script path is passed as a separate argument; do not pass
    user-provided command strings through -Command or cmd /c.
    """
    if not isinstance(script, str) or not script.lower().endswith(".ps1"):
        raise ValueError("Only a trusted PowerShell helper script can be launched")
    return [powershell, "-NoLogo", "-NoProfile", "-NonInteractive",
            "-WindowStyle", "Minimized", "-ExecutionPolicy", "Bypass",
            "-File", script]


def minimized_startupinfo(*, platform=None, subprocess_module=subprocess):
    """Windows requests a minimized, non-foreground helper window.

    We avoid CREATE_NO_WINDOW here: the user asked to minimize, not suppress
    the window entirely, and helper diagnostics remain in the update log.
    """
    platform = sys.platform if platform is None else platform
    if platform != "win32":
        return None
    info = subprocess_module.STARTUPINFO()
    info.dwFlags |= subprocess_module.STARTF_USESHOWWINDOW
    # Windows SW_SHOWMINNOACTIVE = 7: minimized without activating the taskbar.
    info.wShowWindow = 7
    return info
