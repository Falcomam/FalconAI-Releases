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

## One Falcon Ai, one chat window (user preference, 2026-11-24)

Treat **Falcon Ai's existing main chat** as the single interface for all capabilities. Users ask naturally for coding projects, Ollama health/model changes, PC tasks, research, and future functions in that same conversation. Developer Mode should use inline chat project proposals, previews, approval and rejection commands rather than spawning a separate chat, Developer Studio window, or multiple assistants. Keep existing Tools/Updates menus for optional shortcuts only; their actions should feed into the same main chat. Separate opt-in Mini Monitor is a utility, not an additional AI. Avoid modal popups except security-critical explicit approval or essential settings. Preserve existing STOP and permission boundaries. Do not publish the proposed separate-window Developer Studio prototype.

## Future Falcon Ai visual redesign (user preference, 2026-11-24)

User wants Falcon Ai to look significantly better in a future bundled release. Keep **one unified chat window** rather than separate modules/apps. Preserve the permanent purple falcon identity, dark/purple visual theme, clean uncluttered gaming-friendly desktop footprint and accessible status/STOP controls. Candidate UI work: more balanced layout and whitespace, consistent typography, refined purple accents, higher-contrast AI online/offline indications, readable inline code/project previews, simple model controls integrated without busy side panels, responsive window sizing, thoughtful keyboard navigation. Make the redesign after core connectivity and coding reliability are solid, and ship in a consolidated major update with Windows visual acceptance testing. Avoid claiming the redesign is implemented until the app is built and verified.
