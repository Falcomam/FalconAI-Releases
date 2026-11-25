"""Run a trusted, user-exported ComfyUI video workflow without paid services."""
import json
import pathlib
import subprocess
import shutil
import urllib.parse
import uuid

def load_workflow(path, prompt_node, prompt):
    graph = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(graph, dict) or not graph:
        raise ValueError("Export workflow in ComfyUI API format")
    node = graph[str(prompt_node)]
    if node.get("class_type") != "CLIPTextEncode":
        raise ValueError("Select the positive CLIPTextEncode node")
    node["inputs"]["text"] = prompt
    return graph

def generate(client, graph, output_root, stop, gaming, progress):
    if stop() or gaming():
        raise InterruptedError("Generation blocked")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("Install FFmpeg and ffprobe first")
    available = client.request("/object_info")
    missing = sorted({n["class_type"] for n in graph.values()} - set(available))
    if missing:
        raise RuntimeError("Missing ComfyUI nodes: " + ", ".join(missing))
    entry = client.render(graph, stop, gaming, progress=progress)
    if stop() or gaming():
        raise InterruptedError("Generation cancelled")
    files = []
    for node in entry.get("outputs", {}).values():
        for key in ("videos", "gifs", "images"):
            files.extend(f for f in node.get(key, []) if isinstance(f, dict)
                         and str(f.get("filename", "")).lower().endswith(".mp4")
                         and f.get("type") == "output")
    if not files:
        raise RuntimeError("Workflow returned no MP4 output")
    folder = pathlib.Path(output_root) / ("ai-video-" + uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=False)
    target = folder / "draft.mp4"
    query = urllib.parse.urlencode({k: files[0].get(k, "") for k in ("filename","subfolder","type")})
    try:
        with client.opener.open(client.base + "/view?" + query, timeout=30) as src, target.open("xb") as dst:
            total = 0
            while True:
                if stop() or gaming():
                    raise InterruptedError("Download cancelled")
                chunk = src.read(1024*1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 512*1024*1024:
                    raise ValueError("Video exceeds 512 MiB")
                dst.write(chunk)
        probe = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=codec_type","-of","json",str(target)],capture_output=True,check=True,timeout=30)
        if not json.loads(probe.stdout).get("streams"):
            raise RuntimeError("No video stream")
        subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(target),"-f","null","-"],capture_output=True,check=True,timeout=180)
        if stop() or gaming():
            raise InterruptedError("Generation cancelled")
        (folder/"REVIEW_REQUIRED.txt").write_text("AI workflow output. Review before sharing. No upload performed.",encoding="utf-8")
        return target
    except BaseException:
        target.unlink(missing_ok=True)
        raise
