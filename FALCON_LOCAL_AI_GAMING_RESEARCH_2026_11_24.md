# Falcon AI — Local coding research and gaming performance plan
Date: 2026-11-24
Status: Evidence-backed notes, not measured user-PC performance, not a shipped release.

## User's concrete target
- RTX 4060 (typically 8 GB dedicated VRAM), 24 GB system RAM.
- Play Minecraft and other games without local AI consuming substantial GPU resources.
- Build significantly better websites than Falcon V13.9.1's first LostFalcon website: Benchmark #001 (2 files, plain purple background, basic About link).
- Improve developer tools using actual source-backed lessons and reproducible quality checks, not model-parameter hype.

## Source review: transcript-derived video lesson
Video: Web Dev Simplified, "The Best Local Agentic Coding Workflow (Complete Guide)"
https://www.youtube.com/watch?v=UngVdAsQEiU
Transcript-derived lesson and timestamped excerpts:
https://learningatlas.us/learning/video/UngVdAsQEiU

This is a **third-party transcript-derived summary with timestamped caption excerpts**. We have not independently retrieved/reviewed the complete 45-minute verbatim transcript. Do not claim to have done so.

- **0:12-2:09**: Larger parameter counts and context affect model size; hardware requirements are fundamental. Application: use VRAM budget and actual measured memory, not parameter count alone.
- **14:19**: Context growth can spill into system RAM and drastically reduce throughput; lesson discusses an example of a faster all-GPU setup versus context overflow. Application: track model placement and context in every coding benchmark; do not directly transfer the presenter’s reported throughput to the user's 4060.
- **33:31**: Coding tool integration matters; lesson describes Continue and an editor coding agent. Application: Falcon should prove source edits, review, and test gates rather than count text generation alone.
- **42:54**: A real bug report provides a concrete agentic benchmark. Application: retain exactly the same LostFalcon request, then inspect HTML, browser screenshot, manual interaction and generation metrics.

Tech With Tim local coding guide:
https://www.youtube.com/watch?v=hfba9dAT6xE
Complete verbatim transcript was **not** retrieved in this sprint; any additional interpretations need transcript/source verification.

## Primary operating reference
Ollama FAQ: https://github.com/ollama/ollama/blob/main/docs/faq.mdx
Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md

- `ollama ps` reports currently loaded local Ollama models and processor placement.
- `ollama stop MODEL` unloads a model; `keep_alive:0` via `/api/generate` can request immediate unload. This does NOT uninstall it.
- Extra context / parallel requests consume more memory, potentially affecting GPU gaming.
- Do not claim complete VRAM freedom, model quality gains or FPS improvements without on-device measurement.

## Falcon engineering decisions
**Gaming Mode ON** (staged, not shipped): persist explicit pause; block new Falcon chat/agent requests; ask Ollama to unload *only* loaded selected Falcon chat/coder/vision models; verify the change via `/api/ps`; display uncertainty when unloading cannot be confirmed. It never changes Windows game settings, clocks or driver settings, and may affect another Ollama app sharing a selected model. **Gaming Mode OFF** allows loading on demand.

**Dev Mode quality checks** (staged, not shipped): polished website instructions; deterministic static warnings, with benchmark regression based on first LostFalcon website. Static warnings don't prove visual quality. Actual screenshot render/testing must be separately designed, isolated, resource-bounded, approved, and verified before running AI-generated code.

**Concurrent gaming plus heavy inference:** no guarantee on shared 8GB VRAM. Running remote GitHub Actions coding/tests does not use the user's GPU; local Ollama inference does. Prefer pause/unload on game launch, and resume heavier coding sessions after gaming rather than forcing two large workloads simultaneously.

## On-device benchmark protocol (pending user machine)
1. With other GPU tasks closed, record `nvidia-smi` and `ollama ps`, plus Task Manager dedicated GPU RAM usage.
2. On qwen3:4b and qwen2.5-coder:7b with same exact LostFalcon site request, record wall time, output failures/retries, file count, static warnings, and an actual browser screenshot. Avoid asserting 7B automatically wins; log output quality.
3. Repeat gaming baseline with Ollama models unloaded, then with an idle model loaded, and only deliberately test simultaneous inference if the user opts in. Capture stable game FPS/frame time and VRAM usage. Do not treat one short sample as a guarantee.
4. If 7B needs CPU offload with the selected context, reduce context or background load before considering a larger 14B model. On an 8GB GPU, 14B is a separate slower experiment, not recommended while gaming.
5. All data measured on the user's PC is pending; never invent GPU timings or FPS.

## Sprint artifacts and release gate
- `packaging/gaming_mode.py`, `packaging/tests/test_gaming_mode.py`
- `packaging/site_design_check.py`, `packaging/tests/test_site_design_check.py`
- `packaging/developer_chat.py`, `packaging/developer_workspace.py`
- `packaging/prepare_single_chat_candidate.py`: staged integration, agent guard, GUI menu
- Windows/Linux source CI, internal Windows frozen-EXE/clean-install/upgrade checks.
- **No release or installer published from this sprint.** Do not claim user V13.9.1 has these features.
