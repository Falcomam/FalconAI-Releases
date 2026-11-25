"""Regression cases for malformed output from a small local model."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import shorts_mode

def fixture():
    return {"title":"Toaster's parking ticket",
            "lines":["The toaster’s moon — it demanded a refund."]*6,
            "scenes":[{"setting":"moon","action":"stand"}]*6}

class StoryValidation(unittest.TestCase):
    def test_normalizes_typographic_punctuation_and_short_line(self):
        story=shorts_mode.validate_story(fixture())
        self.assertEqual(story["lines"][0],"The toaster's moon - it demanded a refund.")
        self.assertEqual(len(story["lines"]),6)

    def test_rejects_markup_and_too_short(self):
        for invalid in ("<script>hello world</script>","Tiny line."):
            obj=fixture()
            obj["lines"][0]=invalid
            with self.assertRaises(ValueError):
                shorts_mode.validate_story(obj)

    def test_repairs_invalid_model_output(self):
        bad=fixture()
        bad["lines"][0]="Too short."
        good=fixture()
        responses=[]
        for obj in (bad,good):
            ctx=MagicMock()
            ctx.__enter__.return_value.read.return_value=json.dumps({"response":json.dumps(obj)}).encode()
            responses.append(ctx)
        with patch.object(shorts_mode,"check_pause"), patch.object(shorts_mode.urllib.request,"build_opener") as opener:
            opener.return_value.open.side_effect=responses
            result=shorts_mode.script("fixture")
            self.assertEqual(opener.return_value.open.call_count,2)
            self.assertEqual(result,shorts_mode.validate_story(good))

    def test_bounded_invalid_output(self):
        ctx=MagicMock()
        ctx.__enter__.return_value.read.return_value=b'{"response":"{}"}'
        with patch.object(shorts_mode,"check_pause"), patch.object(shorts_mode.urllib.request,"build_opener") as opener:
            opener.return_value.open.return_value=ctx
            with self.assertRaisesRegex(ValueError,"three times"):
                shorts_mode.script("fixture")
            self.assertEqual(opener.return_value.open.call_count,3)

if __name__=="__main__":
    unittest.main()
