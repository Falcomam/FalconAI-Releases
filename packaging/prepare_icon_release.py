"""Build Falcon Ai 13.7.1, preserving the verified 13.7.0 Windows app.

The original purple falcon image is a committed, SHA256-pinned transparent PNG.
Convert to a multi-resolution Windows ICO, embed it in the executable and
installer, and set the Tk window icon to the same asset.
"""
from pathlib import Path
import base64
import hashlib
import shutil

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'build' / 'Falcon_Ai_App_V13_7_0'
TARGET = REPO / 'build' / 'Falcon_Ai_App_V13_7_1'
RUNTIME = REPO / 'build' / 'falcon_app_1371_runtime'
ASSET = REPO / 'packaging' / 'assets' / 'purple_falcon_icon.b64.txt'
ICON_SHA256 = 'b81942ef17af848ae3026c6ab5aed9f7b6d2888188aeafba610a91ecbd33a86a'

if (SOURCE / 'RELEASE_VERSION.txt').read_text(encoding='utf-8').strip() != '13.7.0':
    raise SystemExit('Falcon Ai 13.7.0 base not verified')
if TARGET.exists():
    shutil.rmtree(TARGET)
TARGET.mkdir(parents=True)
shutil.copytree(SOURCE, TARGET, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__','*.pyc','.venv'))
RUNTIME.mkdir(parents=True, exist_ok=True)

png = base64.b64decode(ASSET.read_text(encoding='utf-8').strip(), validate=True)
if hashlib.sha256(png).hexdigest() != ICON_SHA256:
    raise SystemExit('Purple Falcon icon image does not match original SHA256')
src_png = RUNTIME / 'Falcon_Ai_Icon.png'
src_png.write_bytes(png)
with Image.open(src_png) as im:
    if im.format != 'PNG' or im.size != (192,192):
        raise SystemExit('Unexpected original app icon dimensions')
    im = im.convert('RGBA')
    if im.getextrema()[-1] == (255,255):
        raise SystemExit('App icon has no transparent background')
    im = im.resize((256,256), Image.Resampling.LANCZOS)
    icon_path = RUNTIME / 'Falcon_Ai_Icon.ico'
    im.save(icon_path, format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    with Image.open(icon_path) as check:
        if check.format != 'ICO' or 256 not in [size[0] for size in check.ico.sizes()]:
            raise SystemExit('Windows multi-size icon verification failed')

def one(path, before, after):
    file = Path(path)
    text = file.read_text(encoding='utf-8')
    if text.count(before) != 1:
        raise SystemExit(f'Expected one anchor in {file}: {before[:60]!r}; found {text.count(before)}')
    file.write_text(text.replace(before, after, 1), encoding='utf-8')

(TARGET / 'RELEASE_VERSION.txt').write_text('13.7.1\n', encoding='utf-8')
for old, new in (
    ('Falcon Ai V13.7.0 — Command Center', 'Falcon Ai V13.7.1 — Command Center'),
    ('Falcon Ai V13.7.0 ready.', 'Falcon Ai V13.7.1 ready.'),
    ('V13.7.0  /  LOCAL JARVIS', 'V13.7.1  /  LOCAL JARVIS'),
):
    one(TARGET/'falcon.py', old, new)
one(TARGET/'release_updates.py',
    'CURRENT_VERSION = (13, 7, 0)', 'CURRENT_VERSION = (13, 7, 1)')
one(TARGET/'falcon_launcher.py', 'Starting Falcon Ai V13.7.0', 'Starting Falcon Ai V13.7.1')
one(TARGET/'falcon_launcher.py',
    '            app = Falcon(root)',
    """# Match the Windows EXE, installer, taskbar and desktop shortcut icon.
            # Load the SHA256-pinned icon bundled with Falcon Ai.
            try:
                resource = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
                image_path = resource / 'Falcon_Ai_Icon.png'
                if image_path.is_file():
                    window_icon = tk.PhotoImage(file=str(image_path))
                    root.iconphoto(True, window_icon)
                    root._falcon_icon_reference = window_icon
            except Exception as icon_error:
                print('[BOOT] Window icon unavailable: ' + str(icon_error)[:120], file=log)
            app = Falcon(root)""")

# Package-specific modules are prepared separately to avoid modifying the
# published V13.7.0 update channel and keep regression reconstruction possible.
for name in ('app_entry.py','app_updates.py'):
    template = (REPO / 'packaging' / name).read_text(encoding='utf-8')
    template = template.replace('(13, 7, 0)', '(13, 7, 1)')
    template = template.replace('FalconAi-WindowsUpdater/13.7', 'FalconAi-WindowsUpdater/13.7.1')
    if name == 'app_entry.py':
        template = template.replace(
            "if app_updates.CURRENT_VERSION != (13, 7, 1):",
            """if app_updates.CURRENT_VERSION != (13, 7, 1):
            """)
        template = template.replace(
            "print('FALCON AI PACKAGED APP SELF-TEST PASSED')",
            """if not (pathlib.Path(getattr(sys, '_MEIPASS', pathlib.Path(__file__).parent))
                    / 'Falcon_Ai_Icon.png').is_file():
            raise RuntimeError('Falcon Ai app icon missing from packaged build')
        print('FALCON AI V13.7.1 PACKAGED APP SELF-TEST PASSED')""")
    (RUNTIME/name).write_text(template, encoding='utf-8')

# Installer built from the already tested 13.7.0 source, changing only the
# version and icon configuration.
setup = (REPO/'packaging'/'Falcon_Ai.iss').read_text(encoding='utf-8')
setup = setup.replace('#define MyAppVersion "13.7.0"', '#define MyAppVersion "13.7.1"')
setup = setup.replace('UninstallDisplayIcon={app}\\{#MyAppExeName}',
                      'UninstallDisplayIcon={app}\\{#MyAppExeName}\nSetupIconFile=build\\falcon_app_1371_runtime\\Falcon_Ai_Icon.ico')
(RUNTIME/'Falcon_Ai.iss').write_text(setup, encoding='utf-8')
(TARGET/'README_FALCON_AI_APP.txt').write_text(
    (SOURCE/'README_FALCON_AI_APP.txt').read_text(encoding='utf-8')
    .replace('13.7.0','13.7.1')
    + '\nThe Windows EXE, installer, taskbar and GUI use the purple Falcon Ai icon.\n',
    encoding='utf-8')
print('Prepared Falcon Ai V13.7.1 icon build: original icon SHA256 verified')
