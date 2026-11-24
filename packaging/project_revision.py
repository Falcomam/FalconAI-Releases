"""Review-first, rollback-capable edits of Falcon-owned developer projects.

Only existing, explicitly reviewed source files in the developer_projects
workspace may change. No model-provided paths are trusted; no code is run.
Backups are outside the project and retain exact original file bytes.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

import developer_workspace as projects

BACKUPS_FOLDER = ".falcon_revision_backups"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _guard_root(root):
    root = Path(root)
    if not root.is_dir() or projects._reparse(root) or projects._reparse(root.parent):
        raise projects.ProjectError("Developer workspace is missing or redirected")
    return root


def _guard_project(name, workspace):
    projects._check_name(name)
    root = _guard_root(workspace)
    project = root / name
    if not project.is_dir() or projects._reparse(project):
        raise projects.ProjectError("Saved Falcon project not found or unsafe")
    return project


def _read_files(project):
    """Reject foreign/binary/reparse paths, oversized content and collisions."""
    data = {}
    total = 0
    for base, dirs, files in os.walk(project, topdown=True, followlinks=False):
        parent = Path(base)
        if projects._reparse(parent):
            raise projects.ProjectError("Redirected project folder")
        for folder in dirs:
            path = parent / folder
            if projects._reparse(path):
                raise projects.ProjectError("Project contains a redirected folder")
        for filename in files:
            path = parent / filename
            if projects._reparse(path):
                raise projects.ProjectError("Project contains a redirected file")
            relative = path.relative_to(project).as_posix()
            projects._check_path(relative)
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise projects.ProjectError("Project contains a nonregular file")
            if len(data) >= projects.MAX_FILES or info.st_size > projects.MAX_BYTES_PER_FILE:
                raise projects.ProjectError("Project exceeds safe edit limits")
            value = path.read_bytes()
            total += len(value)
            if total > projects.MAX_TOTAL_BYTES or b"\0" in value:
                raise projects.ProjectError("Project contains oversized or binary data")
            try:
                text = value.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise projects.ProjectError("Project contains non-UTF-8 source") from exc
            if relative.casefold() in (key.casefold() for key in data):
                raise projects.ProjectError("Case-insensitive filename collision")
            data[relative] = text
    if not data:
        raise projects.ProjectError("Saved project has no source files")
    return data


def _infer_kind(files):
    names = set(files)
    if "index.html" in names:
        return "website"
    if any(path.endswith("fabric.mod.json") for path in names):
        return "fabric_mod"
    if any(path.endswith(".py") for path in names):
        return "python"
    raise projects.ProjectError("Cannot identify project kind; only Python, website and Fabric starters are editable")


def _snapshot_fingerprint(plan):
    """Canonical identity of already-existing source, including legacy bugs.

    Existing V13.8 websites might have invalid HTML; users must be able to
    ask Falcon to fix it without being blocked by the *new* HTML quality gate.
    Newly proposed replacement files still pass full validation.
    """
    canonical = json.dumps(plan, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    return _sha(canonical)


def load_project(name, *, workspace=projects.WORKSPACE):
    """Capture a bounded, source-only snapshot of an existing project."""
    project = _guard_project(name, workspace)
    files = _read_files(project)
    kind = _infer_kind(files)
    plan = {"name": name, "kind": kind, "files": files}
    return {"plan": plan, "fingerprint": _snapshot_fingerprint(plan)}


def review_revision(base, new_plan):
    """Verify replacement from model uses EXACT same name/kind/file paths."""
    if not isinstance(base, dict) or "plan" not in base:
        raise projects.ProjectError("Missing original reviewed project snapshot")
    original = base["plan"]
    if not isinstance(original, dict) or _snapshot_fingerprint(original) != base.get("fingerprint"):
        raise projects.ProjectError("Original project snapshot changed")
    proposed = projects.review_proposal(new_plan)
    if proposed["name"] != original["name"] or proposed["kind"] != original["kind"]:
        raise projects.ProjectError("Revisions cannot rename or change the project type")
    if set(proposed["files"]) != set(original["files"]):
        raise projects.ProjectError("Revisions cannot add, delete or rename files in this version")
    changed = tuple(path for path in original["files"]
                    if original["files"][path] != proposed["files"][path])
    if not changed:
        raise projects.ProjectError("The proposed revision did not change any files")
    lines = []
    for path in changed:
        before = original["files"][path].splitlines(keepends=True)
        after = proposed["files"][path].splitlines(keepends=True)
        lines.extend(difflib.unified_diff(
            before, after, fromfile="before/" + path, tofile="after/" + path,
            lineterm="\n", n=3))
    diff_text = "".join(lines)
    return {"proposal": proposed, "changed": changed, "diff": diff_text,
            "base_fingerprint": base["fingerprint"],
            "new_fingerprint": proposed["fingerprint"],
            "quality_warnings": proposed.get("quality_warnings", ())}


def _verify_current(name, expected, workspace):
    current = load_project(name, workspace=workspace)
    if current["fingerprint"] != expected:
        raise projects.ProjectError("Saved project changed since review. Start a new edit; no files overwritten.")
    return current


def _safe_backup_root(workspace, name):
    root = _guard_root(workspace)
    backups = root / BACKUPS_FOLDER
    if projects._reparse(backups):
        raise projects.ProjectError("Backup location is redirected")
    backups.mkdir(exist_ok=True)
    sub = backups / name
    if projects._reparse(sub):
        raise projects.ProjectError("Project backup location is redirected")
    sub.mkdir(exist_ok=True)
    return sub


def save_revision_approved(base, new_plan, approved_fingerprint, *, workspace=projects.WORKSPACE):
    """Backup exact originals and replace only changed existing files.

    Require full revision fingerprint and original content snapshot. Every
    target must still match the original on disk before any file replacement.
    On a write failure, attempt rollback from the byte-for-byte backup.
    """
    reviewed = review_revision(base, new_plan)
    if reviewed["new_fingerprint"] != approved_fingerprint:
        raise projects.ProjectError("Revised code changed since approval")
    name = reviewed["proposal"]["name"]
    _verify_current(name, reviewed["base_fingerprint"], workspace)
    project = _guard_project(name, workspace)
    backup_id = uuid.uuid4().hex
    backup = _safe_backup_root(workspace, name) / backup_id
    backup.mkdir(exist_ok=False)
    originals = base["plan"]["files"]
    changes = reviewed["changed"]
    old_payloads = {}
    try:
        for path in changes:
            parts = projects._check_path(path)
            target = project.joinpath(*parts)
            if not target.is_file() or projects._reparse(target):
                raise projects.ProjectError("Project target redirected before edit")
            payload = target.read_bytes()
            if payload != originals[path].encode("utf-8"):
                raise projects.ProjectError("Project changed before edit; no overwrite permitted")
            old_payloads[path] = payload
            b = backup.joinpath(*parts)
            b.parent.mkdir(parents=True, exist_ok=True)
            with b.open("xb") as f:
                f.write(payload)
        # Do not write any changes until every old file has been backed up.
        metadata = {
            "name": name, "base_fingerprint": reviewed["base_fingerprint"],
            "new_fingerprint": reviewed["new_fingerprint"], "changed": list(changes),
        }
        with (backup / "revision.json").open("x", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        written = []
        try:
            for path in changes:
                target = project.joinpath(*projects._check_path(path))
                if projects._reparse(target) or target.read_bytes() != old_payloads[path]:
                    raise projects.ProjectError("Project changed while writing; rolling back")
                staged = target.parent / (".falcon-stage-" + uuid.uuid4().hex + ".tmp")
                try:
                    with staged.open("xb") as f:
                        f.write(reviewed["proposal"]["files"][path].encode("utf-8"))
                    os.replace(staged, target)
                finally:
                    if staged.exists():
                        staged.unlink()
                written.append(path)
        except Exception:
            for path in reversed(written):
                target = project.joinpath(*projects._check_path(path))
                if not projects._reparse(target):
                    try:
                        restore = target.parent / (".falcon-restore-" + uuid.uuid4().hex + ".tmp")
                        restore.write_bytes(old_payloads[path])
                        os.replace(restore, target)
                    except OSError:
                        # Backups remain on disk for user-led recovery.
                        pass
            raise
        return {"project": str(project), "backup_id": backup_id,
                "changed": changes, "executed": False}
    except BaseException:
        # Retain backup even if only partly staged, for diagnostics and
        # recovery; never recursively delete a directory around user files.
        raise


def rollback_revision(name, backup_id, *, workspace=projects.WORKSPACE):
    """Explicit user rollback to a previously saved revision's exact originals.

    Only if today's project still matches the revision that we saved. Never
    overwrite later user edits or follow symlinked backup contents.
    """
    projects._check_name(name)
    if not isinstance(backup_id, str) or len(backup_id) != 32 or \
            any(c not in "0123456789abcdef" for c in backup_id):
        raise projects.ProjectError("Invalid rollback identifier")
    base = _safe_backup_root(workspace, name) / backup_id
    if projects._reparse(base) or not base.is_dir():
        raise projects.ProjectError("Backup not found or redirected")
    metadata = base / "revision.json"
    if projects._reparse(metadata):
        raise projects.ProjectError("Backup metadata is redirected")
    try:
        record = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise projects.ProjectError("Backup metadata unreadable") from exc
    if record.get("name") != name or not isinstance(record.get("changed"), list):
        raise projects.ProjectError("Backup does not match project")
    _verify_current(name, record.get("new_fingerprint"), workspace)
    project = _guard_project(name, workspace)
    payloads = {}
    for path in record["changed"]:
        target = project.joinpath(*projects._check_path(path))
        backed = base.joinpath(*projects._check_path(path))
        if projects._reparse(backed) or not backed.is_file() or projects._reparse(target):
            raise projects.ProjectError("Backup contents are unsafe")
        raw = backed.read_bytes()
        if len(raw) > projects.MAX_BYTES_PER_FILE:
            raise projects.ProjectError("Backup contains oversized data")
        payloads[path] = raw
    for path, raw in payloads.items():
        target = project.joinpath(*projects._check_path(path))
        temp = target.parent / (".falcon-rollback-" + uuid.uuid4().hex + ".tmp")
        try:
            temp.write_bytes(raw)
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()
    _verify_current(name, record.get("base_fingerprint"), workspace)
    return {"project": str(project), "restored": tuple(payloads), "executed": False}
