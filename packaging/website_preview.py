"""Open an already-approved Falcon website preview in the user's browser.

The command is deliberately narrower than generic PC control. Only the exact
index.html of a saved, validated website project can be opened. No execution
permission is granted for Python, native programs, installers or arbitrary URLs.
Opening HTML may still run browser JavaScript under the browser's file policy.
"""
from __future__ import annotations

from pathlib import Path
import stat
import webbrowser

import developer_workspace as projects
import project_revision as revisions


def preview_url(name, *, workspace=projects.WORKSPACE):
    """Return a file:// URL for a saved website's ordinary index.html."""
    projects._check_name(name)
    root = Path(workspace)
    if not root.is_dir() or projects._reparse(root) or projects._reparse(root.parent):
        raise projects.ProjectError("Falcon developer workspace is unavailable or redirected")
    folder = root / name
    index = folder / "index.html"
    if projects._reparse(folder) or projects._reparse(index):
        raise projects.ProjectError("Redirected website preview is not allowed")
    if not folder.is_dir() or not index.is_file():
        raise projects.ProjectError("Saved website index.html was not found")
    if not stat.S_ISREG(index.lstat().st_mode):
        raise projects.ProjectError("Website preview must be a regular file")
    # load_project verifies every saved file and refuses redirected directories.
    snapshot = revisions.load_project(name, workspace=workspace)
    plan = snapshot["plan"]
    if plan["kind"] != "website" or "index.html" not in plan["files"]:
        raise projects.ProjectError("Only saved Falcon website projects can be previewed")
    return index.absolute().as_uri()


def open_website(name, *, workspace=projects.WORKSPACE, opener=webbrowser.open):
    """Open a bounded local browser preview; no new approval prompt."""
    url = preview_url(name, workspace=workspace)
    if not opener(url, new=2):
        raise projects.ProjectError("Default browser could not open this website preview")
    return url
