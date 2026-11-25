# Falcon AI V14 — acceptance and regression checklist

**Release target:** 14.0.0. **Previous tested installed release:** 13.9.1.
Do not describe a candidate as published until GitHub Releases contains its
installer plus the SHA-256 digest and the native Windows release gate passes.

## Automated release gate (GitHub Actions)

- Reconstruct previously tested source stages and finalize V13.9.1 baseline.
- Stage V14 in isolated `build/` directories, compare release file, frozen
  application, launcher, updater and Inno Setup versions.
- Run source unit regressions for permissions/STOP, source/HTML safety, typed
  commands, saved-project edit/backups, gaming mode and V14 contracts.
- Freeze Windows GUI with PyInstaller, run old app self-test, **13/13 packaged
  diagnostics** and V14 foundation self-test.
- Compile Inno Setup installer, perform a clean install, repeat self-tests.
- Download real V13.9.1 installer from the trusted GitHub release, verify its
  GitHub API asset SHA256 digest, install it, retain a sentinel private file,
  upgrade using the existing updater helper and confirm automatic relaunch.
- Refuse release on changed AppId, source/runtime mismatch, missing modules,
  missing digest, missing self-tests or failed data preservation.
- **Only after all of the above**, release `v14.0.0` with a new installer
  (never replace an old version asset) and verify its published SHA256 digest.

## Owner-facing check: one purple chat

1. Confirm displayed version and startup log both say 14.0.0; support report
   must not claim that all 13 source .py files are missing.
2. Type `/foundation`: check descriptions of AVAILABLE/LIMITED/PLANNED.
   It must say rendered-site evaluation and automatic mod builds are planned.
3. Type `/engine list`, `/engine coding`: installed local models and
   independent coding preference should be distinguishable from chat.
4. Type `/engine gaming on`, then `ollama ps` in PowerShell. Verify selected
   Falcon models are unloaded or uncertainty is reported, not fake success.
   While ON, new Falcon chat/project generation is paused; `/foundation`
   is still readable. Type `/engine gaming off` to resume.
5. Create website source with `/project website <goal>`; verify reviewed
   proposal and static design warnings. Source-only review isn't browser
   testing. Approve only after checking contents; ensure changes remain
   under Falcon-owned workspace.
6. Reopen/edit saved source and confirm a diff and backup or safe reject.
   No code should execute or install just because a draft was approved.
7. Verify STOP and normal keyboard commands survive; no ghost input, console
   windows, or second chat.

## Benchmark #001: LostFalcon website (November 24, 2026)

Baseline model: qwen3:4b. Previous result: two files, purple background, a
single About link, simple paragraph, little layout or responsive design.

Keep identical request and compare:
- whether draft is complete enough to review, syntactically valid and safe
- number and kinds of static warnings
- **actual rendered screenshot** vs baseline, including mobile window
- working navigation and honest links, mobile overflow and accessibility
- generation duration/retries; model, context and memory footprint

Better prompts/static warnings do **not** demonstrate better visual outputs.
A rendered browser test requires a future permissioned isolated test worker,
or a manual browser check by the owner.

## Gaming benchmark

PC context: RTX 4060 (~8 GB VRAM) / 24 GB RAM. Test when safe:
- unloaded Ollama baseline: `ollama ps`, `nvidia-smi`, game FPS/frame time
- idle selected model loaded: compare VRAM, responsiveness, FPS/frame times
- intentional inference while game runs only if the owner wants to test it
- return to Gaming Mode ON and verify VRAM released after Ollama unload
- never promise zero FPS impact, background GPU availability, or faster 14B.

**No local owner-PC GPU measurements have been completed as part of CI.**
