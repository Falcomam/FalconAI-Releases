"""Offline mocked tests for Falcon's no-paid-key research foundation."""
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import public_research as research


class FakeResponse:
    def __init__(self, value, redirect=None):
        self.body = io.BytesIO(json.dumps(value).encode("utf-8"))
        self.redirect = redirect or research.API_URL
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return None
    def geturl(self):
        return self.redirect
    def read(self, length):
        return self.body.read(length)


class ResearchTests(unittest.TestCase):
    def test_search_returns_grounded_public_urls(self):
        queries = []
        def open_request(request, *, timeout):
            queries.append(request.full_url)
            self.assertLessEqual(timeout, 8)
            return FakeResponse({"query": {"search": [
                {"title": "Peregrine falcon", "pageid": 123},
                {"title": "Bad", "pageid": -9},
            ]}})
        results = research.search_public_encyclopedia(
            "peregrine falcon", opener=open_request)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://en.wikipedia.org/?curid=123")
        self.assertIn("srsearch=peregrine+falcon", queries[0])
        self.assertTrue(queries[0].startswith(research.API_URL))

    def test_article_extract_is_bounded(self):
        def open_request(request, *, timeout):
            return FakeResponse({"query": {"pages": [{
                "title": "Peregrine falcon", "pageid": 123,
                "extract": "a" * 3000}]}})
        result = research.read_public_article(123, opener=open_request)
        self.assertEqual(len(result["extract"]), research.MAX_EXTRACT_LENGTH)
        self.assertTrue(result["truncated"])

    def test_untrusted_host_redirection_rejected(self):
        def open_request(request, *, timeout):
            return FakeResponse({}, redirect="https://example.org/redirect")
        with self.assertRaises(research.ResearchError):
            research.search_public_encyclopedia("Falcon", opener=open_request)

    def test_bad_queries_and_ids_never_make_network_calls(self):
        def refuse(*args, **kwargs):
            raise AssertionError("Network should not be called")
        for query in ("", "x", "x" * 181, None):
            with self.assertRaises(research.ResearchError):
                research.search_public_encyclopedia(query, opener=refuse)
        for value in (-1, 0, 3.14, "3", True):
            with self.assertRaises(research.ResearchError):
                research.read_public_article(value, opener=refuse)

    def test_malformed_results_fail_closed(self):
        def broken(request, *, timeout):
            return FakeResponse({"query": {"search": "oops"}})
        with self.assertRaises(research.ResearchError):
            research.search_public_encyclopedia("Peregrine falcon", opener=broken)


if __name__ == "__main__":
    unittest.main()
