# Falcon AI — local Windows assistant

Falcon is a dark-purple, single-window Windows assistant that uses local
Ollama models, explicit approval before risky PC/file actions, reviewed
source-code projects and trusted installer-based updates.

**Latest public release at the start of the V14 sprint:** `v13.9.1`.
**Target under development:** `v14.0.0` Foundation. Work in this repository
is **not installed on the user's PC just because it is committed**.
Follow the [GitHub Releases page](https://github.com/Falcomam/FalconAI-Releases/releases)
for the authoritative available installer and verified asset digest.

## Project entry points

- [AGENTS.md](AGENTS.md) — durable engineering agreement for code assistants:
  one chat, STOP, gaming-safe AI, review/permission boundaries, release checks
- [FALCON_ARCHITECTURE_V14.md](FALCON_ARCHITECTURE_V14.md) — V14 module
  boundaries, quality gates and migration away from layered patch scripts
- [FALCON_DEVELOPMENT_BACKLOG.md](FALCON_DEVELOPMENT_BACKLOG.md) — completed
  source work versus planned features and known limitations
- [Local AI and gaming research](FALCON_LOCAL_AI_GAMING_RESEARCH_2026_11_24.md)
  — research limits and RTX 4060 / 24 GB RAM benchmark protocol
- [Release process](RELEASE_PROCESS.md), [update policy](ROADMAP_RELEASE_POLICY.md)

## V14 foundation development

- `packaging/falcon_foundation.py`: capability contract, honest
  `/foundation status` summary of available/limited/planned behavior
- `packaging/gaming_mode.py`: explicit local AI pause and best-effort Ollama
  model unloading to avoid competing with games on the same GPU
- `packaging/developer_chat.py`: single-window Developer Mode, independent
  coding model and reviewed project source; no auto execution
- `packaging/site_design_check.py`: static website-design **hints**;
  does not render screenshots or guarantee aesthetic quality
- `packaging/prepare_v14_release_candidate.py` and
  `packaging/v14_release_checks.py`: full app source/updater identity staging
  with strict checks, stable Windows installer AppId
- `.github/workflows/verify-falcon-ai-v14.yml`: **no-publish** Windows
  EXE, runtime health, foundation, clean-install, prior version upgrade and
  automatic relaunch checks

## Security and honest limits

Generated source is untrusted. Reviewing/approving a source file only writes
the exact reviewed file into Falcon's workspace; it never grants test,
network, system-control or installer permissions. Browser-rendered project
testing, compiling Minecraft Fabric projects, and autonomous app deployment
remain separate future engineering projects.

A larger model does not mean Falcon can run heavy AI without competing for
VRAM while the user plays. Gaming Mode does not guarantee FPS. Current
hardware and visual-design improvements require controlled on-device
benchmarks rather than estimates.

## Maintainer workflow

Develop via reviewed modular commits, run source tests on Windows/Linux, then
build a full frozen Windows candidate and verify a clean install, 13/13
packaged diagnostics, trusted prior-release upgrade, local data preservation,
automatic relaunch and installer SHA-256. Publish a new release only after
passing all checks. Never overwrite an old tag, bypass user consent or
commit private files/data.
