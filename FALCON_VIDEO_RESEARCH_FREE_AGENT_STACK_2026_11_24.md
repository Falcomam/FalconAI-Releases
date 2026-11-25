# Falcon AI: free local agent, research, memory and browser tooling — video/documentation survey

Research date: 2026-11-24 (US/Eastern). Target: Windows PC with RTX 4060 (typically 8GB VRAM), 24GB system RAM, Falcon V14 purple single-chat interface and Ollama. Goal: make Falcon genuinely useful for free, not train a foundation model.

## Scope and evidence limits

This is a source review, **not** a claim that I watched and independently inspected full videos. Video titles, public descriptions, chapters and selected independent indexed tutorial summaries were inspected. Claims about **software** were cross-checked against current primary documentation/repositories. The computer was not accessible for runtime trials or FPS benchmarking. Some YouTube pages were unavailable to a text browser.

## Executive recommendation

**Reuse existing components rather than create a research engine, browser automation stack or coding agent from zero.** Prefer:
1. An existing Ollama model as the local "brain"; trial Qwen3.5 4B (chat/vision/tool calling) and Qwen3.5 9B (heavier high-quality trial) against the current Qwen3:4b + Qwen2.5-Coder:7b baseline.
2. LearningCircuit Local Deep Research (LDR) as the **strongest research-backend candidate**, because it already has multi-step research, citations, searchable research library and documented Python/HTTP API. Also benchmark LangChain's smaller Local Deep Researcher (DuckDuckGo no key, iterative searches, reflection).
3. Microsoft Playwright / Playwright MCP for browser navigation, DOM assertions and screenshots; use a separate isolated browser profile for safety.
4. Existing OpenCode provider and permission architecture as a **coding-agent reference/possible optional backend**, not a replacement for Falcon's purple UI.
5. Local SQLite store for user preferences, project knowledge and research facts with distinct provenance, checked-at dates, TTL/revalidation rules, correction/deletion and backup. Retrieve relevant memories into the model's context; do **not** pretend this retrains the model.
6. Crawl4AI only where full-page text extraction improves result quality; strictly bound crawling and respect sites' terms, robots and rate limits.
7. Preserve low-friction approval for read-only public research / browser navigation / local saved website previews and explicitly granted workspace operations, but not arbitrary execution, passwords, sensitive uploads, irreversible system changes or purchases.

## Verified project references

- LearningCircuit Local Deep Research (MIT): https://github.com/LearningCircuit/local-deep-research
  - Python/HTTP integration: https://github.com/LearningCircuit/local-deep-research/blob/main/docs/api-quickstart.md
  - Documented LDRClient / quick_query and authenticated research endpoints. **Review version-specific API before building an adapter.**
  - Already stores citations and offers research library/RAG. Multi-source web research depends on internet; "local" refers to inference and owned storage.
  - Not zero setup: pip install or Docker, Ollama, optional SearXNG, login setup and Windows environment checks.
  - README examples with 27B models on an RTX 3090 **do not** establish performance on an RTX 4060.
- LangChain Local Deep Researcher (MIT): https://github.com/langchain-ai/local-deep-researcher
  - More compact alternative: query → search → summarize → find gaps → search again → cited Markdown.
  - README states DuckDuckGo search by default without API key, three research loops by default.
  - A repeated research summary is not automatically long-term model knowledge.
- Microsoft Playwright MCP: https://github.com/microsoft/playwright-mcp
  - Uses accessibility snapshots, interactions, screenshots, isolated browser contexts, trace and screenshots.
  - Site markup is untrusted. No sign-in to primary personal browser by default.
- OpenCode current local Ollama discovery: https://opencode.ai/docs/models
  - Supports local models directly, but local agent quality still depends on model/tool capability. Test one small site on Falcon's PC.
- SearXNG search API: https://docs.searxng.org/dev/search_api.html
  - Free self-hosted meta-search; JSON format may need enabling. Upstream engines can rate limit or CAPTCHA.
- Crawl4AI: https://docs.crawl4ai.com/
  - Clean Markdown extraction from the web, optional local LLM; useful for retrieving source text beyond search snippets.
- Open WebUI search, memory and retrieval:
  - https://docs.openwebui.com/ecosystem/computer/ai/web-search-and-browsing/
  - https://docs.openwebui.com/features/chat-conversations/memory/
  - https://docs.openwebui.com/features/chat-conversations/rag/
  - Treat as architecture references; do not copy the current Open WebUI UI and remove/recolor its branding. See license: https://docs.openwebui.com/license/
