"""Local ComfyUI API adapter. Requires a separately installed, compatible API workflow."""
import json
import time
import urllib.request
import urllib.parse
import uuid

class ComfyVideo:
    def __init__(self, port=8188):
        self.base = "http://127.0.0.1:" + str(int(port))
        self.client_id = str(uuid.uuid4())
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base + path, data=data,
            headers={"Content-Type": "application/json"})
        with self.opener.open(req, timeout=10) as response:
            return json.load(response)

    def available(self):
        return self.request("/system_stats")

    def render(self, workflow, stop, gaming, timeout=1800, progress=lambda status: None):
        """Return completed history entry; never upload or silently fall back."""
        if stop() or gaming():
            raise InterruptedError("Generation blocked by STOP or Gaming Mode")
        if not isinstance(workflow, dict) or not workflow or not all(
            isinstance(node, dict) and "class_type" in node for node in workflow.values()
        ):
            raise ValueError("Expected ComfyUI API-format workflow")
        result = self.request("/prompt", {"prompt": workflow, "client_id": self.client_id})
        prompt_id = result["prompt_id"]
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                if stop() or gaming():
                    raise InterruptedError("Generation cancelled")
                history = self.request("/history/" + urllib.parse.quote(prompt_id, safe=""))
                entry = history.get(prompt_id)
                if entry:
                    status = entry.get("status", {})
                    if status.get("status_str") == "error":
                        raise RuntimeError("ComfyUI workflow failed: " + str(status))
                    if status.get("completed"):
                        return entry
                progress("Waiting for ComfyUI " + prompt_id)
                time.sleep(1)
            raise TimeoutError("ComfyUI generation timed out")
        except BaseException:
            # Delete only our queued job. Interrupt running work only if it is ours.
            self.request("/queue", {"delete": [prompt_id]})
            queue = self.request("/queue")
            if any(len(job) > 1 and job[1] == prompt_id for job in queue.get("queue_running", [])):
                self.request("/interrupt", {})
            raise
