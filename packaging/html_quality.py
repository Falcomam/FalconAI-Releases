"""Lightweight static HTML gate for Falcon's generated website proposals.

Text-only analysis. No browser execution, network fetching, JavaScript
evaluation, dependencies, or claims of full HTML5 standards conformance.
"""
from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import unquote


class WebsiteQualityError(ValueError):
    """Reject obviously broken or incomplete generated website sources."""


class _Analyzer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = set()
        self.identifiers = set()
        self.fragments = []
        self.charsets = []
        self.titles = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        attr = dict(attrs)
        if tag == "meta" and "charset" in attr:
            self.charsets.append(attr["charset"])
        if tag == "title":
            self._in_title = True
        if attr.get("id"):
            self.identifiers.add(attr["id"])
        href = attr.get("href")
        if isinstance(href, str) and href.startswith("#") and len(href) > 1:
            self.fragments.append(unquote(href[1:]))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.tags.add("/" + tag)
        if tag == "title":
            self._in_title = False

    def handle_data(self, text):
        if self._in_title:
            self.titles.append(text)


def check_website(files):
    """Validate a complete index.html and return optional static review warnings.

    HTMLParser intentionally accepts a lot of invalid markup. Incomplete
    tokens remain in rawdata after feed(), so inspect that *before* close().
    The checker does not claim to validate CSS, JS or rendered page behavior.
    """
    if not isinstance(files, dict):
        raise WebsiteQualityError("Expected project files")
    homepage = next((path for path in files if path.casefold() == "index.html"), None)
    if not homepage:
        raise WebsiteQualityError("Website project needs an index.html homepage")

    warnings = []
    for path, content in files.items():
        if not path.casefold().endswith((".html", ".htm")):
            continue
        checker = _Analyzer()
        try:
            checker.feed(content)
            unfinished = checker.rawdata.strip()
            checker.close()
        except (ValueError, AssertionError) as exc:
            raise WebsiteQualityError(f"Could not parse {path}: {str(exc)[:120]}") from exc
        if unfinished and ("<" in unfinished):
            raise WebsiteQualityError(
                f"{path} has an incomplete HTML tag near {unfinished[:60]!r}. "
                "Fix the source and regenerate the proposal."
            )
        if path == homepage:
            required = ("html", "head", "body")
            missing = [tag for tag in required
                       if tag not in checker.tags or "/" + tag not in checker.tags]
            if missing:
                raise WebsiteQualityError(
                    "index.html needs complete html, head and body elements: missing "
                    + ", ".join(missing)
                )
            if "title" not in checker.tags or "/title" not in checker.tags \
                    or not "".join(checker.titles).strip():
                raise WebsiteQualityError("index.html needs a nonempty <title>")
            if not any(isinstance(value, str) and value.casefold() == "utf-8"
                       for value in checker.charsets):
                raise WebsiteQualityError(
                    'index.html needs a complete <meta charset="UTF-8"> declaration'
                )

        for fragment in checker.fragments:
            if fragment not in checker.identifiers:
                warnings.append(
                    f"{path}: internal link #{fragment} has no matching element id"
                )
    return warnings
