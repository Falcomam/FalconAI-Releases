"""Loopback ComfyUI transport. Cancellation always names the caller's prompt."""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


class VideoJobFailed(RuntimeError):
    """ComfyUI reported that this prompt finished with an execution error."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("ComfyUI redirected a local request. Check its listening port.")


def check_active(stop, gaming):
    if stop() or gaming():
        raise InterruptedError("Video generation paused by STOP or Gaming Mode.")


class ComfyVideo:
    def __init__(self, port=8188):
        port = int(port)
        if not 1 <= port <= 65535:
            raise ValueError("Invalid loopback port")
        self.base = f"http://127.0.0.1:{port}"
        self.client_id = str(uuid.uuid4())
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base + path, data=data,
                                     headers={"Content-Type": "application/json"})
        with self.opener.open(req, timeout=8) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Local ComfyUI response exceeded the size limit.")
        return json.loads(raw) if raw.strip() else {}

    def available(self):
        return self.request("/system_stats")

    def require_supported(self):
        version = self.available().get("system", {}).get("comfyui_version", "")
        numbers = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:[+-].*)?", version)
        if not numbers or tuple(map(int, numbers.groups())) < (0, 12, 3):
            raise ValueError("Use ComfyUI 0.12.3 or newer for job-specific STOP support.")
        return version

    def _cancel(self, prompt_id):
        # Dequeue first. If the job started meanwhile, the server compares its ID
        # at interruption time. Neither call clears a queue or stops another job.
        for path, body in (("/queue", {"delete": [prompt_id]}),
                           ("/interrupt", {"prompt_id": prompt_id})):
            try:
                self.request(path, body)
            except (OSError, ValueError):
                pass

    def render(self, workflow, stop, gaming, timeout=1800, progress=lambda status: None):
        check_active(stop, gaming)
        if not isinstance(workflow, dict) or not workflow or not all(
                isinstance(n, dict) and isinstance(n.get("class_type"), str)
                and isinstance(n.get("inputs"), dict) for n in workflow.values()):
            raise ValueError("Expected a ComfyUI API workflow.")
        self.require_supported()
        prompt_id = str(uuid.uuid4())
        check_active(stop, gaming)
        try:
            try:
                response = self.request("/prompt", {"prompt": workflow, "client_id": self.client_id,
                                                    "prompt_id": prompt_id})
            except urllib.error.HTTPError as exc:
                if exc.code == 400:
                    raise ValueError("ComfyUI rejected the video graph. Check models and core node versions.") from exc
                raise
            if response.get("prompt_id") != prompt_id or response.get("node_errors"):
                raise RuntimeError("ComfyUI did not accept the complete video job.")
            deadline = time.monotonic() + timeout
            progress("Waiting for local video synthesis")
            while time.monotonic() < deadline:
                check_active(stop, gaming)
                try:
                    entry = self.request("/history/" + prompt_id).get(prompt_id)
                except (OSError, TimeoutError) as exc:
                    raise ConnectionError("Lost the local ComfyUI connection during generation. "
                                          "Check the ComfyUI log and available memory.") from exc
                if entry:
                    status = entry.get("status", {})
                    if status.get("status_str") == "error":
                        for event, details in reversed(status.get("messages", [])):
                            if event == "execution_error":
                                kind = str(details.get("exception_type", "execution error"))[:100]
                                node = str(details.get("node_type", "a node"))[:80]
                                message = f"ComfyUI failed at {node} ({kind})."
                                # Repeating the same model at the same size cannot fix exhausted memory.
                                memory_detail = (kind + " " + str(details.get("exception_message", ""))[:512]).lower()
                                if "out of memory" in memory_detail or "outofmemory" in memory_detail or "memoryerror" in memory_detail:
                                    raise RuntimeError(message)
                                raise VideoJobFailed(message)
                        raise RuntimeError("ComfyUI stopped before producing a video.")
                    if status.get("completed") is True and status.get("status_str") == "success":
                        check_active(stop, gaming)
                        return entry
                time.sleep(.35)
            raise TimeoutError("Local video generation timed out.")
        except BaseException:
            self._cancel(prompt_id)
            raise
