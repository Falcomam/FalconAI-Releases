"""Read-only bounded text search inside an opened Falcon-owned project.

Results never execute code or access arbitrary user folders. A snapshot digest
guards against searching a project that changed since /project open.
"""
from __future__ import annotations

import developer_workspace as projects
import project_browser as browser

MAX_QUERY_CHARS = 80
MAX_MATCHES = 25
MAX_PREVIEW_CHARS = 180


def find_source(name, needle, expected_fingerprint, *,
                workspace=projects.WORKSPACE, max_matches=MAX_MATCHES):
    """Find bounded, case-insensitive substring matches in saved source lines.

    Only use after /project open has captured a fingerprint. Return no source
    beyond approved project files. This function is pure/read-only.
    """
    if not isinstance(needle, str) or not 2 <= len(needle.strip()) <= MAX_QUERY_CHARS:
        raise projects.ProjectError("Search text must be 2–80 characters")
    if "\x00" in needle or "\r" in needle or "\n" in needle:
        raise projects.ProjectError("Search text must be a single line")
    if not isinstance(expected_fingerprint, str) or len(expected_fingerprint) != 64:
        raise projects.ProjectError("Open the saved project before searching")
    if type(max_matches) is not int or not 1 <= max_matches <= MAX_MATCHES:
        raise projects.ProjectError("Search result limit must be from 1 to 25")
    snapshot = browser.open_saved_project(name, workspace=workspace)
    if snapshot["fingerprint"] != expected_fingerprint:
        raise projects.ProjectError("Saved project changed since it was opened. Use /project open again.")
    query = needle.strip().casefold()
    results = []
    for path, contents in sorted(snapshot["plan"]["files"].items(),
                                 key=lambda item: item[0].casefold()):
        for line_number, line in enumerate(contents.splitlines(), 1):
            if query not in line.casefold():
                continue
            text = line.strip()
            if len(text) > MAX_PREVIEW_CHARS:
                text = text[:MAX_PREVIEW_CHARS - 1] + "…"
            results.append({
                "path": path,
                "line": line_number,
                "excerpt": text,
            })
            if len(results) == max_matches:
                return {"name": name, "query": needle.strip(), "matches": tuple(results),
                        "limited": True, "fingerprint": expected_fingerprint}
    return {"name": name, "query": needle.strip(), "matches": tuple(results),
            "limited": False, "fingerprint": expected_fingerprint}
