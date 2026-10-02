"""Explicitly gated local real-model smoke test."""

import os
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "workout-remotion-editor/scripts"
sys.path.insert(0, str(SCRIPTS))
from analyzers.pose import MMPoseProvider


@unittest.skipUnless(
    os.environ.get("REQUIRE_POSE_ANALYZER") == "1",
    "set REQUIRE_POSE_ANALYZER=1 with local assets",
)
class PoseSmoke(unittest.TestCase):
    def test_local_assets_declared(self):
        config, checkpoint = (
            os.environ.get("POSE_CONFIG"),
            os.environ.get("POSE_CHECKPOINT"),
        )
        self.assertTrue(config and Path(config).is_file())
        self.assertTrue(checkpoint and Path(checkpoint).is_file())
        provider = MMPoseProvider(config, checkpoint)
        self.assertEqual(provider.category, "pose")
        # Full inference is exercised by analyze_video against a caller-provided video;
        # this gate verifies import/model acquisition without asserting keypoint values.
        import mmpose.apis

        mmpose.apis.init_model(config, checkpoint, device="cpu")


if __name__ == "__main__":
    unittest.main()
