"""Gaming Mode tests: mocked loopback Ollama, no GPU changes or code execution."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gaming_mode as gm


class Reply:
    def __init__(self, payload):
        self._io = io.BytesIO(json.dumps(payload).encode("utf-8"))
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def read(self, count):
        return self._io.read(count)


class GamingModeTests(unittest.TestCase):
    def test_user_consent_persisted_and_reversible(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(gm, "ROOT", root), patch.object(gm, "SETTINGS", root / "gaming_mode.json"):
                self.assertFalse(gm.enabled())
                self.assertTrue(gm.set_enabled(True))
                self.assertTrue(gm.enabled())
                self.assertFalse(gm.set_enabled(False))
                self.assertFalse(gm.enabled())
                (root / "gaming_mode.json").write_text('{"enabled":"yes"}', encoding="utf-8")
                self.assertFalse(gm.enabled())
                with self.assertRaises(gm.GamingModeError):
                    gm.set_enabled(1)

    def test_no_network_for_unknown_url(self):
        with self.assertRaises(gm.GamingModeError):
            gm._local_request("https://example.com", opener=lambda *_a, **_kw: None)

    def test_selective_unload_loaded_falcon_models_only(self):
        requests = []
        loaded = {"qwen3:4b", "qwen2.5-coder:7b", "other-client:3b"}
        def opener(request, *, timeout):
            self.assertLessEqual(timeout, 4)
            requests.append((request.full_url, request.data))
            if request.full_url == gm.LOCAL_PS:
                return Reply({"models": [{"name": model} for model in sorted(loaded)]})
            self.assertEqual(request.full_url, gm.LOCAL_GENERATE)
            payload = json.loads(request.data)
            self.assertEqual(set(payload), {"model", "keep_alive"})
            self.assertEqual(payload["keep_alive"], 0)
            loaded.discard(payload["model"])
            return Reply({"done": True})
        result = gm.unload_falcon_models(
            ("qwen3:4b", "qwen2.5-coder:7b", "qwen2.5vl:3b"), opener=opener)
        self.assertTrue(result["verified"])
        self.assertEqual(len(result["requested"]), 2)
        self.assertEqual(loaded, {"other-client:3b"})
        self.assertEqual(sum(url == gm.LOCAL_GENERATE for url, _ in requests), 2)

    def test_unloaded_models_are_not_started(self):
        calls = []
        def opener(request, *, timeout):
            calls.append(request.full_url)
            return Reply({"models": []})
        result = gm.unload_falcon_models(("qwen3:4b",), opener=opener)
        self.assertTrue(result["verified"])
        self.assertEqual(calls, [gm.LOCAL_PS, gm.LOCAL_PS])

    def test_unload_failure_cannot_claim_success(self):
        calls = []
        def opener(request, *, timeout):
            calls.append(request.full_url)
            if request.full_url == gm.LOCAL_PS:
                return Reply({"models": [{"name": "qwen3:4b"}]})
            raise ConnectionRefusedError("server closed")
        result = gm.unload_falcon_models(("qwen3:4b",), opener=opener)
        self.assertFalse(result["verified"])
        self.assertEqual(result["failed"], ("qwen3:4b",))
        self.assertEqual(result["remaining"], ("qwen3:4b",))

    def test_unsafe_model_and_malformed_ollama_response_rejected(self):
        with self.assertRaises(gm.GamingModeError):
            gm.unload_falcon_models(("bad; command",), opener=lambda *_a, **_kw: None)
        with self.assertRaises(gm.GamingModeError):
            gm.loaded_models(opener=lambda *_a, **_kw: Reply({"models": "bad"}))


if __name__ == "__main__":
    unittest.main()
