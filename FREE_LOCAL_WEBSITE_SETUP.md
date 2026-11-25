# Falcon AI — no-paid-API website coding setup (November 2026)

This is an **opt-in local-only** setup, not a shipped auto-website feature.

## Hardware target

Owner's main PC: RTX 4060 (typically 8 GB VRAM), 24 GB RAM.
Baseline coder: Ollama `qwen2.5-coder:7b` (~4.7 GB downloaded weights; working memory/context uses additional resources).
Use separate `qwen3:4b` chat if already installed. Do not select a 14B+ model while gaming based on its parameter count alone.

Official model listing: https://ollama.com/library/qwen2.5-coder
Official Ollama downloads: https://ollama.com/download

## Install (user-initiated, no API bill)

1. Install/launch Ollama on Windows from the official website if missing.
2. In PowerShell run `ollama pull qwen2.5-coder:7b`, or review and run `tools/setup-free-coder.ps1`; the helper asks before downloading.
3. In the installed Falcon 14 chat: `/engine list` and `/engine use-code qwen2.5-coder:7b`.
4. Create a website with `/project website <description>`. Read every proposed file with `/project review`, then explicitly approve saving if acceptable.
5. Open the saved `index.html` manually in a browser and inspect the desktop/mobile result. Falcon V14 does **not** autonomously render and critique screenshots.
6. Use `/engine gaming on` to pause local inference and request model unloading before gaming; `/engine gaming off` afterwards.

## Quality benchmark

Use Benchmark #001: the original two-file LostFalcon purple website as the **baseline**. Ask the new model for the same site. Measure:
- successful valid source proposal and number of retries;
- clear responsive layout, functional internal links and thoughtful creator-specific copy;
- visually inspect actual desktop/mobile browser screenshots (manual);
- local generation elapsed time and gaming FPS/VRAM **only on owner's PC**.

No guarantee a particular local model will match ChatGPT or other paid hosted models.
No generated source execution, package installation, deployment or website browser automation is granted by choosing a local model. Full auto-website creation needs a separately reviewed browser/test worker, explicit execution approval, STOP and containment.

## Privacy and cost

Ollama inference runs locally. The model download requires internet and disk space, and electricity/network charges may still apply. No paid inference API is configured.
Never paste secrets/API keys into prompts, scripts or public GitHub commits.
