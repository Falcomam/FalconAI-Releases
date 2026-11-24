"""Build a repeatable, tested Falcon V13.6 candidate from the committed V13.5 source."""
from pathlib import Path, PurePosixPath
import base64, hashlib, io, re, shutil, zipfile

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / 'source-base' / 'Falcon_AI_V13_5_Permanent_Installer.bat'
PATCH = REPO / 'patches' / 'v13.6'
OUT = REPO / 'build' / 'Falcon_AI_V13_6'
SOURCE_SHA = '6d3c24b7eece6e69954851f26bc83e2d7a0dd5a5d16e62041c9025150697022f'

text = BASE.read_text(encoding='ascii')
match = re.search(r'(?ms)^::FALCON_ARCHIVE_BEGIN\r?\n(.*?)\r?\n::FALCON_ARCHIVE_END', text)
if not match:
    raise SystemExit('V13.5 source archive not found in base installer')
raw = base64.b64decode(''.join(match.group(1).split()), validate=True)
if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
    raise SystemExit('V13.5 source archive checksum differs from tested original')
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    for info in archive.infolist():
        if info.is_dir():
            continue
        name = PurePosixPath(info.filename)
        parts = name.parts
        if len(parts) < 2 or parts[0] != 'Falcon_AI_V13_5' or any(p in ('..', '.', '') for p in parts):
            raise SystemExit('Unsafe source archive path')
        rel = PurePosixPath(*parts[1:])
        if any(p in ('.venv', '__pycache__', '.git') for p in rel.parts):
            continue
        target = OUT.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(info))

def replace(path, old, new):
    file = OUT / path
    content = file.read_text(encoding='utf-8')
    if content.count(old) != 1:
        raise SystemExit(f'Expected one exact match in {path}: {old[:70]!r}, found {content.count(old)}')
    file.write_text(content.replace(old, new, 1), encoding='utf-8')

(OUT / 'personality.py').write_bytes((PATCH / 'personality.py').read_bytes())
(OUT / 'tests' / 'test_v136_personality.py').write_bytes((PATCH / 'test_personality.py').read_bytes())
(OUT / 'RELEASE_VERSION.txt').write_text('13.6.0\n', encoding='utf-8')
replace('falcon.py',
    'from notifications import NotificationCenter',
    'from notifications import NotificationCenter\nimport personality')
replace('falcon.py',
    "messages = [{'role':'system','content':SYSTEM}] + clean_history(self.history, maximum=16)",
    "messages = [{'role':'system','content':personality.build_system_prompt(SYSTEM)}] + clean_history(self.history, maximum=16)")
for old,new in [('Falcon AI V13.5 — Command Center','Falcon AI V13.6 — Command Center'),
                ('Falcon V13.5 ready.', 'Falcon V13.6 ready.'),
                ('V13.5  /  LOCAL JARVIS', 'V13.6  /  LOCAL JARVIS')]:
    replace('falcon.py', old, new)

replace('unified.py',
    '             "Commands: /build <goal>, /upgrade <goal>, /do <goal>, /screen,\\n"',
    '             "Commands: /tone casual|focused|quiet|status (local style only),\\n"\n'
    '             "/build <goal>, /upgrade <goal>, /do <goal>, /screen,\\n"')
replace('unified.py',
    '    if not original:\n        return None\n',
    '    if not original:\n        return None\n'
    "    # Pure conversational preference: no independent actions or added UI buttons.\n"
    "    if low in ('be serious for a minute', 'talk seriously', 'switch to serious mode'):\n"
    "        return ('personality', 'focused')\n"
    "    if low in ('talk normally again', 'back to normal', 'switch to normal mode'):\n"
    "        return ('personality', 'casual')\n"
    "    if low in ('/tone', '/personality', '/tone status', '/personality status'):\n"
    "        return ('personality', 'status')\n"
    "    if low.startswith('/tone ') or low.startswith('/personality '):\n"
    "        return ('personality', original.split(' ', 1)[1].strip())\n")
replace('unified.py',
    "        if kind == 'chat':\n            # Explicit /chat forces normal conversation.\n            self.app.chat_message(goal)\n",
    "        if kind == 'chat':\n            # Explicit /chat forces normal conversation.\n            self.app.chat_message(goal)\n"
    "        elif kind == 'personality':\n"
    "            import personality\n"
    "            if goal == 'status':\n"
    "                self.say('Falcon tone: '+personality.get_mode()+'. Type /tone casual, /tone focused, or /tone quiet.')\n"
    "            else:\n"
    "                try:\n"
    "                    current = personality.set_mode(goal)\n"
    "                    self.say('Falcon tone set to '+current+'. This changes conversation style, not permissions or abilities.')\n"
    "                except ValueError:\n"
    "                    self.say('Choose /tone casual, /tone focused, or /tone quiet.')\n"
    "                except OSError as exc:\n"
    "                    self.say('Could not save tone preference: '+str(exc)[:130])\n")
replace('release_updates.py','CURRENT_VERSION = (13, 5, 0)','CURRENT_VERSION = (13, 6, 0)')
replace('tests/test_v135_permanent.py',
    'self.assertEqual(release_updates.CURRENT_VERSION, (13,5,0))',
    'self.assertEqual(release_updates.CURRENT_VERSION, (13,6,0))')
replace('tests/test_v135_permanent.py',
    "self.assertEqual((ROOT/'RELEASE_VERSION.txt').read_text().strip(),'13.5.0')",
    "self.assertEqual((ROOT/'RELEASE_VERSION.txt').read_text().strip(),'13.6.0')")
replace('tests/test_v135_permanent.py', "self.assertIn('13.5.0',value)", "self.assertIn('13.6.0',value)")
replace('tests/test_v131_updates.py',
    "raw = fake_update()\n        url='https://github.com/trusted/falcon-release/releases/download/v13.6/Falcon_AI_Update.zip'",
    "raw = fake_update(version='13.7.0')\n        url='https://github.com/trusted/falcon-release/releases/download/v13.7/Falcon_AI_Update.zip'")
replace('tests/test_v131_updates.py',"'tag_name': 'v13.6'","'tag_name': 'v13.7'")
replace('tests/test_v131_updates.py',
    "self.assertEqual(obj['version'], (13,6,0))",
    "self.assertEqual(obj['version'], (13,7,0))")
(OUT / 'README_V13_6.txt').write_text(
    'FALCON AI V13.6 — CIPHER-STYLE PERSONALITY\n\n'
    'Casual local tone by default; no model, identity, or memory transfer.\n'
    'Type /tone focused to switch to a serious professional style.\n'
    'Type /tone quiet for short neutral responses.\n'
    'Type /tone casual to restore relaxed personality.\n'
    'Type /tone status for the selected style.\n\n'
    'The preference stays on this PC in LOCALAPPDATA/FalconAI/personality.json.\n'
    'No new GUI buttons or outside agent privileges.\n'
    'Existing Docker test, review/approve, STOP and rollback safeguards remain.\n',
    encoding='utf-8')
(OUT / 'BUILD_INFO.txt').write_text(
    'Falcon AI V13.6 — user-selected local personality mode, no extra PC privileges.\n',
    encoding='utf-8')
print('Prepared V13.6 source from verified V13.5 base:', len(list(OUT.rglob('*'))), 'entries')
