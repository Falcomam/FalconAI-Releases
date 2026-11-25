"""Manual Studio fallback: never upload from the application."""
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shorts_controls import MoneyControls
from shorts_report import report

class ManualHandoffTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.day=dt.date.today()
        self.folder=self.root/"shorts"/self.day.isoformat()
        self.folder.mkdir(parents=True)
        self.video=self.folder/"draft.mp4"
        self.video.write_bytes(b"fixture")
        (self.folder/"REVIEW_REQUIRED.txt").touch()
        self.controls=MoneyControls.__new__(MoneyControls)
        self.controls.root=self.root
        self.controls.window=MagicMock()
        self.controls.features=MagicMock()
        self.controls.features.app.busy=False
        self.controls.features._running=False
        self.controls.review_active=False

    def test_decline_is_read_only(self):
        with patch("tkinter.messagebox.askyesno",return_value=False), \
             patch("webbrowser.open") as browser:
            self.controls.manual_upload()
            browser.assert_not_called()
        self.assertFalse((self.folder/"upload_attempt.json").exists())
        self.assertFalse(self.controls.review_active)

    def test_handoff_records_before_open_and_blocks_repeat(self):
        ledger=self.folder/"upload_attempt.json"
        def open_folder(path):
            self.assertEqual(json.loads(ledger.read_text())["state"],"manual_handoff")
            self.assertEqual(Path(path),self.folder)
        with patch("tkinter.messagebox.askyesno",return_value=True) as confirm, \
             patch("shorts_controls.os.startfile",side_effect=open_folder,create=True) as folder, \
             patch("webbrowser.open") as browser:
            self.controls.manual_upload()
            self.controls.manual_upload()
            confirm.assert_called_once()
            folder.assert_called_once()
            self.assertEqual(browser.call_count,2)
        self.assertIn("Manual Studio handoff recorded; upload not verified",report(self.root,self.day))
        self.assertFalse(self.controls.review_active)

    def test_failed_draft_not_handed_off(self):
        (self.folder/"FAILED.txt").touch()
        with patch("tkinter.messagebox.askyesno") as confirm, patch("webbrowser.open") as browser:
            self.controls.manual_upload()
            confirm.assert_not_called()
            browser.assert_not_called()
        self.assertFalse((self.folder/"upload_attempt.json").exists())

if __name__=="__main__":
    unittest.main()
