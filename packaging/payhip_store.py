"""Local Payhip store starter for Falcon Money Mode.

Payhip is a hosted website, not software installed on the user's computer.
This module launches only Payhip's known official HTTPS homepage, and drafts
product copy in Falcon-owned local storage. It never logs in, publishes, changes
seller settings, handles customer cards, or claims product artwork exists.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import uuid
import webbrowser

STORE_URL = "https://payhip.com/"
ROOT = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "FalconAI" / "money_mode" / "store"
FIRST_PRODUCT = "midnight-falcon-wallpapers-vol1"
MAX_DRAFT_BYTES = 10_000

PRODUCT = {
    "status": "DRAFT—ARTWORK NOT YET CREATED OR VERIFIED",
    "title": "Midnight Falcon — Purple Gaming Wallpapers Vol. 1",
    "suggested_price_usd": "4.99",
    "category": "Digital wallpapers",
    "format": "Three original 2560 × 1440 PNG desktop wallpapers (target; NOT yet included)",
    "keywords": ["purple gaming wallpapers", "dark fantasy wallpaper",
                 "desktop backgrounds", "cyberpunk", "falcon art"],
    "description": (
        "Give your setup a midnight glow with Midnight Falcon Vol. 1 — "
        "a collection of original purple-themed gaming desktop wallpapers. "
        "The planned pack features neon skylines, atmospheric mountains, "
        "starfields, and peregrine-falcon-inspired silhouettes. "
        "Files and exact resolution must be verified before publishing."
    ),
    "planned_artworks": [
        "Violet futuristic skyline with a soaring falcon",
        "Purple aurora above an alpine lake",
        "Cosmic falcon silhouette against a nebula",
    ],
    "rights_check": (
        "Confirm every output model/assets' commercial licensing and originality. "
        "Do not publish copyrighted third-party logos or claims of exclusive rights."
    ),
    "platform": "Payhip",
    "platform_url": STORE_URL,
    "checkout_and_delivery": (
        "Payhip handles checkout and instant digital download after the "
        "owner configures a payment processor and uploads a completed product."
    ),
    "pending_owner_actions": [
        "Create/sign in to a personal Payhip seller account",
        "Connect and verify a supported payment processor in Payhip",
        "Review and approve three original, commercially usable PNGs",
        "Upload product ZIP and cover previews in the Payhip web dashboard",
        "Verify price, policies, refund terms and test checkout before publishing",
    ],
}


class StoreError(ValueError):
    """Short safe error for Falcon's chat."""


def _is_redirect(path):
    try:
        st = Path(path).lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(st.st_mode) or bool(
        getattr(st, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def product_folder(*, root=ROOT):
    root = Path(root)
    if _is_redirect(root) or _is_redirect(root.parent):
        raise StoreError("Payhip product workspace is redirected")
    return root / FIRST_PRODUCT


def prepare_first_product(*, root=ROOT):
    """Draft product details idempotently without overwriting a seller's edits."""
    directory = product_folder(root=root)
    if _is_redirect(directory):
        raise StoreError("Payhip product directory is redirected")
    if directory.exists():
        if not directory.is_dir():
            raise StoreError("Payhip product workspace is not a directory")
        info = directory / "PRODUCT_DRAFT.json"
        if _is_redirect(info):
            raise StoreError("Payhip product draft was redirected")
        if not info.is_file() or info.stat().st_size > MAX_DRAFT_BYTES:
            raise StoreError("Existing product draft is missing or oversized")
        return {"path": str(directory), "created": False, "ready_to_sell": False}

    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir() or _is_redirect(root):
        raise StoreError("Payhip workspace is unavailable")

    # Create a new folder exclusively; never remove or overwrite it.
    directory.mkdir(exist_ok=False)
    record = json.dumps(PRODUCT, ensure_ascii=False, indent=2).encode("utf-8")
    if len(record) > MAX_DRAFT_BYTES:
        raise StoreError("Starter product metadata exceeded size limit")
    try:
        with (directory / "PRODUCT_DRAFT.json").open("xb") as stream:
            stream.write(record)
        text = (
            "# Midnight Falcon — Wallpaper Pack Vol. 1\n\n"
            "**DRAFT ONLY. This local workspace contains product metadata, not the customer image ZIP.**\n\n"
            "Price idea: $4.99. Artwork target: three 2560 × 1440 original PNGs.\n"
            "Generate and review each artwork first, confirm commercial-use "
            "rights, then create a customer ZIP. Do not upload this draft as "
            "a finished product.\n\n"
            "Payhip: https://payhip.com/\n"
            "Payhip is web-hosted: Falcon does not install or control it. "
            "You sign in yourself, connect payments and approve publication. "
            "Payhip handles payment and automatic download delivery "
            "after you upload finished product files.\n"
        )
        with (directory / "README_START_HERE.md").open("xb") as stream:
            stream.write(text.encode("utf-8"))
    except BaseException:
        # Avoid removing a partially filled folder, which could destroy edits.
        raise
    return {"path": str(directory), "created": True, "ready_to_sell": False}


def open_store(*, opener=webbrowser.open):
    """Launch a fixed official HTTPS site in the default browser, no shell."""
    if not opener(STORE_URL, new=2):
        raise StoreError("Default browser could not open Payhip")
    return STORE_URL


def start_store(*, opener=webbrowser.open, root=ROOT):
    """One chat action prepares a local first-product brief and opens Payhip."""
    draft = prepare_first_product(root=root)
    site = open_store(opener=opener)
    return {**draft, "site": site, "note": (
        "Opened the official Payhip website. The first product is a local "
        "draft only; no artwork was downloaded and no product was published."
    )}
