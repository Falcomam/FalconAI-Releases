# Falcon Money Mode: original brainrot Shorts
Owner priority 2026-11-24: one Short per day, target 6 PM local time, on a dedicated channel. Shorts takes priority over Payhip; preserve existing work.

## Research
- https://www.youtube.com/watch?v=0BaXowxNwJs — tutorial description covers consistent characters, scripting, imagery, voice, effects and editing. Full captions not obtained.
- https://youtubetotranscript.com/transcript?current_language_code=en&v=0-0gFuDwmXI — indexed transcript material describes consistent multi-scene characters, narration and ambient sound; no claim of watching the entire video.
- https://github.com/Srinivasan-78/study-brainrot-generator — documentation describes time-coded speech and caption escaping; architectural reference only, no copied implementation.
- https://support.google.com/youtube/answer/1311392 and https://support.google.com/youtube/answer/2801973 — original, varied creative work; automated repetitive mass production can violate policy or prevent monetization. Daily cadence is not a guarantee of compliance.
- https://developers.google.com/youtube/data/reference/rest/v3/videos/insert — official upload endpoint.
- https://developers.google.com/youtube/terms/api-services-terms-of-service and https://developers.google.com/youtube/terms/required-minimum-functionality — upload certification, user control over metadata and visibility, authorized access. Recheck current requirements before shipping.

## Product
An original surreal comedy series: fictional object-animal hybrids, rapid escalation, coherent scenes and unexpected payoff. No reused clips, impersonation, copyrighted character copying or scraped scripts. Use locally generated assets with documented commercial-use terms and original audio. No revenue guarantees.

## Implementation order and acceptance tests
1. Improve packaging/shorts_mode.py, currently a standalone draft prototype. Validate schema; reject duplicate ideas and invalid media; keep a daily state machine with explicit failed/uncertain states.
2. Scene-specific visuals, narration, synchronized captions, original sound effects. Preview real rendered output and verify dimensions, duration, audio, and caption timing. No fake claims of AI video when using procedural graphics.
3. Test daily scheduler, time zone/DST, concurrent invocation, pause, cancellation, interrupted render, no catch-up bursts, duplicate uploads and gaming resource use. User can disable it.
4. Official YouTube OAuth and explicit channel confirmation; tokens remain local, never committed. Support user review of actual media and metadata, audience/AI disclosures, upload certification, and visibility choice. Use authorized public scheduling only when platform rules permit; otherwise reviewed upload. Handle uncertain network outcomes without blind retries.
5. Integrate the existing one-window UI and STOP; no arbitrary generated code execution. Free-first on RTX 4060/24 GB; benchmark actual hardware rather than promise FPS.
6. Mock API tests and real authorized test upload before declaring posting operational. Follow AGENTS.md Windows frozen app, clean install, upgrade/relaunch, data preservation and SHA-256 release gates. Never publish a source-only commit as a verified Windows installer.

Current status: prompt changed from horror to original absurd comedy. Gradient backgrounds and local speech only; full scene rendering, scheduling and uploader are not implemented or tested. No video uploaded and no Windows release yet.
