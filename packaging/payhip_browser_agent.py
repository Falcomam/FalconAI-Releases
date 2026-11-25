"""Falcon Payhip browser agent: research, observe, click, upload, verify.

The user starts one bounded task using /money payhip autopilot. The agent
uses a separate local Chrome profile and the user's own Payhip login. It
reads the official Payhip help article; adapts to changing buttons with
Playwright semantic locators and optional LOCAL Ollama vision. It can create
a Payhip product only with verified Invisible visibility. It never makes
public listings, opens billing settings, touches money, bypasses login, or
follows instructions from webpages. No browser credentials leave the PC.

Requires optional Playwright, and Google Chrome on Windows. Normal Falcon
chat does not depend on Playwright being installed.
"""
from __future__ import annotations

import base64
import html
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import stat
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request, ProxyHandler, HTTPSHandler, build_opener
from zipfile import ZipFile, BadZipFile

import payhip_store

PAYHIP_DASHBOARD = "https://payhip.com/dashboard"
OFFICIAL_GUIDE = "https://help.payhip.com/article/59-adding-a-digital-product"
LOCAL_OLLAMA = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5vl:3b"
ALLOWED_DOMAINS = frozenset(("payhip.com", "www.payhip.com", "help.payhip.com"))
APP_DATA = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "FalconAI" / "money_mode"
MAX_ART_BYTES = 100_000_000
MAX_PAGE_ACTIONS = 18
MAX_LOGIN_SECONDS = 120
MAX_HELP_BYTES = 100_000
ZIP_FILENAME = "Midnight_Falcon_3_Wallpaper_Starter_Pack.zip"
COVER_FILENAME = "Midnight_Falcon_Vol1_Preview.png"
PHASE_NAMES = ("products", "new_product", "digital_product")


class BrowserAgentError(ValueError):
    """Safe, actionable error from a limited browser task."""


class BrowserAgentCancelled(BrowserAgentError):
    pass


