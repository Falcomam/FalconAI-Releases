"""Inert, review-first bridge for future Falcon self-improvement workflows.

The caller supplies a trusted source snapshot. This module neither reads the
installed EXE nor writes source, runs tests, approves installation or publishes.
"""
from __future__ import annotations
import hashlib
import hmac

import self_improve_proposals as proposals


def _sha(value):
    if not isinstance(value, str):
        raise proposals.ProposalError("Source snapshot must contain UTF-8 text")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prepare(changes, source_snapshot):
    """Review against the exact known source snapshot, reject hallucinated baselines.

    source_snapshot is an in-memory {relative_path: original_source} mapping
    supplied by a future trusted, bounded source fetcher (not the model).
    """
    result = proposals.review(changes)
    if not isinstance(source_snapshot, dict):
        raise proposals.ProposalError("Trusted source snapshot required")
    for entry in result["files"]:
        path = entry["path"]
        if path not in source_snapshot:
            raise proposals.ProposalError("Proposed file is not in the trusted snapshot: " + path)
        if not hmac.compare_digest(_sha(source_snapshot[path]), entry["before_sha256"]):
            raise proposals.ProposalError("Stale or fabricated source baseline: " + path)
    return result


def verify_review(changes, source_snapshot, reviewed_fingerprint):
    """Recheck after review without authorizing any write or code execution."""
    if not isinstance(reviewed_fingerprint, str) or len(reviewed_fingerprint) != 64:
        raise proposals.ProposalError("Reviewed proposal fingerprint required")
    result = prepare(changes, source_snapshot)
    if not hmac.compare_digest(result["fingerprint"], reviewed_fingerprint):
        raise proposals.ProposalError("Proposal changed since review")
    return {
        "fingerprint": result["fingerprint"],
        "source_snapshot_verified": True,
        "execution_allowed": False,
        "installation_allowed": False,
        "status": "review_fingerprint_verified_not_tested_or_approved",
    }
