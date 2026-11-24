"""Prepare Falcon Ai 13.7.0 from the last verified 13.6.5 source.

Does not remove the working source release, existing user data or legacy installs.
The packaged EXE keeps all Python dependencies behind one visible launcher.
"""
from pathlib import Path
import shutil

repo = Path(__file__).resolve().parents[1]
previous = repo / 'build' / 'Falcon_AI_V13_6_5'
target = repo / 'build' / 'Falcon_Ai_App_V13_7_0'
if (previous / 'RELEASE_VERSION.txt').read_text(encoding='utf-8').strip() != '13.6.5':
    raise SystemExit('Verified Falcon 13.6.5 base required')
if target.exists():
    shutil.rmtree(target)
shutil.copytree(previous, target, ignore=shutil.ignore_patterns('__pycache__','*.pyc','.venv'))
def one(rel, before, after):
    path = target / rel
    data = path.read_text(encoding='utf-8')
    if data.count(before) != 1:
        raise SystemExit(f'Expected exactly one anchor: {rel}, {before!r}, got {data.count(before)}')
    path.write_text(data.replace(before, after, 1), encoding='utf-8')
one('falcon.py', 'Falcon AI V13.6.5 — Command Center', 'Falcon Ai V13.7.0 — Command Center')
one('falcon.py', 'Falcon V13.6.5 ready.', 'Falcon Ai V13.7.0 ready.')
one('falcon.py', 'V13.6.5  /  LOCAL JARVIS', 'V13.7.0  /  LOCAL JARVIS')
one('release_updates.py', 'CURRENT_VERSION = (13, 6, 5)', 'CURRENT_VERSION = (13, 7, 0)')
one('falcon_launcher.py', 'Starting Falcon V13.5', 'Starting Falcon Ai V13.7.0')
one('falcon_launcher.py', 'v13_5_startup.log', 'falcon_ai_app_startup.log')
one('falcon_launcher.py', 'v13_5_startup_previous.log', 'falcon_ai_app_startup_previous.log')
one('falcon_launcher.py', 'Local\\\\FalconAI_V13_5_OneInstance', 'Local\\\\FalconAi_OneInstance')
(target / 'RELEASE_VERSION.txt').write_text('13.7.0\n', encoding='utf-8')
(target / 'README_FALCON_AI_APP.txt').write_text(
    'Falcon Ai V13.7.0 - Windows Application\\n\\n'
    'Launch from your single Falcon Ai desktop shortcut or Start menu.\\n'
    'The full app and Python modules are bundled internally; no Python download is required.\\n'
    'Local AI still uses Ollama on your PC; models are not included.\\n'
    'Your history, preferences, saved notes and logs remain in LOCALAPPDATA/FalconAI.\\n'
    'The older script-based Falcon installation is retained until you choose to remove it.\\n'
    'Updates download SHA256-verified Falcon_Ai_Setup.exe from your trusted GitHub release channel.\\n'
    'The new updater starts the installer after the GUI closes and logs each step.\\n'
    'The app uses normal per-user Windows installation and provides a standard uninstaller.\\n'
    'Developer Mode features remain on the roadmap; do not treat proposals as installed code.\\n',
    encoding='utf-8')
print('Prepared Falcon Ai Windows app V13.7.0 source')
