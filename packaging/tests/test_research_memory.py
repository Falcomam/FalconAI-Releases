"""Offline tests for source-linked local research memory."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import research_memory as memory
from developer_workspace import ProjectError


class ResearchMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.filename = Path(self.temp.name) / "notes.json"
        self.sources = [{"title": "Peregrine falcon",
                         "url": "https://en.wikipedia.org/?curid=12490"}]

    def test_save_recall_replace_and_delete(self):
        first = memory.save_note("falcon", "Bird facts",
                                 "Peregrine falcons are birds of prey.",
                                 self.sources, filename=self.filename)
        self.assertEqual(first["key"], "falcon")
        self.assertEqual(len(memory.load_notes(filename=self.filename)), 1)
        memory.save_note("falcon", "Bird facts", "Updated source-linked summary.",
                         self.sources, filename=self.filename)
        notes = memory.load_notes(filename=self.filename)
        self.assertEqual(len(notes), 1)
        self.assertIn("Updated", notes[0]["summary"])
        self.assertTrue(memory.forget_note("falcon", filename=self.filename))
        self.assertFalse(memory.forget_note("falcon", filename=self.filename))
        self.assertEqual(memory.load_notes(filename=self.filename), ())

    def test_invalid_or_external_sources_rejected(self):
        for url in ("file:///etc/passwd", "https://other.example/private",
                    "https://en.wikipedia.org/?curid=oops"):
            with self.subTest(url=url), self.assertRaises(ProjectError):
                memory.save_note("one", "Topic", "Safe short summary",
                                 [{"title": "Source", "url": url}],
                                 filename=self.filename)
        self.assertFalse(self.filename.exists())

    def test_oversized_content_and_malformed_file_rejected(self):
        with self.assertRaises(ProjectError):
            memory.save_note("one", "Topic", "x" * 1801, self.sources,
                             filename=self.filename)
        self.filename.write_text("not-json", encoding="utf-8")
        with self.assertRaises(ProjectError):
            memory.load_notes(filename=self.filename)

    def test_symlink_file_rejected(self):
        outside = Path(self.temp.name) / "private.json"
        outside.write_text("private", encoding="utf-8")
        try:
            self.filename.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink unavailable")
        with self.assertRaises(ProjectError):
            memory.save_note("one", "Topic", "Summary", self.sources,
                             filename=self.filename)
        self.assertEqual(outside.read_text(encoding="utf-8"), "private")


if __name__ == "__main__":
    unittest.main()
