"""Read-only navigation for Falcon-owned saved Developer Mode projects.

This never executes, modifies, uploads, or removes saved projects.
No files outside the configured Falcon workspace may be opened.
"""
from __future__ import annotations

from pathlib import Path
import stat

import developer_workspace as projects
import project_revision as revisions

MAX_VISIBLE_PROJECTS = 50
MAX_SCANNED_ENTRIES = 500


def list_saved_projects(*, workspace=projects.WORKSPACE, limit=MAX_VISIBLE_PROJECTS):
    """Return a bounded sorted collection of valid, non-redirected project names.

    The backup directory is deliberately invisible. Listing does not read
    project contents, ask Ollama, start any executables, or create folders.
    A missing workspace simply means no saved Developer Mode projects.
    """
    if not isinstance(limit, int) or not 1 <= limit <= MAX_VISIBLE_PROJECTS:
        raise projects.ProjectError("Project list limit must be from 1 to 50")
    root = Path(workspace)
    if not root.exists():
        return ()
    if not root.is_dir() or projects._reparse(root) or projects._reparse(root.parent):
        raise projects.ProjectError("Falcon project workspace is redirected or unsafe")
    found = []
    for index, child in enumerate(root.iterdir()):
        if index >= MAX_SCANNED_ENTRIES:
            raise projects.ProjectError("Too many workspace entries for safe project listing")
        try:
            projects._check_name(child.name)
        except projects.ProjectError:
            continue
        if projects._reparse(child):
            continue
        try:
            if not stat.S_ISDIR(child.lstat().st_mode):
                continue
        except OSError:
            continue
        found.append(child.name)
    return tuple(sorted(found, key=lambda name: (name.casefold(), name))[:limit])


def open_saved_project(name, *, workspace=projects.WORKSPACE):
    """Capture a bounded read-only source snapshot for inline chat inspection."""
    return revisions.load_project(name, workspace=workspace)


def show_saved_file(name, path, expected_fingerprint, *,
                    workspace=projects.WORKSPACE, preview_limit=18000):
    """Prevent showing stale source if project changed since /project open."""
    parts = projects._check_path(path)
    normalized = "/".join(parts)
    snapshot = open_saved_project(name, workspace=workspace)
    if snapshot["fingerprint"] != expected_fingerprint:
        raise projects.ProjectError("Saved project changed since it was opened. Use /project open again.")
    contents = snapshot["plan"]["files"].get(normalized)
    if contents is None:
        raise projects.ProjectError("That file is not in the saved project")
    if not isinstance(preview_limit, int) or not 1 <= preview_limit <= 18000:
        raise projects.ProjectError("Unsafe source preview limit")
    return {
        "name": name,
        "path": normalized,
        "text": contents[:preview_limit],
        "truncated": len(contents) > preview_limit,
        "fingerprint": expected_fingerprint,
    }
