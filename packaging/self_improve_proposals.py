"""Review-only Falcon source improvement proposals. No disk access or execution."""
from __future__ import annotations
import ast
import difflib
import hashlib
import json
import tomllib
import self_improve_risk_hints
import re
from pathlib import PurePosixPath

MAX_FILES = 12
MAX_FILE_BYTES = 150_000
MAX_TOTAL_BYTES = 600_000
SEGMENT = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
EXTENSIONS = frozenset({".py", ".md", ".txt", ".json", ".toml", ".yml", ".yaml"})
BLOCKED = frozenset({".git", ".github", ".venv", "venv", "__pycache__", "node_modules", "dist", "build", "secrets"})
RESERVED = frozenset({"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))})


class ProposalError(ValueError):
    """Proposal is malformed or outside the review-only safety limits."""


def _path(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 200:
        raise ProposalError("Missing or oversized relative path")
    if value.startswith("/") or any(c in value for c in ("\\", ":", "\x00")):
        raise ProposalError("Only simple relative POSIX source paths are accepted")
    parts = value.split("/")
    if len(parts) > 8 or any(
        not SEGMENT.fullmatch(part) or part in (".", "..") or part.endswith(".")
        or part.casefold() in BLOCKED or part.split(".", 1)[0].upper() in RESERVED
        for part in parts
    ):
        raise ProposalError("Unsafe source path")
    if value.casefold() in {"requirements.txt", "pyproject.toml"} or PurePosixPath(value).suffix.lower() not in EXTENSIONS:
        raise ProposalError("Protected or unsupported source file")
    return value


def _source(value, path):
    if not isinstance(value, str) or "\x00" in value:
        raise ProposalError("Source must be plain UTF-8 text")
    raw = value.encode("utf-8")
    if len(raw) > MAX_FILE_BYTES:
        raise ProposalError("Source file exceeds size limit")
    if path.lower().endswith(".py"):
        try:
            ast.parse(value, filename=path)
        except SyntaxError as exc:
            raise ProposalError(f"Python syntax error in {path}, line {exc.lineno}") from exc
    if path.lower().endswith(".json"):
        try:
            json.loads(value)
        except ValueError as exc:
            raise ProposalError(f"Invalid JSON in {path}") from exc
    if path.lower().endswith(".toml"):
        try:
            tomllib.loads(value)
        except tomllib.TOMLDecodeError as exc:
            raise ProposalError(f"Invalid TOML in {path}") from exc
    return raw


def _diff_stats(before, after):
    # Purely textual preview metrics. Never treat as evidence of code safety.
    import difflib
    old = before.splitlines()
    new = after.splitlines()
    additions = deletions = 0
    for op, a, b, c, d in difflib.SequenceMatcher(
            None, old, new, autojunk=False).get_opcodes():
        if op in ("insert", "replace"):
            additions += d - c
        if op in ("delete", "replace"):
            deletions += b - a
    return {"added_lines": additions, "removed_lines": deletions}


def review(changes):
    """Produce inert diffs and hashes from {path: {before: text, after: text}}.

    This function cannot read installed files, execute code, write changes,
    approve a proposal, or publish an installer.
    """
    if not isinstance(changes, dict) or not 1 <= len(changes) <= MAX_FILES:
        raise ProposalError("Expected 1 to 12 changed files")
    seen = set()
    total = 0
    entries = []
    canonical = {}
    for path, item in sorted(changes.items()):
        path = _path(path)
        key = path.casefold()
        if key in seen or any(key.startswith(other + "/") or other.startswith(key + "/") for other in seen):
            raise ProposalError("Duplicate or colliding Windows paths")
        seen.add(key)
        if not isinstance(item, dict) or set(item) != {"before", "after"}:
            raise ProposalError("Each file requires exactly before and after")
        before, after = item["before"], item["after"]
        original, replacement = _source(before, path), _source(after, path)
        total += len(original) + len(replacement)
        if total > MAX_TOTAL_BYTES:
            raise ProposalError("Proposal exceeds total size limit")
        if original == replacement:
            raise ProposalError("No changes in " + path)
        canonical[path] = {"before": before, "after": after}
        diff = "".join(difflib.unified_diff(before.splitlines(keepends=True),
                                           after.splitlines(keepends=True),
                                           fromfile="a/" + path, tofile="b/" + path))
        risk = (self_improve_risk_hints.inspect_python(after, filename=path)
                if path.lower().endswith(".py")
                else {"advisory_only": True, "manual_review_required": False,
                      "indicators": [], "indicators_truncated": False})
        entries.append({"path": path, "before_sha256": hashlib.sha256(original).hexdigest(),
                        "after_sha256": hashlib.sha256(replacement).hexdigest(),
                        "line_changes": _diff_stats(before, after),
                        "risk_hints": risk, "diff": diff})
    digest = hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"fingerprint": digest, "files": entries, "file_count": len(entries),
            "execution_allowed": False, "installation_allowed": False,
            "status": "review_only_not_tested"}
