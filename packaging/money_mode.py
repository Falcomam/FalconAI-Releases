"""Falcon Money Mode: private, free, local seller workspace and agent handoffs.

Order management ideas informed by Agent Fiverr and HustleBot. This module
does NOT embed, install, or run those projects, n8n, Activepieces, or OpenHands.
It creates owner-reviewed specifications for optional external tools. No Fiverr
APIs, scraping, outbound communication, cloud inference, or source execution.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import stat
import uuid

DATA = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "FalconAI" / "money_mode"
ORDERS = DATA / "orders"
ALLOWED_SERVICES = ("website", "artwork", "customer_automation")
STATES = ("new", "working", "review", "delivered")
PROVIDERS = {
    "agent-fiverr": ("order structure", "Adapted locally; NOT an actual Fiverr connection"),
    "hustlebot": ("proposal drafting", "Local drafts only; NO scraping, sending or paid API"),
    "openhands": ("coding-task handoff", "Optional worker NOT installed or connected"),
    "n8n": ("automation blueprint", "Local JSON blueprint; NOT a native import or live connection"),
    "activepieces": ("automation blueprint", "Local JSON blueprint; NOT a native import or live connection"),
}
NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,35}$")
SELLER_HANDLE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,29}$")
SECRET = re.compile(
    r"(?i)(?:\b(?:password|api[_ -]?key|private[_ -]?key|secret|access[_ -]?token)"
    r"\s*[:=]\s*\S+|\bsk-[a-z0-9_-]{15,})")
MAX_ORDER_BYTES = 16_000
MAX_ORDERS = 100
CHECKLIST = {
    "website": (
        "Confirm pages, branding, assets and contact details with customer",
        "Create source and responsive layout in Falcon developer workspace",
        "Review desktop and mobile screenshots and test navigation",
        "Request owner approval of finished files and delivery wording",
    ),
    "artwork": (
        "Confirm dimensions, usage rights, style, and revision limit",
        "Generate original art using commercially permitted models and assets",
        "Review image quality, originality, dimensions and licensing",
        "Request owner approval of finished files and delivery wording",
    ),
    "customer_automation": (
        "Get client-approved FAQs, handoff contact and data permissions",
        "Design grounded FAQ answers and unknown-question human handoff",
        "Build a consent-aware test workflow using optional local tools",
        "Test sample queries, privacy and error states before owner approval",
    ),
}


class MoneyError(ValueError):
    """Recoverable local Money Mode error."""


def _redirected(path):
    try:
        details = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(details.st_mode) or bool(
        getattr(details, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _folder(root, *, create=False):
    root = Path(root)
    if _redirected(root) or _redirected(root.parent):
        raise MoneyError("Redirected Money Mode folders are not permitted")
    if create:
        root.mkdir(parents=True, exist_ok=True)
    if root.exists() and not root.is_dir():
        raise MoneyError("Money Mode storage is not a folder")
    return root


def _path(order_id, *, root=ORDERS):
    if not isinstance(order_id, str) or not NAME.fullmatch(order_id):
        raise MoneyError("Invalid order identifier")
    root = _folder(root)
    path = root / (order_id + ".json")
    if _redirected(path):
        raise MoneyError("Redirected order files are not permitted")
    return path


def _text(value, name, minimum, maximum):
    if not isinstance(value, str):
        raise MoneyError(name + " must be text")
    value = value.strip()
    if not minimum <= len(value) <= maximum:
        raise MoneyError(name + f" must contain {minimum}–{maximum} characters")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise MoneyError(name + " contains control characters")
    if SECRET.search(value):
        raise MoneyError("Do not paste passwords, API keys or tokens into Money Mode")
    return value


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _encode(order):
    raw = json.dumps(order, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    if len(raw) > MAX_ORDER_BYTES:
        raise MoneyError("Saved order is too large")
    return raw


def _read(order_id, *, root=ORDERS):
    file = _path(order_id, root=root)
    if not file.is_file():
        raise MoneyError("No saved order with that ID")
    if file.stat().st_size > MAX_ORDER_BYTES:
        raise MoneyError("Saved order exceeds size limit")
    try:
        order = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MoneyError("Saved order is corrupted") from exc
    if (not isinstance(order, dict) or order.get("id") != order_id
            or order.get("service") not in ALLOWED_SERVICES
            or order.get("status") not in STATES):
        raise MoneyError("Saved order has an unsupported format")
    return order


def _overwrite(order, *, root=ORDERS):
    file = _path(order["id"], root=root)
    _read(order["id"], root=root)
    temp = file.with_name(file.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as handle:
            handle.write(_encode(order))
        if _redirected(file):
            raise MoneyError("Order path changed during save")
        os.replace(temp, file)
    finally:
        temp.unlink(missing_ok=True)


def create_order(service, alias, brief, *, root=ORDERS):
    if service not in ALLOWED_SERVICES:
        raise MoneyError("Service must be website, artwork or customer_automation")
    alias = _text(alias, "Customer alias", 2, 60)
    brief = _text(brief, "Customer brief", 12, 1500)
    root = _folder(root, create=True)
    if len(tuple(root.glob("*.json"))) >= MAX_ORDERS:
        raise MoneyError("Money Mode reached its 100-order local limit")
    order_id = "fm_" + uuid.uuid4().hex[:14]
    order = {
        "id": order_id, "service": service, "client_alias": alias,
        "brief": brief, "quote_usd": None, "status": "new",
        "checklist": list(CHECKLIST[service]), "created_at": _now(),
        "updated_at": _now(), "revisions": 0,
    }
    raw = _encode(order)
    with (root / (order_id + ".json")).open("xb") as handle:
        handle.write(raw)
    return order


def get_order(order_id, *, root=ORDERS):
    return _read(order_id, root=root)


def list_orders(*, root=ORDERS):
    root = _folder(root)
    if not root.exists():
        return ()
    entries = tuple(root.iterdir())
    if len(entries) > MAX_ORDERS + 20:
        raise MoneyError("Too many entries in Money Mode order folder")
    result = []
    for file in entries:
        if file.suffix != ".json":
            continue
        order = _read(file.stem, root=root)
        result.append({"id": order["id"], "service": order["service"],
                       "client_alias": order["client_alias"], "status": order["status"]})
    return tuple(sorted(result, key=lambda item: item["id"]))


def quote_order(order_id, amount, *, root=ORDERS):
    """Set owner-provided USD amount only; no AI-generated prices."""
    try:
        value = Decimal(amount)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise MoneyError("Quote must be an explicit USD amount") from exc
    if not value.is_finite() or value < 0 or value > 100_000 or value.as_tuple().exponent < -2:
        raise MoneyError("Quote must be a finite amount between $0 and $100,000 with at most 2 decimals")
    order = _read(order_id, root=root)
    order["quote_usd"] = format(value, ".2f")
    order["updated_at"] = _now()
    _overwrite(order, root=root)
    return order


def set_status(order_id, status, *, root=ORDERS):
    if status not in STATES:
        raise MoneyError("Status must be new, working, review or delivered")
    order = _read(order_id, root=root)
    order["status"] = status
    order["updated_at"] = _now()
    _overwrite(order, root=root)
    return order


def delete_order(order_id, *, confirmed=False, root=ORDERS):
    """Require explicit confirmation even for owner-initiated deletion."""
    if not confirmed:
        raise MoneyError("To delete this record type /money forget <id> CONFIRM")
    _read(order_id, root=root)
    _path(order_id, root=root).unlink()
    return True


def draft_reply(order):
    """Seller reviews and manually sends this. Never promise an unconfirmed price or deadline."""
    service = {
        "website": "your website project",
        "artwork": "your custom artwork request",
        "customer_automation": "your customer-service automation request",
    }[order["service"]]
    questions = {
        "website": "the required pages, examples you like, brand assets, and preferred launch date",
        "artwork": "the target dimensions, style references, permitted commercial use, and deadline",
        "customer_automation": "your approved FAQ document, how to hand questions to a person, and where inquiries should go",
    }[order["service"]]
    quote = (" The current quoted amount in my records is $" + order["quote_usd"] + "."
             if order.get("quote_usd") is not None else
             " I can confirm price after reviewing the full scope.")
    return ("Hi! Thanks for reaching out about " + service + ". "
            "Could you share " + questions + "?" + quote +
            " I'll confirm the delivery timeline before starting. "
            "[DRAFT ONLY — REVIEW AND SEND YOURSELF]")


def handoff(order_id, provider, *, root=ORDERS):
    """Create a local, inert, provider-specific task contract; does NOT connect to it."""
    if provider not in PROVIDERS:
        raise MoneyError("Unknown integration; use /money tools")
    order = _read(order_id, root=root)
    base = {"schema": "falcon.money.handoff.v1", "provider": provider,
            "order_id": order["id"], "service": order["service"],
            "brief": order["brief"], "tasks": order["checklist"],
            "approval_required_before_external_action": True}
    if provider == "openhands":
        base["instruction"] = ("Create a reviewed source-only " + order["service"] +
                               " deliverable. Do not run, install, publish or contact clients.")
    elif provider in ("n8n", "activepieces"):
        base["instruction"] = (
            "Design a human-reviewed workflow from these requirements. "
            "This is a neutral task blueprint, NOT importable vendor workflow JSON.")
    elif provider == "agent-fiverr":
        base["instruction"] = "Use local order/revision and QA concepts only; no Fiverr access."
        base["quote_usd"] = order.get("quote_usd")
    else:
        base["instruction"] = (
            "Prepare a personalized proposal from this brief only. "
            "Do not scrape platforms, send messages or call a paid API.")
    return base


def save_seller_handle(handle, *, root=ORDERS):
    """Store the owner's public Fiverr handle locally, NEVER login credentials."""
    if not isinstance(handle, str) or not SELLER_HANDLE.fullmatch(handle):
        raise MoneyError("Provide a public seller handle (3-30 letters, digits, . _ or -)")
    folder = _folder(Path(root).parent, create=True)
    file = folder / "seller_profile.json"
    if _redirected(file):
        raise MoneyError("Redirected seller profile not permitted")
    data = json.dumps({"fiverr_handle": handle}, ensure_ascii=True).encode("utf-8")
    temp = file.with_name(file.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(data)
        if _redirected(file):
            raise MoneyError("Seller profile changed during save")
        os.replace(temp, file)
    finally:
        temp.unlink(missing_ok=True)
    return handle


def saved_seller_handle(*, root=ORDERS):
    file = _folder(Path(root).parent) / "seller_profile.json"
    if not file.exists():
        return None
    if _redirected(file) or not file.is_file() or file.stat().st_size > 1000:
        raise MoneyError("Seller profile file is unsafe")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MoneyError("Seller profile cannot be read") from exc
    handle = data.get("fiverr_handle") if isinstance(data, dict) else None
    if not isinstance(handle, str) or not SELLER_HANDLE.fullmatch(handle):
        raise MoneyError("Invalid saved seller handle")
    return handle


def tool_catalog():
    return tuple({"name": name, "purpose": purpose, "integration": note}
                 for name, (purpose, note) in PROVIDERS.items())


def handle_command(text, *, root=ORDERS):
    """Deterministic single-chat commands; no subprocesses, network or API tokens."""
    text = (text or "").strip()
    low = text.casefold()
    if low in ("", "help"):
        return ("FALCON MONEY MODE — local seller assistant (source candidate)\n"
                "/money new website|artwork|customer_automation | ClientAlias | requirements\n"
                "/money list • /money show <id> • /money quote <id> <USD>\n"
                "/money status <id> new|working|review|delivered\n"
                "/money handoff <id> agent-fiverr|hustlebot|openhands|n8n|activepieces\n"
                "/money tools • /money seller <public_handle>\n"
                "/money forget <id> CONFIRM\n"
                "No Fiverr messages sent, external tools installed or paid API used.")
    if low == "seller":
        name = saved_seller_handle(root=root)
        return "Public Fiverr seller: " + (name if name else "not configured")
    if low.startswith("seller "):
        parts = text.split()
        if len(parts) != 2:
            raise MoneyError("Use /money seller <public_handle>")
        handle = save_seller_handle(parts[1], root=root)
        return ("Saved public seller handle locally: @" + handle +
                ". No Fiverr login or account access has been granted.")
    if low == "tools":
        return "EXTERNAL TOOL BLUEPRINTS (not installed or connected):\n" + "\n".join(
            "- " + item["name"] + ": " + item["integration"] for item in tool_catalog())
    if low.startswith("new "):
        parts = [p.strip() for p in text[4:].split("|", 2)]
        if len(parts) != 3:
            raise MoneyError("Use /money new website | ClientAlias | project requirements")
        order = create_order(*parts, root=root)
        return ("Saved local order " + order["id"] + " (" + order["service"] +
                ").\nNext: /money show " + order["id"] +
                "\nNo Fiverr account accessed or message sent.")
    if low == "list":
        orders = list_orders(root=root)
        return ("SAVED ORDERS:\n" + "\n".join(
            "- " + o["id"] + ": " + o["service"] + " • " + o["client_alias"]
            + " • " + o["status"] for o in orders)) if orders else "No local Money Mode orders saved."
    parts = text.split()
    if len(parts) == 2 and parts[0].lower() == "show":
        order = _read(parts[1], root=root)
        return ("ORDER: " + order["id"] + "\nService: " + order["service"] +
                "\nCustomer alias: " + order["client_alias"] +
                "\nRequirements: " + order["brief"] +
                "\nQuote: " + ("$" + order["quote_usd"] if order["quote_usd"] else "not supplied") +
                "\nStatus: " + order["status"] +
                "\nChecklist:\n" + "\n".join("- " + task for task in order["checklist"]) +
                "\n\nSUGGESTED CLIENT REPLY:\n" + draft_reply(order))
    if len(parts) == 3 and parts[0].lower() == "quote":
        order = quote_order(parts[1], parts[2], root=root)
        return "Saved owner-specified quote for " + order["id"] + ": $" + order["quote_usd"]
    if len(parts) == 3 and parts[0].lower() == "status":
        order = set_status(parts[1], parts[2].lower(), root=root)
        return "Order " + order["id"] + " locally marked " + order["status"] + ". Nothing was delivered."
    if len(parts) == 3 and parts[0].lower() == "handoff":
        return ("REVIEWABLE LOCAL BLUEPRINT (nothing connected or executed):\n" +
                json.dumps(handoff(parts[1], parts[2].lower(), root=root), ensure_ascii=False, indent=2))
    if len(parts) == 3 and parts[0].lower() == "forget" and parts[2] == "CONFIRM":
        delete_order(parts[1], confirmed=True, root=root)
        return "Deleted the specified local order record. No external account affected."
    raise MoneyError("Unknown Money Mode command. Type /money help.")
