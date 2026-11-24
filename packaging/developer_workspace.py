"""Falcon Ai Developer Mode — review-first, isolated multi-file project writer.

Only a user-approved, exact SHA-256 proposal is written. Generated source is
NEVER executed, installed, downloaded or given PC-control permissions. All
created files live in a new Falcon-owned project directory with exclusive
create semantics, and no user file is overwritten.

This is the V13.8 development module, not a published application feature.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import html_quality

BASE = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "FalconAI"
WORKSPACE = BASE / "developer_projects"
MAX_FILES = 32
MAX_BYTES_PER_FILE = 200_000
MAX_TOTAL_BYTES = 1_000_000
MAX_RAW_PROPOSAL = 1_150_000
ALLOWED_KINDS = frozenset({"python", "website", "fabric_mod"})
ALLOWED_EXTENSIONS = frozenset({
    ".py", ".html", ".htm", ".css", ".js", ".mjs", ".json", ".md", ".txt",
    ".toml", ".yaml", ".yml", ".xml", ".java", ".kt", ".kts",
    ".gradle", ".properties", ".svg",
})
ALLOWED_BASENAMES = frozenset({".gitignore"})
FORBIDDEN_SEGMENTS = frozenset({".git", ".github", ".venv", "node_modules", "__pycache__"})
NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}$")
SEGMENT_RE = re.compile(r"^[a-zA-Z0-9._-]{1,100}$")
RESERVED_WINDOWS = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})


class ProjectError(ValueError):
    """Generated project rejected before any user-visible files are changed."""


def _check_name(name):
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise ProjectError("Project name must be 1–40 plain letters, digits, underscores or hyphens")
    return name


def _check_path(path):
    if not isinstance(path, str) or not path or len(path) > 220:
        raise ProjectError("File path is missing or too long")
    # Source model output always uses forward slash separators. No device paths,
    # drive paths, UNC paths, backslashes, ADS, or directory traversal.
    if path.startswith("/") or "\\" in path or ":" in path or "\0" in path:
        raise ProjectError("Absolute paths, drive names and backslashes are not allowed")
    parts = path.split("/")
    if not 1 <= len(parts) <= 12:
        raise ProjectError("Unsupported project directory depth")
    for part in parts:
        if (part in (".", "..", "") or part.endswith((" ", "."))
                or not SEGMENT_RE.fullmatch(part)):
            raise ProjectError("Unsafe file path component")
        if part.casefold() in FORBIDDEN_SEGMENTS:
            raise ProjectError("Generated projects cannot write hidden tool/runtime directories")
        if part.split(".", 1)[0].upper() in RESERVED_WINDOWS:
            raise ProjectError("Reserved Windows filename")
    suffix = Path(parts[-1]).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS and parts[-1] not in ALLOWED_BASENAMES:
        raise ProjectError("File extension is not supported for review-first coding")
    return tuple(parts)


def parse_proposal(raw):
    """Parse one bounded JSON object, optionally inside one exact JSON fence.

    Model formatting recovery is narrow: no commentary, appended objects,
    ambiguous duplicate keys, NaN or executable code can be accepted.
    """
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_RAW_PROPOSAL:
        raise ProjectError("Project proposal must be a bounded JSON document")
    payload = raw.strip()
    if payload.startswith("```"):
        match = re.fullmatch(
            r"```(?:json)?[ \\t]*\\r?\\n(?P<body>.*?)\\r?\\n```",
            payload, flags=re.I | re.S)
        if not match:
            raise ProjectError("Only one complete JSON code fence is supported")
        payload = match.group("body")

    def unique_pairs(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                raise ValueError("Duplicate JSON key")
            data[key] = value
        return data

    def reject_constant(value):
        raise ValueError("Non-standard JSON constant: " + value)

    try:
        plan = json.loads(payload, object_pairs_hook=unique_pairs,
                          parse_constant=reject_constant)
    except (TypeError, ValueError) as exc:
        raise ProjectError("The coding model must return one unambiguous JSON project") from exc
    return review_proposal(plan)


def review_proposal(plan):
    """Return a deterministic, complete review; invalid syntax blocks install."""
    if not isinstance(plan, dict) or set(plan) != {"name", "kind", "files"}:
        raise ProjectError("Project must contain only name, kind and files")
    name = _check_name(plan["name"])
    kind = plan["kind"]
    if not isinstance(kind, str) or kind not in ALLOWED_KINDS:
        raise ProjectError("Project type must be python, website or fabric_mod")
    files = plan["files"]
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise ProjectError("Project must contain 1–32 files")
    seen = set()
    total_bytes = 0
    clean = {}
    for path, contents in files.items():
        parts = _check_path(path)
        folded = "/".join(parts).casefold()
        if folded in seen:
            raise ProjectError("Duplicate file path, including Windows case-insensitive collisions")
        # Reject cases where a proposed file is also somebody else's folder.
        if any(other == folded or other.startswith(folded + "/") or folded.startswith(other + "/")
               for other in seen):
            raise ProjectError("Conflicting file and directory paths")
        seen.add(folded)
        if not isinstance(contents, str) or "\0" in contents:
            raise ProjectError("Generated file contents must be UTF-8 text")
        encoded = contents.encode("utf-8")
        total_bytes += len(encoded)
        if len(encoded) > MAX_BYTES_PER_FILE or total_bytes > MAX_TOTAL_BYTES:
            raise ProjectError("Generated project is larger than the safety limit")
        if path.lower().endswith(".py"):
            try:
                ast.parse(contents, filename=path)
            except SyntaxError as exc:
                raise ProjectError(f"Python syntax error in {path}, line {exc.lineno}") from exc
        if path.lower().endswith(".json"):
            try:
                json.loads(contents)
            except ValueError as exc:
                raise ProjectError(f"Invalid JSON in {path}") from exc
        clean[path] = contents
    quality_warnings = []
    if kind == "website":
        try:
            quality_warnings = html_quality.check_website(clean)
        except html_quality.WebsiteQualityError as exc:
            raise ProjectError("Website HTML validation failed: " + str(exc)) from exc
    canonical = json.dumps(
        {"name": name, "kind": kind, "files": clean},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return {
        "name": name,
        "kind": kind,
        "files": clean,
        "file_count": len(clean),
        "byte_count": total_bytes,
        "fingerprint": hashlib.sha256(canonical).hexdigest(),
        "execution_allowed": False,
        "quality_warnings": tuple(quality_warnings),
    }


def _reparse(path):
    """Reject symlinks and Windows directory junctions/reparse points."""
    try:
        attrs = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(attrs.st_mode) or bool(
        getattr(attrs, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def save_approved(plan, approved_fingerprint, *, workspace=WORKSPACE):
    """Create a brand-new project after exact review digest approval.

    Caller MUST gather explicit approval in the GUI. This method cannot be
    used to overwrite an existing project; code isn't executed by this module.
    """
    proposal = review_proposal(plan)
    if (not isinstance(approved_fingerprint, str)
            or approved_fingerprint != proposal["fingerprint"]):
        raise ProjectError("Proposal changed since approval; review again")
    directory = Path(workspace)
    if _reparse(directory) or _reparse(directory.parent):
        raise ProjectError("Refusing a redirected workspace")
    directory.mkdir(parents=True, exist_ok=True)
    if _reparse(directory):
        raise ProjectError("Refusing a redirected workspace")
    project = directory / proposal["name"]
    if project.exists() or project.is_symlink():
        raise ProjectError("Project already exists; choose a new project name")
    # The destination path is exclusive; no old user files are ever replaced.
    project.mkdir(exist_ok=False)
    try:
        for relative, contents in proposal["files"].items():
            target = project.joinpath(*_check_path(relative))
            parent = target.parent
            if parent != project:
                parent.mkdir(parents=True, exist_ok=True)
            cursor = project
            for component in _check_path(relative)[:-1]:
                cursor = cursor / component
                if _reparse(cursor):
                    raise ProjectError("Project directory was redirected")
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(contents)
        return {"path": str(project), "fingerprint": proposal["fingerprint"],
                "file_count": proposal["file_count"], "executed": False}
    except BaseException:
        # Keep the partial newly created folder for diagnostics rather than
        # ever recursively deleting a path after untrusted filesystem changes.
        raise
