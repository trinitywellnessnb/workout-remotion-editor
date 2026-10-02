"""Phase 2 logic and worker tests without Ultralytics, torch, or model downloads."""
from __future__ import annotations

import copy
import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "workout-remotion-editor/scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_video import analyze
from analyzers.base import Result, Unavailable, run_provider
from analyzers.object_tracking import ObjectTracking, tracking_intervals
from analyzers.object_tracking_worker import rotation_degrees, run as worker_run
from analyzers.visual_evidence import crop_risks, derive, valid_box
from validate_analysis import load_json, validate_document


def person(track=1, box=None, label="person"):
    return {"track_id": track, "class_id": 0 if label == "person" else 13,
            "class_name": label, "bbox": box or [0.2, 0.1, 0.6, 0.9], "confidence": 0.8}


def samples(objects=None, count=10, interval="interval:0"):
    objects = [person()] if objects is None else objects
    return [{"time": i * 0.2, "sample_index": i, "frame_index": i * 6,
             "interval_id": interval, "detections": copy.deepcopy(objects)} for i in range(count)]


def intervals():
    return [{"id": "interval:0", "start": 0, "end": 2, "sample_interval": 0.2,
             "scene_id": None, "reason": "fixture lifecycle"}]


class FixtureProvider:
    name, category, upstream, version = "fixture", "object_tracking", "fixture", "1"
    configuration = {"coordinate_space": "display_normalized_xyxy"}

    def __init__(self, observations=None, crop=None):
        self.observations = samples() if observations is None else observations
        self.crop = crop

    def analyze(self, source, timeout):
        evidence = derive(self.observations, intervals(), self.crop)
        evidence["tracking_intervals"] = intervals()
        return Result(evidence=evidence)


def document(provider=None):
    with patch("analyzers.media_probe.executable", side_effect=Unavailable("missing")):
        return analyze([Path("raw.mp4")], supplied_metadata={"duration": 2, "width": 1920, "height": 1080},
                       providers=[provider or FixtureProvider()])


