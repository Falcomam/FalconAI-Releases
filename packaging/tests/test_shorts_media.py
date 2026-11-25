"""Real six-scene media smoke test using synthetic audio, no network or models."""
import math
import shutil
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import shorts_mode
from shorts_timing import scene_frames, story_key

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class MediaSmokeTest(unittest.TestCase):
    def test_full_six_scene_render(self):
        story={"title":"Synthetic smoke test",
               "lines":["The moon demanded a refund for its broken toaster."]*6,
               "scenes":[{"setting":s,"action":a} for s,a in zip(
                   ("moon","city","kitchen","ocean","desert","gym"),
                   ("jump","run","panic","fall","stand","celebrate"))]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(shorts_mode,"check_pause"):
            root=Path(tmp)
            frames=[]
            for i in range(6):
                path=root/f"voice{i}.wav"
                with wave.open(str(path),"wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
                    w.writeframes(b"".join(struct.pack("<h",int(1500*math.sin(2*math.pi*(300+i*30)*n/8000))) for n in range(17600)))
                frames.append(scene_frames(path))
            duration=shorts_mode.render_video(root,story,story_key(story),frames)
            self.assertAlmostEqual(duration,sum(frames)/30,delta=1)
            self.assertGreater((root/"draft.mp4").stat().st_size,10000)
            self.assertEqual((root/"captions.srt").read_text().count("-->"),6)
            self.assertFalse((root/"REVIEW_REQUIRED.txt").exists())
