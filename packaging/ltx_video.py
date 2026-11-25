"""A native, text-to-video LTX-Video 2B graph for the owner's local ComfyUI."""
from pathlib import Path, PureWindowsPath
import secrets
import urllib.error

from comfy_video import ComfyVideo, VideoJobFailed, check_active
from video_workflow import InvalidClip, generate, media_tools, render_to

CHECKPOINT = "ltx-video-2b-v0.9.5.safetensors"
ENCODERS = ("t5xxl_fp8_e4m3fn.safetensors", "t5xxl_fp16.safetensors")
WIDTH, HEIGHT, FRAMES, FPS, STEPS = 320, 576, 49, 24, 24
OUTPUT_NODE = "12"


def daily_enabled(root):
    return (Path(root) / "ltx_daily.on").is_file()


def set_daily(value, root):
    marker = Path(root) / "ltx_daily.on"
    if value:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    else:
        marker.unlink(missing_ok=True)


def build_workflow(prompt, seed, *, checkpoint=CHECKPOINT, encoder=ENCODERS[0],
                   width=WIDTH, height=HEIGHT, frames=FRAMES, steps=STEPS, dynamic_codec=False):
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 1600:
        raise ValueError("Describe the clip in 1–1600 characters.")
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise ValueError("Invalid video seed.")
    if (any(type(n) is not int for n in (width, height, frames, steps))
            or not all(96 <= n <= 768 and n % 32 == 0 for n in (width, height))
            or not 9 <= frames <= 97 or (frames - 1) % 8 or not 2 <= steps <= 40):
        raise ValueError("Invalid LTX dimensions, frame count or step count.")

    def node(kind, **inputs):
        return {"class_type": kind, "inputs": inputs}

    return {
        "1": node("CheckpointLoaderSimple", ckpt_name=checkpoint),
        "2": node("CLIPLoader", clip_name=encoder, type="ltxv", device="default"),
        "3": node("CLIPTextEncode", clip=["2", 0], text=prompt.strip()),
        "4": node("CLIPTextEncode", clip=["2", 0], text="watermark, captions, motion smear, visual distortion"),
        "5": node("LTXVConditioning", positive=["3", 0], negative=["4", 0], frame_rate=FPS),
        "6": node("EmptyLTXVLatentVideo", width=width, height=height, length=frames, batch_size=1),
        "7": node("LTXVScheduler", steps=steps, max_shift=2.05, base_shift=.95,
                  stretch=True, terminal=.1, latent=["6", 0]),
        "8": node("KSamplerSelect", sampler_name="res_multistep"),
        "9": node("SamplerCustom", model=["1", 0], add_noise=True, noise_seed=seed, cfg=3.0,
                  positive=["5", 0], negative=["5", 1], sampler=["8", 0],
                  sigmas=["7", 0], latent_image=["6", 0]),
        "10": node("VAEDecodeTiled", samples=["9", 0], vae=["1", 2],
                   tile_size=256, overlap=64, temporal_size=32, temporal_overlap=8),
        "11": node("CreateVideo", images=["10", 0], fps=FPS),
        OUTPUT_NODE: node("SaveVideo", video=["11", 0], filename_prefix="FalconAI/LTX",
                          format="mp4", **({"format.codec": "auto"} if dynamic_codec else {"codec": "auto"})),
    }


def _installed(definition, field, names, folder):
    spec = definition["input"]["required"][field]
    choices = spec[0] if isinstance(spec[0], list) else spec[1].get("options", [])
    for name in names:
        for path in choices:
            if isinstance(path, str) and PureWindowsPath(path).name == name:
                return path
    raise ValueError(f"Add {names[0]} to ComfyUI/models/{folder}, then refresh ComfyUI.")


class LTXVideo:
    def __init__(self, client, checkpoint, encoder, dynamic_codec):
        self.client = client
        self.checkpoint = checkpoint
        self.encoder = encoder
        self.dynamic_codec = dynamic_codec

    @classmethod
    def connect(cls, stop=lambda: False, gaming=lambda: False, *, client=None):
        media_tools()
        incompatible = None
        for candidate in ([client] if client else [ComfyVideo(8188), ComfyVideo(8000)]):
            check_active(stop, gaming)
            try:
                candidate.require_supported()
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                continue
            except ValueError as exc:
                incompatible = exc
                continue
            break
        else:
            if incompatible is not None:
                raise incompatible
            raise ConnectionError("Start local ComfyUI on port 8188 or 8000, then choose Check LTX setup.")
        definitions = {}
        for node in build_workflow("setup", 0).values():
            kind = node["class_type"]
            if kind in definitions:
                continue
            check_active(stop, gaming)
            definition = candidate.request("/object_info/" + kind).get(kind)
            if not definition:
                raise ValueError("Update ComfyUI to install the core node " + kind + ".")
            definitions[kind] = definition
        checkpoint = _installed(definitions["CheckpointLoaderSimple"], "ckpt_name", [CHECKPOINT], "checkpoints")
        encoder = _installed(definitions["CLIPLoader"], "clip_name", ENCODERS, "text_encoders")
        fmt = definitions["SaveVideo"]["input"]["required"]["format"][0]
        return cls(candidate, checkpoint, encoder, fmt == "COMFY_DYNAMICCOMBO_V3")

    def render(self, prompt, destination, stop, gaming, *, preview=False, seed=None,
               width=WIDTH, height=HEIGHT, frames=FRAMES, steps=STEPS, progress=lambda _: None):
        graph = build_workflow(prompt, secrets.randbits(63) if seed is None else seed,
                               checkpoint=self.checkpoint, encoder=self.encoder,
                               width=width, height=height, frames=frames, steps=steps,
                               dynamic_codec=self.dynamic_codec)
        save = generate if preview else render_to
        return save(self.client, graph, destination, stop, gaming, progress,
                    output_node=OUTPUT_NODE, expected=(width, height, frames))


def scene_prompt(story, index):
    scene = story["scenes"][index]
    return (f"A single continuous shot from an original animated comedy titled {story['title']}. "
            f"The recurring character is introduced this way: {story['lines'][0]} "
            f"Keep its colors, silhouette and proportions consistent. In this shot the setting is "
            f"the {scene['setting']}. The action is {scene['action']}: {story['lines'][index]} "
            "Show the action unfolding from start to finish, with expressive movement, "
            "a clear subject, cinematic lighting, and a vertical composition. No lettering.")


def render_scene(engine, story, index, key, destination, stop, gaming, progress):
    prompt = scene_prompt(story, index)
    count = len(story["scenes"])
    seed = int(key[:15], 16) + index
    label = f"LTX scene {index + 1} of {count}"
    check_active(stop, gaming)
    progress(f"Generating {label}")
    try:
        return engine.render(prompt, destination, stop, gaming, seed=seed)
    except (InvalidClip, VideoJobFailed) as exc:
        check_active(stop, gaming)
        progress(f"Retrying {label} once. {exc}")
        return engine.render(prompt, destination, stop, gaming, seed=seed + count)
