# Falcon Ai — Consolidated development backlog (2026-11-24)

## Extended coding sprint — review pipeline and model-response quality

- Added risk hints for potentially high-impact Python APIs, including subprocess, dynamic execution and writing files. The analyzer uses AST only, flags common import aliases and explicitly labels findings **advisory only**, not proof of safety.
- Added `self_improve_chat_preview.py`: renders a bounded human-readable source diff, exact fingerprint, risk notes and explicit no-execution/no-installation labels. It is **not yet connected to the installed Falcon GUI**.
- Expanded `self_improve_test_plan.py` to carry advisory manual-review warnings forward without executing any dynamic tests. Source and test plan remain pinned to independently trusted SHA-256 manifests.
- Hardened the read-only source snapshot loader to reject symlink/reparse ancestors and added regression coverage.
- Improved `developer_workspace.parse_proposal`: accepts a single clean Markdown JSON fence from smaller Ollama models while refusing surrounding commentary, duplicate keys and nonstandard JSON values. Added strict JSON/TOML project-file validation and line/column JSON errors.
- **Release status:** These changes are in development source only. User's installed V13.9.1 remains unchanged. Complete Windows CI suites and package/upgrade integration are required before any new release.

## Current self-improvement development sprint — 2026-11-24

- The review-only source proposal gate and SHA-256 baseline bridge passed Windows regression tests (run 45504551336).
- Added `packaging/self_improve_source_snapshot.py`: bounded reads of explicitly named source files from a caller-selected development checkout, with path/size checks, reparse-point/symlink refusal, inode checks and byte-exact UTF-8 decoding. It does **not** prove checkout identity and must not be pointed at a model-selected path or the installed app.
- Added `prepare_from_checkout` and `verify_from_checkout` in the review bridge. It re-reads the source on verification and rejects stale changes. Existing Falcon's installed EXE is unchanged.
- Expanded review to validate TOML syntax and report lines added/removed. Parsing source is not executing tests or certifying code safety.
- Added `packaging/self_improve_test_plan.py` to produce inert, fingerprint-linked test-gate descriptions. The plan never executes generated code or installs dependencies. Dynamic tests are specifically marked as requiring isolated execution and explicit approval.
- Added Windows CI tests for source reader, live rechecks, syntax checks and inert test plans. Earlier source-reader Windows validation passed (run 45504969427) and TOML review suite passed (run 45505116775). Verify the latest combined run status separately before declaring all changes tested.
- **New pinned-source validation:** `read_pinned_snapshot` checks caller-provided SHA-256 digests against byte-exact checkout contents; the review bridge exposes pinned prepare/recheck methods. Digests must come from independently trusted CI metadata, **never** from the model. The inert test-plan builder now requires these pinned digests.
- **Next:** independently verify source manifest provenance, explicit test approval UI, sandboxed worker with cancellation and bounded logs, then a complete frozen EXE and installer integration run. Keep all of this development-only until those gates pass.

## Verified v13.9.1 user acceptance and next self-improvement work (2026-11-24)

- User installed v13.9.1 and supplied a support report showing **13/13 packaged diagnostics passed**. Auto Improve correctly reports that legacy source-file upgrades are blocked for the installed EXE; this is an intentional safety restriction, not a crash.
- Published verified v13.9.1 Windows update: https://github.com/Falcomam/FalconAI-Releases/releases/tag/v13.9.1 ; installer pipeline succeeded with real prior-version upgrade, clean install and data preservation: https://github.com/Falcomam/FalconAI-Releases/actions/runs/45503489494.
- **Development-only, not installed:** `packaging/self_improve_proposals.py` reviews bounded source edits as inert text with Python/JSON syntax checks, readable unified diffs and SHA-256 proposal fingerprints.
- **Development-only, not installed:** `packaging/self_improve_review_bridge.py` requires a trusted caller-supplied source snapshot and checks the exact baseline digest and reviewed proposal fingerprint; it rejects stale, fabricated or altered source. It neither fetches installed code nor executes or writes proposals.
- Tests: `packaging/tests/test_self_improve_proposals.py` and `test_self_improve_review_bridge.py`; native Windows CI workflow `validate-self-improve-proposals.yml`. Do not claim that future run succeeded until its conclusion is checked.
- **Next integration gate:** design a bounded trusted source reader and explicit GUI review flow, then separate permission-gated isolated tests/builds; no self-installation or unrestricted code execution. Keep these components off the packaged runtime until full Windows release gates pass.


**User direction:** Work in substantial, tested batches. Stay inside ONE Falcon Ai and ONE main chat window. Don't release or notify for tiny progress. Let the verified-test-ready release watcher announce an actual major Windows update. **Latest verified release: v13.9.1 (2026-11-24); user confirmed installation and 13/13 diagnostics.**

## Latest completed bundle: Falcon Ai V13.9.0 — released, Windows verified

