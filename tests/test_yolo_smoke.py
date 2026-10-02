"""Opt-in real-model smoke test: RUN_YOLO_SMOKE=1 YOLO_MODEL=/path/model.pt."""
from __future__ import annotations

import os
import unittest
from pathlib import Path


@unittest.skipUnless(os.environ.get("RUN_YOLO_SMOKE") == "1", "real YOLO smoke is opt-in")
class RealYoloSmokeTest(unittest.TestCase):
    def test_local_model_inference_and_tracking(self):
        model_path = Path(os.environ["YOLO_MODEL"])
        self.assertTrue(model_path.is_file(), "YOLO_MODEL must be a local model file")
        import numpy
        from ultralytics import YOLO
        model = YOLO(str(model_path))
        frame = numpy.zeros((320, 320, 3), dtype=numpy.uint8)
        result = model.track(frame, persist=False, tracker="bytetrack.yaml",
                             device=os.environ.get("YOLO_DEVICE", "cpu"), verbose=False)
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
