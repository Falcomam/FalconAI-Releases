"""Retrieve and fully decode local ComfyUI output before exposing it for review."""
import json
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import uuid

from comfy_video import check_active

MAX_VIDEO = 512 * 1024 * 1024


class InvalidClip(ValueError):
    """The completed job returned unusable media."""


def load_workflow(path, prompt_node, prompt):
    graph = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(graph, dict) or not graph:
        raise ValueError("Export the workflow in ComfyUI API format.")
    node = graph.get(str(prompt_node), {})
    if node.get("class_type") != "CLIPTextEncode":
        raise ValueError("Select the positive CLIPTextEncode node.")
    node["inputs"]["text"] = prompt
    return graph


def media_tools():
    for tool in ("ffprobe", "ffmpeg"):
        if not shutil.which(tool):
            raise RuntimeError(f"Install {tool} and restart Falcon. See Money Mode > Get FFmpeg media tools.")


def _output_file(entry, output_node):
    outputs = entry.get("outputs", {})
    nodes = outputs.values() if output_node is None else [outputs.get(output_node, {})]
    for node in nodes:
        for key in ("videos", "images", "gifs"):
            for item in node.get(key, []):
                if not isinstance(item, dict) or item.get("type") != "output":
                    continue
                name, sub = item.get("filename"), item.get("subfolder", "")
                if not isinstance(name, str) or not name.lower().endswith(".mp4"):
                    continue
                if (not isinstance(sub, str) or PureWindowsPath(name).name != name
                        or PureWindowsPath(sub).anchor or ".." in PureWindowsPath(sub).parts
                        or ":" in name + sub or "\x00" in name + sub):
                    raise ValueError("Invalid video output location from ComfyUI.")
                return {"filename": name, "subfolder": sub, "type": "output"}
    raise InvalidClip("The completed workflow returned no MP4 from its video output.")


def _media_command(args, stop, gaming, timeout):
    check_active(stop, gaming)
    with subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)) as proc:
        end = time.monotonic() + timeout
        try:
            while time.monotonic() < end:
                check_active(stop, gaming)
                try:
                    data, _ = proc.communicate(timeout=.25)
                except subprocess.TimeoutExpired:
                    continue
                if proc.returncode:
                    raise InvalidClip("ComfyUI returned an undecodable video.")
                return data
            raise TimeoutError("Local video verification timed out.")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()


def render_to(client, graph, target, stop, gaming, progress, *, output_node=None, expected=None):
    check_active(stop, gaming)
    media_tools()
    target = Path(target)
    if target.exists():
        raise FileExistsError(target)
    entry = client.render(graph, stop, gaming, progress=progress)
    check_active(stop, gaming)
    query = urllib.parse.urlencode(_output_file(entry, output_node))
    progress("Verifying the generated video")
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".part", delete=False) as dst:
            temp = Path(dst.name)
            deadline = time.monotonic() + 180
            with client.opener.open(client.base + "/view?" + query, timeout=8) as src:
                total = 0
                while True:
                    check_active(stop, gaming)
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Local video retrieval timed out.")
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_VIDEO:
                        raise ValueError("Video exceeds 512 MiB.")
                    dst.write(chunk)
        source = ["-protocol_whitelist", "file,pipe", "-f", "mov", "-i", str(temp)]
        probe = _media_command(["ffprobe", "-v", "error", *source, "-select_streams", "v:0",
                                "-show_entries", "stream=width,height,nb_frames,codec_name",
                                "-of", "json"], stop, gaming, 30)
        streams = json.loads(probe).get("streams", [])
        if len(streams) != 1:
            raise InvalidClip("No video stream in local output.")
        video = streams[0]
        if expected and (video.get("width"), video.get("height"), video.get("nb_frames")) != (
                expected[0], expected[1], str(expected[2])):
            raise InvalidClip("Generated clip dimensions or frame count did not match the LTX request.")
        decode = ["ffmpeg", "-nostdin", "-v", "error", "-xerror", *source, "-map", "0:v:0"]
        if expected:
            # Cap the hash output even if the container understates its frame count.
            hashes = _media_command([*decode, "-fps_mode", "passthrough", "-frames:v", str(expected[2] + 1),
                                     "-f", "framemd5", "-"], stop, gaming, 180)
            frames = [line.rsplit(b",", 1)[-1].strip() for line in hashes.splitlines()
                      if line and not line.startswith(b"#")]
            if len(frames) != expected[2]:
                raise InvalidClip("Decoded frame count differs from the LTX request.")
            if len(frames) > 1 and len(set(frames)) == 1:
                raise InvalidClip("All decoded LTX frames were identical.")
        else:
            _media_command([*decode, "-f", "null", "-"], stop, gaming, 180)
        check_active(stop, gaming)
        temp.replace(target)
        return target
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def generate(client, graph, output_root, stop, gaming, progress, *, output_node=None, expected=None):
    """Save a standalone local preview outside the daily upload ledger."""
    check_active(stop, gaming)
    media_tools()
    if output_node is None:
        available = client.request("/object_info")
        missing = {node["class_type"] for node in graph.values()} - set(available)
        if missing:
            raise RuntimeError("Missing ComfyUI nodes: " + ", ".join(sorted(missing)))
    folder = Path(output_root) / ("ai-video-" + uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=False)
    try:
        target = render_to(client, graph, folder / "draft.mp4", stop, gaming, progress,
                           output_node=output_node, expected=expected)
        check_active(stop, gaming)
        (folder / "REVIEW_REQUIRED.txt").write_text("Local video preview. Review before sharing.", encoding="utf-8")
        return target
    except BaseException:
        shutil.rmtree(folder)
        raise
