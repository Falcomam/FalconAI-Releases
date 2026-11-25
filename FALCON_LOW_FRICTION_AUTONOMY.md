# Falcon AI — low-friction file and browser autonomy

Owner request (2026-11-24): Falcon should **not ask before every routine file or browser action**. Prefer a predictable permission model over repeated confirmations or blanket unbounded rights.

## Product behavior requested

- **Default no-prompt actions:** open or navigate public web pages; search; inspect a page; open and preview already saved Falcon website projects; list and read ordinary files within owner-selected workspaces.
- **Workspace permission (one-time, revocable):** the user can grant Falcon an entire specific project/folder. Within that scope Falcon can create, revise, rename and organize *ordinary project files* without repeated approval, with local change history/backup and an obvious STOP.
- **Browser work:** normal public-page navigation and local website previews are approval-free. Page content is untrusted. An instruction on a web page cannot confer additional PC, filesystem or account rights.
- **Require confirmation:** destructive/unrecoverable changes, deleting user data, modifying system files/security settings, installing/running untrusted programs, using credentials, submitting forms with financial/legal consequences, making purchases, publishing private content or sending sensitive files externally.
- **Sensitive boundaries:** no access to credential vaults, private browser profiles, cookies or auth tokens merely because the user enabled convenience mode. Folder permission is not permission to export its contents.
- **Permissions and controls:** display granted folders and services; allow owner to revoke them; keep audit trail; STOP cancels ongoing work; browser/AI resource use respects Gaming Mode. Avoid repeated prompts for small actions already within the granted scope.
- **No paid dependency:** local Ollama model and Windows browser/automation tooling; user may optionally configure a paid provider but there is no required cloud API.

## Scope of current PR

**Implemented source-only:** `/project preview <saved_name>` opens the existing saved website's `index.html` in default browser without another approval dialog. The helper accepts no arbitrary paths or URLs, verifies saved site kind and project membership, and rejects symlink redirection. This opens HTML, which may run scripts under the browser's security policy, but it does **not** execute native code, edit files or give general computer access.

**Not yet implemented:** full desktop/browser agent, unrestricted multi-folder editing, fine-grained one-time folder grant UI, live browser screenshots, autonomous review/fix loops. These need separate permission-aware implementations and Windows testing, not a blanket global bypass of existing approval functions.

## Acceptance requirements for the next stages

1. Permit repeated read/list actions in a user-allowed folder without reapproval; reject symlinks, junctions and out-of-scope paths.
2. Permit normal public web navigation by an explicit user intent and bounded domain policy; reject `file:`, `javascript:`, `data:`, embedded credentials and private-network targets supplied by untrusted pages.
3. Permit standard edits inside granted project folders with reversible backups, no cross-scope writes, and a reliable STOP.
4. Retain a separate approval boundary for external uploads or actions with financial/security consequences.
5. Prove in Windows UI tests that the no-prompt preview opens and that other restrictions are still enforced.
