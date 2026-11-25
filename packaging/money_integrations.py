"""Optional real local adapters for Falcon Money Mode workflow engines.

n8n and Activepieces both expose POST webhooks; Falcon can call an explicitly
configured loopback webhook. OpenHands Agent Server exposes a /health endpoint;
we only probe it here. No external agent is installed or auto-started.

Outbound workflow dispatch requires an explicit per-action user command. There
is no hidden Fiverr integration, model-generated arbitrary URL or paid API.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, ProxyHandler, build_opener
from urllib.error import URLError, HTTPError

DEFAULT_FOLDER = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "FalconAI" / "money_mode"
MAX_RESPONSE_BYTES = 8192
MAX_CONFIG_BYTES = 4096
MAX_PAYLOAD_BYTES = 12000
URL_RULES = {
    "n8n": re.compile(r"^/(?:webhook|webhook-test)/[a-zA-Z0-9/_-]{4,180}$"),
    "activepieces": re.compile(r"^/api/v1/webhooks/[a-zA-Z0-9/_-]{4,180}(?:/sync)?$"),
}
PROVIDERS = ("n8n", "activepieces")


class ConnectorError(ValueError):
    """A safe, user-facing integration error."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ConnectorError("Local integration refused an HTTP redirect")


def _opener():
    return build_opener(ProxyHandler({}), _NoRedirect()).open


def _validated_endpoint(provider, endpoint):
    if provider not in PROVIDERS:
        raise ConnectorError("Unsupported workflow provider")
    if not isinstance(endpoint, str) or len(endpoint) > 300:
        raise ConnectorError("Invalid local workflow URL")
    try:
        parts = urlsplit(endpoint)
        port = parts.port
    except ValueError as exc:
        raise ConnectorError("Invalid local workflow port") from exc
    if (parts.scheme != "http" or parts.hostname != "127.0.0.1"
            or not 1 <= (port or 0) <= 65535 or parts.username or parts.password
            or parts.query or parts.fragment
            or parts.netloc != f"127.0.0.1:{port}"
            or not URL_RULES[provider].fullmatch(parts.path)):
        raise ConnectorError(
            "Only a local 127.0.0.1 n8n/Activepieces webhook path is supported")
    return endpoint


def _configuration_file(*, folder=DEFAULT_FOLDER):
    folder = Path(folder)
    if folder.is_symlink() or folder.parent.is_symlink():
        raise ConnectorError("Redirected Money Mode configuration folder")
    if folder.exists() and not folder.is_dir():
        raise ConnectorError("Money Mode configuration location is not a folder")
    config = folder / "local_workflow_endpoints.json"
    if config.is_symlink():
        raise ConnectorError("Redirected workflow settings not allowed")
    return config


def load_endpoints(*, folder=DEFAULT_FOLDER):
    file = _configuration_file(folder=folder)
    if not file.exists():
        return {}
    if not file.is_file() or file.stat().st_size > MAX_CONFIG_BYTES:
        raise ConnectorError("Workflow settings file is invalid")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConnectorError("Workflow settings could not be loaded") from exc
    if not isinstance(data, dict) or len(data) > len(PROVIDERS):
        raise ConnectorError("Workflow settings format is invalid")
    for provider, endpoint in data.items():
        _validated_endpoint(provider, endpoint)
    return data


