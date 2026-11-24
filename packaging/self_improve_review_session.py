"""Ephemeral approval state for Falcon development-only improvement proposals.

The controller never runs tests, writes source, or installs. An authorized UI
must separately obtain a real user gesture; callers must not allow the model
to invoke 'record_user_test_consent'. Consent permits a FUTURE isolated test
request for this exact proposal, not any arbitrary command or deployment.
"""
from __future__ import annotations

import hmac
import secrets

import self_improve_chat_preview as previews
import self_improve_review_bridge as bridge
import self_improve_test_plan as test_plans
import self_improve_proposals as proposals


class ReviewSession:
    def __init__(self, *, trusted_checkout, trusted_sha256):
        self._root = trusted_checkout
        if not isinstance(trusted_sha256, dict) or not trusted_sha256:
            raise proposals.ProposalError("Trusted SHA256 source manifest required")
        self._pinned = dict(trusted_sha256)
        self._changes = None
        self._fingerprint = None
        self._nonce = None
        self._review_visible = False
        self._consent = False
        self._stopped = False

    @property
    def state(self):
        if self._stopped:
            return "stopped"
        if self._consent:
            return "test_consent_recorded"
        if self._review_visible:
            return "reviewed"
        if self._changes is not None:
            return "draft"
        return "empty"

    def submit(self, changes):
        if self._stopped:
            raise proposals.ProposalError("Session stopped; create a new review session")
        # Validation and source snapshot verification run before state changes.
        checked = bridge.prepare_pinned_from_checkout(
            changes, trusted_checkout=self._root, trusted_sha256=self._pinned)
        self._changes = {
            name: {"before": item["before"], "after": item["after"]}
            for name, item in changes.items()
        }
        self._fingerprint = checked["fingerprint"]
        self._nonce = secrets.token_urlsafe(24)
        self._review_visible = False
        self._consent = False
        return {"fingerprint": self._fingerprint, "state": self.state}

    def show_review(self):
        if self._stopped or self._changes is None:
            raise proposals.ProposalError("No active proposal to review")
        output = previews.render(self._changes, trusted_checkout=self._root,
                                 trusted_sha256=self._pinned)
        # Recheck after the display is built to protect against source changes.
        bridge.verify_pinned_from_checkout(
            self._changes, trusted_checkout=self._root, trusted_sha256=self._pinned,
            reviewed_fingerprint=self._fingerprint)
        complete = "[Preview truncated:" not in output
        self._review_visible = complete
        self._consent = False
        return {"text": output, "fingerprint": self._fingerprint,
                "review_token": self._nonce if complete else None,
                "review_complete": complete, "state": self.state}

    def record_user_test_consent(self, *, review_token, fingerprint):
        """UI-side consent gate. Never route model-written text directly here.

        It records a request to use a future isolated test worker, nothing more.
        """
        if self._stopped or not self._review_visible or self._changes is None:
            raise proposals.ProposalError("Show the complete proposal review first")
        if (not isinstance(review_token, str) or not isinstance(fingerprint, str)
                or not hmac.compare_digest(review_token, self._nonce)
                or not hmac.compare_digest(fingerprint, self._fingerprint)):
            raise proposals.ProposalError("Review token or fingerprint mismatch")
        verified = bridge.verify_pinned_from_checkout(
            self._changes, trusted_checkout=self._root, trusted_sha256=self._pinned,
            reviewed_fingerprint=self._fingerprint)
        self._consent = True
        return {"fingerprint": verified["fingerprint"],
                "state": self.state, "tests_executed": False,
                "deployment_approved": False,
                "scope": "request_isolated_tests_only"}

    def test_plan(self):
        if self._stopped or self._changes is None:
            raise proposals.ProposalError("No active proposal")
        plan = test_plans.plan(self._changes, trusted_checkout=self._root,
                               trusted_sha256=self._pinned)
        plan["review_state"] = self.state
        plan["user_test_consent_recorded"] = self._consent
        return plan

    def stop(self):
        """Permanent fail-closed cancellation; never restore old consent."""
        self._changes = None
        self._fingerprint = None
        self._nonce = None
        self._review_visible = False
        self._consent = False
        self._stopped = True
        return {"state": "stopped", "tests_executed": False}

    reject = stop
