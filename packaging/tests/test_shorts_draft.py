import datetime as dt
import tempfile
import sys
import unittest
from pathlib import Path
from PIL import Image, ImageChops
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shorts_schedule import due
from shorts_visuals import render_scene

class DraftTests(unittest.TestCase):
    def test_daily(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            now=dt.datetime(2026,11,24,16,tzinfo=dt.timezone(dt.timedelta(hours=-5)))
            self.assertFalse(due(now.replace(hour=15),root,enabled=True,paused=False))
            self.assertTrue(due(now,root,enabled=True,paused=False))
            self.assertFalse(due(now,root,enabled=False,paused=False))
            self.assertFalse(due(now,root,enabled=True,paused=True))
            (root/"2026-11-24").mkdir()
            self.assertFalse(due(now,root,enabled=True,paused=False))
            self.assertTrue(due(now+dt.timedelta(days=1),root,enabled=True,paused=False))
            with self.assertRaises(ValueError):
                due(now.replace(tzinfo=None),root,enabled=True,paused=False)

    def test_visuals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            a,b,c=(root/n for n in ("a.png","b.png","c.png"))
            render_scene("seed",0,"moon","jump",a)
            render_scene("seed",0,"moon","jump",b)
            render_scene("seed",1,"city","run",c)
            with Image.open(a) as ia, Image.open(b) as ib, Image.open(c) as ic:
                self.assertEqual(ia.size,(720,1280))
                self.assertIsNone(ImageChops.difference(ia,ib).getbbox())
                self.assertIsNotNone(ImageChops.difference(ia,ic).getbbox())
            with self.assertRaises(ValueError):
                render_scene("seed",0,"unknown","jump",a)

if __name__=="__main__":
    unittest.main()
