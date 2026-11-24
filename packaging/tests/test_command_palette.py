"""Single chat /command completion and inert categorized shortcut tests."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import command_palette as cp


class FakeEntry:
    def __init__(self):
        self.text = ""
        self.bindings = {}
        self.cursor = 0
        self.focused = False
        self.deleted = 0
    def get(self):
        return self.text
    def delete(self, start, end):
        self.deleted += 1
        self.text = ""
        self.cursor = 0
    def insert(self, start, value):
        self.text = value
        self.cursor = len(value)
    def icursor(self, where):
        self.cursor = len(self.text) if where == "end" else int(where)
    def index(self, index):
        return self.cursor
    def bind(self, event, callback):
        self.bindings[event] = callback
    def focus_set(self):
        self.focused = True


class FakeHint:
    def __init__(self):
        self.text = None
    def configure(self, *, text):
        self.text = text


class CommandPaletteTests(unittest.TestCase):
    def test_catalog_is_grouped_unique_and_inert(self):
        titles = [title for title, commands in cp.GROUPS]
        self.assertEqual(titles, ["AI & Models", "Coding & Projects",
                                  "PC & Research", "Help & Settings"])
        self.assertEqual(len(cp.COMMANDS), len(set(cp.COMMANDS)))
        self.assertIn("/project review", cp.COMMANDS)
        self.assertIn("/engine use ", cp.COMMANDS)
        self.assertIn("/stop", cp.COMMANDS)

    def test_single_completion(self):
        tab = cp.TabCompletion()
        self.assertEqual(tab.complete("/project w"), "/project website ")
        self.assertEqual(tab.complete("/engine sta"), "/engine status")

    def test_ambiguous_prefix_and_cycling(self):
        tab = cp.TabCompletion()
        self.assertEqual(tab.complete("/engine"), "/engine ")
        first = tab.complete("/engine ")
        self.assertEqual(first, "/engine status")
        self.assertEqual(tab.complete(first), "/engine list")
        self.assertEqual(tab.complete("/engine list"), "/engine use ")
        self.assertEqual(tab.complete("/engine use ", reverse=True), "/engine list")

    def test_shift_tab_reverse(self):
        tab = cp.TabCompletion()
        self.assertEqual(tab.complete("/engine ", reverse=True), "/engine start")
        self.assertEqual(tab.complete("/engine start", reverse=True), "/engine use ")

    def test_no_autocomplete_freeform_text_or_arguments(self):
        tab = cp.TabCompletion()
        for text in ("Tell me a story", "create a website", "/engine use qwen3:4b",
                     "/project website create a game", "/do open Notepad and type Hello"):
            with self.subTest(text=text):
                self.assertIsNone(tab.complete(text))

    def test_no_implicit_dispatch_when_menu_shortcut_selected(self):
        e = FakeEntry()
        h = FakeHint()
        controller = cp.EntryController(e, h)
        controller.insert("/project approve")
        self.assertTrue(e.focused)
        self.assertEqual(e.text, "/project approve")
        self.assertEqual(e.deleted, 1)
        self.assertIn("TAB", h.text)
        # No execute/send handlers exist in the palette controller.
        self.assertFalse(hasattr(controller, "dispatch"))
        self.assertFalse(hasattr(controller, "send"))
        with self.assertRaises(ValueError):
            controller.insert("/execute shell --danger")

    def test_tab_event_edits_existing_input_but_does_not_send(self):
        e = FakeEntry()
        h = FakeHint()
        cp.EntryController(e, h)
        e.text, e.cursor = "/proje", 6
        self.assertEqual(e.bindings["<Tab>"](None), "break")
        self.assertEqual(e.text, "/project ")
        self.assertEqual(e.bindings["<Tab>"](None), "break")
        self.assertEqual(e.text, "/project website ")
        self.assertIn("<Shift-Tab>", e.bindings)

    def test_mid_entry_focus_unchanged(self):
        e = FakeEntry()
        h = FakeHint()
        cp.EntryController(e, h)
        e.text, e.cursor = "/engine st", 4
        self.assertIsNone(e.bindings["<Tab>"](None))
        self.assertEqual(e.text, "/engine st")

    def test_partial_help_and_cycling_with_multiple_choices(self):
        tab = cp.TabCompletion()
        self.assertIn("TAB", tab.suggestion("/project"))
        self.assertEqual(tab.suggestion("ordinary chat")[:3], "TAB")
        self.assertEqual(tab.complete("/foobar"), None)
        self.assertEqual(tab.complete("/engine st"), "/engine status")

    def test_legacy_entry_keeps_enter_to_send(self):
        e = FakeEntry()
        h = FakeHint()
        e.bind("<Return>", lambda event: "send")
        cp.EntryController(e, h)
        self.assertEqual(e.bindings["<Return>"](None), "send")


if __name__ == "__main__":
    unittest.main()
