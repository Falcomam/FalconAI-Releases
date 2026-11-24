"""Single bounded formatting-repair retry for local Falcon coding models.

Only retries malformed source proposals. No code is executed, installed,
downloaded or saved. STOP cancellation is checked around each model request.
"""
from __future__ import annotations

import time

import developer_workspace as projects

MAX_ATTEMPTS = 2


def generate_with_one_retry(*, kind, messages, model, cancel, ask,
                            token_limit=4600, total_timeout=180):
    if kind not in projects.ALLOWED_KINDS:
        raise projects.ProjectError("Unsupported generated project type")
    if not isinstance(messages, list) or len(messages) < 2:
        raise projects.ProjectError("Developer Mode messages are missing")
    if not callable(ask):
        raise projects.ProjectError("Local coding model unavailable")

    if not isinstance(token_limit, int) or not 1000 <= token_limit <= 10000:
        raise projects.ProjectError("Unsafe coding model output limit")
    if not isinstance(total_timeout, (int, float)) or not 10 <= total_timeout <= 300:
        raise projects.ProjectError("Unsafe coding model time budget")
    deadline = time.monotonic() + total_timeout
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        if cancel.is_set():
            return None
        remaining = deadline - time.monotonic()
        if remaining < 5:
            raise projects.ProjectError("Local coding model time budget exhausted")
        prompts = list(messages)
        if attempt:
            prompts.append({
                "role": "user",
                "content": (
                    "Your previous source proposal was rejected by local static review: "
                    + str(last_error)[:200]
                    + ". Regenerate the ENTIRE project from scratch as one strict JSON object. "
                    "Include all files. Do not add Markdown, commentary, terminal commands "
                    "or claims that the code was executed."
                ),
            })
        raw = ask(prompts, model=model, fmt="json",
                  limit=token_limit, timeout=min(180, remaining), cancel=cancel)
        if cancel.is_set():
            return None
        try:
            candidate = projects.parse_proposal(raw)
            if candidate["kind"] != kind:
                raise projects.ProjectError("AI response used the wrong project type")
        except projects.ProjectError as exc:
            last_error = exc
            continue
        return {
            "name": candidate["name"],
            "kind": candidate["kind"],
            "files": candidate["files"],
        }
    raise projects.ProjectError(
        "Local coding model could not return a valid source proposal after "
        + str(MAX_ATTEMPTS) + " attempts: " + str(last_error)[:240]
    )
