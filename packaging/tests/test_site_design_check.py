"""Falcon website design benchmark #001: static baseline diagnostics only.

The minimal sample reproduces the source structure from the first 2026-11-24
LostFalcon website test. No screenshots, private paths or browser execution.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import site_design_check as design
import developer_workspace as workspace

BASELINE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LostFalcon YouTube Channel</title>
    <style>
        body { background-color: #8a2be2; }
        nav { background-color: #6a0dad; }
        nav a { color: white; text-decoration: none; padding: 10px; }
        section { margin: 20px; }
        h1 { color: white; }
        p { color: #e0e0ff; }
    </style>
</head>
<body>
    <nav><a href="#about">About</a></nav>
    <h1>LostFalcon YouTube Channel</h1>
    <section id="about"><p>Welcome to the LostFalcon YouTube channel!</p></section>
</body></html>
"""

MODERN = """<!doctype html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LostFalcon</title><style>
body { background: #120c1d; color: #fff; }
.grid { display: grid; gap: 24px; grid-template-columns: repeat(2, 1fr); }
@media (max-width: 700px) { .grid { grid-template-columns: 1fr; } }
</style></head><body>
<header><nav><a href="#home">Home</a><a href="#about">About</a></nav></header>
<main id="home"><h1>LostFalcon Gaming</h1>
<section><h2>Videos</h2><p>Creator highlights</p>
<a href="https://www.youtube.com/">Watch videos</a></section>
<section id="about"><h2>About</h2><p>Gaming and adventures</p></section>
</main><footer>LostFalcon</footer></body></html>
"""


class DesignSignalsTests(unittest.TestCase):
    def test_first_website_is_clearly_flagged_for_review(self):
        warnings = design.inspect({"index.html": BASELINE})
        self.assertGreaterEqual(len(warnings), 4)
        self.assertTrue(any("viewport" in w.lower() for w in warnings))
        self.assertTrue(any("flex/grid" in w.lower() for w in warnings))
        self.assertTrue(any("responsive" in w.lower() for w in warnings))
        self.assertTrue(any("outbound" in w.lower() for w in warnings))

    def test_fuller_responsive_sample_has_no_heuristic_warnings(self):
        self.assertEqual(design.inspect({"index.html": MODERN}), ())

    def test_advisory_only_does_not_block_review_or_write_files(self):
        proposal = {"name": "lostfalcon-website", "kind": "website",
                    "files": {"index.html": BASELINE, "README.md": "Test"}}
        reviewed = workspace.review_proposal(proposal)
        self.assertTrue(reviewed["quality_warnings"])
        self.assertFalse(reviewed["execution_allowed"])
        self.assertEqual(reviewed["file_count"], 2)

    def test_design_check_never_executes_scripts(self):
        html = MODERN.replace("</body>", '<script>throw new Error("do not run")</script></body>')
        self.assertEqual(design.inspect({"index.html": html}), ())


if __name__ == "__main__":
    unittest.main()