class VisualTests(unittest.TestCase):
    def test_one_tracked_athlete_and_persistent_identity(self):
        evidence = document()["evidence"]
        self.assertEqual(len(evidence["tracked_entities"]), 1)
        self.assertEqual(len(evidence["detections"]), 10)
        self.assertEqual(evidence["subject_candidates"][0]["state"], "candidate")
        self.assertEqual(len({d["entity_id"] for d in evidence["detections"]}), 1)
        self.assertEqual(evidence["subject_candidates"][0]["confidence"], None)

    def test_multiple_people_and_ambiguity(self):
        data = document(FixtureProvider(samples([person(1), person(2, [0.65, 0.1, 0.95, 0.9])])))
        self.assertEqual(len(data["evidence"]["tracked_entities"]), 2)
        self.assertTrue(all(c["state"] == "ambiguous" for c in data["evidence"]["subject_candidates"]))
        self.assertIn("primary_athlete_ambiguous", data["evidence"]["crop_constraints"][0]["risk_flags"])

    def test_larger_crossing_person_does_not_replace_incumbent(self):
        observations = samples()
        for index in (3, 4):
            observations[index]["detections"].append(person(2, [0.01, 0.01, 0.99, 0.99]))
        evidence = document(FixtureProvider(observations))["evidence"]
        selected = [c for c in evidence["subject_candidates"] if c["state"] == "candidate"]
        self.assertEqual(len(selected), 1)
        self.assertTrue(selected[0]["entity_id"].endswith("track:1"))

    def test_background_crowd_and_mirror_remain_ambiguous(self):
        observations = samples([person(1), person(2), person(3)])
        evidence = document(FixtureProvider(observations))["evidence"]
        self.assertFalse(any(c["state"] == "candidate" for c in evidence["subject_candidates"]))

    def test_track_loss_is_observed_gap_not_invented_box(self):
        observations = samples()
        observations[4]["detections"] = []
        evidence = document(FixtureProvider(observations))["evidence"]
        self.assertEqual(len(evidence["tracked_entities"][0]["gaps"]), 1)
        missing = next(c for c in evidence["crop_constraints"] if abs(c["time"] - 0.8) < 1e-6)
        self.assertIn("athlete_track_lost", missing["risk_flags"])
        self.assertNotIn("minimum_visible_region", missing)

    def test_brief_exit_does_not_change_subject(self):
        observations = samples()
        for index in (7, 8, 9):
            observations[index]["detections"] = []
        candidates = document(FixtureProvider(observations))["evidence"]["subject_candidates"]
        self.assertEqual(candidates[0]["state"], "candidate")

    def test_scene_boundary_reuses_raw_id_without_reusing_entity(self):
        first = samples(count=5)
        second = samples(count=5, interval="interval:1")
        for item in second:
            item["time"] += 1
            item["sample_index"] += 5
        spans = intervals()
        spans[0]["end"] = 1
        spans.append({**spans[0], "id": "interval:1", "start": 1, "end": 2})
        result = derive(first + second, spans)
        self.assertEqual(len(result["tracked_entities"]), 2)
        self.assertNotEqual(result["tracked_entities"][0]["id"], result["tracked_entities"][1]["id"])

    def test_supported_object_is_candidate_not_fabricated_equipment_identity(self):
        evidence = document(FixtureProvider(samples([person(), person(2, [0.4, 0.6, 0.8, 0.95], "bench")])))["evidence"]
        self.assertTrue(any(r["kind"] == "equipment_candidate" for r in evidence["visual_regions"]))
        self.assertTrue(any(d["class_name"] == "bench" and d["category"] == "object" for d in evidence["detections"]))
        self.assertNotIn("barbell", json.dumps(evidence))

    def test_custom_and_unknown_equipment_keep_model_labels(self):
        observations = samples([person(), person(2, [0.4, 0.6, 0.8, 0.95], "unknown_equipment"),
                                person(3, [0.4, 0.6, 0.8, 0.95], "custom_handle")])
        evidence = derive(observations, intervals(), equipment_classes=["custom_handle"])
        self.assertEqual({d["category"] for d in evidence["detections"]},
                         {"person", "unknown_equipment", "equipment"})
        self.assertTrue(any(d["class_name"] == "custom_handle" for d in evidence["detections"]))

    def test_no_detection_does_not_fabricate_unknown_equipment(self):
        evidence = document(FixtureProvider(samples([])))["evidence"]
        self.assertEqual(evidence["detections"], [])
        self.assertEqual(evidence["tracked_entities"], [])
        self.assertNotIn("minimum_visible_region", evidence["crop_constraints"][0])

    def test_untracked_detection_is_not_a_persistent_athlete(self):
        evidence = document(FixtureProvider(samples([person(None)])))["evidence"]
        self.assertEqual(evidence["tracked_entities"], [])
        self.assertNotIn("entity_id", evidence["detections"][0])

    def test_valid_and_invalid_boxes(self):
        self.assertTrue(valid_box([0, 0, 1, 1]))
        for box in ([0, 0, 0, 1], [0.8, 0, 0.2, 1], [-0.1, 0, 1, 1], [0, 0, 1, 1.1],
                    [True, 0, 1, 1], [0, 0, float("nan"), 1], [0, 1]):
            self.assertFalse(valid_box(box), box)
        data = document()
        data["evidence"]["detections"][0]["bbox"]["x2"] = 0.1
        for basic in (False, True):
            self.assertTrue(validate_document(data, basic=basic))

    def test_confidence_bounds_and_nonfinite_scores(self):
        for value in (-0.1, 1.1, True, float("inf")):
            data = document()
            data["evidence"]["detections"][0]["confidence"] = value
            self.assertTrue(validate_document(data, basic=True))

    def test_crop_geometry_and_serialization(self):
        risks = crop_risks([0.2, 0.1, 0.6, 0.9], [[0.6, 0.4, 0.9, 0.6]], [0.1, 0, 0.65, 0.7])
        self.assertIn("athlete_bottom_cutoff", risks["risk_flags"])
        self.assertIn("tracked_equipment_outside_crop", risks["risk_flags"])
        self.assertLess(risks["box_coverage"], 1)
        data = document(FixtureProvider(crop=[0.1, 0, 0.65, 0.7]))
        self.assertEqual(validate_document(json.loads(json.dumps(data))), [])
        self.assertEqual(validate_document(data, basic=True), [])

    def test_reference_and_lifecycle_validation(self):
        for collection, key, value in (("detections", "entity_id", "missing"),
                                        ("tracked_entities", "last_seen", 3),
                                        ("visual_regions", "interval_id", "missing"),
                                        ("crop_constraints", "region_ids", ["missing"])):
            data = document()
            data["evidence"][collection][0][key] = value
            self.assertTrue(validate_document(data, basic=True))

    def test_legacy_compatibility_and_version_gate(self):
        root = Path(__file__).with_name("fixtures")
        for name in ("legacy-valid.json", "scene-valid.json", "activity-valid.json"):
            self.assertEqual(validate_document(load_json(root / name)), [])
        data = document()
        data["schema_version"] = "2.4"
        self.assertTrue(validate_document(data))

    def test_analyzer_provenance_and_references_are_namespaced(self):
        data = document()
        run = data["evidence"]["runs"][-1]
        self.assertEqual(run["provider"], "fixture")
        self.assertEqual(run["category"], "object_tracking")
        self.assertEqual(run["version"], "1")
        self.assertTrue(data["evidence"]["detections"][0]["entity_id"].startswith(run["id"] + ":"))
        self.assertEqual(validate_document(data), [])

    def test_provider_context_isolated_and_prior_scene_reference_preserved(self):
        class ContextProvider(FixtureProvider):
            consumes_context = True

            def analyze(self, source, timeout, context):
                self.seen_context = copy.deepcopy(context)
                context.clear()
                return super().analyze(source, timeout)
        provider = ContextProvider()
        data = document(provider)
        self.assertTrue(provider.seen_context["runs"])
        self.assertEqual(len(data["evidence"]["runs"]), 2)
        spans, warnings = tracking_intervals({"id": "s", "duration": 2}, {
            "scenes": [{"id": "prior:scene", "source_id": "s", "run_id": "prior",
                        "start": 0, "end": 2}]}, 5, False)
        self.assertEqual(spans[0]["scene_id"], "prior:scene")
        self.assertFalse(warnings)

    def test_invalid_provider_output_is_quarantined(self):
        observations = samples()
        observations[0]["detections"][0]["confidence"] = 2
        data = document(FixtureProvider(observations))
        self.assertEqual(data["evidence"]["runs"][-1]["status"], "failed")
        self.assertNotIn("detections", data["evidence"])
        self.assertEqual(validate_document(data), [])


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.model = Path(self.temporary.name) / "tiny.pt"
        self.model.write_bytes(b"mock weights")
        self.source = {"id": "s", "path": "raw.mp4", "duration": 2, "fps": 30}

    def tearDown(self):
        self.temporary.cleanup()

    def invoke(self, data=None, failure=None, version="8.4.171"):
        with patch("analyzers.object_tracking.importlib.util.find_spec", return_value=object()), patch(
            "analyzers.object_tracking.metadata.version", return_value=version), patch(
            "analyzers.object_tracking.command", side_effect=failure,
            return_value=json.dumps(data or {"status": "success", "samples": samples()})) as invoke:
            run, result = run_provider(ObjectTracking(self.model), self.source, 1)
        return run, result, invoke

    def test_missing_dependency(self):
        with patch("analyzers.object_tracking.importlib.util.find_spec", return_value=None):
            run, result = run_provider(ObjectTracking(self.model), self.source, 1)
        self.assertEqual(run["status"], "unavailable")
        self.assertTrue(run["fallback"])
        self.assertFalse(result.evidence)

    def test_model_load_failure(self):
        run, result, _ = self.invoke({"status": "failed", "errors": ["Model load failed"]})
        self.assertEqual(run["status"], "failed")
        self.assertIn("Model load failed", run["errors"])
        self.assertFalse(result.evidence)

    def test_inference_failure_and_partial_results(self):
        run, result, _ = self.invoke({"status": "partial", "samples": samples(),
                                     "errors": ["Inference failed after observed samples"]})
        self.assertEqual(run["status"], "partial")
        self.assertTrue(result.evidence["detections"])
        run, result, _ = self.invoke(failure=RuntimeError("CUDA failed"))
        self.assertEqual(run["status"], "failed")
        self.assertFalse(result.evidence)

    def test_missing_model_unknown_duration_and_untested_version(self):
        self.model.unlink()
        run, _, _ = self.invoke()
        self.assertEqual(run["status"], "skipped")
        self.model.write_bytes(b"mock")
        self.source["duration"] = None
        run, _, _ = self.invoke()
        self.assertEqual(run["status"], "skipped")
        self.source["duration"] = 2
        run, _, _ = self.invoke(version="9")
        self.assertEqual(run["status"], "skipped")

    def test_worker_environment_is_local_and_has_no_shell(self):
        _, _, invoke = self.invoke()
        args, kwargs = invoke.call_args
        self.assertEqual(kwargs["env"]["YOLO_OFFLINE"], "true")
        self.assertEqual(kwargs["env"]["YOLO_AUTOINSTALL"], "false")
        self.assertNotIn("ULTRALYTICS_API_KEY", kwargs["env"])
        self.assertIsInstance(args[0], list)
        self.assertEqual(json.loads(args[0][-1])["configuration"]["model"], str(self.model.resolve()))

    def test_graceful_fallback_preserves_pipeline(self):
        with patch("analyzers.object_tracking.importlib.util.find_spec", return_value=None), patch(
            "analyzers.media_probe.executable", side_effect=Unavailable("missing")):
            data = analyze([Path("raw.mp4")], supplied_metadata={"duration": 2},
                           providers=[ObjectTracking(self.model), FixtureProvider()])
        self.assertEqual([r["status"] for r in data["evidence"]["runs"]], ["partial", "unavailable", "success"])
        self.assertTrue(data["evidence"]["detections"])
        self.assertEqual(data["segments"], [])


