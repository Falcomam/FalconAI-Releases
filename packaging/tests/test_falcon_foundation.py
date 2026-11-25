"""Falcon V14 architecture foundation: honest capability and no-side-effect tests."""
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import falcon_foundation as foundation
import developer_chat


class FoundationTests(unittest.TestCase):
    def test_version_and_unique_complete_capability_catalog(self):
        self.assertEqual(foundation.VERSION, "14.0.0")
        self.assertTrue(foundation.check_contract())
        self.assertEqual(len(foundation.BY_KEY), len(foundation.CAPABILITIES))
        for item in foundation.CAPABILITIES:
            self.assertIn(item.state, foundation.STATUS)

    def test_not_yet_built_features_never_claim_available(self):
        for key in ("browser_visual_critic", "isolated_project_tests",
                    "fabric_mod_builds", "autonomous_app_install"):
            item = foundation.BY_KEY[key]
            self.assertEqual(item.state, "planned")

    def test_coding_and_gaming_are_distinct(self):
        self.assertEqual(foundation.BY_KEY["gaming_mode"].state, "available")
        self.assertEqual(foundation.BY_KEY["coding_model"].state, "available")
        self.assertEqual(foundation.BY_KEY["self_improvement"].state, "limited")

    def test_read_only_summary_keeps_uncertainty(self):
        summary = foundation.render_status(gaming=True, coding_model="qwen2.5-coder:7b")
        self.assertIn("FALCON FOUNDATION V14.0.0", summary)
        self.assertIn("Saved Gaming Mode: ON", summary)
        self.assertIn("installation not checked", summary)
        self.assertIn("Render", "Render")
        self.assertIn("not runtime tests", summary)
        self.assertIn("Nothing was run", summary)

    def test_route_is_same_chat_and_no_unrelated_capture(self):
        self.assertEqual(developer_chat.route("/foundation"), ("foundation", ""))
        self.assertEqual(developer_chat.route("/foundation status"), ("foundation", ""))
        self.assertEqual(developer_chat.route("/capabilities"), ("foundation", ""))
        self.assertIsNone(developer_chat.route("Please make my foundation nice"))

    def test_gaming_mode_does_not_hide_read_only_status(self):
        class FakeApp:
            def __init__(self):
                self.messages=[]
            def append(self, role, value):
                self.messages.append((role, value))
        app=FakeApp()
        chat=developer_chat.ChatFeatures(app)
        with patch.object(developer_chat.gaming_mode, "enabled", return_value=True), \
             patch.object(developer_chat.engine_manager, "saved_coding_model",
                          return_value="qwen2.5-coder:7b"):
            self.assertTrue(chat.dispatch("/foundation status"))
        self.assertIn("Gaming Mode: ON", app.messages[-1][1])
        self.assertIn("PLANNED", app.messages[-1][1])


if __name__ == "__main__":
    unittest.main()
