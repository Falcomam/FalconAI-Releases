"""Advisory, deterministic design-review signals for generated HTML websites.

This is not a browser/screenshot test and does not claim to measure aesthetics.
It supplements HTML syntax checks and makes the first LostFalcon minimal-site
failure visible before users approve a proposal. Warnings never authorize
execution and never silently rewrite source.
"""
from __future__ import annotations

from html.parser import HTMLParser
import re


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.anchors = []
        self.meta_viewport = False
        self.css_parts = []
        self._style_depth = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append(tag)
        if tag == "meta" and str(values.get("name", "")).casefold() == "viewport":
            self.meta_viewport = bool(values.get("content"))
        if tag == "a" and values.get("href"):
            self.anchors.append(str(values["href"]))
        if tag == "style":
            self._style_depth += 1

    def handle_endtag(self, tag):
        if tag == "style" and self._style_depth:
            self._style_depth -= 1

    def handle_data(self, data):
        if self._style_depth:
            self.css_parts.append(data)


def inspect(files):
    """Return advisory warnings from visible, static source only.

    A static site can be high quality with few features; these are prompts for
    human review, not pass/fail criteria. No network, CSS engine, or JS executes.
    """
    if not isinstance(files, dict) or not isinstance(files.get("index.html"), str):
        return ("Homepage source unavailable for design review",)
    html = files["index.html"]
    page = _Page()
    page.feed(html)
    page.close()
    css = "\n".join(page.css_parts + [
        value for path, value in files.items()
        if isinstance(path, str) and path.lower().endswith(".css")
        and isinstance(value, str)
    ]).casefold()
    warnings = []

    if not page.meta_viewport:
        warnings.append("Mobile viewport meta tag missing; layout may be scaled on phones")
    if not re.search(r"display\s*:\s*(?:grid|flex|inline-grid|inline-flex)\b", css):
        warnings.append("No CSS flex/grid layout detected; review whether design is overly basic")
    if not any(marker in css for marker in ("@media", "@container", "clamp(", "minmax(")):
        warnings.append("No responsive CSS adaptation detected; manually check mobile layout")
    if "main" not in page.tags:
        warnings.append("No main content landmark; review page structure and accessibility")
    if page.tags.count("section") < 2 and page.tags.count("article") < 2:
        warnings.append("Only minimal content grouping detected; compare against the requested page sections")
    if not any(href.startswith(("https://", "http://")) for href in page.anchors):
        warnings.append("No outbound page link detected; verify any requested creator/video destination")
    return tuple(warnings)
