"""Reject visibly broken HTML, warn about missing navigation targets.

No generated HTML or JS is ever executed by these tests.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import html_quality as html

VALID = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<title>LostFalcon</title></head>
<body><nav><a href="#home">Home</a><a href="#about">About</a></nav>
<main id="home"><h1>Falcon</h1></main><section id="about">Hi</section>
</body></html>
"""


class WebsiteValidationTests(unittest.TestCase):
    def test_valid_site_no_warnings(self):
        self.assertEqual(html.check_website({"index.html": VALID}), [])

    def test_real_broken_meta_from_user_test_rejected(self):
        broken = VALID.replace('<meta charset="UTF-8">', '<meta charset="UTF-\n')
        with self.assertRaisesRegex(html.WebsiteQualityError, "incomplete|UTF-8"):
            html.check_website({"index.html": broken})

    def test_missing_required_html_structure(self):
        for page in [
            '<!doctype html><title>Falcon</title>',
            VALID.replace("</head>", ""),
            VALID.replace('<meta charset="UTF-8">', ""),
            VALID.replace("<title>LostFalcon</title>", ""),
            VALID.replace("<title>LostFalcon</title>", "<title></title>"),
            VALID.replace("</body>", ""),
        ]:
            with self.subTest(page=page[:50]), self.assertRaises(html.WebsiteQualityError):
                html.check_website({"index.html": page})

    def test_no_index_html_rejected(self):
        with self.assertRaisesRegex(html.WebsiteQualityError, "index.html"):
            html.check_website({"landing.html": VALID})

    def test_broken_links_reported_but_do_not_execute(self):
        page = VALID.replace('id="about"', 'id="the-team"')
        notices = html.check_website({"index.html": page})
        self.assertTrue(any("#about" in n for n in notices))

    def test_valid_unicode_and_fragment_encoding(self):
        page = VALID.replace('href="#about"', 'href="#about%20us"').replace(
            'id="about"', 'id="about us"').replace("LostFalcon", "LostFalcon 🦅")
        self.assertEqual(html.check_website({"index.html": page}), [])

    def test_unclosed_secondary_html_file_rejected(self):
        files = {"index.html": VALID, "about.html": "<div>About</div><meta charset=\""}
        with self.assertRaisesRegex(html.WebsiteQualityError, "about.html"):
            html.check_website(files)

    def test_does_not_modify_user_file_dictionary(self):
        files = {"index.html": VALID, "style.css": "body { color: purple; }"}
        copied = files.copy()
        html.check_website(files)
        self.assertEqual(copied, files)


if __name__ == "__main__":
    unittest.main()
