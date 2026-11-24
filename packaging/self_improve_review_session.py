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

MAX_AUDIT_EVENTS = 256


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
        self._events = []
        self._dropped_events = 0
        self._pages_seen = set()
        self._page_count = 0
        self._cached_pages = None

    def _log(self, record):
        self._events.append(record)
        if len(self._events) > MAX_AUDIT_EVENTS:
            self._events.pop(0)
            self._dropped_events += 1

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
        self._pages_seen.clear()
        self._page_count = 0
        self._cached_pages = None
        self._log({"event": "proposal_submitted",
                             "fingerprint": self._fingerprint})
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
        self._pages_seen = {0} if complete else set()
        self._page_count = 1 if complete else 0
        self._log({"event": "review_displayed" if complete else "review_truncated",
                             "fingerprint": self._fingerprint})
        return {"text": output, "fingerprint": self._fingerprint,
                "review_token": self._nonce if complete else None,
                "review_complete": complete, "state": self.state}

    def show_review_page(self, index):
        """Page the full fingerprinted diff; all pages required for consent.

        The human-facing UI must call this from actual navigation. Model output
        must not simulate viewing pages or consent gestures.
        """
        if self._stopped or self._changes is None:
            raise proposals.ProposalError("No active proposal to review")
        if self._cached_pages is None:
            self._cached_pages = previews.render_pages(
                self._changes, trusted_checkout=self._root,
                trusted_sha256=self._pinned)
        pages = self._cached_pages
        if not isinstance(index, int) or not 0 <= index < len(pages):
            raise proposals.ProposalError("Review page is out of range")
        # The cached view is only a presentation optimization. Re-validate
        # current pinned source before returning any page or test consent.
        bridge.verify_pinned_from_checkout(
            self._changes, trusted_checkout=self._root,
            trusted_sha256=self._pinned, reviewed_fingerprint=self._fingerprint)
        if self._page_count not in (0, len(pages)):
            raise proposals.ProposalError("Review pages changed; start review again")
        self._page_count = len(pages)
        self._pages_seen.add(index)
        complete = len(self._pages_seen) == self._page_count
        self._review_visible = complete
        self._consent = False
        self._log({"event": "review_page_displayed",
                             "fingerprint": self._fingerprint,
                             "page": index + 1, "page_count": len(pages),
                             "review_complete": complete})
        return {"text": "Review page " + str(index + 1) + "/" +
                str(len(pages)) + "\n" + pages[index],
                "page": index + 1, "page_count": len(pages),
                "fingerprint": self._fingerprint,
                "review_complete": complete,
                "review_token": self._nonce if complete else None,
                "state": self.state}

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
        self._log({"event": "test_consent_recorded",
                             "fingerprint": self._fingerprint,
                             "scope": "request_isolated_tests_only"})
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
        self._pages_seen.clear()
        self._page_count = 0
        self._cached_pages = None
        self._log({"event": "session_stopped",
                             "consent_revoked": True})
        return {"state": "stopped", "tests_executed": False}

    def audit(self):
        """Return bounded metadata only, signaling if old events were omitted."""
        result = [dict(item) for item in self._events]
        if self._dropped_events:
            result.insert(0, {"event": "older_events_omitted",
                              "count": self._dropped_events})
        return tuple(result)

    reject = stop
