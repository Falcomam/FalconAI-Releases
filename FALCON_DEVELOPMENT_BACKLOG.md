# Falcon Ai — Consolidated development backlog (2026-11-24)

## HIGHEST PRIORITY — Falcon Money Mode (owner request, 2026-11-24)

This supersedes the relative priority of all previously listed *feature-development* backlog items. Preserve non-negotiable security, STOP, packaging integrity, and current-user data. See `FALCON_MONEY_MODE_CUSTOMER_AUTOMATION.md`.

**Why:** owner wants Falcon to help earn real money from Fiverr services: custom websites, original AI art and customer automation for businesses, with screen understanding and minimal repetitive prompts for routine actions.

**Do these tasks first, in order:**

1. **Local Customer Order Assistant MVP in existing Falcon chat:** import owner-provided sanitized order brief, extract deliverables/requirements, quote only provided price, ask about missing details, maintain deadline/revision checklist, draft client replies without sending them, persist/remove project state privately. Tests: no real Fiverr access or unauthorized outbound calls, sanitized local data, restart recall, correct scope, cancellation.
2. **Demo customer-service automation product:** FAQ/chatbot website template based only on client-supplied facts, clear human handoff for unsupported questions, optional approved lead-intake with visitor consent, simple offline reproducible tests and installation guide. Keep client API secrets out of code/logs.
3. **Website quality:** substantially improve AI design prompts; render and inspect real desktop/mobile previews with Playwright in an isolated context; verify navigation; review and fix source with backups, STOP and appropriate code-execution approval.
4. **Original AI graphics offer:** evaluate freely licensed local image-generation tooling for RTX 4060; produce legally usable custom assets; verify commercial licensing and actual output quality before listing a service.
5. **Workflow + research/memory:** support research-backed client briefs and grounded source-linked memory that is reversible, private and refreshable; routine local file/browser preview actions low-friction only within granted scope. No scraping, mass messaging, unauthenticated Fiverr bot, uploads or auto-delivery.

**Release order:** source-only branch/tests → CI → Windows frozen EXE/installer/upgrade verification → trusted public release; no unfinished feature claims. Real clients, sales, revenue and hosting costs cannot be promised.


## Falcon focused-edit and approval sprint — 2026-11-24

**User direction:** substantial coding batches, one purple chat, no per-commit alerts or GitHub manual checking, preserve working installed Falcon V13.9.1 until a full trusted release.

### Built and tested development features

- **Independent coding model**: `/engine use-code <installed_model>` and `/engine coding`; installed-only selection, independent chat model settings, fallback when the coding model is unavailable. No model downloads or increased PC permissions.
- **Bounded local model generation**: two attempts maximum, retry only invalid code/JSON proposals, one shared deadline, STOP checks, no source writes until reviewed. Project revisions retain a larger bounded token output budget.
- **`/project check`** in one chat: read-only static diagnostics for pending source proposals or opened saved Falcon projects, fingerprint/stale-project checks, warnings for possible third-party imports and unsupported runtime validation. No source execution or dependency installation.
- **Better STOP and source draft preservation**: owned busy flag clears on STOP, late callbacks are ignored, and an existing reviewed proposal survives failed replacement generation.
- **Frozen staging integration**: helper modules copied into Windows candidate; project revision staging preserves new command routing; targeted source editing is staged in saved-project browser without replacing full project edits. Command palette exposes installed coding model and static checks, hides unsupported packaged-EXE self-patch shortcut.
- **Targeted source edit path**: `project_targeted_edits.py` chooses relevant complete files from a trusted bounded saved-project snapshot, now scores filename and source-word overlap, includes all explicitly named files or fails clearly, asks Ollama for strict changed-files JSON only, rejects outside-selected existing file edits, merges all untouched files exactly, and submits a normal SHA-256 source diff to existing review/approval/backup/rollback machinery.
- **Staged one-chat focused edits**: `/project edit-small <saved_name> <request>` available only in development candidate. Supports STOP, independent coding model, bounded retry, `/project diff`, explicit `/project approve`, backup ID and rollback. Windows acceptance tests cover no-write-before-approval and full backup/restore on temporary projects.
- **Self-improvement review session**: pinned source hashes, nonce-bound review, all-page visibility before test consent, metadata-only bounded audit history, stale-check before each cached page, STOP cancels consent. Consent does not run tests and never approves an app update.
- **Developer review CLI**: read-only bounded proposal/manifest JSON support and source diff/test planning, never executes or installs code.
- **Repair broken originals**: validate proposed replacement Python/JSON/TOML without rejecting historically broken original source.

