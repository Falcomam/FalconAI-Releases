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


## Follow-up sprint: scene timing
- Source commits: edd8c5a (timing and duplicate detection), f061fbc (six separate narrated scenes and burned-in captions), 94859b5 (unit tests), d9aed1a (Windows/Linux source CI).
- A local Linux FFmpeg smoke test rendered a single 720x1280 gradient scene with a synthetic sine-wave audio track, then concatenated and burned SRT subtitles. ffprobe reported video plus audio, 720x1280, 2.24 seconds. This is not a full six-scene run, Windows speech test, CI result, or actual AI-character video.
- Remaining: run source CI, test six-scene media, add consistent original character visuals using locally licensed models, add quality gate and daily scheduler, then official authorized channel upload.
- Current research: https://www.youtube.com/watch?v=0mT4p86ZxGQ describes a shot-by-shot local ComfyUI workflow using LTX and Flux; description only, no complete transcript obtained. Benchmark VRAM before choosing a model.
- Official current upload documentation: https://developers.google.com/youtube/data/guides/uploading_a_video and https://developers.google.com/youtube/data/reference/rest/v3/videos/insert describe authorized upload. Reconcile current API policy and required minimum functionality before release. https://support.google.com/youtube/answer/1311392 and https://support.google.com/youtube/answer/2801973 reinforce originality and anti-spam; don't assume AI-generated daily posts qualify for monetization.
- No live uploads or new installer in this sprint.


## Follow-up: recurring cartoon visuals and draft watch
- Added shorts_visuals.py (82f8967), story-selected scene rendering and camera motion (5c9e4aa, f012bfe). The model now chooses from validated settings and poses. One deterministic procedural cartoon creature retains its colors and body style across the six scenes. This is simple authored art, not diffusion-generated animation.
- Added opt-in foreground draft watch (c6e19e1, 1ad3c5d), default preparation at 4 PM local time to leave review time before the proposed 6 PM publication. One date reservation, no missed-day catchup. Requires process running; no Windows background installation or YouTube posting yet.
- Added test_shorts_draft.py (4c583d7) and updated CI (38bae12). Tests configured, CI result not confirmed. Pillow dependency now required; frozen installer integration still pending.
- Local Linux FFmpeg smoke test using a synthetic PNG and sine-wave audio passed the new camera filter: ffprobe confirmed 720x1280 video, audio stream, 1.7 seconds. Does not verify full renderer, Ollama, Windows speech, actual visual quality or uploaded output.
- Next: improve scene-specific artwork, use a licensed local image-generation backend, verify full media output, connect authorized YouTube upload and integrate the daily scheduler with Falcon's existing STOP and main UI. No release published.


## Follow-up: YouTube upload adapter
- Added packaging/shorts_upload.py (6795ac4, fa64925) and mocked tests (649e61d), CI compile step (11a21f5). Standalone CLI, not installed in Falcon yet.
- Validates final MP4 via ffprobe, requests owner-provided desktop OAuth credentials and browser authorization, checks channel identity, asks user to review the actual video and select title, description, category, visibility, audience, altered-media disclosure and optional future publication time. Requires certification and explicit upload. Uses a resumable upload and durable attempt ledger; ambiguous errors require checking YouTube Studio rather than creating a second upload.
- No saved tokens, public upload automation, account setup, live upload or verified Windows installer yet. Mock tests added but no verified CI result in this session. Release still needs actual media/Windows tests, upload API verification, published client privacy policy, policy review and UI integration.
- Google documentation checked: https://developers.google.com/youtube/data/guides/uploading_a_video ; https://developers.google.com/youtube/terms/required-minimum-functionality ; https://developers.google.com/youtube/terms/api-services-terms-of-service ; https://developers.google.com/youtube/data/reference/rest/v3/videos/insert . As of this check the current insert docs state unverified projects are no longer automatically private-only; actual OAuth/account restrictions still need testing.
- Source-only usage for maintainer testing: Python 3.11+, Pillow, FFmpeg/ffprobe, Ollama, Windows speech, google-api-python-client, google-auth-oauthlib. Generate with python packaging/shorts_mode.py; upload separately with python packaging/shorts_upload.py --client-secrets PATH --date YYYY-MM-DD. Never commit the OAuth JSON or paste tokens into chat. Owner must review actual media, voice rights and channel selection.


