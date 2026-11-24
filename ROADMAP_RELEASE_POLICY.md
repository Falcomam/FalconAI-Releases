# Project Falcon — Release and Update Policy

**User-approved preference (2026-11-24):** Bundle multiple related, tested features into **one substantial Falcon Ai update** instead of frequently releasing tiny versions. Avoid asking for a manual reinstall or desktop ZIP extraction when Falcon Ai's verified in-app installer updater can be used.

## Release cadence
- Feature bundles: collect meaningful work (reliability, Model Manager, Developer Mode, UI polish), test each subsystem, then publish one consolidated release.
- Exceptions: urgent security fixes, broken startup, or broken updater may justify isolated emergency fixes.
- No arbitrary scheduled release dates. Ship only after tests and clear release notes.
- Preserve the working Windows installer-based update → automatic relaunch path, purple Falcon icon, purple minimalist Command Center, Mini Monitor, local data, Ollama, STOP, and explicit authorization boundaries.
- Test against previous installed Falcon Ai release using a native Windows upgrade integration test that checks update completion, relaunch, and user-data preservation.
- Never ship untested model-generated code, grant broader PC permissions, or move/deleting user files as part of convenience updates.

## Planned bundled release: Falcon Ai V13.8.0
1. AI engine health checking, clear offline status, manual reconnection and safe launch prompt.
2. Optional local model selection (Qwen or installed Llama model) without changing PC safety policy.
3. First Developer Mode: plain-English multi-file project proposals, preview, explicit user approval before writing to a confined local workspace, syntax-only checks; no arbitrary code execution.
4. Diagnostics and end-to-end packaged Windows installer update/relaunch tests.
