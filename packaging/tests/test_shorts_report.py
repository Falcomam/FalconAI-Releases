import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shorts_report import report

class ReportTests(unittest.TestCase):
    def test_read_only_status_and_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            day=dt.date(2026,11,24)
            folder=root/"shorts"/day.isoformat()
            with patch("shorts_report.shutil.which",return_value=None):
                status=report(root,day,gaming=True)
            self.assertIn("No draft yet",status)
            self.assertIn("ON (paused)",status)
            self.assertIn("Missing ffmpeg",status)
            self.assertFalse((root/"shorts").exists())
            folder.mkdir(parents=True)
            (folder/"REVIEW_REQUIRED.txt").touch()
            self.assertIn("Reserved or incomplete",report(root,day))
            (folder/"draft.mp4").touch()
            self.assertIn("Video ready for review",report(root,day))
            ledger=folder/"upload_attempt.json"
            ledger.write_text('{"state":"pending_or_uncertain"}')
            self.assertIn("Upload uncertain",report(root,day))
            ledger.write_text(json.dumps({"state":"uploaded","video_id":"abc"}))
            self.assertIn("public visibility not verified",report(root,day))
            (folder/"FAILED.txt").touch()
            self.assertIn("Failed or interrupted",report(root,day))
            ledger.write_text("broken")
            self.assertIn("Unreadable upload receipt",report(root,day))