class Tensor:
    def __init__(self, values):
        self.values = values

    def cpu(self):
        return self

    def tolist(self):
        return self.values


class WorkerTests(unittest.TestCase):
    def worker(self, *, fail_at=None, device="cpu", rotation=0, times=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        model_path = Path(temporary.name) / "tiny.pt"
        model_path.write_bytes(b"mock")
        timestamps = times or [0, 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4, 1.6, 1.8]
        frames = [SimpleNamespace(pts=t + 7, time_base=1, to_ndarray=lambda **k: SimpleNamespace(shape=(1080, 1920, 3)))
                  for t in timestamps]
        stream = SimpleNamespace(start_time=7, time_base=1)
        container = SimpleNamespace(streams=SimpleNamespace(video=[stream]), decode=lambda _: iter(frames),
                                    close=lambda: None)
        calls = []
        class Model:
            names, task = {0: "person", 13: "bench"}, "detect"

            def __init__(self, *args, **kwargs):
                pass

            def track(self, image, **kwargs):
                calls.append(kwargs)
                if fail_at is not None and len(calls) >= fail_at and kwargs["device"] != "cpu":
                    raise RuntimeError("GPU unavailable")
                if fail_at is not None and len(calls) == fail_at and device == "cpu":
                    raise RuntimeError("inference failure")
                boxes = SimpleNamespace(is_track=True, id=Tensor([1]), xyxyn=Tensor([[0.2, 0.1, 0.6, 0.9]]),
                                        conf=Tensor([0.8]), cls=Tensor([0]))
                return [SimpleNamespace(boxes=boxes, names=self.names)]
        modules = {"av": SimpleNamespace(open=lambda _: container),
                   "numpy": SimpleNamespace(ascontiguousarray=lambda a: a, rot90=lambda a, k: a),
                   "ultralytics": SimpleNamespace(__version__="8.4.171", YOLO=Model,
                                                   settings=SimpleNamespace(update=lambda _: None))}
        payload = {"source": {"path": "raw.mp4", "duration": 2, "rotation": rotation},
                   "configuration": {"model": str(model_path), "device": device, "tracker": "bytetrack",
                                     "equipment_classes": [], "sample_fps": 5, "full_frame": False,
                                     "imgsz": 640, "detector_confidence": 0.1}, "intervals": intervals()}
        with patch.dict(sys.modules, modules), patch.object(socket, "socket"), patch.object(
            socket, "create_connection"), patch.object(socket, "getaddrinfo"):
            # A real socket class is needed by the worker's blocking subclass.
            socket.socket = self.socket_type
            result = worker_run(payload)
        return result, calls

    def setUp(self):
        self.socket_type = socket.socket

    def test_pts_nonzero_origin_and_sampling(self):
        result, calls = self.worker(times=[0, 0.05, 0.21, 0.41, 0.61, 0.81, 1.01, 1.21, 1.41, 1.61, 1.81])
        self.assertEqual(result["status"], "success")
        self.assertAlmostEqual(result["samples"][1]["time"], 0.21)
        self.assertFalse(calls[0]["persist"])
        self.assertTrue(calls[1]["persist"])
        self.assertGreater(result["statistics"]["samples_skipped"], 0)
        self.assertEqual(len(result["statistics"]["model_sha256"]), 64)

    def test_gpu_failure_retries_cpu(self):
        result, calls = self.worker(fail_at=1, device="mps")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["statistics"]["device_used"], "cpu")
        self.assertTrue(result["warnings"])
        self.assertEqual(calls[1]["device"], "cpu")

    def test_worker_inference_failure_retains_only_observed_samples(self):
        result, _ = self.worker(fail_at=4)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["samples"]), 3)
        self.assertTrue(result["errors"])

    def test_gap_reset_distinguishes_reused_raw_id(self):
        result, calls = self.worker(times=[0, 0.2, 1.2, 1.4])
        self.assertFalse(calls[2]["persist"])
        self.assertNotEqual(result["samples"][0]["detections"][0]["track_id"],
                            result["samples"][2]["detections"][0]["track_id"])

    def test_rotation_supported_and_nonright_angle_rejected(self):
        self.assertEqual(rotation_degrees(-90), 270)
        with self.assertRaises(ValueError):
            rotation_degrees(15)
        result, _ = self.worker(rotation=15)
        self.assertEqual(result["status"], "failed")


if __name__ == "__main__":
    unittest.main()
