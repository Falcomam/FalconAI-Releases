"""Read-only static diagnostics for proposed Falcon Developer Mode projects.

Accepts the already reviewed in-memory project plan. No filesystem access,
network, subprocess, imports of generated project modules, or code execution.
"""
from __future__ import annotations

import ast
import hashlib
import hmac
import json
import tomllib

import developer_workspace as projects


def inspect(plan, expected_fingerprint=None):
    """Re-validate, summarize file types, warnings and source content digests."""
    review = projects.review_proposal(plan)
    if expected_fingerprint is not None:
        if (not isinstance(expected_fingerprint, str)
                or not hmac.compare_digest(review["fingerprint"], expected_fingerprint)):
            raise projects.ProjectError("Project changed since its review; generate a new review")
    files = []
    total_lines = 0
    warnings = list(review["quality_warnings"])
    for path, contents in sorted(review["files"].items()):
        extension = path.rsplit(".", 1)[-1].lower() if "." in path else "other"
        raw = contents.encode("utf-8")
        lines = len(contents.splitlines())
        total_lines += lines
        static_gate = "text_review_only"
        if extension == "py":
            ast.parse(contents, filename=path)
            static_gate = "python_ast_parsed"
        elif extension == "json":
            json.loads(contents)
            static_gate = "json_syntax_parsed"
        elif extension == "toml":
            tomllib.loads(contents)
            static_gate = "toml_syntax_parsed"
        elif extension in ("html", "htm"):
            static_gate = ("html_structure_reviewed" if review["kind"] == "website"
                           else "html_not_verified")
        elif extension in ("js", "mjs", "java", "kt", "kts", "gradle", "css"):
            static_gate = "syntax_not_executed_or_compiled"
            warnings.append(path + ": full language validation requires an approved isolated worker")
        files.append({
            "path": path, "bytes": len(raw), "lines": lines,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "static_gate": static_gate,
        })
    return {
        "project": review["name"],
        "kind": review["kind"],
        "fingerprint": review["fingerprint"],
        "file_count": len(files),
        "total_lines": total_lines,
        "files": files,
        "warnings": warnings[:30],
        "warnings_truncated": len(warnings) > 30,
        "code_executed": False, "tests_executed": False,
        "dependencies_installed": False, "build_created": False,
    }


def render(report, *, limit=12000):
    """Bounded in-chat report. This never implies generated source was run."""
    if not isinstance(limit, int) or limit < 1000 or limit > 12000:
        raise projects.ProjectError("Invalid static report limit")
    result = [
        "PROJECT STATIC CHECK (no code executed)",
        "Project: " + report["project"] + " | Type: " + report["kind"],
        "Source fingerprint: " + report["fingerprint"],
        "Files: " + str(report["file_count"]) + " | Source lines: " + str(report["total_lines"]),
    ]
    for file in report["files"]:
        result.append("- " + file["path"] + " (" + file["static_gate"] + ")")
    if report["warnings"]:
        result.append("Warnings/limits:")
        result.extend("- " + w for w in report["warnings"])
    result.append("Executed tests: NONE | Installed dependencies: NONE | Compiled builds: NONE")
    text = "\n".join(result)
    if len(text) > limit:
        return text[:limit - 70] + "\n[Static report truncated. All source remains unchanged.]"
    return text
