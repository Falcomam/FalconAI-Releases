"""Offline regression and abuse tests for the free local Money Mode."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import money_mode as money


class MoneyModeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "falcon" / "orders"

    def create(self, service="website"):
        return money.create_order(service, "ExampleClient",
            "Build a professional three-page responsive company website.",
            root=self.root)

    def test_full_owner_workflow_and_persistent_recall(self):
        order = self.create()
        self.assertEqual(order["quote_usd"], None)
        self.assertEqual(order["status"], "new")
        self.assertEqual(len(money.list_orders(root=self.root)), 1)
        saved = money.get_order(order["id"], root=self.root)
        self.assertEqual(saved["brief"], order["brief"])
        self.assertIn("not supplied", money.handle_command("show " + order["id"], root=self.root))
        quoted = money.quote_order(order["id"], "225.50", root=self.root)
        self.assertEqual(quoted["quote_usd"], "225.50")
        self.assertIn("$225.50", money.draft_reply(quoted))
        money.set_status(order["id"], "review", root=self.root)
        self.assertEqual(money.get_order(order["id"], root=self.root)["status"], "review")
        self.assertIn("Nothing was delivered", money.handle_command(
            "status " + order["id"] + " delivered", root=self.root))

    def test_all_services_and_five_inert_handoffs(self):
        for kind in money.ALLOWED_SERVICES:
            order = self.create(kind)
            self.assertEqual(len(order["checklist"]), 4)
            for provider in money.PROVIDERS:
                with self.subTest(kind=kind, provider=provider):
                    data = money.handoff(order["id"], provider, root=self.root)
                    self.assertEqual(data["provider"], provider)
                    self.assertEqual(data["service"], kind)
                    self.assertTrue(data["approval_required_before_external_action"])
                    self.assertNotIn("client_alias", data)
        self.assertEqual(len(money.tool_catalog()), 5)
        tools = money.handle_command("tools", root=self.root)
        self.assertIn("not installed or connected", tools)
        self.assertIn("hustlebot", tools)

    def test_client_reply_does_not_invent_price_or_deadline(self):
        order = self.create("customer_automation")
        draft = money.draft_reply(order)
        self.assertIn("confirm price", draft)
        self.assertIn("confirm the delivery timeline", draft)
        self.assertIn("DRAFT ONLY", draft)
        self.assertNotIn("225", draft)

    def test_invalid_and_secret_inputs_blocked(self):
        for alias, brief in [
            ("A", "A reasonable customer website request"),
            ("Client", "short"),
            ("Client", "Please store api_key=sk-example-super-secret-secret"),
            ("Client", "password: hunter2 for my website"),
        ]:
            with self.subTest(alias=alias, brief=brief):
                with self.assertRaises(money.MoneyError):
                    money.create_order("website", alias, brief, root=self.root)
        self.assertFalse(self.root.exists())

    def test_price_validation_and_no_guessing(self):
        order = self.create()
        for amount in ["-1", "NaN", "Infinity", "9.999", "100000.01", "hello"]:
            with self.subTest(amount=amount):
                with self.assertRaises(money.MoneyError):
                    money.quote_order(order["id"], amount, root=self.root)
        self.assertIsNone(money.get_order(order["id"], root=self.root)["quote_usd"])
        with self.assertRaises(money.MoneyError):
            money.set_status(order["id"], "refunded", root=self.root)

    def test_delete_requires_confirmed_explicit_command(self):
        order = self.create()
        with self.assertRaises(money.MoneyError):
            money.delete_order(order["id"], root=self.root)
        with self.assertRaises(money.MoneyError):
            money.handle_command("forget " + order["id"], root=self.root)
        self.assertEqual(len(money.list_orders(root=self.root)), 1)
        self.assertTrue(money.delete_order(order["id"], confirmed=True, root=self.root))
        self.assertEqual(money.list_orders(root=self.root), ())

    def test_traversal_and_unsupported_tools_refused(self):
        self.create()
        for identifier in ("../private", "C:\\secret", ".", "file:///etc/passwd"):
            with self.subTest(identifier=identifier), self.assertRaises(money.MoneyError):
                money.get_order(identifier, root=self.root)
        with self.assertRaises(money.MoneyError):
            money.handoff(money.list_orders(root=self.root)[0]["id"], "fiverr-bot",
                          root=self.root)

    def test_symlink_to_external_record_rejected(self):
        order = self.create()
        file = self.root / (order["id"] + ".json")
        outside = self.root.parent / "private.txt"
        outside.write_text("NO TOUCH", encoding="utf-8")
        file.unlink()
        try:
            file.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(money.MoneyError):
            money.get_order(order["id"], root=self.root)
        self.assertEqual(outside.read_text(encoding="utf-8"), "NO TOUCH")

    def test_user_chat_command_roundtrip(self):
        response = money.handle_command(
            "new website | Example | Build an accessible four-page website with purple colors",
            root=self.root)
        self.assertIn("Saved local order", response)
        saved = money.list_orders(root=self.root)[0]
        self.assertIn(saved["id"], money.handle_command("list", root=self.root))
        handoff = money.handle_command(
            "handoff " + saved["id"] + " n8n", root=self.root)
        self.assertIn("NOT importable", handoff)
        self.assertEqual(json.loads(handoff.split("\n", 1)[1])["provider"], "n8n")


if __name__ == "__main__":
    unittest.main()