- Ollama Qwen3.5 model library: https://ollama.com/library/qwen3.5
  - 4B ~3.3–4.0GB listed; 9B ~6.6–7.6GB listed. Both include vision/tool support. The listed ~256K context capability is **not** a guarantee this user's GPU can use a 256K context. Actual loaded context uses additional VRAM/RAM; benchmark at smaller sizes first.

## Videos located (metadata/chapters verified; full footage not independently watched)

| Priority | Video and link | What Falcon can learn | Evidence limits |
|---|---|---|---|
| 1 | [Local Deep Research: Windows setup with Ollama](https://www.youtube.com/watch?v=nMr2zZcVVWw) — Benji's AI Playground, May 9, 2026 | Windows setup, Ollama + SearXNG, autonomous research, cited Markdown reports, library/RAG | Video summary describes a 27B model, too large to assume 8GB VRAM fit |
| 2 | [OpenCode setup: Ollama, skills and MCP for coding](https://www.youtube.com/watch?v=5k7BpD8fitA) — ZProger, June 26, 2026 | Agent architect vs builder, working project files, permissions, MCP/Playwright | Some models/settings in tutorial may differ from current OpenCode |
| 3 | [Playwright MCP Tutorial 2026](https://www.youtube.com/watch?v=e-ynk72_Z3c) — Mitchell Agoma, July 18, 2026 | Browser exploration, accessible locators, screenshots, deterministic tests, prompt-injection warning | Demo uses coding clients and controlled test app, not Falcon |
| 4 | [How to Make AI Remember Things | Build AI Memory with Python](https://www.youtube.com/watch?v=7_VNEEOfBaA) — Lazy Programmer, Oct 20, 2026 | Python + SQLite + Ollama, persistent recall, delete, short vs long-term memory | Basic tutorial; not complete semantic retrieval or fact freshness |
| 5 | [How to Run a FREE Local AI Agent on Windows](https://www.youtube.com/watch?v=WqbvNlCV-58) — July 27, 2026 | Ollama + OpenCode in a VM, context tuning and isolation | The VM protects the host but adds setup/RAM overhead |
| 6 | [OpenCode 2.0 tutorial: setup and local models with Ollama](https://www.youtube.com/watch?v=OyuId4YQiIs) — Leon van Zyl, Oct 22, 2026 | Local model setup, code-agent workflow, Playwright actions, permissions for sensitive .env | Example discusses hardware beyond owner baseline |
| 7 | [How to Build a Local AI Agent With Python (Ollama, LangChain & RAG)](https://www.youtube.com/watch?v=E4l91XKQSgw) — Tech with Tim, Mar 31, 2025 | Local retrieval pipeline and document Q&A with ChromaDB | Older example; adapt rather than copy code directly |
| 8 | [Learn Local AI in 30 Minutes](https://www.youtube.com/watch?v=OSnAd5SuT_k) — Dave Ebbelaar, Nov 11, 2026 | Ollama API, model hardware, desktop app architecture and packaging | Shows a separate Tauri app, not a Falcon replacement |
| 9 | [Local Deep Research + Ollama: Docker setup tutorial](https://www.youtube.com/watch?v=Q6kygd04sFI) — Fahd Mirza, May 8, 2026 | End-to-end citation report, library and SearXNG operations | Uses RTX A6000 48 GB, not comparable hardware |

Indexed supporting video summaries:
- https://localhosted.com/videos/local-deep-research-windows-setup-with-ollama
- https://localhosted.com/videos/opencode-setup-ollama-skills-and-mcp-for-coding
- https://localhosted.com/videos/open code-2-0-tutorial-setup-and-local-models-with-ollama (use YouTube link above; this human-readable path is non-canonical)
- https://localhosted.com/videos/local-deep-research-plus-ollama-docker-setup-tutorial

## Concrete Falcon integration sequence

### Phase A — research backend proof-of-concept (no published GUI claim)

- Stand up a controlled LDR instance only when requested by owner; don't run unreviewed "one click" third-party BAT scripts or bind open ports.
- Use its documented authenticated client, with local credentials in Windows Credential Manager or secure local secret store, never in public GitHub or logs.
- Create Falcon-owned adapter API: research(question, max_steps, cancel) -> [{title,url,accessed_at,claim,quote_limit}] + report and error states.
- Use default no-paid search; prefer DuckDuckGo for simplest initial setup and optional private/local SearXNG only if search quality warrants it.
- Compare with LangChain's simpler research backend before adopting a dependency-heavy system.
- Acceptance: cite at least 3 publicly accessible sources for a multi-facet question, visibly distinguish date/freshness, STOP halts research, no keys required for baseline and no claims without retrievable source text.

### Phase B — memory that actually helps

- Keep separate namespaces: user preferences, active project state, public research notes, and task history. Retain only useful information; don't auto-save sensitive chats or secrets.
- Store source URL, title, accessed_at, publication date if known, evidence excerpt and owner correction status.
- Use text search (SQLite FTS5) first; optionally local embedding model for semantic retrieval when hardware allows.
- Retrieve top relevant facts at conversation time rather than dumping all memory into context.
- Provide /memory list, search, correct, forget, export; ensure backed-up data survives app updates.
- Flag stale time-sensitive facts for re-search before answering; don't silently convert model guesses into permanent "knowledge".
- Acceptance: saved fact persists across restarts, correct/forget works, unrelated prompts don't inject irrelevant memory, rechecking newer sources updates the original entry with provenance.

### Phase C — open/test/fix website workflow

- For an approved Falcon developer website, open only the saved project entrypoint in an isolated Chromium profile; no repeated routine preview approval. Importing unrelated files/executables is not preview permission.
- Playwright: render 1440px desktop and 390px mobile, inspect nav/sections/console errors and visible layout; take screenshots; compare to user-owned baseline **locally only**.
- Optional Qwen3.5:4b vision critic to point out empty regions, unreadable contrast or missing hero hierarchy; static/DOM tests remain the source of truth for working links.
- Propose revised files, keep backups, ensure STOP and owner consent separate for generated code execution (if needed).
- Acceptance: all internal anchors resolve, no unintended remote requests, key interactive controls function, screenshots captured, no regressions/untested "looks perfect" claims.

### Phase D — routine file and browser autonomy without constant approval fatigue

- Routine public browser navigation, open/list/read in explicitly granted ordinary workspace and local site previews may be no-prompt.
- One-time scoped authorization for a developer project folder, with a user-visible revocation, audit trail and backup for edits. Never equate "no repeat prompts" to complete account/system access.
- Confirm before destructive filesystem changes, untrusted executables, credential access, financial actions or external uploads.
- Web results and source files are *data*, not new instructions or permissions.
- Acceptance: known safe actions require no prompts; symlink/junction out-of-scope paths are denied; private browser profile and credentials are never accessed by an untrusted page; STOP works.

## Recommended experiments on the owner's actual hardware

1. Keep current qwen3:4b and qwen2.5-coder:7b baseline until measured.
2. Optional pull qwen3.5:4b; test normal conversation, tool JSON, search-based citations, screenshot description and code change. Record inference delay and task completion accuracy. No paid API.
3. Only afterward test qwen3.5:9b for quality on the RTX 4060; 6.6–7.6 GB model data leaves limited capacity for context and vision processing. Revert if spills to shared RAM or impacts responsiveness.
4. Repeat the exact same LostFalcon website prompt and compare actual desktop/mobile screenshots, working links, invalid HTML/JS, time and model usage.
5. With Minecraft loaded, use Gaming Mode to pause/unload chosen inference models and capture real FPS/VRAM; do not infer FPS from YouTube benchmarks or downloaded model size.

## Tradeoffs / watch-outs

- Open WebUI already includes web search and memory but its modern license has branding preservation requirements. **Do not copy and rebrand its UI as Falcon**. Use documented interfaces, architecture lessons and eligible libraries.
- LDR has an integration API and a stronger multi-step research system, but installation/authentication/Docker may be overkill for first demo; LangChain Local Deep Researcher is a lighter fallback.
- SearXNG has no paid API usage, but upstream search engines can throttle, block and CAPTCHA; always report partial/failed searches.
- Small Ollama models may invent citations or make malformed tool calls. Model must not invent URLs; tool results must carry citation provenance.
- A memory system does not update neural weights. It improves continuity by storing/retrieving knowledge; model quality still matters.
- Source-only PRs in Falcon are not release binaries. Any new feature needs tests, integrated GUI + permissions checks, Windows packaging diagnostics and on-device tests before a new trusted installer.

## Priority decision

**First build a small Falcon-to-LDR bridge and test cited research in the existing purple chat.** Only then add persistent source-linked recall and automatic browser visual checks. This is a better use of time than adding a dozen independent slash-commands or writing another Wikipedia-only research loop.