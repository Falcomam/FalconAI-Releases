"""V13.8 candidate: local AI engine safety and error handling."""
import io
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine_manager as engine


class FakeResponse:
    def __init__(self, payload):
        self.buffer = io.BytesIO(payload)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass
    def read(self, count):
        return self.buffer.read(count)


def opener(raw):
    def open_request(request, *, timeout):
        assert request.full_url == engine.API_TAGS
        assert timeout <= 3
        return FakeResponse(raw)
    return open_request


class LocalEngineTests(unittest.TestCase):
    def test_local_only_endpoint(self):
        self.assertEqual(engine.API_TAGS, "http://127.0.0.1:11434/api/tags")

    def test_reports_installed_models(self):
        data = {"models": [{"name": "qwen3:4b"}, {"name": "llama3.2:3b"},
                           {"name": "qwen3:4b"}, {"name": "../../evil"}]}
        result = engine.probe(opener=opener(json.dumps(data).encode()))
        self.assertEqual(result["models"], ("qwen3:4b", "llama3.2:3b"))
        self.assertTrue(result["online"])

    def test_unreachable_is_offline_not_ready(self):
        def offline(request, *, timeout):
            raise ConnectionRefusedError("refused")
        result = engine.probe(opener=offline)
        self.assertFalse(result["online"])
        self.assertIn("refused", result["detail"])

    def test_response_rejects_wrong_shape(self):
        self.assertFalse(engine.probe(opener=opener(b"[]"))["online"])
        self.assertFalse(engine.probe(opener=opener(b'{"models":"none"}'))["online"])

    def test_oversize_response_is_offline(self):
        self.assertFalse(engine.probe(opener=opener(b"x" * (engine.MAX_RESPONSE + 1)))["online"])

    def test_start_requires_explicit_confirmation(self):
        with self.assertRaises(engine.EngineError):
            engine.start_ollama(confirmed=False)

    def test_only_listed_models_can_be_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "engine_model.json"
            with patch.object(engine, "DATA", Path(directory)), patch.object(engine, "CONFIG", config):
                self.assertEqual(engine.saved_chat_model(), "qwen3:4b")
                with self.assertRaises(engine.EngineError):
                    engine.save_chat_model("not-installed:latest", installed_models=("qwen3:4b",))
                with self.assertRaises(engine.EngineError):
                    engine.save_chat_model("some; command", installed_models=("some; command",))
                self.assertFalse(config.exists())
                self.assertEqual(engine.save_chat_model("llama3.2:3b",
                                  installed_models=("qwen3:4b", "llama3.2:3b")), "llama3.2:3b")
                self.assertEqual(engine.saved_chat_model(), "llama3.2:3b")

    def test_saved_bad_setting_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "engine_model.json"
            config.write_text(json.dumps({"chat_model": "hello\nexit"}), encoding="utf-8")
            with patch.object(engine, "CONFIG", config):
                self.assertEqual(engine.saved_chat_model(), "qwen3:4b")


if __name__ == "__main__":
    unittest.main()
