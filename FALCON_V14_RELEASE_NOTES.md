# Falcon AI V14.0.0 — Foundation release notes

**Planned release:** v14.0.0. Publish only after native Windows CI proves
frozen EXE self-test, 13/13 packaged diagnostics, foundation self-test,
clean installation, SHA256-verified v13.9.1 upgrade, local data retention and
automatic restart. This file is not itself proof of publication.

## Included in candidate

- Truthful, read-only `/foundation` or `/foundation status` capability report
  inside the existing dark-purple Falcon main chat.
- Explicit `/engine gaming on|off|status` plus Tools > AI Engine toggles.
  ON pauses new Falcon AI chat/developer model requests and *asks Ollama* to
  unload only the selected models currently loaded (best effort); OFF
  resumes local inference on demand. No game settings, GPU clocks or
  unrelated processes are modified. A shared Ollama model may also be used
  by other Ollama clients and need reloading.
- Separate installed coding-model selection, reviewed source-code proposals,
  focused edits, static checks, back-up and rollback workflows inherited
  from the tested development source.
- Better website generation prompt with responsive-page guidance and static
  design-depth warnings. The first LostFalcon website is Benchmark #001.
  These warnings do **not** render a site or prove visual quality.
- Safer, source-first developer architecture; explicit roadmap separating
  source-only operations, review, testing and executable install consent.
- V14 version identity in GUI and launcher logs, application updater,
  frozen entry self-test and Inno Setup installer; consistent Windows AppId
  to support in-place updates.
- Existing STOP, single chat, purple UI/icon, mini monitor, packaged
  13/13 diagnostics, SHA256 update checks and local data retention preserved.

## Known limitations

- Does not run GPT-6 locally; configured Ollama models remain separate.
- No fully autonomous website browser screenshot critic, generated code
  execution, Fabric mod compilation or automatic app deployment.
- No empirical RTX 4060 gaming FPS improvements verified; performance
  depends on game, available VRAM and Ollama load.
- Qwen3:4b and Qwen2.5-Coder 7B website benchmark comparison not yet
  measured on the owner's PC.
- Frozen legacy Auto Improve source self-modification remains disabled
  by design, rather than pretending to upgrade the installed EXE.
- Unsigned Windows installer may prompt Windows SmartScreen; verify
  official GitHub release and SHA256 digest before approving installation.

## User testing sequence

Use Falcon's **Check Updates** function to check the trusted public release
feed and approve the update when it is genuinely published. Then test
`/foundation`, `/engine list`, `/engine gaming on`, `ollama ps`, and
`/engine gaming off`. Test one small source project with `/project website`
and review the actual file/browser output. Keep Benchmark #001 unchanged
for future comparisons.