## Follow-up: full media pipeline validation
- 3d98134 extracts render_video for offline testing, checks required executables before reserving a daily draft, probes the finished MP4 and compares duration with the caption timeline before marking ready.
- 19fbf83 adds a six-scene integration test with synthetic WAV audio and the actual procedural renderer. f81fe9a requires FFmpeg/ffprobe on Windows and Linux CI. CI results not yet retrieved.
- A separate local Linux command-level smoke test used the same six FFmpeg scene commands and final concatenation/subtitles command with simple generated PNGs and synthetic WAVs. ffprobe verified 14.433008 seconds, 720x1280 video, one audio stream and 300184 bytes. This was not a checkout of the repository, which was unavailable to the local test container due to DNS/network restrictions. No Ollama, Windows speech, real YouTube or frozen EXE was tested.
- Rechecked current official YouTube API documentation (https://developers.google.com/youtube/data/guides/quota_and_compliance_audits and https://developers.google.com/youtube/terms/required-minimum-functionality): unverified projects are no longer automatically limited to private uploads, but authorization, user metadata controls, certification and other developer policy requirements remain.
- Next: confirm exact-head CI, fix any failures, add real Windows speech test, improve local art quality, stage the actual main-chat integration and package only after the release gates pass.


## Owner UX update: startup report
Show a read-only daily Shorts report automatically when the main chat initializes, and via /shorts status. Keep one application rather than introducing another window. Report local draft state, saved upload receipt (not live public visibility), STOP, gaming pause, missing media tools, proposed schedule, and next action. No AI work or upload is triggered by the report. Implemented in shorts_report.py and developer_chat.py; report regression tests and CI syntax coverage added. Still needs staged/frozen packaging and native startup verification; not installed yet. No claims of real-time YouTube analytics until authorized API data is available.


## Follow-up: packaging Money Mode
- 135da26 adds an explicit seven-module staging manifest and checks the staged chat integration before copying. 406fd4a calls it from the V14 foundation candidate reconstruction. 4ec0bbd adds five regression cases for successful/repeated staging, missing module, conflicting target, absent integration, and invalid source syntax.
- Local isolated Python smoke test of the staging function using synthetic source/candidate directories passed all five cases. This was a manually reproduced function test, not an actual repository checkout, frozen Windows build or installer check.
- Existing Money Mode menu offers report, generate, preview, daily draft opt-in and pause. Native startup/menu, full packaging path and actual owner PC generation remain unverified. Do not claim a release or automated public publishing. The user wants an automatic startup report and no routine command typing.


## Release readiness sprint: in-app reviewed publishing
- Committed shorts_publish_ui.py (33d057d, a9bc86a), wired review/upload into the Money Mode menu (3b0c7f0), included the eighth runtime module in staging (d1b423f), and added focused tests (c7d2288). Review and session-pause gates prevent the local scheduler launching while upload review is open. OAuth credentials are supplied locally, Google endpoints restricted, and tokens are not saved by the application.
- The local source copies of the nine core/staging modules matched their Git blob hashes. The existing 10-check local harness passed again, including actual six-scene render: 14.433008 seconds, 664565 bytes. Four new unit tests passed for review certification/metadata, OAuth endpoints, scheduler overlap, and pause on failed preference write. Real Tk menu construction and report/generate callback tests passed on Linux Xvfb. No real Google connection or upload occurred.
- 8f86e04 stages Google client dependencies and adds Shorts imports and inert metadata validation to the existing frozen foundation self-test. Native installer CI is NOT confirmed; the available workflow-run lookup filters PR runs and returned no runs for the checked commit. Local normal git checkout fails DNS resolution. Local Google API dependencies are absent. No published release or automatic public posting.
- Next release blockers: confirm exact-head Windows CI, fix packaging/discovery issues, provision trusted FFmpeg/ffprobe, test Windows narration, verify quality and licensing of art/voice, test authorized private/scheduled upload with owner account, then frozen EXE clean install, upgrade/relaunch and data preservation before publishing. Review upload requirements at https://developers.google.com/youtube/terms/required-minimum-functionality . Keep startup report and menu, one draft/day, no mass uploads.


## Immediate workaround sprint: isolate platform and account blockers
- Native Windows internal verification run https://github.com/Falcomam/FalconAI-Releases/actions/runs/45548674631 (job 138984330434) reported success for source reconstruction/tests and frozen EXE build, including the existing job's packaged self-checks. Clean-install step still in progress; upgrade/relaunch and installer SHA gate pending. Do not infer the exact run covers later commits without confirming checkout SHA and the final result. No public release created.
- 89bc9a7 adds test_shorts_windows_speech.py, exercising the real create() speech and rendering path on Windows with a fixed local story, six WAVs, final MP4 probe, one-draft reservation, cancellation, and no upload. The existing Shorts source workflow watches this path; the native test result is not yet confirmed. It isolates the speech and FFmpeg dependency from Ollama and YouTube.
- Legitimate account fallback: after a verified build produces a reviewed draft, the owner can manually upload draft.mp4 from its dated local Shorts folder using https://studio.youtube.com/ and choose the correct channel, audience, AI disclosure and publication time. This needs no custom Google OAuth client; it is not automatic posting. Do not run the Falcon API uploader for the same file after a manual upload; check Studio first. Automatic upload and public visibility still require separate account verification.
- Preserve the in-progress installer job; diagnose its actual result before changing its build workflow. On successful native gates, retain the exact tested candidate, digest and source SHA through the established trusted release process; do not reconstruct from a newer unverified checkout. A source-only pass or a Windows test of fixture speech does not establish a live AI/channel workflow.


## Windows candidate passed; artifact retention fix
- Run 45548674631 / job 138984330434 concluded success. Actual checkout log identifies 8f86e04fb44f797514dc88b52748b4aa8638ae0b (includes in-app upload controls and Google client dependencies). Logs confirm frozen app diagnostics, clean install, 13.9.1 upgrade, automatic relaunch, preserved data, and final installer SHA-256 8afe84232d8569813f64364094e73bde77633305d79b3eee51509f3edf67c693. This is not a live YouTube upload or real Windows narration test, nor verification of subsequent source commits.
- The successful job had no retained artifacts when queried. Do not claim that exact installer is downloadable or publish a rebuilt file using its old digest.
- 68c3a59 adds retention of the actual installer, SHA-256 and checkout commit after all Windows release gates, and adds Shorts source/staging/tests to the Windows candidate workflow trigger paths. Internal artifact only, no public publication. Verify the new run and artifact identity before release; confirm native speech test independently. No new public installer yet.
