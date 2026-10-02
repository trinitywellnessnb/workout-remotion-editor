"""Separate real-tool tests; core validation does not install media analyzers."""
from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "workout-remotion-editor/scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_video import analyze
from analyzers.motion_activity import MotionActivity
from analyzers.scene import Scene
from validate_analysis import validate_document


class RealToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = [tool for tool in ("ffmpeg", "ffprobe", "auto-editor") if not shutil.which(tool)]
        if importlib.util.find_spec("scenedetect") is None:
            missing.append("scenedetect")
        if importlib.util.find_spec("av") is None:
            missing.append("av")
        if missing:
            message = "optional integrations unavailable: " + ", ".join(missing)
            if os.environ.get("REQUIRE_ANALYZERS") == "1":
                raise RuntimeError(message)
            raise unittest.SkipTest(message)
        cls.workspace = tempfile.TemporaryDirectory()
        cls.video = Path(cls.workspace.name) / "raw.mp4"
        inputs = [
            "color=black:s=160x120:r=30:d=3",
            "color=white:s=160x120:r=30:d=1",
            "testsrc2=s=160x120:r=30:d=2",
            "color=black:s=160x120:r=30:d=2",
            "sine=frequency=440:sample_rate=48000:duration=4",
            "anullsrc=r=48000:cl=mono:d=4",
        ]
        args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        for source in inputs:
            args.extend(["-f", "lavfi", "-i", source])
        args.extend(["-filter_complex", "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0[v];"
                      "[4:a][5:a]concat=n=2:v=0:a=1[a]",
                     "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", str(cls.video)])
        subprocess.run(args, check=True, timeout=60)
        cls.original_hash = hashlib.sha256(cls.video.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def test_real_motion_audio_and_scene_evidence_without_source_edits(self):
        data = analyze([self.video], providers=[Scene("content"), MotionActivity()], timeout=60)
        self.assertEqual(validate_document(data), [])
        self.assertEqual(data["segments"], [])
        runs = data["evidence"]["runs"]
        self.assertTrue(all(run["status"] == "success" for run in runs), runs)
        boundaries = data["evidence"]["scene_boundaries"]
        self.assertTrue(any(abs(item["time"] - 3) < 0.15 for item in boundaries), boundaries)
        regions = data["evidence"]["activity_regions"]
        self.assertTrue(any(item["type"] == "motion_active" and item["end"] > 4.5 for item in regions), regions)
        self.assertTrue(any(item["type"] == "audio_inactive" and item["end"] > 7.5 for item in regions), regions)
        candidates = data["evidence"]["candidate_dead_time"]
        self.assertTrue(any(item["start"] < 0.1 and 2.8 < item["end"] < 3.1 for item in candidates), candidates)
        self.assertEqual(hashlib.sha256(self.video.read_bytes()).hexdigest(), self.original_hash)
        self.assertEqual(sorted(path.name for path in self.video.parent.iterdir()), ["raw.mp4"])

    def test_real_adaptive_and_fade_detectors(self):
        for detector in ("adaptive", "threshold"):
            with self.subTest(detector=detector):
                data = analyze([self.video], providers=[Scene(detector)], timeout=60)
                self.assertEqual(validate_document(data), [])
                self.assertEqual(data["evidence"]["runs"][-1]["status"], "success")
                self.assertTrue(data["evidence"]["scene_boundaries"])

    def test_vfr_uses_source_seconds(self):
        video = self.video.parent / "vfr.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(self.video),
                        "-vf", "select=if(lt(t\\,4)\\,not(mod(n\\,2))\\,1)", "-fps_mode", "vfr",
                        "-an", str(video)], check=True, timeout=60)
        try:
            data = analyze([video], providers=[Scene("content"), MotionActivity()], timeout=60)
            self.assertEqual(validate_document(data), [])
            self.assertEqual(data["evidence"]["runs"][1]["status"], "success", data["evidence"]["runs"])
            self.assertTrue(any(abs(item["time"] - 3) < 0.2
                                for item in data["evidence"]["scene_boundaries"]))
            self.assertEqual(data["evidence"]["runs"][-1]["status"], "success")
            self.assertFalse(any(item["type"].startswith("audio")
                                 for item in data["evidence"]["activity_regions"]))
        finally:
            video.unlink()

    def test_actual_unsupported_media_graceful_fallback(self):
        source = self.video.parent / "unsupported.mp4"
        source.write_bytes(b"not a media container")
        try:
            data = analyze([source], timeout=30)
            self.assertEqual(validate_document(data), [])
            self.assertIsNone(data["sources"][0]["duration"])
            self.assertEqual(data["segments"], [])
            self.assertTrue(all(run["fallback"] for run in data["evidence"]["runs"]))
            self.assertEqual(source.read_bytes(), b"not a media container")
        finally:
            source.unlink()


if __name__ == "__main__":
    unittest.main()
