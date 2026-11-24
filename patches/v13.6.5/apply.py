"""Project Falcon V13.6.5: compact status dropdown and accurate version reporting."""
from pathlib import Path
import shutil

repo = Path(__file__).resolve().parents[2]
source = repo / 'build' / 'Falcon_AI_V13_6_4'
target = repo / 'build' / 'Falcon_AI_V13_6_5'
if (source / 'RELEASE_VERSION.txt').read_text().strip() != '13.6.4':
    raise SystemExit('Verified V13.6.4 source required')
if target.exists():
    shutil.rmtree(target)
shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

def replace(rel, old, new):
    p = target / rel
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Expected one anchor in {rel}, found {count}: {old[:90]!r}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')

(target / 'status_dropdown.py').write_text(r'''"""Compact, optional activity dropdown attached to Falcon's main status badge.

No independent agent or background polling: reads the same status displayed in
Falcon's main UI, with the same STOP handler and optional full Mini Monitor.
"""
import tkinter as tk

BASE = '#171426'
PANEL = '#211b35'
TEXT = '#f6f1ff'
MUTED = '#b5a8cd'
ACCENT = '#c1a7ff'
DANGER = '#ff9aaf'

class StatusDropdown:
    def __init__(self, app):
        self.app = app
        self.popup = tk.Toplevel(app.root)
        self.popup.withdraw()
        self.popup.overrideredirect(True)
        self.popup.configure(bg=BASE, highlightthickness=1,
                             highlightbackground='#47365f')
        self.popup.geometry('324x194')
        self.popup.transient(app.root)
        self.visible = False

        heading = tk.Frame(self.popup, bg=BASE)
        heading.pack(fill='x', padx=12, pady=(11, 7))
        tk.Label(heading, text='◆ FALCON  •  LIVE ACTIVITY',
                 bg=BASE, fg=ACCENT,
                 font=('Segoe UI', 9, 'bold')).pack(side='left')
        tk.Button(heading, text='×', command=self.hide,
                  bg=BASE, fg=MUTED, relief='flat', borderwidth=0,
                  font=('Segoe UI', 11), cursor='hand2').pack(side='right')

        info = tk.Frame(self.popup, bg=PANEL)
        info.pack(fill='both', expand=True, padx=10, pady=(0, 8))
        tk.Label(info, text='CURRENT STATUS', bg=PANEL, fg=MUTED,
                 font=('Segoe UI', 8, 'bold')).pack(anchor='w', padx=12, pady=(9, 2))
        self.status = tk.Label(info, text='Ready • Local Ollama',
                               bg=PANEL, fg=TEXT,
                               font=('Segoe UI', 11, 'bold'), anchor='w',
                               justify='left', wraplength=280)
        self.status.pack(fill='x', padx=12)
        self.description = tk.Label(info, text='No active task reported.',
                                    bg=PANEL, fg=MUTED,
                                    font=('Segoe UI', 9), justify='left',
                                    anchor='w', wraplength=280)
        self.description.pack(fill='x', padx=12, pady=(5, 6))

        footer = tk.Frame(self.popup, bg=BASE)
        footer.pack(fill='x', padx=10, pady=(0, 10))
        tk.Button(footer, text='Open Mini Monitor', command=self.open_window,
                  bg='#423064', fg=TEXT, relief='flat', cursor='hand2',
                  font=('Segoe UI', 9), padx=8).pack(side='left')
        tk.Button(footer, text='STOP', command=self.stop,
                  bg='#593041', fg=DANGER, relief='flat', cursor='hand2',
                  font=('Segoe UI', 9, 'bold'), padx=12).pack(side='right')

        self.update_status(app.status.cget('text'))
        app.root.bind('<Configure>', self._on_main_move, add='+')

    def _on_main_move(self, event):
        if event.widget is self.app.root and self.visible:
            self._position()

    def _position(self):
        arrow = self.app.status_dropdown_button
        arrow.update_idletasks()
        width = 324
        x = max(0, arrow.winfo_rootx() + arrow.winfo_width() - width)
        y = arrow.winfo_rooty() + arrow.winfo_height() + 3
        self.popup.geometry(f'{width}x194+{x}+{y}')

    def update_status(self, message):
        if not self.popup.winfo_exists():
            return
        msg = str(message).replace('●', '', 1).strip() or 'Ready'
        self.status.configure(text=msg[:150])
        low = msg.casefold()
        if 'error' in low or 'failed' in low:
            description = 'Falcon reported a problem. Open the main window for details.'
        elif 'ready' in low or 'stopped' in low:
            description = 'No active task reported.'
        else:
            description = 'Showing Falcon’s actual status. No estimated progress.'
        self.description.configure(text=description)

    def show(self):
        if not self.popup.winfo_exists():
            return
        self.update_status(self.app.status.cget('text'))
        self._position()
        self.popup.deiconify()
        self.popup.lift()
        self.visible = True
        self.app.status_dropdown_button.configure(text='▴')

    def hide(self):
        if self.popup.winfo_exists():
            self.popup.withdraw()
        self.visible = False
        self.app.status_dropdown_button.configure(text='▾')

    def toggle(self):
        self.hide() if self.visible else self.show()

    def open_window(self):
        self.hide()
        self.app.open_mini_monitor()

    def stop(self):
        self.app.stop()
        self.update_status(self.app.status.cget('text'))

    def close(self):
        if self.popup.winfo_exists():
            self.popup.destroy()
        self.visible = False
''', encoding='utf-8')

