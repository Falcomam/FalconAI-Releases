"""Tests for real local workflow POSTs and read-only OpenHands discovery."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import money_integrations as connectors


class FakeResponse:
    status = 200
    def __init__(self, raw=b"{}"):
        self.raw = io.BytesIO(raw)
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        pass
    def read(self, limit):
        return self.raw.read(limit)


ORDER = {
    "id": "fm_0123456789abcd",
    "service": "customer_automation",
    "brief": "Build a safe demo customer support workflow with handoff.",
    "client_alias": "PRIVATE CUSTOMER",
    "quote_usd": "175.00",
}


class LocalMoneyIntegrationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "integrations"

    def test_n8n_real_webhook_post_after_explicit_user_action(self):
        url = "http://127.0.0.1:5678/webhook-test/abcd-1234"
        connectors.set_endpoint("n8n", url, folder=self.folder)
        seen = []
        def opener(request, *, timeout):
            seen.append((request, timeout))
            return FakeResponse()
        with self.assertRaises(connectors.ConnectorError):
            connectors.invoke_workflow("n8n", ORDER, folder=self.folder,
                                       opener=opener)
        self.assertEqual(seen, [])
        output = connectors.invoke_workflow("n8n", ORDER, confirmed=True,
                                            folder=self.folder, opener=opener)
        self.assertEqual(output["status"], 200)
        request, timeout = seen[0]
        self.assertEqual(request.full_url, url)
        self.assertEqual(request.get_method(), "POST")
        self.assertLessEqual(timeout, 8)
        payload = json.loads(request.data)
        self.assertEqual(payload["service"], "customer_automation")
        self.assertNotIn("client_alias", payload)
        self.assertNotIn("quote_usd", payload)
        self.assertTrue(payload["owner_review_required_before_external_delivery"])
        self.assertIn("NOT verified", output["detail"])

    def test_activepieces_real_webhook_can_be_selected(self):
        url = "http://127.0.0.1:8080/api/v1/webhooks/abcde123/sync"
        connectors.set_endpoint("activepieces", url, folder=self.folder)
        self.assertEqual(connectors.load_endpoints(folder=self.folder)["activepieces"], url)
        called = Mock(return_value=FakeResponse())
        result = connectors.invoke_workflow("activepieces", ORDER,
                                             confirmed=True, folder=self.folder,
                                             opener=called)
        self.assertEqual(result["provider"], "activepieces")
        self.assertEqual(called.call_count, 1)

    def test_no_arbitrary_host_protocol_url_paths_or_credentials(self):
        invalid = [
            "https://127.0.0.1:5678/webhook/valid123",
            "http://localhost:5678/webhook/valid123",
            "http://127.0.0.2:5678/webhook/valid123",
            "http://evil.com:5678/webhook/valid123",
            "http://127.0.0.1:5678/api/credentials",
            "http://user:pass@127.0.0.1:5678/webhook/valid123",
            "http://127.0.0.1:5678/webhook/valid123?callback=evil",
            "http://127.0.0.1:5678/webhook/valid123#frag",
            "file:///etc/passwd", "http://127.0.0.1:0/webhook/valid123",
            "http://127.0.0.1:99999/webhook/valid123",
            "http://127.0.0.1:5678/webhook/../../private",
        ]
        for value in invalid:
            with self.subTest(url=value), self.assertRaises(connectors.ConnectorError):
                connectors.set_endpoint("n8n", value, folder=self.folder)
        self.assertFalse(self.folder.exists())

    def test_config_roundtrip_and_disconnect(self):
        connectors.set_endpoint("n8n", "http://127.0.0.1:5678/webhook/abcde",
                                folder=self.folder)
        connectors.set_endpoint("activepieces",
                                "http://127.0.0.1:8080/api/v1/webhooks/12345",
                                folder=self.folder)
        self.assertEqual(len(connectors.load_endpoints(folder=self.folder)), 2)
        self.assertTrue(connectors.remove_endpoint("n8n", folder=self.folder))
        self.assertFalse(connectors.remove_endpoint("n8n", folder=self.folder))
        self.assertEqual(set(connectors.load_endpoints(folder=self.folder)),
                         {"activepieces"})

    def test_webhook_does_not_follow_ambient_proxies(self):
        import urllib.request
        opener = connectors._opener()
        self.assertIsNotNone(opener)
        self.assertFalse(any(isinstance(x, urllib.request.ProxyHandler)
                             and x.proxies for x in opener.handlers))
        self.assertTrue(any(isinstance(x, connectors._NoRedirect)
                            for x in opener.handlers))

    def test_untrusted_order_data_must_be_valid(self):
        connectors.set_endpoint("n8n", "http://127.0.0.1:5678/webhook/abcde",
                                folder=self.folder)
        called = Mock(return_value=FakeResponse())
        invalid = [
            {**ORDER, "id": "../private"},
            {**ORDER, "service": "shell"},
            {**ORDER, "brief": "X"},
            {**ORDER, "brief": "x" * 1501},
        ]
        for order in invalid:
            with self.subTest(order=order["id"]), self.assertRaises(connectors.ConnectorError):
                connectors.invoke_workflow("n8n", order, confirmed=True,
                                           folder=self.folder, opener=called)
        called.assert_not_called()

    def test_openhands_health_probe_only(self):
        seen = []
        def fake(request, *, timeout):
            seen.append(request)
            return FakeResponse()
        output = connectors.probe_openhands(opener=fake)
        self.assertTrue(output["online"])
        self.assertEqual(seen[0].get_method(), "GET")
        self.assertEqual(seen[0].full_url, "http://127.0.0.1:8000/health")
        self.assertIn("not authorized", output["reason"])
        self.assertFalse(connectors.probe_openhands(
            opener=lambda req, **kwargs: (_ for _ in ()).throw(OSError("offline")))["online"])


if __name__ == "__main__":
    unittest.main()