### Evidence and release limits

- Numerous source regressions passed on Windows and Linux; saved-project source staging and focused-edit chat with explicit backup/rollback passed Windows development CI.
- An internal frozen-EXE, clean install and upgrade/relaunch/data-preservation run succeeded during this sprint. More recent focused-edit staging has separate source validation; a **fresh internal package validation is required** before release.
- No new public installer/release tag was created. User-installed V13.9.1 stays untouched. These are **development source** features, not claims of installed capabilities.
- Actual model-generated code execution, compiling arbitrary apps, running Fabric toolchains, networked dependency installs and autonomous Falcon EXE replacement remain **not implemented**. A future isolated worker will require explicit permission, verified sandbox boundaries, resource limits, STOP/cancellation and trustworthy build approvals.

### Final focused-edit and clipped-review safety gates

- Focused-edit mode is staged as `/project edit-small <saved_name> <request>`, not yet installed. It uses the existing diff+approval+backup+rollback workflow; Windows staged integration tests exercised full temporary-workspace save and explicit rollback.
- Context selection combines bounded filename and source-word relevance, protects user-named files against silently being omitted, and reports files that exceed context limits rather than writing a partial replacement. Two model attempts at most, with one overall deadline and STOP support.
- **Approval-safety fix:** new project previews >5,000 characters per file or >24,000 characters total can no longer mark a draft as fully reviewed. Staged saved-project revision diffs >26,000 characters likewise refuse approval; user needs smaller changes until complete paged approval is integrated.
- Cross-platform main source regression and staged Windows chat/browsing regression cover these checks. Verify exact head CI before claiming the installer is version-ready. Internal Windows candidate tests deliberately do **not** publish.
- Follow-up usability work: add complete paged source review for generated project files so very large drafts can safely be approved, instead of permanently blocking them on truncated previews.

### Next milestones

1. Verify final cross-platform targeted-edit and final internal Windows installer gates on the exact candidate SHA; repair failures before publishing any version.
2. Strengthen focused edit validation for multiple files and project UI prompts; only ship when frozen runtime, clean install and prior-version upgrade/relaunch/data integrity tests pass.
3. Build and independently security-test an explicit-approval resource-limited isolated project test worker (without modifying the live app).
4. Extend packaging workflows for creating runnable standalone websites/Python apps/mod starters with accurate toolchain compatibility checks.
5. Keep all functionality in one Falcon command center with safe review, STOP and one-click verified updates.

## Extended Falcon coding sprint — post-13.9.1 development (2026-11-24)

**Release status:** All work below is in the public development source. The user's working V13.9.1 remains unchanged. Do not release, claim installed functionality, or hand over an installer until a separate versioned frozen EXE/clean install/upgrade/relaunch/data-retention release gate succeeds.

### Self-improvement source review foundation
- Added `self_improve_review_session.py`: ephemeral draft/review/test-consent states. Exact SHA-256 proposal and unpredictable review token required; rechecks trusted pinned baseline before consent; STOP or rejection permanently invalidates token. Consent is for **requesting future isolated tests only**, never for installation or execution. Truncated previews cannot create approval.
- Added `self_improve_cli.py`: development-only read-only CLI for a caller-pinned trusted checkout and JSON proposal. Supports source diffs or inert test-plan output. Bounded JSON input, duplicate-key/NaN rejection, no model-provided commands and no code execution.
- Proposal reviews can now **repair broken original Python, JSON or TOML source**; the original is bounded and pinned, while the proposed replacement must pass syntax checks.
- Combined Windows and Linux source test suites include the new session, CLI, source repair and review rollback protections.

### Better in-chat Developer Mode, coding models and reliability
- Added `project_static_check.py` and `/project check`: static diagnostics for pending proposals, with a review fingerprint; when a Falcon-owned saved project is opened, checks its snapshot again and refuses stale source. Reports files, lines, digests, source parsing and warnings. Clearly says **no program tests, dependencies or builds were executed**.
- Added `developer_generation.py`: one bounded JSON source repair retry for small local Ollama coding models (max 2 attempts). STOP checked before/after requests, no retries of Ollama transport failures, no writes or auto execution. Applied to new projects and staged edit revisions.
- Added independent coding model selection via `/engine use-code <installed_name>` and `/engine coding`, with saved preference and fallback to the already installed chat model; no model downloads or new permissions. Source-based edit revision uses the same coding selector.
- Fixed Developer Mode STOP clearing its owned busy state and ignoring late callbacks; launching a replacement draft now preserves the previous reviewed proposal until a valid new draft is ready. Busy reject instructs STOP rather than silently dropping the draft.
- Updated single-chat/next-bundle Windows staging scripts to include the new helper and checker; revised project browser/revision patch anchors to retain `/project check` and busy-safe reject handling.
- `validate-falcon-dev-sprint.yml` runs the combined developer, engine, review and security suites across Windows and Linux. Several successful runs occurred during this sprint. The *internal no-publish* Windows installer build must still complete all gates before any release decision.

