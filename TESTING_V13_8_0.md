# Falcon Ai V13.8.0 — User acceptance test

This is for **after an official release is published**, not development candidates.

## Safe update
1. Open the installed Falcon Ai V13.7.1.
2. Use its **Updates > Check for updates** menu and review the release notes.
3. Approve the normal SHA256-verified installer update. It should close Falcon, install, and reopen.
4. Verify the purple icon and **V13.8.0** title. Existing local history/settings must remain.
5. If the app fails to reopen, do not reinstall repeatedly. Copy the support report and update log from LOCALAPPDATA/FalconAI/logs/app_installer_update.log.

## Local engine
1. Ask **Hey Falcon, say hello in one sentence.** An actual model reply should appear.
2. Use /engine status and /engine list in the **same chat window**. Check that model names match the Ollama installation.
3. To test the offline case, close Ollama normally and use /engine status. The status should say AI Offline, not Ready.
4. Type /engine start to launch the existing local Ollama server. No downloading models or added PC permissions.
5. Use /engine use qwen3:4b (or another exact, already installed model), and verify a reply still works. Invalid names must be rejected.

## Developer Mode — code is not executed
1. In Falcon's **existing chat**, type: /project website Make a dark-purple LostFalcon homepage with a hero and a subscribe link.
2. A proposal should list generated files but **not save, execute or install anything** yet.
3. Type /project approve **before** reviewing. It must refuse until a project review is opened.
4. Type /project review; inspect file names and code previews. Use /project show index.html if present.
5. Type /project approve; it should save new text files to LOCALAPPDATA/FalconAI/developer_projects/<project_name> without executing code.
6. Repeat with the same project name. It must never silently overwrite the previous project.
7. Generate a throwaway Python project or Minecraft Fabric mod starter to test other project types. Fabric generation is a **starter**, not a compiled or game-tested mod.
8. During a draft, press STOP; no partial user project may be saved.

## Report issues
Use Falcon's **Copy Report** in Tools, review it for secrets before sharing, and say which exact step failed. Windows may show a reputation warning because the app's installer is not code-signed; use only the official GitHub release page and verified checksums.

**Release rule:** Do not label this package ready for user testing unless source tests, packaged EXE checks, clean Windows installer and full prior-release upgrade/relaunch tests have passed.
