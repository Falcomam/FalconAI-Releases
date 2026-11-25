"""Payhip self-guided agent security and browser integration tests."""
import io
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import payhip_browser_agent as agent


class Response:
    url = agent.OFFICIAL_GUIDE
    def __init__(self, content):
        self.buf = io.BytesIO(content)
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        self.buf.close()
    def read(self, length):
        return self.buf.read(length)


class ResearchAndFileTests(unittest.TestCase):
    def test_research_reads_only_official_payhip_help(self):
        urls = []
        def fake_open(req, timeout):
            urls.append(req.full_url)
            return Response(
                b"<html><ol><li>Upload your product file</li>"
                b"<li>Enter a price and product name</li>"
                b"<li>Choose invisible visibility</li></ol></html>")
        result = agent.research_official_steps(opener=fake_open)
        self.assertTrue(result["online"])
        self.assertEqual(urls, [agent.OFFICIAL_GUIDE])
        self.assertEqual(len(result["steps"]), 3)

    def test_missing_help_uses_bounded_offline_fallback(self):
        def offline(req, timeout):
            raise OSError("network offline")
        result = agent.research_official_steps(opener=offline)
        self.assertFalse(result["online"])
        self.assertEqual(result["steps"], ())

    def test_cross_host_help_redirect_is_blocked(self):
        class WrongResponse(Response):
            url = "https://example.com/instructions"
        with self.assertRaises(agent.BrowserAgentError):
            agent.research_official_steps(
                opener=lambda req, timeout: WrongResponse(b"evil"))

    def _assets(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name)
        with ZipFile(folder / agent.ZIP_FILENAME, "w") as z:
            for i in range(3):
                z.writestr(f"{i+1:02d}.png", b"\x89PNG\r\n\x1a\nhello")
        (folder / agent.COVER_FILENAME).write_bytes(b"\x89PNG\r\n\x1a\nsomepng")
        return folder

    def test_exact_known_zip_and_cover_allowed(self):
        folder = self._assets()
        files = agent.find_first_product_assets(download_dir=folder)
        self.assertEqual(files["zip"].name, agent.ZIP_FILENAME)
        self.assertEqual(files["cover"].name, agent.COVER_FILENAME)

    def test_missing_zip_blocked(self):
        folder = self._assets()
        (folder / agent.ZIP_FILENAME).unlink()
        with self.assertRaisesRegex(agent.BrowserAgentError, "Required product file"):
            agent.find_first_product_assets(download_dir=folder)

    def test_incorrect_cover_blocked(self):
        folder = self._assets()
        (folder / agent.COVER_FILENAME).write_bytes(b"not-an-image")
        with self.assertRaisesRegex(agent.BrowserAgentError, "not a PNG"):
            agent.find_first_product_assets(download_dir=folder)

    def test_zip_must_contain_three_pngs(self):
        folder = self._assets()
        with ZipFile(folder / agent.ZIP_FILENAME, "w") as z:
            z.writestr("onlyone.png", b"test")
        with self.assertRaisesRegex(agent.BrowserAgentError, "exactly three PNGs"):
            agent.find_first_product_assets(download_dir=folder)

    def test_zip_traversal_blocked(self):
        folder = self._assets()
        with ZipFile(folder / agent.ZIP_FILENAME, "w") as z:
            for i in range(3):
                z.writestr(f"../evil_{i}.png", b"test")
        with self.assertRaisesRegex(agent.BrowserAgentError, "unsafe path"):
            agent.find_first_product_assets(download_dir=folder)

    def test_cancel_stops_before_action(self):
        cancelled = threading.Event()
        cancelled.set()
        with self.assertRaises(agent.BrowserAgentCancelled):
            agent._cancel(cancelled)


class BrowserSmoke(unittest.TestCase):
    """Run with FALCON_PAYHIP_BROWSER_SMOKE=1 and an installed Chromium engine."""

    def test_real_chromium_offline_simulated_payhip(self):
        import os
        if os.getenv("FALCON_PAYHIP_BROWSER_SMOKE") != "1":
            self.skipTest("Optional real Chromium browser test not requested")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright not installed")
        test = ResearchAndFileTests()
        test.setUp()
        assets = test._assets()
        product = {
            "title": "Midnight Falcon — Purple Gaming Wallpapers Vol. 1",
            "suggested_price_usd": "4.99",
            "description": "Three original purple falcon gaming backgrounds",
        }
        dashboard = ("<!doctype html><html><body>"
                     "<a href='/products'>Products</a></body></html>")
        products = ("<!doctype html><html><body>"
                    "<a href='/product/add'>Add new product</a></body></html>")
        choice = ("<!doctype html><html><body>"
                  "<a href='/product/new/digital'>Digital Product</a></body></html>")
        form = """<!doctype html><html><body>
        <form id="product" onsubmit="event.preventDefault();window.location.assign(\'/product/edit/mock\')">
         <label>Upload product file <input name="productFile" type="file" accept=".zip"></label>
         <label>Product title <input name="productName" type="text"></label>
         <label>Price <input type="number" name="price"></label>
         <label>Cover image <input name="coverImage" type="file" accept="image/png"></label>
         <label>Description <textarea name="description"></textarea></label>
         <label><input type="radio" name="visibility" value="Visible" checked>Visible</label>
         <label><input type="radio" name="visibility" value="Invisible">Invisible</label>
         <button type="submit">Add Product</button>
        </form></body></html>"""
        saved = ("<!doctype html><html><body>"
                 "<h1>Product created privately</h1></body></html>")
        pages = {"/dashboard": dashboard, "/products": products,
                 "/product/add": choice, "/product/new/digital": form,
                 "/product/edit/mock": saved}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            try:
                page = browser.new_page()
                page.route("https://payhip.com/**", lambda route: route.fulfill(
                    status=200, content_type="text/html",
                    body=pages.get(__import__("urllib.parse").parse.urlsplit(
                        route.request.url).path, "not found")
                ))
                result = agent.fill_invisible_listing(
                    page, product,
                    {"zip": assets / agent.ZIP_FILENAME,
                     "cover": assets / agent.COVER_FILENAME},
                    requester=None)
                self.assertEqual(result["status"], "invisible_product_saved_in_browser")
                from urllib.parse import urlsplit
                self.assertEqual(urlsplit(result["url"]).path, "/product/edit/mock")
            finally:
                browser.close()

    def test_never_saves_without_invisible_visibility(self):
        import os
        if os.getenv("FALCON_PAYHIP_BROWSER_SMOKE") != "1":
            self.skipTest("Optional real Chromium browser test not requested")
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            try:
                page = browser.new_page()
                page.goto("about:blank")
                page.set_content("<html><body><button>Add Product</button>"
                                 "<label><input type='radio' name='visibility' "
                                 "checked>Visible</label></body></html>")
                with self.assertRaises(agent.BrowserAgentError):
                    agent._select_invisible(page)
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
