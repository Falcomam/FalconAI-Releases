# Falcon AI — release process

This public repository will host vetted Falcon update releases for the existing Windows installation. No personal files, AI memories, API keys, logs, or credentials should be uploaded here.

## Release requirements

- Publish a tested full application package as `Falcon_AI_Update.zip` using a newer version tag.
- Keep `RELEASE_VERSION.txt` inside the ZIP consistent with that tag.
- Validate archive structure, versions, and SHA-256 asset digest before Falcon stages it.
- Require explicit user approval before installing executable code.
- Back up the installed version and restore it if update startup fails.
- Keep gaming uninterrupted: no automatic focus switches, console pop-ups, or restarts while a game is running; notify about available and completed updates, not every routine poll.
- Once implemented, Falcon may quietly check GitHub every five minutes. The currently installed V13.5 does not yet have that timer.

**Status:** Repository connection test succeeded only after this file can be committed. No downloadable update is published by this document.
