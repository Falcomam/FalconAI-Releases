"""Free public research foundation for Falcon AI.

This module retrieves bounded, attributed public encyclopedia search results.
It has no general network/PC-control privileges and no paid API. Wikipedia is
a starting source, not a substitute for full multi-source web research.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler

API_URL = "https://en.wikipedia.org/w/api.php"
MAX_RESPONSE_BYTES = 256_000
MAX_QUERY_LENGTH = 180
MAX_RESULTS = 5
MAX_EXTRACT_LENGTH = 1800
TITLE_RE = re.compile(r"^[^\x00-\x1f\x7f<>]{1,250}$")


class ResearchError(ValueError):
    pass


def _query_api(params, *, opener=None):
    """Fetch JSON from one fixed public host; no redirects to other hosts."""
    if opener is None:
        # Explicitly bypass environment/system proxies; use ordinary HTTPS.
        opener = build_opener(ProxyHandler({})).open
    arguments = {"format": "json", "formatversion": "2", **params}
    url = API_URL + "?" + urlencode(arguments)
    request = Request(url, headers={
        "Accept": "application/json", "User-Agent": "FalconAI-Research/0.1 (public Wikipedia research)"})
    try:
        with opener(request, timeout=8) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else API_URL
            if final_url.split("?", 1)[0] != API_URL:
                raise ResearchError("Research endpoint redirected outside its allowed host")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ResearchError("Research reply exceeds size limit")
        payload = json.loads(raw)
    except (OSError, TimeoutError, ValueError, TypeError) as exc:
        raise ResearchError("Could not retrieve public research results") from exc
    if not isinstance(payload, dict):
        raise ResearchError("Unexpected research response")
    return payload


def search_public_encyclopedia(query, *, limit=5, opener=None):
    """Search publicly accessible articles; return trustworthy *links*, not assertions."""
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= MAX_QUERY_LENGTH:
        raise ResearchError("Provide a 2–180 character research question")
    if type(limit) is not int or not 1 <= limit <= MAX_RESULTS:
        raise ResearchError("Research result limit must be 1–5")
    payload = _query_api({
        "action": "query", "list": "search", "srsearch": query.strip(),
        "srnamespace": "0", "srlimit": str(limit),
        "srprop": "", "utf8": "1",
    }, opener=opener)
    matches = payload.get("query", {}).get("search", [])
    if not isinstance(matches, list):
        raise ResearchError("Invalid research result list")
    output = []
    for item in matches[:limit]:
        if not isinstance(item, dict):
            continue
        title, pageid = item.get("title"), item.get("pageid")
        if not isinstance(title, str) or not TITLE_RE.fullmatch(title):
            continue
        if type(pageid) is not int or pageid <= 0:
            continue
        output.append({"title": title, "pageid": pageid,
                       "url": "https://en.wikipedia.org/?curid=" + str(pageid),
                       "source": "Wikipedia"})
    return tuple(output)


def read_public_article(pageid, *, opener=None):
    """Read a bounded plaintext extract of an already-discovered article ID."""
    if type(pageid) is not int or not 1 <= pageid <= 2_147_483_647:
        raise ResearchError("Invalid article identifier")
    payload = _query_api({
        "action": "query", "prop": "extracts", "explaintext": "1",
        "exsectionformat": "plain", "exintro": "1",
        "pageids": str(pageid),
    }, opener=opener)
    pages = payload.get("query", {}).get("pages", [])
    if not isinstance(pages, list) or len(pages) != 1:
        raise ResearchError("Invalid article response")
    article = pages[0]
    if not isinstance(article, dict) or article.get("pageid") != pageid:
        raise ResearchError("Article not found")
    title, extract = article.get("title"), article.get("extract")
    if not isinstance(title, str) or not TITLE_RE.fullmatch(title) or not isinstance(extract, str):
        raise ResearchError("Article text unavailable")
    return {"title": title, "pageid": pageid, "source": "Wikipedia",
            "url": "https://en.wikipedia.org/?curid=" + str(pageid),
            "extract": extract[:MAX_EXTRACT_LENGTH], "truncated": len(extract) > MAX_EXTRACT_LENGTH}


def research(query, *, opener=None):
    """Collect up to three attributed source excerpts; never execute page instructions."""
    found = search_public_encyclopedia(query, limit=3, opener=opener)
    sources = []
    for item in found:
        try:
            sources.append(read_public_article(item["pageid"], opener=opener))
        except ResearchError:
            continue
    return {"question": query.strip(), "sources": tuple(sources),
            "limitations": "Encyclopedia-only source collection; verify with primary/current sources for time-sensitive questions. This is not unrestricted web browsing."}
