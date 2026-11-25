"""Source candidate regression: Money Mode stays within the existing Falcon chat."""
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "build" / "Falcon_Ai_MoneyMode_Candidate"
if not (CANDIDATE / "developer_chat.py").exists():
    raise unittest.SkipTest("Money Mode staged chat candidate is not present")
sys.path.insert(0, str(CANDIDATE.resolve()))
import developer_chat as chat


class DummyApp:
    def __init__(self):
        self.root = types.SimpleNamespace(after=lambda _ms, fn: fn())
        self.busy = False
        self.messages = []
        self.status = None
    def append(self, role, message):
        self.messages.append((role, message))
    def set_status(self, value):
        self.status = value


class MoneyChatIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.app = DummyApp()
        self.features = chat.ChatFeatures(self.app)

    def test_money_route_stays_in_existing_chat(self):
        self.assertEqual(chat.route("/money list"), ("money_mode", "list"))
        self.assertEqual(chat.route("/money seller falconant"),
                         ("money_mode", "seller falconant"))
        self.assertEqual(chat.route("/money faq-demo"), ("money_mode", "faq-demo"))
        with patch.object(chat.money_mode, "handle_command", return_value="done") as work:
            self.assertTrue(self.features.dispatch("/money list"))
        work.assert_called_once_with("list")
        self.assertEqual(self.app.messages[-1], ("Falcon", "done"))

    def test_source_only_faq_demo_uses_normal_review_gate(self):
        self.assertTrue(self.features.dispatch("/money faq-demo"))
        self.assertIsNotNone(self.features.pending)
        self.assertEqual(self.features.pending["plan"]["kind"], "website")
        self.assertFalse(self.features.pending["review"]["execution_allowed"])
        self.assertFalse(self.features.pending["reviewed"])
        self.assertIn("source proposal only", self.app.messages[-1][1])
        self.features.dispatch("/money faq-demo")
        self.assertIn("Review or reject", self.app.messages[-1][1])

    def test_no_money_actions_while_app_busy(self):
        self.app.busy = True
        with patch.object(chat.money_mode, "handle_command") as work:
            self.features.dispatch("/money list")
        work.assert_not_called()
        self.assertIn("busy", self.app.messages[-1][1])


if __name__ == "__main__":
    unittest.main()
