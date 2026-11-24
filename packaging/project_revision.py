"""Review-first, rollback-capable edits of Falcon-owned developer projects.

Only explicitly reviewed source files in the developer_projects workspace
may change or be added. Deletion and renaming are forbidden. No model-provided
paths are trusted; no code is run. Backups are outside the project and retain
exact original file bytes.
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
    """Review existing-file updates and safe additions; never delete or rename."""
    if not isinstance(base, dict) or "plan" not in base:
        raise projects.ProjectError("Missing original reviewed project snapshot")
    original = base["plan"]
    if not isinstance(original, dict) or _snapshot_fingerprint(original) != base.get("fingerprint"):
        raise projects.ProjectError("Original project snapshot changed")
    proposed = projects.review_proposal(new_plan)
    if proposed["name"] != original["name"] or proposed["kind"] != original["kind"]:
        raise projects.ProjectError("Revisions cannot rename or change the project type")
    if not set(original["files"]).issubset(proposed["files"]):
        raise projects.ProjectError("Revisions cannot delete or rename existing files")
    # Type inference is based on well-known filenames. Never allow a revision
    # that will become unreadable as the original project kind after saving.
    if _infer_kind(proposed["files"]) != original["kind"]:
        raise projects.ProjectError("Added file would change the detected project type")
    added = tuple(path for path in proposed["files"]
                  if path not in original["files"])
    updated = tuple(path for path in original["files"]
                    if original["files"][path] != proposed["files"][path])
    changed = updated + added
    if not changed:
        raise projects.ProjectError("The proposed revision did not change any files")
    lines = []
    for path in changed:
        before = original["files"][path].splitlines(keepends=True) if path in original["files"] else []
        after = proposed["files"][path].splitlines(keepends=True)
        lines.extend(difflib.unified_diff(
            before, after, fromfile=("before/" + path if path in original["files"] else "/dev/null"),
            tofile="after/" + path, lineterm="\n", n=3))
    diff_text = "".join(lines)
    return {"proposal": proposed, "changed": changed, "added": added,
            "updated": updated, "diff": diff_text,
            "base_fingerprint": base["fingerprint"],
            "new_fingerprint": proposed["fingerprint"],
            "quality_warnings": proposed.get("quality_warnings", ())}


def _verify_current(name, expected, workspace):
    current = load_project(name, workspace=workspace)
    if current["fingerprint"] != expected:
        raise projects.ProjectError("Saved project changed since review. Start a new edit; no files overwritten.")
    return current


def _validate_target_parent(project, target):
    """Check all existing parent path components for unsafe redirections."""
    relative = target.relative_to(project).parts[:-1]
    current = project
    for part in relative:
        current = current / part
        if projects._reparse(current) or (current.exists() and not current.is_dir()):
            raise projects.ProjectError("Unsafe destination directory")


def _create_parents_checked(project, target, created):
    """Create missing directories without following existing symlinks."""
    current = project
    for part in target.relative_to(project).parts[:-1]:
        current = current / part
        if projects._reparse(current):
            raise projects.ProjectError("Redirected destination folder")
        if not current.exists():
            current.mkdir(exist_ok=False)
            created.append(current)
        if projects._reparse(current) or not current.is_dir():
            raise projects.ProjectError("Unsafe destination directory")


def _remove_empty_folders(folders, stop=None):
    """Clean up only directories that were created/emptied by this operation."""
    seen = set()
    for directory in reversed(folders):
        current = directory
        while current not in seen and (stop is None or current != stop):
            seen.add(current)
            if projects._reparse(current):
                break
            try:
                current.rmdir()
            except OSError:
                break
            if stop is None:
                break
            current = current.parent


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
    """Backup existing changes; exclusively create new files after approval.

    Require exact proposal fingerprint and full original content snapshot.
    No generated file is executed. In the event of a write failure, attempt
    restoring original files and removing only our newly created files.
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
    added = set(reviewed["added"])
    old_payloads = {}
    created_folders = []
    try:
        for path in changes:
            parts = projects._check_path(path)
            target = project.joinpath(*parts)
            if path in added:
                _validate_target_parent(project, target)
                if target.exists() or target.is_symlink():
                    raise projects.ProjectError("New file already exists; refusing overwrite")
                continue
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
        # All existing changed files are backed up before any writes begin.
        metadata = {
            "name": name, "base_fingerprint": reviewed["base_fingerprint"],
            "new_fingerprint": reviewed["new_fingerprint"], "changed": list(changes),
            "added": list(reviewed["added"]), "created_dirs": [],
        }
        with (backup / "revision.json").open("x", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        written = []
        try:
            for path in changes:
                target = project.joinpath(*projects._check_path(path))
                if path in added:
                    _create_parents_checked(project, target, created_folders)
                    if target.exists() or target.is_symlink():
                        raise projects.ProjectError("New file appeared during save; refusing overwrite")
                    # 'xb' is exclusive on both Windows and POSIX. In particular,
                    # never call os.replace on a model-proposed new destination.
                    payload = reviewed["proposal"]["files"][path].encode("utf-8")
                    with target.open("xb") as f:
                        written.append(path)
                        f.write(payload)
                    continue
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
            # Persist only directories that this save actually created.
            # A failed metadata write must trigger the same rollback path.
            metadata["created_dirs"] = [p.relative_to(project).as_posix()
                                        for p in created_folders]
            with (backup / "revision.json").open("w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception:
            # Back out only writes that this operation actually completed. A
            # changed user file must never be removed just for convenience.
            for path in reversed(written):
                target = project.joinpath(*projects._check_path(path))
                if projects._reparse(target):
                    continue
                try:
                    if path in added:
                        if (target.is_file() and target.read_bytes() ==
                                reviewed["proposal"]["files"][path].encode("utf-8")):
                            target.unlink()
                    else:
                        restore = target.parent / (".falcon-restore-" + uuid.uuid4().hex + ".tmp")
                        restore.write_bytes(old_payloads[path])
                        os.replace(restore, target)
                except OSError:
                    # Backups are left for explicit user recovery.
                    pass
            _remove_empty_folders(created_folders)
            raise
        return {"project": str(project), "backup_id": backup_id,
                "changed": changes, "added": reviewed["added"], "executed": False}
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
    if (record.get("name") != name or not isinstance(record.get("changed"), list)
            or not isinstance(record.get("added", []), list)
            or not isinstance(record.get("created_dirs", []), list)):
        raise projects.ProjectError("Backup does not match project")
    current = _verify_current(name, record.get("new_fingerprint"), workspace)
    project = _guard_project(name, workspace)
    payloads = {}
    added = set(record.get("added", []))
    if (not record["changed"] or len(set(record["changed"])) != len(record["changed"])
            or len(added) != len(record.get("added", []))
            or not added.issubset(record["changed"])):
        raise projects.ProjectError("Backup has duplicate or missing changed files")
    # This backup can only clean up directories created by the original save.
    possible_dirs = set()
    for filename in added:
        bits = projects._check_path(filename)
        for count in range(1, len(bits)):
            possible_dirs.add("/".join(bits[:count]))
    created_dirs = record.get("created_dirs", [])
    if (len(created_dirs) != len(set(created_dirs))
            or any(not isinstance(d, str) or d not in possible_dirs
                   for d in created_dirs)):
        raise projects.ProjectError("Backup has invalid created-directory metadata")
    original_plan = {
        "name": current["plan"]["name"], "kind": current["plan"]["kind"],
        "files": dict(current["plan"]["files"]),
    }
    for path in record["changed"]:
        target = project.joinpath(*projects._check_path(path))
        if path not in original_plan["files"] or projects._reparse(target):
            raise projects.ProjectError("Backup contents are unsafe")
        if path in added:
            # These files did not exist before the revision. They can be
            # removed only if the entire project matches the saved revision.
            original_plan["files"].pop(path)
            continue
        backed = base.joinpath(*projects._check_path(path))
        if projects._reparse(backed) or not backed.is_file():
            raise projects.ProjectError("Backup contents are unsafe")
        raw = backed.read_bytes()
        if len(raw) > projects.MAX_BYTES_PER_FILE:
            raise projects.ProjectError("Backup contains oversized data")
        try:
            original_plan["files"][path] = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise projects.ProjectError("Backup has invalid UTF-8") from exc
        payloads[path] = raw
    # Check the entire *future restored project* before replacing anything.
    # A corrupted or modified backup must never overwrite working user files.
    if _snapshot_fingerprint(original_plan) != record.get("base_fingerprint"):
        raise projects.ProjectError("Backup integrity check failed; no files restored")
    for path, raw in payloads.items():
        target = project.joinpath(*projects._check_path(path))
        temp = target.parent / (".falcon-rollback-" + uuid.uuid4().hex + ".tmp")
        try:
            temp.write_bytes(raw)
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()
    for path in added:
        target = project.joinpath(*projects._check_path(path))
        _validate_target_parent(project, target)
        if target.is_file() and not projects._reparse(target):
            if target.read_bytes() != current["plan"]["files"][path].encode("utf-8"):
                raise projects.ProjectError("New file changed during rollback; refusing deletion")
            target.unlink()
    # Only remove directories created by the original save, if still empty.
    _remove_empty_folders(
        [project.joinpath(*d.split("/")) for d in created_dirs], stop=project)
    _verify_current(name, record.get("base_fingerprint"), workspace)
    return {"project": str(project), "restored": tuple(payloads),
            "removed_added": tuple(sorted(added)), "executed": False}