replace('falcon.py',
        '        self.status.pack()\n',
        """        self.status.pack(side='left')
        self.status_dropdown_button = tk.Button(
            status_frame, text='▾', command=self.toggle_status_dropdown,
            bg=C['panel'], fg=C['purple'], activebackground=C['panel2'],
            activeforeground=C['text'], cursor='hand2', relief='flat',
            borderwidth=0, padx=10, pady=9, font=('Segoe UI', 10, 'bold'))
        self.status_dropdown_button.pack(side='right')
""")
replace('falcon.py',
        '    def open_mini_monitor(self):\n',
        """    def toggle_status_dropdown(self):
        if getattr(self, 'status_dropdown', None) is None:
            from status_dropdown import StatusDropdown
            self.status_dropdown = StatusDropdown(self)
        self.status_dropdown.toggle()

    def open_mini_monitor(self):
""")
replace('falcon.py',
        """        if monitor is not None:
            monitor.update_status(message)""",
        """        if monitor is not None:
            monitor.update_status(message)
        dropdown = getattr(self, 'status_dropdown', None)
        if dropdown is not None:
            dropdown.update_status(message)""")
replace('falcon.py',
        """    def on_close(self):
        if getattr(self, 'mini_monitor', None) is not None:""",
        """    def on_close(self):
        if getattr(self, 'status_dropdown', None) is not None:
            self.status_dropdown.close()
        if getattr(self, 'mini_monitor', None) is not None:""")
replace('falcon.py',
        "'No newer stable release was published to this channel. Current version: 13.4.'",
        "'No newer stable release was published to this channel. Current version: ' + '.'.join(map(str, release_updates.CURRENT_VERSION)) + '.'")
replace('release_updates.py', 'CURRENT_VERSION = (13, 6, 4)', 'CURRENT_VERSION = (13, 6, 5)')
for old, new in (
    ('Falcon AI V13.6.4 — Command Center', 'Falcon AI V13.6.5 — Command Center'),
    ('Falcon V13.6.4 ready.', 'Falcon V13.6.5 ready.'),
    ('V13.6.4  /  LOCAL JARVIS', 'V13.6.5  /  LOCAL JARVIS'),
):
    replace('falcon.py', old, new)
(target / 'RELEASE_VERSION.txt').write_text('13.6.5\n', encoding='utf-8')
for rel in (
    'tests/test_v135_permanent.py', 'tests/test_v131_updates.py',
    'tests/test_v1361_restart.py', 'tests/test_v1362_restart.py',
    'tests/test_v1363_restart_button.py', 'tests/test_v1364_monitor.py',
):
    p = target / rel
    data = p.read_text(encoding='utf-8')
    data = data.replace('(13,6,4)', '(13,6,5)').replace('(13, 6, 4)', '(13, 6, 5)')
    data = data.replace('13.6.4', '13.6.5').replace('Falcon_AI_V13_6_4/', 'Falcon_AI_V13_6_5/')
    p.write_text(data, encoding='utf-8')
(target / 'tests' / 'test_v1365_dropdown.py').write_text(
    """from pathlib import Path
import unittest
import release_updates

ROOT = Path(__file__).resolve().parents[1]
class DropdownTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(release_updates.CURRENT_VERSION, (13,6,5))
        self.assertEqual((ROOT/'RELEASE_VERSION.txt').read_text().strip(),'13.6.5')
    def test_status_arrow(self):
        ui = (ROOT/'falcon.py').read_text(encoding='utf-8')
        popup = (ROOT/'status_dropdown.py').read_text(encoding='utf-8')
        self.assertIn('status_dropdown_button', ui)
        self.assertIn('def toggle_status_dropdown(', ui)
        self.assertIn('def open_mini_monitor(', ui)
        self.assertIn('dropdown.update_status(message)', ui)
        self.assertIn('command=self.stop', popup)
        self.assertIn('overrideredirect(True)', popup)
        self.assertIn('Open Mini Monitor', popup)
        self.assertIn('status_dropdown_button.configure', popup)
    def test_version_message_not_hardcoded(self):
        ui = (ROOT/'falcon.py').read_text(encoding='utf-8')
        self.assertIn('release_updates.CURRENT_VERSION', ui)
        self.assertNotIn('Current version: 13.4.', ui)
    def test_update_safety_retained(self):
        updater = (ROOT/'APPLY_RELEASE_UPDATE.ps1').read_text(encoding='utf-8')
        self.assertNotIn('$home', updater.lower())
        self.assertIn('restart_helper.py', updater)
        self.assertIn('Move-Item -LiteralPath $backup -Destination $Live', updater)
""", encoding='utf-8')
(target / 'FOLDER_GUIDE.txt').write_text(
    'PROJECT FALCON - CLEAN APP LAYOUT\n'
    'START_HERE.bat             Start Falcon from one shortcut\n'
    'falcon.py                  Main application UI\n'
    'status_dropdown.py         Status arrow dropdown attached to top bar\n'
    'mini_monitor.py            Optional separate floating monitor\n'
    'restart_helper.py          Verified restart path\n'
    'release_updates.py         GitHub release verification\n'
    'APPLY_RELEASE_UPDATE.ps1   Update installer and backup recovery\n'
    'tests/                     Bundled tests (not desktop shortcuts)\n'
    'LOCALAPPDATA/FalconAI/logs/  Local diagnostics outside program folder\n'
    'Keep internal modules in place. Future packaging will hide them from normal use.\n',
    encoding='utf-8')
print('Built Project Falcon 13.6.5: status dropdown and accurate version messages')
