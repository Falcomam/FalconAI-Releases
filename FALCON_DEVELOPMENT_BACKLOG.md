# Falcon Ai — Consolidated development backlog (2026-11-24)

**User direction:** Work in substantial, tested batches. Stay inside ONE Falcon Ai and ONE main chat window. Don't release or notify for tiny progress. Let the verified-test-ready release watcher announce an actual major Windows update. **Current installed version: v13.8.0.**

## Next major bundled milestone: quality and experience

| Priority | Feature / acceptance standard | State |
|---|---|---|
| P0 | Generated website checker detects malformed/unclosed HTML, missing complete UTF-8 meta, required page structure. Warns about broken same-page anchors. Never saves invalid proposals. | Development source; cross-OS CI |
| P0 | One-click **Copy reply** on individual Falcon messages; exact Unicode and multiline code, no other messages or clipboard network access | Development candidate, earlier Windows unit tests passed |
| P0 | Minecraft-style **Tab / Shift+Tab** completion, descriptive hint, **Commands** categorized button next to Send. Inserts but never executes or approves. | Development candidate, earlier Windows unit tests passed |
| P0 | Integration tests: all three coexist with Developer Mode and the original chat; packaged Windows EXE smoke test | Still required |
| P0 | Full Windows installer, v13.8.0 → newer-version in-place upgrade, relaunch and local-data-preservation test, SHA-256 digest | Required **before** release |

## Next planned coding upgrades (prioritized independently)

1. **Edit existing projects through chat:** Ask Falcon to revise a prior generated project. Show a per-file diff; allow user to approve exact changed files, stage a backup, and rollback. Never silently overwrite a different project or files outside its workspace.
2. **Better validation:** Python AST parse and optional linting, HTML structural diagnostics, JSON validation, JavaScript syntax-only checks with locally available runtimes when authorized. Explicitly differentiate static checks from executed tests.
3. **Safe run/test loop:** Optional isolated and resource-limited code execution behind explicit user approval, with STOP and a visible record of commands/results. Never run generated code as part of drafting or previewing.
4. **Coding model support:** Switch a dedicated local coding model when installed and resource-feasible; retain safe fallback and clear Ollama error messages.
5. **Project packaging:** For websites show preview instructions; for Python create environment scaffolding/requirements; for Fabric mod starters validate version compatibility before promising runnable jars. Ask permission for dependency installs, builds and executables.
6. **Long-project management:** Small project index in the main chat, reopen a saved draft, file list, code search and inline diffs. No new AI windows.

## Reliability / interface milestones

7. **Ollama resilience:** local-only health checks and reconnect; optional start action; error handling when model missing, exhausted memory, or server stops mid-request. No silent installations.
8. **Unified dark-purple redesign:** cleaner message blocks, command picker integrated into composer, responsive screen sizes, readable code/diffs, subtle copy affordance, falcon icon branding, accessible contrast and keyboard navigation. Keep GUI lightweight and familiar.
9. **Diagnostics:** optional connection-status display, simplified privacy-reviewed support report, reproducible local error summaries, consistent STOP behavior and cancellation tests.
10. **Windows release engineering:** CI matrices for new features, exact installer identity, integrity-verified updates, install/upgrade/relaunch/data-retention tests before release.

## Safety and truthfulness rules

- Each item remains **planned or development-only** until its concrete code and tests are completed.
- No model-generated source is automatically executed, installed, deployed, or given new PC permissions.
- Code changes via GitHub must have reviewable commits and tests; failures block publication.
- Development automations may not have connected tool access on every run; if unavailable, record blockers, do not pretend work happened.
- Release only a meaningful batch, with notes of tested features and limitations. **User action** is only needed for verified install/testing or an essential approval decision.
