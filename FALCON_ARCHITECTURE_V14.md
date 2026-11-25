# Falcon AI V14 — maintained architecture foundation

**Target:** Falcon AI V14.0.0, a stable engineering foundation for the
owner's Windows local assistant. This document describes **delivered source**
and **future targets** separately. A file in the repository is not proof the
feature is in a user-installed release.

## North-star flow

User request → one Command Center → intent routing → local model selector →
bounded project proposal → static validation → fingerprinted full review →
user approval → safe Falcon-owned workspace → (future, separately approved)
isolated test/build worker → actual rendered result and user acceptance.

Separate, authorized paths cover local PC actions, trusted app updates, and
Ollama lifecycle management; none should silently grant another path rights.

## Component boundaries

| Layer | Maintained module / interface | Contract |
|---|---|---|
| Main app | `falcon.py` (staged reconstructed source) | UI, STOP, approvals; no model-generated arbitrary system commands |
| Local models | `engine_manager.py`, `agent.py` | Installed model selection; localhost Ollama; independent coder choice |
| Resource policy | `gaming_mode.py` | Explicit reversible AI pause, best-effort selected model unload, no FPS promises |
| Developer routing | `developer_chat.py` | One chat, preview and approval; no source execution |
| Proposal schema | `developer_workspace.py` | Strict JSON, safe paths, SHA256 fingerprints, explicit save |
| Static checks | `project_static_check.py`, `html_quality.py`, `site_design_check.py` | Syntax/heuristic checks; no browser simulation |
| Existing projects | `project_browser.py`, `project_revision.py`, `project_targeted_edits.py` | Bounded reads/edits, diff, backup, rollback |
| Public capabilities | `falcon_foundation.py` | Declares shipped/limited/future meaning; no fabricated availability |
| Installer/update | `app_entry.py`, `app_updates.py`, Inno Setup + workflows | Signed/digest-aware release channels, prior-release upgrade tests |

## V14 quality gates

**Q1 No permission escalation:** all new risky actions require user consent;
approved source save does not authorize execution, package installation,
computer control or external network access.

**Q2 No gaming regressions:** explicit ON/OFF state, no new Ollama requests
while paused through chat and agent entrypoint, unload selected loaded models
only, no driver/OS changes. Verify with mocks; actual GPU performance pending.

**Q3 No fake coding success:** generated source can pass static checks and
still look poor. Render a website in a real browser and compare it to
Benchmark #001 in a *future* isolated test worker. Don't describe heuristic
checks as visual evaluation.

**Q4 Preserved app:** single purple GUI, mini monitor, STOP, working prior
commands and autocomplete, one-click updater, notifications and local data.

**Q5 Release integrity:** consistent V14.0.0 metadata across visible GUI,
launcher boot log, RELEASE_VERSION.txt, runtime updater, app entry and Inno
Setup; verified prior v13.9.1 asset digest; frozen app 13/13 diagnostics; clean
install, in-place upgrade, user data and relaunch; explicit no-publish gate
until green.

**Q6 Observable outcomes:** report model, parameters/context, output
retries, time and rendered result on owner's hardware when available.
Never invent model superiority or game FPS.

## Migration plan beyond V14

The historical build is layered on sequential `prepare_*` patches; this
makes integration fragile. Do **not** replace the current production build in
one giant untested rewrite. Instead:

1. Introduce stable public interfaces and living architecture tests (V14).
2. Move independently tested modules into a first-class maintained app
   source tree in small vertical slices, validating identical GUI,
   permissions, local data and updater each time.
3. Add a separately consented isolated test executor (no unbounded shell,
   repo or network access), browser screenshot review, build tooling and
   packaging with safe output.
4. Add coding benchmarks and hardware-specific model policies, including
   gaming-safe mode. Only promote actual measured improvements.
5. Automate candidate staging and release checks; never auto-install or
   self-rewrite an installed EXE without the owner's informed approval.

## Definition of done

A subsystem's **source implementation** is done only when tests pass; a
**Windows candidate** is done only after a frozen build and installer
verification; a **shipped Falcon version** is done only when the trusted
GitHub Release asset and digest exist. Full autonomous app generation,
executing untrusted source and a screenshot-based critic are *not*
automatically implemented by this V14 architecture document.
