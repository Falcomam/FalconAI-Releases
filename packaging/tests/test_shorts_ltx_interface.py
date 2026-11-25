"""Exercise installed-source chat routing and the real Money Mode menu after staging."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "build/Falcon_Ai_V14_4_Candidate"


@unittest.skipUnless((SOURCE / "developer_chat.py").is_file(), "Reconstruct the Windows candidate first")
class StagedInterfaceTests(unittest.TestCase):
    def staged(self, code):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable, "-c", code], cwd=tmp, check=True,
                           env=dict(os.environ, PYTHONPATH=str(SOURCE), LOCALAPPDATA=tmp))

    def test_staged_commands_and_existing_daily_draft(self):
        self.staged("""
from unittest.mock import Mock
import developer_chat as chat
features = chat.ChatFeatures(Mock())
features._money_controls = Mock()
assert features.dispatch('/shorts clip A falcon rolls left')
features._money_controls.generate_clip.assert_called_once_with('A falcon rolls left')
features._shorts_draft = Mock()
assert features.dispatch('/shorts draft')
features._shorts_draft.assert_called_once_with()
assert chat.route('/shorts clipboard') is None
""")

    @unittest.skipUnless(sys.platform == "win32" or os.environ.get("DISPLAY"), "Native Tk display required")
    def test_main_window_menu_invokes_clip_and_report(self):
        self.staged("""
from tkinter import Tk
from unittest.mock import Mock, patch
from shorts_controls import MoneyControls
root = Tk()
root.withdraw()
try:
    features = Mock()
    features.app.root = root
    features.app.busy = features._running = False
    controls = MoneyControls(features)
    with patch('tkinter.simpledialog.askstring', return_value='Falcon takes flight'):
        controls.menu.invoke('Generate LTX preview clip…')
    features._launch.assert_called_once()
    controls.menu.invoke('Daily report')
    features._shorts_status.assert_called_once()
    controls.menu.invoke('Use LTX-Video for daily drafts')
    assert controls.ltx_choice.get()
finally:
    root.destroy()
""")
