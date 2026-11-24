"""Targeted source-only edits for Falcon's small local coding models.

Selects complete relevant source files from a previously trusted project
snapshot, then merges small JSON 'changes' proposals with unchanged originals.
Never reads arbitrary paths, writes files, executes code or grants approval.
"""
from __future__ import annotations

import json
import re

import developer_workspace as projects
import project_revision as revisions

MAX_CONTEXT_CHARS = 24_000
MAX_TARGET_FILES = 10
WORD = re.compile(r"[a-zA-Z0-9_]+")


def _base(base):
    if not isinstance(base, dict) or not isinstance(base.get("plan"), dict):
        raise projects.ProjectError("Trusted original project snapshot required")
    if base.get("fingerprint") != revisions._snapshot_fingerprint(base["plan"]):
        raise projects.ProjectError("Original project snapshot changed")
    return base["plan"]


def select_context(base, goal, *, max_chars=MAX_CONTEXT_CHARS, max_files=MAX_TARGET_FILES):
    plan = _base(base)
    if not isinstance(goal, str) or not 8 <= len(goal.strip()) <= 1100:
        raise projects.ProjectError("Describe the targeted edit in 8–1100 characters")
    if not isinstance(max_chars, int) or not 1000 <= max_chars <= MAX_CONTEXT_CHARS:
        raise projects.ProjectError("Unsafe coding model context limit")
    if not isinstance(max_files, int) or not 1 <= max_files <= MAX_TARGET_FILES:
        raise projects.ProjectError("Unsafe target file count")
    names = tuple(sorted(plan["files"]))
    goal_words = set(WORD.findall(goal.casefold()))
    ranked = []
    for path in names:
        parts = set(WORD.findall(path.casefold()))
        match = len(parts & goal_words)
        direct = int(path.casefold() in goal.casefold())
        root = path.rsplit("/", 1)[-1].casefold()
        priority = int(root in {"main.py", "app.py", "index.html", "readme.md"})
        ranked.append((-(100 * direct + 10 * match + priority),
                       len(plan["files"][path]), path))
    ranked.sort()
    selected = {}
    used = 0
    for _, length, path in ranked:
        if len(selected) >= max_files:
            break
        if length + used <= max_chars:
            selected[path] = plan["files"][path]
            used += length
    if not selected:
        raise projects.ProjectError(
            "No complete source file fits the coding context limit; choose a smaller project")
    return {
        "name": plan["name"], "kind": plan["kind"],
        "source_fingerprint": base["fingerprint"],
        "selected_files": selected,
        "all_existing_paths": names,
        "selected_chars": used,
        "execution_allowed": False,
    }


def parse_targeted_changes(base, raw, context):
    """Review a bounded changed-file object against exact existing source.

    The model may update selected existing files or add safe new source files.
    It may not touch unselected existing files, delete files, rename the project
    or set a new baseline. Unchanged originals are always merged unchanged.
    """
    plan = _base(base)
    if (not isinstance(context, dict)
            or context.get("source_fingerprint") != base["fingerprint"]
            or not isinstance(context.get("selected_files"), dict)):
        raise projects.ProjectError("Trusted selected source context required")
    for path, content in context["selected_files"].items():
        if plan["files"].get(path) != content:
            raise projects.ProjectError("Selected source differs from original snapshot")
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > projects.MAX_RAW_PROPOSAL:
        raise projects.ProjectError("Targeted source proposal exceeds safety limit")
    payload = raw.strip()
    if payload.startswith("```"):
        matched = re.fullmatch(r"```(?:json)?[ \t]*\r?\n(?P<body>.*?)\r?\n```",
                               payload, flags=re.I | re.S)
        if not matched:
            raise projects.ProjectError("Only one complete JSON proposal fence is supported")
        payload = matched.group("body")
    try:
        response = projects._strict_json_loads(payload)
    except (ValueError, TypeError) as exc:
        raise projects.ProjectError("Targeted changes must contain strict JSON") from exc
    if not isinstance(response, dict) or set(response) != {"changes"}:
        raise projects.ProjectError("Return exactly one changes object")
    changes = response["changes"]
    if not isinstance(changes, dict) or not 1 <= len(changes) <= MAX_TARGET_FILES:
        raise projects.ProjectError("Targeted edit must change 1–10 files")
    merged = dict(plan["files"])
    selected = set(context["selected_files"])
    for path, content in changes.items():
        projects._check_path(path)
        if path in merged and path not in selected:
            raise projects.ProjectError("Model tried to edit source outside selected context: " + path)
        if not isinstance(content, str):
            raise projects.ProjectError("Model must provide full UTF-8 source text")
        merged[path] = content
    replacement = {"name": plan["name"], "kind": plan["kind"],
                   "files": merged}
    review = revisions.review_revision(base, replacement)
    return {"plan": replacement, "revision": review,
            "selected_paths": tuple(context["selected_files"]),
            "execution_allowed": False}