def set_endpoint(provider, endpoint, *, folder=DEFAULT_FOLDER):
    endpoint = _validated_endpoint(provider, endpoint)
    config = load_endpoints(folder=folder)
    config[provider] = endpoint
    file = _configuration_file(folder=folder)
    file.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(config, sort_keys=True, indent=2).encode("utf-8")
    if len(raw) > MAX_CONFIG_BYTES:
        raise ConnectorError("Workflow settings exceed maximum size")
    temp = file.with_name(file.name + "." + os.urandom(8).hex() + ".tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(raw)
        if file.is_symlink():
            raise ConnectorError("Workflow settings changed during update")
        os.replace(temp, file)
    finally:
        temp.unlink(missing_ok=True)
    return endpoint


def remove_endpoint(provider, *, folder=DEFAULT_FOLDER):
    if provider not in PROVIDERS:
        raise ConnectorError("Unknown workflow engine")
    config = load_endpoints(folder=folder)
    if provider not in config:
        return False
    del config[provider]
    file = _configuration_file(folder=folder)
    temp = file.with_name(file.name + "." + os.urandom(8).hex() + ".tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(json.dumps(config).encode("utf-8"))
        if file.is_symlink():
            raise ConnectorError("Workflow settings changed during update")
        os.replace(temp, file)
    finally:
        temp.unlink(missing_ok=True)
    return True


def _read_bounded_response(response):
    raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ConnectorError("Local workflow reply is larger than expected")
    return raw


def _minimal_payload(order):
    """Keep private client aliases, quotes and account data out of workflow calls."""
    if not isinstance(order, dict):
        raise ConnectorError("Invalid client order")
    service = order.get("service")
    if service not in ("website", "artwork", "customer_automation"):
        raise ConnectorError("Unsupported client work type")
    order_id = order.get("id")
    if not isinstance(order_id, str) or not re.fullmatch(r"fm_[a-f0-9]{14}", order_id):
        raise ConnectorError("Invalid client order ID")
    brief = order.get("brief")
    if not isinstance(brief, str) or not 12 <= len(brief) <= 1500:
        raise ConnectorError("Client brief is missing or too large")
    return {
        "schema": "falcon.money.workflow.v1",
        "order_id": order_id, "service": service,
        "task_description": brief,
        "mode": "owner_requested_local_workflow",
        "owner_review_required_before_external_delivery": True,
    }


def invoke_workflow(provider, order, *, confirmed=False, folder=DEFAULT_FOLDER,
                    opener=None, timeout=8):
    """ACTUALLY POST to one specifically configured local workflow webhook.

    The command caller must obtain owner confirmation. This is not a dry run
    and may trigger any actions configured in that local workflow instance.
    """
    if not confirmed:
        raise ConnectorError("Explicit user confirmation required before triggering a workflow")
    endpoints = load_endpoints(folder=folder)
    if provider not in endpoints:
        raise ConnectorError("Connect a local workflow endpoint first")
    endpoint = _validated_endpoint(provider, endpoints[provider])
    payload = json.dumps(_minimal_payload(order)).encode("utf-8")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ConnectorError("Workflow payload is too large")
    if opener is None:
        opener = _opener()
    request = Request(endpoint, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "FalconAI-MoneyMode/0.1",
    })
    try:
        with opener(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            _read_bounded_response(response)
    except (OSError, TimeoutError, HTTPError, URLError) as exc:
        raise ConnectorError("Local workflow could not be triggered") from exc
    if not 200 <= status <= 299:
        raise ConnectorError("Local workflow returned a non-success HTTP status")
    return {"provider": provider, "order_id": order["id"],
            "status": status, "sent_to": "local-workflow",
            "detail": "Webhook accepted request; downstream execution and delivery NOT verified"}


def probe_openhands(*, port=8000, opener=None):
    """Read-only health probe against an already-running local OpenHands server."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise ConnectorError("Invalid OpenHands local port")
    if opener is None:
        opener = _opener()
    request = Request(f"http://127.0.0.1:{port}/health", headers={
        "Accept": "application/json", "User-Agent": "FalconAI-MoneyMode/0.1"})
    try:
        with opener(request, timeout=3) as response:
            code = getattr(response, "status", 200)
            _read_bounded_response(response)
    except (OSError, TimeoutError, HTTPError, URLError) as exc:
        return {"online": False, "reason": "OpenHands local server is not responding"}
    return {"online": code == 200,
            "reason": "OpenHands local server responds; agent execution not authorized"}
