"""Describe test gates for a reviewed Falcon improvement without running them.

This is planning data only. No subprocess, no shell invocation, no permission
grant, no filesystem writes, no model-provided commands. A future sandbox
worker must independently verify paths, snapshot hashes and user consent.
"""
from __future__ import annotations

import hashlib
import re

import self_improve_review_bridge as bridge
import self_improve_proposals as proposals

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def plan(changes, *, trusted_checkout, trusted_sha256):
    """Return exact pinned review digest and non-executable test requirements.

    The returned steps are descriptions rather than commands. Tests that run
    arbitrary Python are always categorized 'requires_approved_isolation'.
    """
    reviewed = bridge.prepare_pinned_from_checkout(
        changes, trusted_checkout=trusted_checkout, trusted_sha256=trusted_sha256)
    files = []
    for item in reviewed["files"]:
        path = proposals._path(item["path"])
        if not HEX64.fullmatch(item["before_sha256"]) or not HEX64.fullmatch(item["after_sha256"]):
            raise proposals.ProposalError("File fingerprint unavailable")
        extension = path.rsplit(".", 1)[-1].lower()
        static = ["source_size_and_path_checks", "source_diff_and_fingerprint"]
        if extension == "py":
            static.append("python_ast_parse")
        elif extension == "json":
            static.append("json_decode")
        elif extension == "toml":
            static.append("toml_decode")
        else:
            static.append("manual_format_review")
        files.append({"path": path, "baseline_sha256": item["before_sha256"],
                      "proposed_sha256": item["after_sha256"], "static_checks": static,
                      "line_changes": item["line_changes"]})
    return {
        "proposal_sha256": reviewed["fingerprint"],
        "file_count": len(files),
        "files": files,
        "static_review": "performed_without_executing_source",
        "dynamic_tests": "requires_approved_isolation",
        "dynamic_tests_executed": False,
        "installer_built": False,
        "deployment_approved": False,
        "next_required_gate": "explicit_approval_of_isolated_test_plan",
    }
