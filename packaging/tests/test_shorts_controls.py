import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shorts_controls import enabled, set_enabled, ready_video

class MoneyControlTests(unittest.TestCase):
    def test_preferences(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.assertFalse(enabled(root))
            set_enabled(True,root)
            self.assertTrue(enabled(root))
            set_enabled(False,root)
            self.assertFalse(enabled(root))
            with self.assertRaises(ValueError):
                set_enabled("yes",root)
            (root/"shorts_preferences.json").write_text("bad")
            self.assertFalse(enabled(root))

    def test_preview_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            day=dt.date(2026,11,24)
            folder=root/"shorts"/day.isoformat()
            folder.mkdir(parents=True)
            video=folder/"draft.mp4"
            video.write_bytes(b"test")
            self.assertIsNone(ready_video(root,day))
            (folder/"REVIEW_REQUIRED.txt").touch()
            self.assertEqual(ready_video(root,day),video)
            (folder/"FAILED.txt").touch()
            self.assertIsNone(ready_video(root,day))