### Next milestones
1. Finish/fix frozen-executable installer CI, clean install and in-place upgrade/relaunch/data-retention verification for the new development candidate.
2. Add full-source review support when a proposed diff exceeds the chat preview limit; never issue approval for clipped source.
3. Implement a separately authorized isolated test worker only after independent sandbox/security review, resource limits, cancellation, bounded logs and trusted source pinning.
4. Integrate review-first Falcon source improvement workflow into a new packaged runtime; avoid trying to rewrite frozen EXEs. Verified release assets only through the trusted update process.
5. Improve coding output quality, performance, specific actionable diagnostics and standalone coding projects before claiming full autonomous coding capability.

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


## Gaming-friendly local AI and LostFalcon Benchmark #001 — 2026-11-24

**User target:** Falcon should coexist with games on an RTX 4060-class 8 GB VRAM PC with 24 GB system RAM. The aim is to protect game resources, not to promise concurrent heavy local model inference at zero FPS cost. User wants evidence-based coding quality gains; the first public-facing website from V13.9.1 is our reference failure case.

### Development changes (NOT installed in public V13.9.1)
- Explicit reversible `/engine gaming on|off|status`: persists independently of chat/coding model choices. ON pauses new chat/project generation via the staged main GUI, gates agent.ask_ollama, and attempts to unload only Falcon's currently loaded selected chat/coding/vision model names via loopback Ollama `/api/ps` + `/api/generate` `keep_alive:0`. OFF permits future work, with model reloading on demand. No GPU/driver/Windows game settings modified, no shutdown of Ollama service, no model downloads or generated source execution. Unload may affect another Ollama client sharing the same selected model; the UI now warns.
- Gaming ON/OFF actions added to Falcon's command palette and AI Engine menu; busy generation requires STOP or completion before enabling. A saved ON state survives an app restart and boot status reports paused rather than fake Ready.
- Website prompt now requires coherent hero, modern layout, responsive viewport/CSS, meaningful sections, honest CTA links, and no fabricated URLs. It still requests compact valid JSON suitable for a small local model.
- New static website advisory `site_design_check.py` surfaces missing mobile viewport, modern flex/grid layout, responsive CSS adaptation, main landmark, content depth and outbound destination links. It **does not run a browser or score visual beauty**; warnings never silently reject/modify source, and never approve it.
- Deterministic regression `test_site_design_check.py` reconstructs the original two-file LostFalcon website's simple HTML for Benchmark #001. Tests assert multiple design-depth warnings and fewer warnings on a fuller responsive example. User screenshot is **not committed** to the public repo.
- Security/behavior tests `test_gaming_mode.py` mock Ollama, verify scoped unloading, no accidental model loads, explicit on/off persistence, bounded local endpoints, and honest failure status. Developer chat tests cover busy rejection and mode pause. Source suites run on Windows and Linux.
- Official reference: https://github.com/ollama/ollama/blob/main/docs/faq.mdx (model keep_alive/unload, memory/context/parallel requests); actual gaming GPU impact is hardware-dependent and remains **unmeasured**.

### Remaining release and quality gates
1. Verify exact-head Windows + Linux source CI, staged Falcon one-chat integration, and frozen EXE/installer/clean upgrade tests. CI is development-only and may be cancelled/replaced by subsequent pushes. Do not call this a shipped update.
2. Run controlled on-device benchmark with the same LostFalcon prompt on qwen3:4b vs qwen2.5-coder:7b (and optional 14B when not gaming), record real elapsed time, memory, number of retries, static findings and browser screenshots. No measured FPS or model quality improvement exists yet.
3. Add isolated browser-render screenshot review and explicit user-approved website test worker with STOP/resource limits; current HTML hints are not proof of a good design.
4. Decide release version (candidate V13.10.0) only after installer, upgrade/relaunch, preserved user data, and trusted SHA256 release asset checks pass. Keep current installed V13.9.1 working until then.