class _PageInstructions(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_li = False
        self.depth = 0
        self.parts = []
        self.instructions = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.depth += 1
            if self.depth == 1:
                self.in_li = True
                self.parts = []

    def handle_endtag(self, tag):
        if tag == "li" and self.depth:
            self.depth -= 1
            if self.depth == 0:
                value = " ".join(" ".join(self.parts).split())
                if value:
                    self.instructions.append(value[:300])
                self.in_li = False

    def handle_data(self, data):
        if self.in_li:
            self.parts.append(data)


def research_official_steps(*, opener=None):
    """Refresh a bounded help article, never scrape customer or store data."""
    opener = opener or build_opener(ProxyHandler({})).open
    request = Request(OFFICIAL_GUIDE, headers={
        "User-Agent": "FalconAI-HelpReader/1.0 (seller documentation)"
    })
    try:
        with opener(request, timeout=8) as response:
            actual = getattr(response, "url", OFFICIAL_GUIDE)
            parts = urlsplit(actual)
            if parts.scheme != "https" or parts.hostname != "help.payhip.com":
                raise BrowserAgentError("The help article redirected off Payhip")
            raw = response.read(MAX_HELP_BYTES + 1)
            if len(raw) > MAX_HELP_BYTES:
                raise BrowserAgentError("Payhip help page was unexpectedly large")
    except (OSError, TimeoutError) as exc:
        return {"source": OFFICIAL_GUIDE, "online": False, "steps": (),
                "note": "Official guide unavailable; using locally verified task steps"}
    page = _PageInstructions()
    page.feed(raw.decode("utf-8", "replace"))
    relevant = tuple(step for step in page.instructions if any(
        word in step.casefold() for word in ("product", "upload", "price",
                                             "cover", "description", "visibility")
    ))[:8]
    return {"source": OFFICIAL_GUIDE, "online": True,
            "steps": relevant, "note": "Read official Payhip guide"}


def _safe_regular_file(path, extension):
    file = Path(path)
    if _is_redirect(file) or _is_redirect(file.parent):
        raise BrowserAgentError("Refusing redirected product file")
    if file.suffix.lower() != extension or not file.is_file():
        raise BrowserAgentError("Required product file unavailable: " + file.name)
    if not stat.S_ISREG(file.lstat().st_mode) or not 0 < file.stat().st_size <= MAX_ART_BYTES:
        raise BrowserAgentError("Product file is not a safe regular file")
    return file


def _is_redirect(path):
    try:
        st = Path(path).lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(st.st_mode) or bool(
        getattr(st, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def find_first_product_assets(*, download_dir=None):
    """Use ONLY the two known starter files, never arbitrary Downloads files."""
    folder = Path(download_dir or (Path.home() / "Downloads"))
    product_zip = _safe_regular_file(folder / ZIP_FILENAME, ".zip")
    cover = _safe_regular_file(folder / COVER_FILENAME, ".png")
    try:
        with ZipFile(product_zip, "r") as bundle:
            entries = [item for item in bundle.infolist() if not item.is_dir()]
            images = [item for item in entries if item.filename.lower().endswith(".png")]
            if len(images) != 3:
                raise BrowserAgentError("First wallpaper ZIP must contain exactly three PNGs")
            if any(item.filename.startswith(("/", "\\")) or ".." in
                   Path(item.filename.replace("\\", "/")).parts for item in entries):
                raise BrowserAgentError("Wallpaper ZIP contains an unsafe path")
            if any(item.file_size > MAX_ART_BYTES for item in entries):
                raise BrowserAgentError("Wallpaper ZIP entry too large")
    except BadZipFile as exc:
        raise BrowserAgentError("Wallpaper ZIP is damaged") from exc
    with cover.open("rb") as stream:
        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
            raise BrowserAgentError("Product cover is not a PNG")
    return {"zip": product_zip, "cover": cover}


def _cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise BrowserAgentCancelled("Falcon STOP cancelled Payhip browser task")


def _guard_payhip(page):
    parts = urlsplit(page.url)
    if parts.scheme != "https" or parts.hostname not in (
            "payhip.com", "www.payhip.com"):
        raise BrowserAgentError("Browser left the official Payhip website; stopping")


def _named_control(page, names, *, roles=("button", "link")):
    """Return only one visible semantic control that matches a known task goal."""
    for name in names:
        for role in roles:
            locator = page.get_by_role(role, name=re.compile(r"^\s*" +
                                       re.escape(name) + r"\s*$", re.I))
            if locator.count() == 1 and locator.is_visible():
                return locator
    return None


def _dom_candidates(page):
    """Read clickable elements without their input values or sensitive attributes."""
    raw = page.locator("button, a, [role=button]").evaluate_all(
        """elements => elements.slice(0,150).map((el,index) => ({
            index, tag:el.tagName.toLowerCase(),
            label:(el.getAttribute('aria-label') || el.innerText || '').trim().slice(0,100),
            href:el.tagName === 'A' ? (el.getAttribute('href') || '').slice(0,150) : '',
            visible:!!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
        }))"""
    )
    return [item for item in raw if item.get("visible") and item.get("label")]


def _vision_pick(page, goal, allowed_names, *, model=MODEL, requester=None):
    """Vision fallback nominates a DOM control; code revalidates it before click.

    Only the LOCAL Ollama loopback is used, no remote AI service. Page contents
    cannot change the goal or authorize unlisted actions.
    """
    candidates = _dom_candidates(page)
    eligible = []
    for item in candidates:
        label = item["label"].casefold()
        if not any(name.casefold() in label for name in allowed_names):
            continue
        if item["href"]:
            absolute = urlsplit(page.url)._replace(fragment="")
            from urllib.parse import urljoin
            target = urlsplit(urljoin(page.url, item["href"]))
            if target.scheme != "https" or target.hostname not in ALLOWED_DOMAINS:
                continue
        eligible.append(item)
    if not eligible:
        return None
    if len(eligible) == 1:
        return eligible[0]
    if requester is None:
        return None
    try:
        image = page.screenshot(type="png", full_page=False, timeout=8000)
        instruction = {
            "task": "Identify which listed control advances the allowed Payhip task.",
            "goal": goal, "options": eligible,
            "rules": "Return JSON ONLY with {'index': option.index}; never suggest new tasks."
        }
        response = requester({
            "model": model, "stream": False, "format": "json",
            "options": {"temperature": 0},
            "messages": [{"role": "user",
                          "content": json.dumps(instruction),
                          "images": [base64.b64encode(image).decode("ascii")]}]
        })
        picked = json.loads(response["message"]["content"])
        index = picked.get("index")
        if type(index) is int:
            return next((x for x in eligible if x["index"] == index), None)
    except (OSError, TimeoutError, ValueError, KeyError, TypeError):
        pass
    return None


def _ollama_request(data):
    body = json.dumps(data).encode("utf-8")
    request = Request(LOCAL_OLLAMA, body, {"Content-Type": "application/json"},
                      method="POST")
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=20) as res:
            response = res.read(32_000)
    except OSError:
        return {}
    return json.loads(response)


def _click_advance(page, names, goal, *, cancel, requester=None):
    _cancel(cancel)
    _guard_payhip(page)
    locator = _named_control(page, names)
    if locator is None:
        # A screenshot + local model may choose an element, but only from
        # role/name candidates relevant to this specific allowlisted phase.
        candidate = _vision_pick(page, goal, names, requester=requester)
        if candidate is None:
            raise BrowserAgentError("Could not safely identify Payhip control: " + goal)
        locator = page.locator("button, a, [role=button]").nth(candidate["index"])
        if not locator.is_visible():
            raise BrowserAgentError("Payhip control changed while Falcon was observing")
    locator.click(timeout=8_000)
    _cancel(cancel)
    _guard_payhip(page)


def _fill(page, value, names, *, number_only=False):
    for name in names:
        locator = page.get_by_label(re.compile(r"^\s*" + re.escape(name) +
                                               r"\s*$", re.I))
        if locator.count() == 1:
            locator.fill(str(value), timeout=8_000)
            return
        locator = page.get_by_placeholder(re.compile(re.escape(name), re.I))
        if locator.count() == 1:
            locator.fill(str(value), timeout=8_000)
            return
    if number_only:
        locator = page.locator('input[type="number"]')
        if locator.count() == 1:
            locator.fill(str(value), timeout=8_000)
            return
    raise BrowserAgentError("Payhip field not identified safely: " + "/".join(names))


def _upload_unique(page, path, *, kind):
    inputs = page.locator('input[type="file"]')
    options = []
    for index in range(min(inputs.count(), 12)):
        control = inputs.nth(index)
        attrs = {attr: (control.get_attribute(attr) or "").lower()
                 for attr in ("name", "id", "accept", "aria-label")}
        value = " ".join(attrs.values())
        if kind == "product" and ("product" in value or "zip" in value):
            options.append(control)
        if kind == "cover" and ("cover" in value or "image" in value or "png" in value):
            options.append(control)
    if not options and inputs.count() == 1:
        options.append(inputs.nth(0))
    if len(options) != 1:
        raise BrowserAgentError("Payhip " + kind + " upload field is ambiguous")
    options[0].set_input_files(str(path), timeout=15_000)


def _select_invisible(page):
    radio = page.get_by_role("radio", name=re.compile("^Invisible$", re.I))
    if radio.count() == 1:
        radio.check(timeout=8_000)
        if not radio.is_checked():
            raise BrowserAgentError("Invisible visibility was not confirmed")
        return
    label = page.get_by_label(re.compile("^Invisible$", re.I))
    if label.count() == 1:
        label.check(timeout=8_000)
        if not label.is_checked():
            raise BrowserAgentError("Invisible visibility was not confirmed")
        return
    raise BrowserAgentError("Cannot verify Payhip Invisible setting; product not saved")


def _wait_for_login(page, cancel):
    """User signs into a persistent Chrome profile once; Falcon never sees password."""
    end = time.monotonic() + MAX_LOGIN_SECONDS
    while time.monotonic() < end:
        _cancel(cancel)
        url = urlsplit(page.url)
        if url.scheme == "https" and url.hostname in ("payhip.com", "www.payhip.com"):
            if "/dashboard" in url.path:
                return
        page.wait_for_timeout(500)
    raise BrowserAgentError("Sign in to Payhip in Falcon's Chrome window and retry")


def fill_invisible_listing(page, product, files, *, cancel=None, requester=None):
    """Perform a bounded seller-authorized workflow, no public publishing."""
    _cancel(cancel)
    page.goto(PAYHIP_DASHBOARD, wait_until="domcontentloaded", timeout=30_000)
    _wait_for_login(page, cancel)
    _click_advance(page, ["Products"], "open seller Products page",
                   cancel=cancel, requester=requester)
    _click_advance(page, ["Add new product", "Add New Product", "Add Product"],
                   "open create product menu", cancel=cancel, requester=requester)
    _click_advance(page, ["Digital Product", "Digital product", "Digital"],
                   "choose Digital Product", cancel=cancel, requester=requester)
    _upload_unique(page, files["zip"], kind="product")
    _fill(page, product["title"], ["Product name", "Product title", "Title", "Name"])
    _fill(page, product["suggested_price_usd"], ["Price", "Price (USD)", "Amount"],
          number_only=True)
    _upload_unique(page, files["cover"], kind="cover")
    _fill(page, product["description"], ["Description", "Product description"])
    _select_invisible(page)
    _cancel(cancel)
    _guard_payhip(page)
    # This makes an INVISIBLE seller-only product, never a public listing.
    save = _named_control(page, ["Add Product", "Save Product", "Save"])
    if save is None:
        raise BrowserAgentError("Cannot identify final Payhip save button")
    start_url = page.url
    save.click(timeout=10_000)
    _cancel(cancel)
    _guard_payhip(page)
    # Dynamic product saves can change URL asynchronously. Do not announce
    # success merely because the button accepted a click.
    verified = False
    until = time.monotonic() + 10
    while time.monotonic() < until:
        _cancel(cancel)
        _guard_payhip(page)
        current = urlsplit(page.url)
        if page.url != start_url and ("/product/edit/" in current.path
                                       or "/products/" in current.path):
            verified = True
            break
        visible = page.get_by_text(re.compile(
            r"product (?:created|added|saved) successfully|product created",
            re.I))
        if visible.count() and visible.first.is_visible():
            verified = True
            break
        page.wait_for_timeout(250)
    if not verified:
        raise BrowserAgentError(
            "Falcon clicked Save on the Invisible listing but Payhip did not "
            "confirm it. Inspect the Chrome tab; Falcon will not click Save again.")
    return {"status": "invisible_product_saved_in_browser",
            "url": page.url,
            "warning": ("Payhip confirmed a seller-only Invisible product in browser. "
                        "Review it before making the listing public.")}


def run_first_product(*, cancel=None, download_dir=None, opener=None,
                      requester=None):
    """One explicit local task. Never starts hidden account automation."""
    _cancel(cancel)
    files = find_first_product_assets(download_dir=download_dir)
    state = payhip_store.prepare_first_product()
    product_file = Path(state["path"]) / "PRODUCT_DRAFT.json"
    product = json.loads(product_file.read_text(encoding="utf-8"))
    if not all(x in product for x in ("title", "suggested_price_usd", "description")):
        raise BrowserAgentError("Missing required product draft details")
    guide = research_official_steps(opener=opener)
    _cancel(cancel)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserAgentError(
            "Falcon's Playwright browser driver is not installed in this build") from exc
    profile = APP_DATA / "payhip_chrome_profile"
    profile.parent.mkdir(parents=True, exist_ok=True)
    if _is_redirect(profile) or _is_redirect(profile.parent):
        raise BrowserAgentError("Falcon Chrome profile is redirected; refusing access")
    with sync_playwright() as playwright:
        try:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile), channel="chrome", headless=False,
                args=["--no-first-run"], accept_downloads=False)
        except Exception as exc:
            raise BrowserAgentError(
                "Couldn't launch installed Google Chrome for Payhip: " +
                str(exc)[:180]) from exc
        try:
            context.set_default_timeout(8_000)
            page = context.pages[0] if context.pages else context.new_page()
            result = fill_invisible_listing(
                page, product, files, cancel=cancel, requester=requester or _ollama_request)
            return {**result, "research": guide["note"],
                    "research_url": guide["source"]}
        finally:
            context.close()
