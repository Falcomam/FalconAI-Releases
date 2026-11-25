"""Native Windows speech + actual rendering acceptance test.

Runs only on Windows with FFmpeg available. Uses a fixed original story in
place of Ollama to isolate speech/media failures. No credentials or uploads.
All writes stay in a temporary directory.
"""
import datetime as dt
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import shorts_mode
from shorts_upload import probe

STORY = {
    "title": "The Moon's Unpaid Toaster",
    "lines": [
        "A toaster with cat ears demanded rent from the moon.",
        "It jumped into a kitchen and stole a tiny ladder.",
        "The ladder ran through town wearing six enormous yellow boots.",
        "Our toaster panicked when the ocean sent a parking ticket.",
        "It celebrated by opening a gym for exhausted floating pancakes.",
        "The moon paid its rent using one completely imaginary coin.",
    ],
    "scenes": [
        {"setting": s, "action": a} for s, a in zip(
            ("moon", "kitchen", "city", "ocean", "gym", "moon"),
            ("stand", "jump", "run", "panic", "celebrate", "fall")
        )
    ],
}

@unittest.skipUnless(sys.platform == "win32", "Native Windows speech required")
class WindowsShortsAcceptance(unittest.TestCase):
    def test_real_speech_and_six_scene_draft(self):
        missing = [name for name in ("powershell.exe", "ffmpeg", "ffprobe")
                   if not shutil.which(name)]
        self.assertFalse(missing, "Windows media prerequisites missing: " + ", ".join(missing))
        day = dt.date(2026, 11, 24)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "shorts"
            with patch.object(shorts_mode, "ROOT", root), \
                 patch.object(shorts_mode, "OUT", out), \
                 patch.object(shorts_mode, "script", return_value=STORY) as script:
                folder = shorts_mode.create("fixture", day)
                self.assertEqual(folder, out / day.isoformat())
                self.assertTrue((folder / "REVIEW_REQUIRED.txt").is_file())
                self.assertFalse((folder / "FAILED.txt").exists())
                self.assertFalse((folder / "upload_attempt.json").exists())
                self.assertTrue(12 <= probe(folder / "draft.mp4") <= 60)
                self.assertEqual(len(list(folder.glob("voice[0-5].wav"))), 6)
                self.assertEqual((folder / "captions.srt").read_text().count("-->"), 6)
                with self.assertRaises(FileExistsError):
                    shorts_mode.create("fixture", day)
                script.assert_called_once_with("fixture")
                stop = threading.Event()
                stop.set()
                with self.assertRaises(RuntimeError):
                    shorts_mode.create("fixture", day + dt.timedelta(days=1), cancel=stop)
                self.assertFalse((out / (day + dt.timedelta(days=1)).isoformat()).exists())


if __name__ == "__main__":
    unittest.main()
