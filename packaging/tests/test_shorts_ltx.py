"""Network and media contract tests with a loopback ComfyUI fixture."""
from contextlib import ExitStack
import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import urllib.parse
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comfy_video
import ltx_video as ltx
import shorts_controls
import shorts_mode
import video_workflow


class LTXContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.store.cleanup)
        cls.clip = Path(cls.store.name) / "fixture.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=96x160:r=24",
                        "-frames:v", "49", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(cls.clip)], check=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.calls = []
        self.models = [ltx.CHECKPOINT]
        self.version = "0.12.3"
        self.status = "success"
        self.filename = "sample.mp4"
        self.served = self.clip.read_bytes()
        self.dynamic = False
        self.redirect = False
        self.bad_ack = False
        self.stop = threading.Event()
        owner = self

        class API(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, obj):
                raw = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                route = urllib.parse.urlsplit(self.path).path
                owner.calls.append((route, None))
                if route == "/system_stats":
                    self.reply({"system": {"comfyui_version": owner.version}})
                elif route.startswith("/object_info/"):
                    kind = route.split("/")[-1]
                    fields = {"ckpt_name": [owner.models], "clip_name": ["COMBO", {"options": list(ltx.ENCODERS)}],
                              "format": ["COMFY_DYNAMICCOMBO_V3"] if owner.dynamic else [["auto", "mp4"]]}
                    self.reply({kind: {"input": {"required": fields}}})
                elif route.startswith("/history/"):
                    if owner.status == "pending":
                        owner.stop.set()
                        self.reply({})
                    else:
                        out = {"filename": owner.filename, "type": "output", "subfolder": "FalconAI"}
                        self.reply({route.split("/")[-1]: {
                            "status": {"status_str": owner.status, "completed": True},
                            "outputs": {"noise": {"images": [dict(out, filename="wrong.mp4")]},
                                        ltx.OUTPUT_NODE: {"images": [out]}}}})
                elif route == "/view":
                    owner.query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    if owner.redirect:
                        self.send_response(302)
                        self.send_header("Location", "/redirect-destination")
                        self.end_headers()
                    else:
                        self.reply(owner.served)
                else:
                    self.send_error(404)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                owner.calls.append((self.path, body))
                if self.path == "/prompt":
                    self.reply({"prompt_id": "other-job" if owner.bad_ack else body["prompt_id"], "node_errors": {}})
                else:
                    self.reply(b"")

        api = ThreadingHTTPServer(("127.0.0.1", 0), API)
        thread = threading.Thread(target=api.serve_forever, kwargs={"poll_interval": .03}, daemon=True)
        thread.start()
        self.addCleanup(api.server_close)
        self.addCleanup(api.shutdown)
        self.client = comfy_video.ComfyVideo(api.server_port)

    def generate(self, **opts):
        engine = ltx.LTXVideo.connect(client=self.client)
        return engine.render("A falcon banks left.", self.root, self.stop.is_set, lambda: False,
                             preview=True, width=96, height=160, frames=49, **opts)

    def test_job_download_decode_and_atomic_review(self):
        video = self.generate(seed=17)
        self.assertEqual(video.read_bytes(), self.clip.read_bytes())
        self.assertTrue((video.parent / "REVIEW_REQUIRED.txt").is_file())
        self.assertEqual(self.query, {"filename": ["sample.mp4"], "type": ["output"], "subfolder": ["FalconAI"]})
        graph = next(body["prompt"] for path, body in self.calls if path == "/prompt")
        self.assertEqual(graph["9"]["inputs"]["noise_seed"], 17)
        self.assertEqual(graph["3"]["inputs"]["text"], "A falcon banks left.")
        self.assertEqual(graph["10"]["inputs"]["samples"], ["9", 0])
        self.assertFalse((video.parent / "upload_attempt.json").exists())

    def test_concurrent_output_is_never_overwritten(self):
        engine = ltx.LTXVideo.connect(client=self.client)
        target = self.root / "clip.mp4"
        def progress(message):
            if message == "Verifying the generated video":
                target.write_bytes(b"existing output")
        with self.assertRaises(FileExistsError):
            engine.render("A falcon banks left.", target, self.stop.is_set,
                          lambda: False, width=96, height=160, frames=49,
                          progress=progress)
        self.assertEqual(target.read_bytes(), b"existing output")
        self.assertEqual(list(self.root.iterdir()), [target])

    def test_dynamic_save_and_models_in_subfolder(self):
        self.dynamic = True
        self.models = ["video/" + ltx.CHECKPOINT]
        self.generate()
        graph = next(body["prompt"] for path, body in self.calls if path == "/prompt")
        self.assertEqual(graph["1"]["inputs"]["ckpt_name"], self.models[0])
        self.assertEqual(graph["12"]["inputs"]["format.codec"], "auto")

    def test_missing_models_or_legacy_interrupt_stop_before_submission(self):
        self.models = []
        with self.assertRaisesRegex(ValueError, "checkpoints"):
            self.generate()
        self.version = "0.3.1"
        with self.assertRaisesRegex(ValueError, "job-specific"):
            self.generate()
        self.assertNotIn("/prompt", [p for p, _ in self.calls])
        self.assertFalse(list(self.root.iterdir()))

    def test_stop_while_queued_only_addresses_own_job(self):
        self.status = "pending"
        with self.assertRaises(InterruptedError):
            self.generate()
        submitted = next(b["prompt_id"] for p, b in self.calls if p == "/prompt")
        self.assertEqual([(p, b) for p, b in self.calls if p in ("/queue", "/interrupt")],
                         [("/queue", {"delete": [submitted]}), ("/interrupt", {"prompt_id": submitted})])
        self.assertFalse(list(self.root.iterdir()))

    def test_gaming_and_stop_prevent_model_requests(self):
        for stop, gaming in ((True, False), (False, True)):
            with self.assertRaises(InterruptedError):
                ltx.LTXVideo.connect(lambda: stop, lambda: gaming, client=self.client)
        self.assertEqual(self.calls, [])

    def test_error_history_and_ambiguous_submission_leave_no_preview(self):
        self.status = "error"
        with self.assertRaises(RuntimeError):
            self.generate()
        self.bad_ack = True
        with self.assertRaisesRegex(RuntimeError, "accept"):
            self.generate()
        self.assertNotIn("/view", [p for p, _ in self.calls])
        self.assertFalse(list(self.root.iterdir()))

    def test_invalid_media_metadata_redirect_and_size_bound(self):
        self.filename = "../unrelated.mp4"
        with self.assertRaisesRegex(ValueError, "location"):
            self.generate()
        self.filename = "clip.mp4"
        self.redirect = True
        with self.assertRaisesRegex(ValueError, "redirect"):
            self.generate()
        self.assertNotIn("/redirect-destination", [p for p, _ in self.calls])
        self.redirect = False
        with patch.object(video_workflow, "MAX_VIDEO", 24), self.assertRaisesRegex(ValueError, "exceeds"):
            self.generate()
        self.served = b"invalid media"
        with self.assertRaisesRegex(ValueError, "undecodable"):
            self.generate()
        self.assertFalse(list(self.root.iterdir()))

    def test_output_geometry_and_graph_bounds(self):
        engine = ltx.LTXVideo.connect(client=self.client)
        with self.assertRaisesRegex(ValueError, "frame count"):
            engine.render("hi", self.root, lambda: False, lambda: False, preview=True)
        self.assertFalse(list(self.root.iterdir()))
        for opts in (dict(frames=18), dict(width=321), dict(steps=0)):
            with self.assertRaises(ValueError):
                ltx.build_workflow("hi", 0, **opts)

    def test_frozen_frames_never_become_a_reviewable_preview(self):
        still = self.root / "still.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=purple:s=96x160:r=24",
                        "-frames:v", "49", "-c:v", "libx264", str(still)], check=True)
        self.served = still.read_bytes()
        with self.assertRaisesRegex(ValueError, "identical"):
            self.generate()
        self.assertEqual(list(self.root.iterdir()), [still])

    def test_scene_retries_only_after_a_confirmed_failure(self):
        story = {"title": "Moon Mail", "lines": ["A bird flies."] * 6,
                 "scenes": [{"setting": "moon", "action": "jump"}] * 6}
        def render(engine):
            return ltx.render_scene(engine, story, 2, "abcdef1234567890", self.root / "clip.mp4",
                                    self.stop.is_set, lambda: False, lambda message: None)
        for failure in (comfy_video.VideoJobFailed("sampler failed"), video_workflow.InvalidClip("bad MP4")):
            with self.subTest(failure=failure):
                engine = Mock()
                engine.render.side_effect = [failure, failure]
                with self.assertRaises(type(failure)):
                    render(engine)
                self.assertEqual(engine.render.call_count, 2)
                first, retry = engine.render.call_args_list
                self.assertEqual(first.args, retry.args)
                self.assertEqual(retry.kwargs["seed"], first.kwargs["seed"] + 6)
        for failure in (ConnectionError("lost submission"), TimeoutError(), InterruptedError(),
                        RuntimeError("out of memory"), ValueError("invalid output path"), FileExistsError()):
            with self.subTest(failure=failure):
                engine = Mock()
                engine.render.side_effect = failure
                with self.assertRaises(type(failure)):
                    render(engine)
                engine.render.assert_called_once()
        def stop_before_retry(*args, **kwargs):
            self.stop.set()
            raise video_workflow.InvalidClip("bad MP4")
        engine = Mock()
        engine.render.side_effect = stop_before_retry
        with self.assertRaises(InterruptedError):
            render(engine)
        engine.render.assert_called_once()

    def test_six_ai_scenes_preserve_narration_captions_and_daily_review(self):
        out = self.root / "shorts"
        day = datetime.date(2026, 1, 1)
        story = {"title": "Moon Mail", "lines": ["A tiny bird delivers mail across the quiet moon."] * 6,
                 "scenes": [{"setting": "moon", "action": "jump"}] * 6}
        attempted = []
        def render(prompt, target, *args, **kwargs):
            attempted.append(target.name)
            if target.name == "ltx2.mp4" and attempted.count(target.name) == 1:
                raise video_workflow.InvalidClip("frames were identical")
            shutil.copy2(self.clip, target)
        engine = Mock()
        engine.render.side_effect = render
        real_run = shorts_mode.run
        def media(args, folder):
            if args[0] != "powershell.exe":
                return real_run(args, folder)
            with wave.open(str(folder / "voice.wav"), "wb") as wav:
                wav.setparams((1, 2, 8000, 0, "NONE", ""))
                wav.writeframes(b"\0\0" * 17600)
        self.assertFalse(ltx.daily_enabled(self.root))
        shorts_controls.set_enabled(True, self.root)
        ltx.set_daily(True, self.root)
        with ExitStack() as stack:
            for name, value in (("ROOT", self.root), ("OUT", out), ("run", media)):
                stack.enter_context(patch.object(shorts_mode, name, value))
            stack.enter_context(patch.object(ltx.LTXVideo, "connect", return_value=engine))
            stack.enter_context(patch.object(shorts_mode, "preflight"))
            stack.enter_context(patch.object(shorts_mode, "script", return_value=story))
            stack.enter_context(patch.object(shorts_mode, "render_scene", side_effect=AssertionError("visual fallback")))
            folder = shorts_mode.create("fixture", day)
            self.assertEqual(attempted, [f"ltx{i}.mp4" for i in (0, 1, 2, 2, 3, 4, 5)])
            self.assertEqual(len({c.kwargs["seed"] for c in engine.render.call_args_list}), 7)
            self.assertIn("LTX-Video", (folder / "REVIEW_REQUIRED.txt").read_text())
            self.assertEqual(shorts_controls.ready_video(self.root, day), folder / "draft.mp4")
            self.assertEqual((folder / "captions.srt").read_text().count("-->"), 6)
            self.assertFalse((folder / "upload_attempt.json").exists())
            with self.assertRaises(FileExistsError):
                shorts_mode.create("fixture", day)
            # A failed generation cannot fall through to an illustrated or reviewable draft.
            story["lines"] = ["A second bird paints silver stars on every letter."] * 6
            next_day = day + datetime.timedelta(days=1)
            engine.render.side_effect = RuntimeError("scene failed")
            with self.assertRaisesRegex(RuntimeError, "scene failed"):
                shorts_mode.create("fixture", next_day)
            self.assertTrue((out / next_day.isoformat() / "FAILED.txt").is_file())
            self.assertIsNone(shorts_controls.ready_video(self.root, next_day))
        ltx.set_daily(False, self.root)
        self.assertTrue(shorts_controls.enabled(self.root))
