"""Actual Chromium browser smoke tests for the customer FAQ demo.

This is a generated static test project in the ephemeral CI workspace.
No customer data, Fiverr access, production deployment, or paid AI API.
Run only when playwright and its Chromium browser are available.
"""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import customer_faq

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise unittest.SkipTest("Playwright not installed; browser test must run in dedicated CI job")


class FAQBrowserSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        project = customer_faq.make_faq_website(
            "demo_faq", "Northstar Coffee Demo",
            [
                {"question": "What are your opening hours?",
                 "answer": "The demo cafe is open Monday-Friday, 8am-5pm."},
                {"question": "Do you offer delivery?",
                 "answer": "This fictional shop does not offer delivery."},
                {"question": "How do I contact the team?",
                 "answer": "Please use the contact email on this page."},
            ], "demo@example.com")
        for filename, data in project["files"].items():
            (Path(cls.tmp.name) / filename).write_text(data, encoding="utf-8")
        cls.page_url = (Path(cls.tmp.name) / "index.html").as_uri()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.tmp.cleanup()

    def test_desktop_loads_and_links_exist(self):
        page = self.browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(self.page_url)
        self.assertIn("Northstar Coffee Demo", page.title())
        self.assertEqual(page.locator("#faqs details").count(), 3)
        self.assertEqual(page.locator("a[href='#assistant']").count(), 2)
        self.assertTrue(page.locator("a[href='mailto:demo@example.com']").is_visible())
        page.locator("summary").first.click()
        self.assertTrue(page.get_by_text(
            "The demo cafe is open Monday-Friday, 8am-5pm.").first.is_visible())
        self.assertEqual(errors, [])
        page.close()

    def test_chat_answers_known_facts_and_hands_off_unknown(self):
        page = self.browser.new_page(viewport={"width": 1200, "height": 800})
        page.goto(self.page_url)
        page.locator("#question").fill("What are your opening hours?")
        page.get_by_role("button", name="Ask").click()
        self.assertIn("Monday-Friday, 8am-5pm", page.locator("#transcript").inner_text())
        page.locator("#question").fill("What is the secret discount code?")
        page.get_by_role("button", name="Ask").click()
        self.assertIn("I don't have a verified answer", page.locator("#transcript").inner_text())
        self.assertIn("demo@example.com", page.locator("#transcript").inner_text())
        page.close()

    def test_mobile_viewport_has_no_horizontal_overflow(self):
        page = self.browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(self.page_url)
        doc_width = page.evaluate("document.documentElement.scrollWidth")
        self.assertLessEqual(doc_width, 391)
        self.assertTrue(page.get_by_role("heading", name="Ask our FAQ assistant").is_visible())
        self.assertTrue(page.get_by_role("button", name="Ask").is_visible())
        page.close()


if __name__ == "__main__":
    unittest.main()