- **Official release:** https://github.com/Falcomam/FalconAI-Releases/releases/tag/v13.9.0
- **Successful Windows installer and in-place upgrade CI:** https://github.com/Falcomam/FalconAI-Releases/actions/runs/45499071490
- **Verified installer:** Falcon_Ai_Setup.exe, SHA256 `8e2f7642b19a0a55d08d27d48ddf7f1edc53ee473f2ee74452eeea0011de7e4b`.
- Includes Copy Reply, command completion/picker, website source quality checks, saved-project list/open/show, reviewed source edits and additions, safe file backups and rollback, retaining one purple chat, Ollama and STOP.
- GitHub Windows CI passed source regression, frozen EXE smoke, clean install, v13.8.0 -> v13.9.0 installer upgrade/relaunch and preserved user data. **Do not mistake this for user-hardware acceptance testing.**
- Next development work is post-v13.9.0 and must remain development-only until a new substantial tested package is released. Never rewrite v13.9.0 GitHub Release assets.

## Frozen-EXE diagnostic mismatch from user V13.9.0 report (2026-11-24; fixed in V13.9.1)

- **Confirmed user report:** Installed Falcon V13.9.0 GUI starts, but legacy `diagnostics.py` (carried forward from V13.5) checks 11 loose `.py` files plus `START_HERE.bat`/`ROLLBACK_LAST_UPDATE.bat`, reporting 0/13 despite a valid frozen Windows installation. Two Improve runs were blocked and installed no patch.
- **Post-release development fix:** `packaging/packaged_diagnostics.py` checks 11 bundled import loaders plus the installed `Falcon Ai.exe` and `app_update_restart.ps1` instead. Report records its scope, and existing Copy Report code still recognizes `present` statuses.
- **Safety:** `packaging/prepare_packaged_health_candidate.py` overrides the legacy diagnostics module **only in frozen app entry**, preserves source legacy behavior, and blocks the old source-file self-upgrader's auto/run/install/rollback against packaged EXEs. Improve must say it is unsupported rather than pretending to modify an EXE or attempting to overwrite bundled files. Existing user data is untouched.
- **Windows frozen EXE smoke PASS:** [health candidate Windows tests, including frozen Improve guard](https://github.com/Falcomam/FalconAI-Releases/actions/runs/45501935842) verify actual packaged self-check writes **13/13 present** statuses, not only source-level mocks. The separate guard regression test is also included in later validation.
- **Released in V13.9.1 and confirmed by user:** Installed self-check now reports 13/13. Legacy EXE source rewriting remains blocked by design. Future self-improvement requires an approved test/build/release pipeline.

## Post-v13.9.0 tested development: read-only source search + minimized update PowerShell

- `/project open <saved_name>` then `/project search <phrase>`: read-only source search in the **one already opened Falcon-owned developer project only**. Bounded to 25 line excerpts with filename/line info and stale snapshot fingerprint verification. Supports Unicode symbols and never accesses unrelated directories or executes source code.
- Updated the **internal installer-updater PowerShell** launch for future versions to use `-WindowStyle Minimized` and Windows `STARTF_USESHOWWINDOW/SW_SHOWMINNOACTIVE`. User-requested terminals and Ollama permissions remain unchanged, logs remain in `LOCALAPPDATA/FalconAI/logs/app_installer_update.log`.
- The installed Windows `Falcon Ai.exe` is already built as a windowed, no-console GUI; normal Start Menu and Desktop shortcuts point to this EXE. An older shortcut pointing to `START_HERE.bat` or `powershell.exe` can still show a console and must be repinned to the current EXE (not something fixed by minimizing the updater helper).
- **Verified on Windows CI:** [source + in-chat + minimized PowerShell mocked-process tests](https://github.com/Falcomam/FalconAI-Releases/actions/runs/45500259624). This does **not** include a new installer or actual GUI update on the user's PC.
- **Release policy:** Remains post-13.9 development work, for a future tested bundled release. Do not rewrite published v13.9.0 or claim the current installed version has this fix.

## Post-v13.9.0 priorities

1. Improve coding model output quality and show actionable static code diagnostics.
2. Read-only source search in saved projects in the original chat. Do not give filesystem-wide search or code-execution rights.
3. Improve per-file source edits to reduce small-model context overhead without breaking explicit review, SHA256 approval and backups.
4. Add opt-in, safely restricted build/test capabilities (requires permission and platform isolation).
5. Improve Ollama reconnect, performance, STOP behavior and purple UI coherence.
6. Validate new bundled Windows releases using EXE smoke, clean install, real upgrade/relaunch and data integrity checks; publish only after full gates.

## Next planned coding upgrades (prioritized independently)

1. **Edit existing projects through chat:** Ask Falcon to revise a prior generated project. Show a per-file diff; allow user to approve exact changed files, stage a backup, and rollback. Never silently overwrite a different project or files outside its workspace.
2. **Better validation:** Python AST parse and optional linting, HTML structural diagnostics, JSON validation, JavaScript syntax-only checks with locally available runtimes when authorized. Explicitly differentiate static checks from executed tests.
3. **Safe run/test loop:** Optional isolated and resource-limited code execution behind explicit user approval, with STOP and a visible record of commands/results. Never run generated code as part of drafting or previewing.
4. **Coding model support:** Switch a dedicated local coding model when installed and resource-feasible; retain safe fallback and clear Ollama error messages.
5. **Project packaging:** For websites show preview instructions; for Python create environment scaffolding/requirements; for Fabric mod starters validate version compatibility before promising runnable jars. Ask permission for dependency installs, builds and executables.
6. **Long-project management:** Small project index in the main chat, reopen a saved draft, file list, code search and inline diffs. No new AI windows.

## In-chat saved-project revisions — development candidate (2026-11-24)

**Implemented and verified in Windows source/functional CI (not yet released):**

- `/project edit <saved_name> <request>` loads only an existing Falcon-owned developer project, supplies those bounded source files to the local coding model, and requires the same filename set/name/type in its JSON response.
- `/project diff` and `/project review` display a source-only unified diff and fingerprint in the original Falcon chat; `/project show <file>` still previews proposed source.
- `/project approve` cannot save until a review. Saves only when original project contents and proposed SHA-256 fingerprint are unchanged; makes exact-byte backup outside the project before changing anything.
- `/project rollback <name> <backup_id>` explicitly restores the saved snapshot **only if neither the user's current files nor backup contents have been modified**, protecting later edits from being overwritten.
- Existing V13.8 websites with malformed HTML can be loaded for repair even though the **replacement** must pass new static HTML checks. No generated project code is executed.
- Unit and staged Windows chat acceptance tests cover diff, review-before-approval, rejection, stale files, unsafe paths, malformed syntax, backup integrity, old-site repair and rollback: [verified Windows CI](https://github.com/Falcomam/FalconAI-Releases/actions/runs/45495562641).

**Limits:** only previously saved Falcon projects; edits can change and **add** approved plain-text source files. Deletion and renaming remain blocked. Full project rewrites may exceed a small local model's context size. No EXE/installer was published for this work. The next major release still requires packaged Windows GUI/installer and in-place upgrade/relaunch tests.

## Extend existing projects with new source files (development candidate, 2026-11-24)

- Falcon can now propose **new project source files** as part of `/project edit`, alongside changes to existing files. Review displays their `/dev/null` diff; `/project approve` still requires an explicit review and exact SHA-256 proposal fingerprint. All original file paths must remain.
- New destinations use exclusive file creation, rejecting existing paths instead of silently overwriting; path traversal, redirected folders, changed originals, invalid syntax and unexpected project-type changes are refused.
- Revision backups track changed originals and which new files and directories Falcon created; explicit rollback restores originals, removes approved new files only when the current snapshot is unchanged, and keeps user-created or pre-existing folders.
- Windows regression tests include nested additions, add-only proposals, mixed edits/additions, actual chat approval and rollback, bad paths, symlink attacks, stale edits and pre-existing directory retention: [source and chat test result](https://github.com/Falcomam/FalconAI-Releases/actions/runs/45497770802).
- **No automatic execution or installation of generated code**. Source validation is not the same as executing a program. Full packaged GUI/installer, v13.8.0 upgrade/relaunch and user-data checks remain release gates.

## Saved-project browser in Falcon's main chat (development candidate, 2026-11-24)

- Implemented read-only `/project list`, `/project open <saved_name>`, and `/project show <relative_file>` for safely inspecting prior Falcon-owned Developer Mode projects.
- The organized Commands menu contains List and Open shortcuts; the project catalog is bounded (50 visible names / 500 scanned directory entries). No command executes project source or reads outside Falcon's developer workspace.
- Opening a project does not approve any code changes. It refuses to displace an active review; file previews check the snapshot fingerprint and refuse stale or modified data, unsafe paths, redirected files and symlinks. Existing STOP and review/approval behavior stays unchanged.
- Passed combined native Windows source, Python and one-chat regression suites including previous project-revision feature. [CI evidence](https://github.com/Falcomam/FalconAI-Releases/actions/runs/45496335846).
- **Not yet released:** This remains part of the next substantial Windows installer bundle, pending frozen app, full installer, v13.8.0 upgrade/relaunch and user-data-preservation tests.

## Reliability / interface milestones

6a. **Optional PC-powered build/test worker:** Later investigate an explicit opt-in Windows worker on the user's own main PC that only pulls trusted Falcon sources and runs *pre-approved* builds/tests in an isolated directory with resource limits, STOP, logs, and no unrestricted remote desktop/filesystem access. This would add compute for model inference, builds and local testing; it would **not** make the ChatGPT model faster or automatically grant cloud ChatGPT access to the PC. No worker is connected or deployed yet.

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
