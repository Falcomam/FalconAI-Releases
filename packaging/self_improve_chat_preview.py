"""One-chat text preview for development-only Falcon improvement proposals.

This is a pure review formatter, NOT an in-app command. No code execution,
source writes, approvals, test runs or installer changes are performed.
"""
from __future__ import annotations
import hmac

import self_improve_review_bridge as bridge
import self_improve_test_plan as test_plans
import self_improve_proposals as proposals

MAX_PREVIEW = 24_000


def _visible(value):
    # Prevent terminal/GUI control characters from leaking into log/chat preview.
    return "".join(char if char == "\n" or char.isprintable()
                   else ("\\u%04x" % ord(char)) for char in value)


def render(changes, *, trusted_checkout, trusted_sha256, preview_limit=MAX_PREVIEW):
    """Produce a bounded, human-readable, unapproved source diff preview."""
    if not isinstance(preview_limit, int) or not 1200 <= preview_limit <= MAX_PREVIEW:
        raise proposals.ProposalError("Preview must remain bounded")
    summary = test_plans.plan(changes, trusted_checkout=trusted_checkout,
                              trusted_sha256=trusted_sha256)
    reviewed = bridge.prepare_pinned_from_checkout(changes,
                            trusted_checkout=trusted_checkout, trusted_sha256=trusted_sha256)
    if not hmac.compare_digest(summary["proposal_sha256"], reviewed["fingerprint"]):
        raise proposals.ProposalError("Proposal changed while preparing review")
    lines = [
        "FALCON IMPROVEMENT PROPOSAL — DEVELOPMENT PREVIEW ONLY",
        "Fingerprint: " + summary["proposal_sha256"],
        "Changed files: " + str(summary["file_count"]),
        "Code executed: NO | Tests executed: NO | Installed: NO",
        "Dynamic testing requires isolated worker + explicit approval.",
        "Risk indicators are advisory, not proof of safety.",
    ]
    for item in reviewed["files"]:
        path = proposals._path(item["path"])
        flags = item["risk_hints"]
        hints = [str(x["indicator"]) for x in flags["indicators"]]
        lines.append("\nFILE: " + path)
        lines.append("Added lines: " + str(item["line_changes"]["added_lines"]) +
                     " | Removed lines: " + str(item["line_changes"]["removed_lines"]))
        if hints:
            lines.append("Manual risk review: " + ", ".join(hints[:12]))
        lines.append("DIFF:\n" + _visible(item["diff"]))
    body = "\n".join(lines)
    if len(body) > preview_limit:
        return body[:preview_limit - 110] + "\n[Preview truncated: exact full proposal remains unchanged; review source before approval.]"
    return body
