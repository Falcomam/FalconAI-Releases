"""Development-only Falcon self-improvement review CLI (no installation).

This tool accepts a trusted checkout and independently trusted SHA256 manifest
supplied by the human/CI caller, plus a model-proposed JSON change. It prints
review information only. It NEVER runs or installs proposed source code.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import self_improve_chat_preview as previews
import self_improve_test_plan as plans
import self_improve_proposals as proposals

MAX_INPUT_BYTES = 1_500_000


def _load_json(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise proposals.ProposalError("Missing or oversized review input")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise proposals.ProposalError("Review input exceeds maximum size")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("Non-standard JSON constant: " + value)

    try:
        return json.loads(raw.decode("utf-8"),
                          object_pairs_hook=unique_pairs,
                          parse_constant=invalid_constant)
    except (ValueError, UnicodeDecodeError) as exc:
        raise proposals.ProposalError("Invalid, ambiguous or non-UTF8 input JSON") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("review", "plan"))
    parser.add_argument("--checkout", required=True, help="Trusted development checkout")
    parser.add_argument("--pinned-manifest", required=True, help="Trusted SHA-256 JSON mapping")
    parser.add_argument("--proposal", required=True, help="Proposed before/after JSON mapping")
    args = parser.parse_args(argv)
    try:
        pins = _load_json(args.pinned_manifest)
        changes = _load_json(args.proposal)
        if args.mode == "review":
            result = previews.render(changes, trusted_checkout=args.checkout,
                                      trusted_sha256=pins)
        else:
            result = json.dumps(plans.plan(changes, trusted_checkout=args.checkout,
                                           trusted_sha256=pins), indent=2,
                                ensure_ascii=False)
        print(result)
    except (OSError, proposals.ProposalError) as exc:
        print("Review blocked: " + str(exc)[:300], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
