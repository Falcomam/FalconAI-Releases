"""Regression cases for malformed output from a small local model."""
import json
import urllib.error
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


    def test_request_budget_and_schema(self):
        ctx=MagicMock()
        ctx.__enter__.return_value.read.return_value=json.dumps({"response":json.dumps(fixture())}).encode()
        with patch.object(shorts_mode,"check_pause"), patch.object(shorts_mode.urllib.request,"build_opener") as opener:
            opener.return_value.open.return_value=ctx
            shorts_mode.script("fixture")
            body=json.loads(opener.return_value.open.call_args.args[0].data)
            self.assertIs(body["think"],False)
            self.assertEqual(body["options"]["num_predict"],1024)
            self.assertEqual(body["format"]["properties"]["scenes"]["minItems"],6)

    def test_http_500_recovers(self):
        ctx=MagicMock()
        ctx.__enter__.return_value.read.return_value=json.dumps({"response":json.dumps(fixture())}).encode()
        err=urllib.error.HTTPError("http://127.0.0.1:11434/api/generate",500,"internal",{},None)
        with patch.object(shorts_mode,"check_pause"), patch.object(shorts_mode.urllib.request,"build_opener") as opener:
            opener.return_value.open.side_effect=[err,ctx]
            self.assertEqual(shorts_mode.script("fixture"),shorts_mode.validate_story(fixture()))
            self.assertEqual(opener.return_value.open.call_count,2)

    def test_prefers_installed_writer_without_changing_chat(self):
        self.assertEqual(shorts_mode.preferred_story_model("qwen3:4b",["qwen3:4b",shorts_mode.SHORTS_MODEL]),shorts_mode.SHORTS_MODEL)
        self.assertEqual(shorts_mode.preferred_story_model("qwen3:4b",["qwen3:4b"]),"qwen3:4b")

if __name__=="__main__":
    unittest.main()
