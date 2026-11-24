"""Per-Falcon-reply copy tests: literal text, per-link identity and no auto-copy."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import message_copy


class FakeRoot:
    def __init__(self):
        self.contents = None
        self.clears = 0
        self.update_count = 0
        self.scheduled = []
    def clipboard_clear(self):
        self.clears += 1
        self.contents = ""
    def clipboard_append(self, value):
        self.contents += value
    def update_idletasks(self):
        self.update_count += 1
    def after(self, ms, callback):
        self.scheduled.append((ms, callback))


class FakeText:
    def __init__(self):
        self.inserts = []
        self.bindings = {}
        self.configs = {}
        self.cursor = None
    def insert(self, index, value, tags):
        self.inserts.append((index, value, tags))
    def tag_configure(self, name, **kwargs):
        self.configs[name] = kwargs
    def tag_bind(self, name, event, handler):
        self.bindings[(name, event)] = handler
    def configure(self, **kwargs):
        self.cursor = kwargs.get("cursor", self.cursor)


class ReplyCopyTests(unittest.TestCase):
    def test_exact_payload_and_click_only(self):
        root, text = FakeRoot(), FakeText()
        reply = 'Hello\n\n    print("🦅 Falcon")\n  End & code: <html>\t\n'
        tag = message_copy.attach_copy_reply(text, root, reply)
        self.assertIsNone(root.contents)
        self.assertEqual(root.clears, 0)
        self.assertEqual(len(text.inserts), 1)
        self.assertIn("Copy reply", text.inserts[0][1])
        text.bindings[(tag, "<Button-1>")]()
        self.assertEqual(root.contents, reply)
        self.assertEqual(root.clears, 1)
        self.assertEqual(root.update_count, 1)
        self.assertEqual(text.configs[tag]["foreground"], "#69e6bc")
        self.assertEqual(root.scheduled[0][0], 1100)
        root.scheduled[0][1]()
        self.assertEqual(text.configs[tag]["foreground"], "#a884ff")

    def test_different_messages_copy_their_own_text(self):
        root, text = FakeRoot(), FakeText()
        first = message_copy.attach_copy_reply(text, root, "FIRST\nanswer")
        second = message_copy.attach_copy_reply(text, root, "SECOND\nanswer")
        self.assertNotEqual(first, second)
        text.bindings[(second, "<Button-1>")]()
        self.assertEqual(root.contents, "SECOND\nanswer")
        text.bindings[(first, "<Button-1>")]()
        self.assertEqual(root.contents, "FIRST\nanswer")
        self.assertEqual(root.clears, 2)

    def test_hover_affordance_and_error(self):
        root, text = FakeRoot(), FakeText()
        tag = message_copy.attach_copy_reply(text, root, "Body")
        text.bindings[(tag, "<Enter>")]()
        self.assertEqual(text.cursor, "hand2")
        text.bindings[(tag, "<Leave>")]()
        self.assertEqual(text.cursor, "xterm")
        errors = []
        tag2 = message_copy.attach_copy_reply(text, root, "Different", on_error=errors.append)
        def broken():
            raise OSError("locked clipboard")
        root.clipboard_clear = broken
        self.assertEqual(text.bindings[(tag2, "<Button-1>")](), "break")
        self.assertIn("locked clipboard", errors[0])

    def test_rejects_nonliteral_without_widget_changes(self):
        root, text = FakeRoot(), FakeText()
        with self.assertRaises(TypeError):
            message_copy.attach_copy_reply(text, root, ["not text"])
        self.assertFalse(text.inserts)

    def test_long_reply_preserved(self):
        root, text = FakeRoot(), FakeText()
        answer = "# Project\n" + ("line of Python source = 1234\n" * 5000)
        tag = message_copy.attach_copy_reply(text, root, answer)
        text.bindings[(tag, "<Button-1>")]()
        self.assertEqual(root.contents, answer)


if __name__ == "__main__":
    unittest.main()
