# Falcon AI — engineering instructions for future coding sprints

## OVERRIDING OWNER PRIORITY: Falcon Money Mode (set 2026-11-24)

**2026-11-24 latest owner preference: real browser autonomy.** The owner wants Falcon to research a task and actually click through the browser, complete forms, upload prepared product files and verify its work, without screenshot-by-screenshot coaching. The highest-priority first implementation is a seller-invoked, policy-conscious Payhip workflow: use official Payhip instructions, semantic Playwright controls plus optional local qwen2.5vl vision when ambiguous, a separate persistent local Chrome login profile, bounded actions/STOP, exact reviewed product files, and verified Invisible-only listing creation. Do not claim it is shipped until a frozen Windows executable, real-browser offline simulation, installer and upgrade/restart checks pass. Never scrape buyer data, bypass platform protection, copy passwords/cookies to external tools, change payments, or publish publicly without explicit owner authorization. Keep future workflows site-specific with safe allowlists; no unrestricted blind-click agent.


**Number-one priority over all optional/new features:** turn Falcon into a practical, free-first Fiverr-business assistant that helps the owner earn revenue by making **client-ready websites, original AI graphics and customer-service automation projects**, and by organizing the owner's customer work. This prioritization overrides the older generic feature ordering and cosmetic/UI ideas below. It does not override security safeguards, preserving a working app, STOP, data retention, legal/platform restrictions or required release validation.

**Next actionable development deliverable:** implement a fully local **Customer Order Assistant** in Falcon's existing purple chat. It should accept a manually provided client brief; capture requested work, quoted price (only if supplied), customer requirements, deadlines, revisions and missing details; maintain privacy-safe local state; draft personalized responses; and show the reviewable deliverable checklist. Do not auto-contact Fiverr clients or scrape orders.

**Then:** build a tested customer-service **FAQ chatbot template** to sell to approved clients (grounded in their supplied FAQs; safe unknown-answer/human-handoff behavior); significantly improve responsive website generation/preview/test/fix quality; then support licensed original artwork with free local tooling. Make practical cross-feature improvements only when they unblock this priority (e.g. web research, retrieval memory, bounded browser preview, file operations).

**Business reality:** no claims of automatic earnings, guaranteed sales, zero-cost always-on hosting or a functional Fiverr connection unless verified. Protect customers' data; use platform-native auto-replies and human approval for messaging, deliveries, account or financial actions. Defer low-value redesigns and generic slash-commands unless they directly serve a working customer deliverable.


The owner wants Falcon to become a capable, gaming-friendly **local Windows assistant
and software-development agent**. Work in the real repository and make tested
commits, not fictional releases. GPT-6 can implement Falcon through tools but
**does not run inside Falcon** unless a supported model/API is separately
installed and configured.

## Non-negotiable product contract

- **One Falcon Command Center**: one dark-purple main chat, not separate AI
  windows. Preserve keyboard input, STOP, review and explicit approval.
- **Gaming first**: on the owner's RTX 4060 / 24 GB RAM, pausing local AI and
  unloading Ollama models must be possible before gaming. Never claim GPU
  or FPS measurements until the user's PC is actually measured. Do not
  change power plans, driver settings, GPU clocks or unrelated processes.
- **Safety gates**: generated project source is untrusted. Source review and
  user approval are separate from execution/testing consent and separate
  again from application-upgrade consent. STOP must work, and backups must
  preserve local data. No autonomous self-patching of frozen EXEs.
- **Honesty**: differentiate static syntax validation, mocked unit tests,
  frozen installer checks, true browser screenshots, and real on-device
  end-user tests. Never mark a capability shipped because a source module
  was committed.
- **Release channel**: installed Falcon only changes via a trusted, newer
  GitHub Release with checked installer digest and verified Windows
  install/upgrade/relaunch preserving %LOCALAPPDATA%/FalconAI.
- **Privacy**: never commit user screenshots, personal path details, logs,
  memories, credentials, screenshots of private apps, raw prompts or models.

## Existing repository anatomy

- `packaging/`: reusable **source modules**, Windows packaging entry,
  deterministic transformation stages, local-model integrations.
- `packaging/prepare_*.py`: build-time, exact-anchor staging from previous
  verified source; no user-machine installs. Historical stages are brittle
  and should eventually be replaced by a maintained first-class source tree
  through an independently verified migration.
- `packaging/tests/test_*.py`: mocked source tests and fail-closed
  security/approval tests.
- `.github/workflows/validate-*.yml`: source regressions; verification of
  packaging requires separate Windows frozen executable and installer gates.
- `packaging/falcon_foundation.py`: machine-readable truthful capability
  catalog for shipped, limited and future functionality.
- `FALCON_ARCHITECTURE_V14.md`: modular architecture and migration roadmap.
- `FALCON_LOCAL_AI_GAMING_RESEARCH_2026_11_24.md`: hardware and benchmark
  research, including first LostFalcon site benchmark.

## Coding sprint checklist

1. Read this contract, actual latest public release tag, relevant source,
   the current development backlog and the user's newest feedback.
2. Define bounded acceptance tests BEFORE adding capability claims.
3. Make modular change(s) and review negative/security cases. Never
   download unreviewed model-produced scripts or execute project code.
4. Run mocked regression tests. Check staged integrations, not only
   free-standing modules: frozen import availability, CLI/main-chat
   interactions, no bypasses, STOP, data safety.
5. For Windows release candidates: frozen EXE import/self-tests including
   packaged 13/13 health, clean installer, SHA256-verified current public
   release upgrade, automatic relaunch and user data preservation.
6. Only after ALL release gates pass: publish version and installer with
   correct app/updater/installer version identity, digest, release notes,
   limitations. Never overwrite a public release tag.
7. Report exactly what was changed/committed/tested and what's missing.
   When a requested release is not complete, say so; no background promises.

## Models and quality

Chat model, coding model and vision model are different roles. Small
models may need concise prompts, smaller edit contexts, retries, and static
checks. Benchmark #001 is a two-file, bare-purple LostFalcon YouTube
website created in V13.9.1. Its screenshot is a user-owned reference not
to be placed in a public GitHub repository. Evaluate new websites by
same request, code correctness, rendered screenshot, working navigation,
mobile responsiveness, elapsed generation time and FPS impact when gaming.
A CSS heuristic cannot measure visual taste.

## Anti-patterns to avoid

- Another new /command that duplicates existing functionality without
  improving quality, usability or evidence.
- "Self improving" a packaged Windows EXE by writing into its bundled files.
- Fake claims of Docker/browser testing or a fully built Fabric mod.
- Making gaming mode silently kill processes or tune GPU clocks.
- Auto-approving unreviewed project source or running untrusted code.
- Calling a CI green check a public release before SHA256/installer gates.
