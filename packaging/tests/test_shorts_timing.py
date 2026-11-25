import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shorts_timing import distinct_story, scene_frames, timeline, scene_theme, story_key

class ShortsTimingTests(unittest.TestCase):
    def setUp(self):
        self.story = {"title":"Test","lines":["The toaster rode a bicycle through the moon."] * 6}

    def test_actual_wave_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"voice.wav"
            with wave.open(str(p),"wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
                w.writeframes(bytes(16000))
            self.assertEqual(scene_frames(p),36)

    def test_timing(self):
        result=timeline(self.story["lines"], [90]*6)
        self.assertIn("00:00:00,000 --> 00:00:03,000",result)
        self.assertIn("00:00:15,000 --> 00:00:18,000",result)

    def test_bad_inputs(self):
        for counts in ([1]*6,[500]*6,[90]*5,[True]*6):
            with self.assertRaises(ValueError):
                timeline(self.story["lines"],counts)
        with self.assertRaises(ValueError):
            timeline(["{unsafe}"]*6,[90]*6)

    def test_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            old=root/"2026-11-23"; old.mkdir()
            (old/"story.json").write_text(json.dumps(self.story),encoding="utf-8")
            with self.assertRaises(ValueError):
                distinct_story(self.story,root,root/"2026-11-24")

    def test_palette(self):
        key=story_key(self.story)
        self.assertNotEqual(scene_theme(key,0),scene_theme(key,1))
        self.assertEqual(scene_theme(key,0),scene_theme(key,0))

if __name__=="__main__":
    unittest.main()
