"""Offline checks for customer FAQ deliverables with no paid AI or network."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import customer_faq as faq
import developer_workspace as projects

EXAMPLE = [
    {"question": "What are your opening hours?",
     "answer": "We open Monday through Friday, 9 a.m. to 5 p.m."},
    {"question": "Do you offer local delivery?",
     "answer": "Yes, delivery is available within five miles of the store."},
]


class ClientFAQTests(unittest.TestCase):
    def test_generates_complete_source_only_website(self):
        plan = faq.make_faq_website(
            "example_faq", "Example Floral Shop", EXAMPLE, "help@example.com")
        self.assertEqual(plan["kind"], "website")
        self.assertEqual(set(plan["files"]),
                         {"index.html", "styles.css", "app.js", "README.md"})
        self.assertIn("Example Floral Shop", plan["files"]["index.html"])
        self.assertIn("href=\"#assistant\"", plan["files"]["index.html"])
        self.assertIn("href=\"mailto:help@example.com\"", plan["files"]["index.html"])
        review = projects.review_proposal(plan)
        self.assertFalse(review["execution_allowed"])
        self.assertEqual(review["file_count"], 4)
        self.assertFalse(any("internal link #" in message
                             for message in review["quality_warnings"]))

    def test_source_uses_only_facts_supplied_by_client(self):
        plan = faq.make_faq_website(
            "flowers", "Flower Shop", EXAMPLE, "support@example.com")
        js = plan["files"]["app.js"]
        self.assertIn("Monday through Friday", js)
        self.assertIn("five miles", js)
        self.assertIn("I don", js)
        self.assertIn("HANDOFF", js)
        self.assertIn("textContent = text", js)
        self.assertNotIn("fetch(", js)
        self.assertNotIn("localStorage", js)
        self.assertNotIn("api.openai.com", js)

    def test_untrusted_content_cannot_create_html_or_script_tags(self):
        attack = [
            {"question": "<script>alert('x')</script>",
             "answer": "</script><img src=x onerror=alert(1)>"},
            {"question": "What are your business hours?",
             "answer": "We will confirm by email."},
        ]
        plan = faq.make_faq_website("shop", "<Acme> & Co", attack,
                                    "help@example.com")
        html = plan["files"]["index.html"]
        js = plan["files"]["app.js"]
        self.assertIn("&lt;Acme&gt; &amp; Co", html)
        self.assertNotIn("<script>alert", html)
        self.assertNotIn("</script><img", js)
        self.assertIn(r"\u003c/script\u003e", js)
        self.assertIn("textContent", js)
        projects.review_proposal(plan)

    def test_duplicate_and_invalid_faqs_fail_closed(self):
        for rows in ([], EXAMPLE[:1], EXAMPLE * 16,
                     [EXAMPLE[0], dict(EXAMPLE[0])],
                     [{"question": "yes", "answer": "okay"}, {"question": "", "answer": "no"}],
                     [{"question": "a", "answer": "b", "secret": "x"}, EXAMPLE[1]]):
            with self.subTest(rows=str(rows)[:50]), self.assertRaises(faq.FAQError):
                faq.make_faq_website("shop", "Shop", rows, "help@example.com")
        for email in ("", "javascript:alert(1)", "mail@example.com?subject=spam"):
            with self.subTest(email=email), self.assertRaises(faq.FAQError):
                faq.make_faq_website("shop", "Shop", EXAMPLE, email)

    def test_no_install_or_browser_control_on_generation(self):
        plan = faq.make_faq_website("shop", "Shop", EXAMPLE, "help@example.com")
        self.assertEqual(len(plan["files"]), 4)
        # Pure plan generation returns UTF-8 text; application controls the
        # review/approval process before any workspace writes.
        self.assertTrue(all(isinstance(v, str) for v in plan["files"].values()))


if __name__ == "__main__":
    unittest.main()
