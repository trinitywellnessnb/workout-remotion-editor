"""Deterministic Phase 2 tests; no model, download, GPU, or video decoder required."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "workout-remotion-editor/scripts"
sys.path.insert(0, str(SCRIPTS))

from analyzers.base import Result, Unavailable, run_provider
from analyzers.object_tracking import YoloObjectTracking, derive_visual_evidence, normalize_samples
from analyze_video import analyze
from validate_analysis import validate_document

SOURCE = {"id": "source-1", "path": "/fixture.mp4", "duration": 5, "fps": 30,
          "width": 100, "height": 200,
          "metadata": {"timestamp_origin_verified": True, "audio_streams": 0}}


def detection(track, x1, y1, x2, y2, confidence=.9, category="person"):
    return {"track_id": track, "bounding_box": [x1, y1, x2, y2],
            "confidence": confidence, "category": category}


def samples(primary=True):
    rows = []
    for t in (0, .5, 1, 1.5, 2, 2.5):
        found = [detection(1, 20 + t * 2, 20, 70 + t * 2, 180)] if primary else []
        # A much larger, high-confidence foreground crossing is intentionally brief.
        if t == 1:
            found.append(detection(2, 0, 0, 100, 200, .99))
        rows.append({"timestamp": t, "scene": 0, "detections": found})
    return rows


class EvidenceTests(unittest.TestCase):
    def normalized(self, rows=None):
        evidence = normalize_samples(rows or samples(), SOURCE, "ultralytics-yolo", "fixture.pt")
        evidence.update(derive_visual_evidence(evidence, 2))
        return evidence

    def test_single_person_persistent_track_and_crop_evidence(self):
        evidence = self.normalized()
        self.assertEqual(len(evidence["tracked_entities"]), 2)
        role = evidence["entity_roles"][0]
        self.assertEqual(role["entity_id"], "scene-0:track-1")
        self.assertFalse(role["ambiguous"])
        self.assertEqual(evidence["visual_regions"][0]["coordinate_space"], "normalized_xyxy")
        self.assertTrue(evidence["crop_constraints"][0]["advisory_only"])

    def test_brief_foreground_crossing_does_not_steal_athlete(self):
        self.assertEqual(self.normalized()["entity_roles"][0]["entity_id"], "scene-0:track-1")

    def test_ambiguous_people_preserve_uncertainty(self):
        rows = []
        for t in (0, .5, 1, 1.5):
            rows.append({"timestamp": t, "scene": 0, "detections": [
                detection(1, 10, 20, 45, 180), detection(2, 55, 20, 90, 180)]})
        self.assertTrue(self.normalized(rows)["entity_roles"][0]["ambiguous"])

    def test_track_loss_reacquisition_and_crop_risk(self):
        rows = [{"timestamp": 0, "scene": 0, "detections": [detection(1, 20, 20, 70, 180)]},
                {"timestamp": 2, "scene": 0, "detections": [detection(1, 30, 20, 80, 180)]}]
        evidence = self.normalized(rows)
        self.assertEqual(len(evidence["tracked_entities"]), 1)
        self.assertIn("temporary_subject_loss", evidence["crop_constraints"][0]["risk_reasons"])

    def test_scene_boundary_resets_identity(self):
        rows = [{"timestamp": 0, "scene": 0, "detections": [detection(7, 20, 20, 70, 180)]},
                {"timestamp": 3, "scene": 1, "detections": [detection(7, 20, 20, 70, 180)]}]
        evidence = self.normalized(rows)
        self.assertEqual({e["id"] for e in evidence["tracked_entities"]},
                         {"scene-0:track-7", "scene-1:track-7"})

    def test_supported_model_labels_are_not_rewritten_as_gym_equipment(self):
        rows = [{"timestamp": 0, "scene": 0, "detections": [
            detection(1, 10, 10, 20, 20, category="sports ball"),
            detection(2, 30, 20, 70, 180)]}]
        evidence = self.normalized(rows)
        self.assertEqual(evidence["object_detections"][0]["category"], "sports ball")
        self.assertIn("athlete_equipment_union", {region["type"] for region in evidence["visual_regions"]})

    def test_invalid_bounds_and_confidence_rejected(self):
        for bad in ([20, 20, 10, 40], [-1, 0, 10, 10], [0, 0, 101, 10]):
            rows = [{"timestamp": 0, "detections": [detection(1, *bad)]}]
            if bad == [0, 0, 101, 10]:
                # Decoder rounding beyond the edge is safely clamped.
                self.assertEqual(normalize_samples(rows, SOURCE, "p", "m")["object_detections"][0]["bounding_box"][2], 1)
            else:
                with self.assertRaises(ValueError):
                    normalize_samples(rows, SOURCE, "p", "m")
        with self.assertRaises(ValueError):
            normalize_samples([{"timestamp": 0, "detections": [detection(1, 0, 0, 10, 10, 1.1)]}], SOURCE, "p", "m")


class ProviderFallbackTests(unittest.TestCase):
    def test_missing_dependency_and_model_are_optional(self):
        provider = YoloObjectTracking("missing.pt")
        real_import = __import__
        def missing(name, *args, **kwargs):
            if name == "ultralytics":
                raise ImportError
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=missing):
            run, result = run_provider(provider, SOURCE, 1)
        self.assertEqual(run["status"], "unavailable")
        self.assertFalse(result.evidence)

    def test_model_load_and_inference_failure_fall_back(self):
        class BadUltralytics:
            __version__ = "fixture"
            @staticmethod
            def YOLO(path):
                raise RuntimeError("bad model")
        with patch("analyzers.object_tracking.Path.is_file", return_value=True), patch("analyzers.object_tracking.importlib.import_module", side_effect=lambda name: BadUltralytics if name == "ultralytics" else object()):
            run, _ = run_provider(YoloObjectTracking("bad.pt"), SOURCE, 1)
        self.assertEqual(run["status"], "failed")
        self.assertIn("model load", run["errors"][0])

        class BadModel:
            def track(self, *args, **kwargs):
                raise RuntimeError("inference exploded")
        class GoodUltralytics:
            __version__ = "fixture"
            YOLO = staticmethod(lambda path: BadModel())
        class Capture:
            def __init__(self, path): self.once = False
            def isOpened(self): return True
            def get(self, prop): return 30
            def read(self):
                if self.once:
                    return False, None
                self.once = True
                return True, object()
            def release(self):
                pass
        class CV2:
            CAP_PROP_FPS = 5
            CAP_PROP_POS_MSEC = 0
            VideoCapture = Capture
        def modules(name):
            return GoodUltralytics if name == "ultralytics" else CV2
        with patch("analyzers.object_tracking.Path.is_file", return_value=True), patch(
                "analyzers.object_tracking.importlib.import_module", side_effect=modules):
            run, result = run_provider(YoloObjectTracking("fixture.pt"), SOURCE, 1)
        self.assertEqual(run["status"], "failed")
        self.assertIn("inference failed", run["errors"][0])
        self.assertFalse(result.evidence)

    def test_existing_pipeline_continues_without_yolo(self):
        with patch("analyzers.media_probe.executable", side_effect=Unavailable("missing")), patch(
                "analyzers.object_tracking.importlib.import_module", side_effect=ImportError):
            document = analyze([Path("raw.mp4")], supplied_metadata={k: v for k, v in SOURCE.items()
                               if k not in {"id", "path"}}, providers=[YoloObjectTracking()])
        self.assertEqual(document["evidence"]["runs"][-1]["status"], "unavailable")
        self.assertEqual(validate_document(document), [])


class SemanticValidationTests(unittest.TestCase):
    def document(self):
        evidence = normalize_samples(samples(), SOURCE, "ultralytics-yolo", "fixture.pt")
        evidence.update(derive_visual_evidence(evidence, 2))
        class Fixture:
            name, category, upstream, version, configuration = "fixture-yolo", "object_tracking", "fixture", "1", {}
            def analyze(self, source, timeout):
                return Result(evidence=copy.deepcopy(evidence))
        with patch("analyzers.media_probe.executable", side_effect=Unavailable("missing")):
            return analyze([Path("raw.mp4")], supplied_metadata={k: v for k, v in SOURCE.items()
                           if k not in {"id", "path"}}, providers=[Fixture()])

    def test_valid_serialization_and_provenance(self):
        document = self.document()
        self.assertEqual(validate_document(document), [])
        self.assertEqual(document["evidence"]["runs"][-1]["category"], "object_tracking")

    def test_invalid_detection_bounds_confidence_and_missing_references(self):
        for mutate in (
            lambda d: d["evidence"]["object_detections"][0].update(bounding_box=[.5, .2, .4, .8]),
            lambda d: d["evidence"]["object_detections"][0].update(confidence=1.1),
            lambda d: d["evidence"]["entity_roles"][0].update(entity_id="missing"),
            lambda d: d["evidence"]["crop_constraints"][0].update(region_id="missing")):
            document = self.document()
            mutate(document)
            self.assertTrue(validate_document(document))


if __name__ == "__main__":
    unittest.main()
