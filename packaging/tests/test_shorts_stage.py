import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stage_shorts import stage_shorts, MODULES

class StageShortsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source=Path(self.tmp.name)/"source"
        self.target=Path(self.tmp.name)/"target"
        self.source.mkdir()
        self.target.mkdir()
        (self.target/"developer_chat.py").write_text(
            "self.app.root.after_idle(self._setup_money_mode)\n"
            "def _setup_money_mode(self):\n"
            "    shorts_mode.create(model, cancel=cancel)\n",encoding="utf-8")
        for name in MODULES:
            (self.source/name).write_text("VALUE = 1\n",encoding="utf-8")

    def test_stage_and_repeat(self):
        self.assertEqual(stage_shorts(self.source,self.target),MODULES)
        self.assertTrue(all((self.target/n).read_bytes()==(self.source/n).read_bytes() for n in MODULES))
        self.assertEqual(stage_shorts(self.source,self.target),MODULES)

    def test_missing_module_no_partial_copy(self):
        (self.source/MODULES[-1]).unlink()
        with self.assertRaises(RuntimeError):
            stage_shorts(self.source,self.target)
        self.assertFalse((self.target/MODULES[0]).exists())

    def test_conflict_preserved(self):
        (self.target/MODULES[-1]).write_text("VALUE = 2\n",encoding="utf-8")
        with self.assertRaises(RuntimeError):
            stage_shorts(self.source,self.target)
        self.assertEqual((self.target/MODULES[-1]).read_text(),"VALUE = 2\n")
        self.assertFalse((self.target/MODULES[0]).exists())

    def test_missing_integration(self):
        (self.target/"developer_chat.py").write_text("# no integration\n")
        with self.assertRaises(RuntimeError):
            stage_shorts(self.source,self.target)
        self.assertFalse((self.target/MODULES[0]).exists())

    def test_syntax_failure(self):
        (self.source/MODULES[-1]).write_text("def invalid(\n")
        with self.assertRaises(SyntaxError):
            stage_shorts(self.source,self.target)
        self.assertFalse((self.target/MODULES[0]).exists())
