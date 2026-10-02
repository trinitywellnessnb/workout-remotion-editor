"""Manual real-model API smoke test; never download models or run in core CI."""
from __future__ import annotations

import hashlib
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
from analyzers.object_tracking import ObjectTracking
from validate_analysis import validate_document


@unittest.skipUnless(os.environ.get("WORKOUT_TRACKING_MODEL"), "Separately provisioned local model required")
class TrackingSmoke(unittest.TestCase):
    def test_real_cpu_api_timestamps_provenance_and_source_integrity(self):
        model = Path(os.environ["WORKOUT_TRACKING_MODEL"])
        self.assertTrue(model.is_file(), "Local model must be provisioned before running this test")
        self.assertIsNotNone(shutil.which("ffmpeg"))
        self.assertIsNotNone(shutil.which("ffprobe"))
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "synthetic.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                            "testsrc2=size=320x240:rate=10:duration=2", "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", str(video)], check=True, timeout=30)
            before = hashlib.sha256(video.read_bytes()).hexdigest()
            data = analyze([video], providers=[ObjectTracking(model, device="cpu", sample_fps=5)], timeout=120)
            self.assertEqual(validate_document(data), [])
            run = data["evidence"]["runs"][-1]
            self.assertIn(run["status"], {"success", "no_results"}, run)
            self.assertGreater(run["statistics"]["samples_analyzed"], 0)
            self.assertEqual(run["statistics"]["device_used"], "cpu")
            self.assertEqual(len(run["statistics"]["model_sha256"]), 64)
            self.assertEqual(hashlib.sha256(video.read_bytes()).hexdigest(), before)
            self.assertEqual(data["segments"], [])
            # Synthetic media verifies API/normalization, not gym detection accuracy.


if __name__ == "__main__":
    unittest.main()
