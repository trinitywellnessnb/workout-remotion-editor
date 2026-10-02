"""Deterministic Phase 3 tests; no MMPose, network, GPU, or decoder required."""

from __future__ import annotations
import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "workout-remotion-editor/scripts"
sys.path.insert(0, str(SCRIPTS))
from analyzers.base import Result, run_provider
from analyzers.pose import (
    COCO_17,
    MMPoseProvider,
    build_pose_evidence,
    derive_joint_metrics,
    derive_movement_signals,
    normalize_pose_samples,
    smooth_pose_samples,
)
from analyze_video import analyze
from validate_analysis import validate_document

SOURCE = {
    "id": "source-1",
    "path": "/fixture.mp4",
    "duration": 3,
    "fps": 30,
    "width": 100,
    "height": 200,
}


def points(wrist_y=80):
    p = [[50, 20] for _ in COCO_17]
    vals = {
        "left_shoulder": (40, 60),
        "left_elbow": (40, 100),
        "left_wrist": (80, wrist_y),
        "right_shoulder": (60, 60),
        "right_elbow": (60, 100),
        "right_wrist": (20, wrist_y),
        "left_hip": (42, 120),
        "right_hip": (58, 120),
        "left_knee": (42, 155),
        "right_knee": (58, 155),
        "left_ankle": (42, 195),
        "right_ankle": (58, 195),
    }
    for k, v in vals.items():
        p[COCO_17.index(k)] = list(v)
    return p


def sample(t=0, scene="scene-0", entity="foreign:yolo:entity", wrist_y=80, **extra):
    pose = {
        "keypoints": points(wrist_y),
        "scores": [0.9] * 17,
        "association_method": "supplied_roi",
        "association_confidence": 0.9,
        "entity_id": entity,
        "detection_id": "foreign:detection",
        **extra,
    }
    return {"timestamp": t, "scene_id": scene, "poses": [pose]}


class CoreTests(unittest.TestCase):
    def test_partial_low_confidence_and_left_right_preserved(self):
        row = sample()
        row["poses"][0]["keypoints"][9] = None
        row["poses"][0]["scores"][10] = 0.1
        pose = normalize_pose_samples([row], SOURCE)[0]
        by = {p["name"]: p for p in pose["keypoints"]}
        self.assertEqual(by["left_wrist"]["state"], "missing")
        self.assertEqual(by["right_wrist"]["state"], "low_confidence")
        self.assertEqual(pose["entity_id"], "foreign:yolo:entity")

    def test_ambiguous_pose_is_not_forced_to_entity(self):
        pose = normalize_pose_samples([sample(association_ambiguous=True)], SOURCE)[0]
        self.assertNotIn("entity_id", pose)

    def test_pose_without_yolo_is_valid_candidate(self):
        row = sample()
        row["poses"][0].pop("entity_id")
        row["poses"][0].pop("detection_id")
        row["poses"][0]["association_method"] = "pose_only_candidate"
        self.assertNotIn("entity_id", normalize_pose_samples([row], SOURCE)[0])

    def test_bad_coordinate_confidence_and_nonfinite_rejected(self):
        for value, field in [(math.nan, "point"), (1.1, "score")]:
            row = sample()
            if field == "point":
                row["poses"][0]["keypoints"][0][0] = value
            else:
                row["poses"][0]["scores"][0] = value
            with self.assertRaises(ValueError):
                normalize_pose_samples([row], SOURCE)

    def test_outside_frame_is_not_clipped_visible(self):
        row = sample()
        row["poses"][0]["keypoints"][0] = [-2, 20]
        p = normalize_pose_samples([row], SOURCE)[0]["keypoints"][0]
        self.assertEqual(p["state"], "outside_frame")
        self.assertLess(p["x"], 0)

    def test_known_angle_and_complete_provenance(self):
        pose = normalize_pose_samples([sample()], SOURCE)[0]
        metrics = derive_joint_metrics([pose])
        left = next(m for m in metrics if m["metric_name"] == "left_elbow_angle")
        self.assertAlmostEqual(left["value"], 63.434949, 5)
        self.assertEqual(left["pose_sample_id"], pose["id"])
        self.assertEqual(len(left["contributing_landmarks"]), 3)

    def test_low_confidence_suppresses_metric(self):
        row = sample()
        row["poses"][0]["scores"][COCO_17.index("left_elbow")] = 0.1
        metrics = derive_joint_metrics(normalize_pose_samples([row], SOURCE))
        self.assertNotIn("left_elbow_angle", {m["metric_name"] for m in metrics})

    def test_smoothing_reduces_jitter_and_preserves_endpoint(self):
        raw = normalize_pose_samples(
            [sample(i * 0.1, wrist_y=y) for i, y in enumerate((80, 90, 78, 92, 80))],
            SOURCE,
        )
        smooth = smooth_pose_samples(raw)
        rx = [p["x"] for s in raw for p in s["keypoints"] if p["name"] == "left_wrist"]
        sx = [
            p["x"] for s in smooth for p in s["keypoints"] if p["name"] == "left_wrist"
        ]
        # x is stable; y demonstrates jitter reduction.
        ry = [
            next(p["y"] for p in s["keypoints"] if p["name"] == "left_wrist")
            for s in raw
        ]
        sy = [
            next(p["y"] for p in s["keypoints"] if p["name"] == "left_wrist")
            for s in smooth
        ]
        self.assertLess(max(sy) - min(sy), max(ry) - min(ry))
        self.assertLess(abs(sy[-1] - ry[-1]), 0.06)
        self.assertEqual(rx, sx)

    def test_scene_state_reset(self):
        raw = normalize_pose_samples(
            [sample(0, "scene-0"), sample(0.5, "scene-1", wrist_y=120)], SOURCE
        )
        smooth = smooth_pose_samples(raw)
        actual = next(
            p["y"] for p in smooth[1]["keypoints"] if p["name"] == "left_wrist"
        )
        self.assertAlmostEqual(actual, 0.6)

    def test_movement_and_hysteresis(self):
        raw = normalize_pose_samples(
            [sample(i * 0.2, wrist_y=y) for i, y in enumerate((70, 90, 110, 90, 70))],
            SOURCE,
        )
        signals = derive_movement_signals(raw)
        self.assertIn(
            "normalized_trajectory_speed", {s["signal_type"] for s in signals}
        )
        self.assertIn("direction_change_candidate", {s["signal_type"] for s in signals})
        tiny = normalize_pose_samples(
            [sample(i * 0.2, wrist_y=y) for i, y in enumerate((80, 80.1, 80))], SOURCE
        )
        self.assertNotIn(
            "direction_change_candidate",
            {s["signal_type"] for s in derive_movement_signals(tiny)},
        )

    def test_pose_crop_risk(self):
        evidence = build_pose_evidence([sample()], SOURCE)
        self.assertIn(
            "ankle_cutoff_risk", evidence["pose_crop_constraints"][0]["risk_reasons"]
        )


class ProviderTests(unittest.TestCase):
    def test_missing_assets_and_dependency_are_unavailable(self):
        run, _ = run_provider(MMPoseProvider(None, None), SOURCE, 1)
        self.assertEqual(run["status"], "unavailable")
        with (
            patch("analyzers.pose.Path.is_file", return_value=True),
            patch("analyzers.pose.importlib.import_module", side_effect=ImportError),
        ):
            run, _ = run_provider(MMPoseProvider("c.py", "m.pth"), SOURCE, 1)
        self.assertEqual(run["status"], "unavailable")

    def test_model_load_failure_isolated(self):
        class APIs:
            @staticmethod
            def init_model(*a, **k):
                raise RuntimeError("broken")

        def module(n):
            return type("M", (), {"__version__": "x"}) if n == "mmpose" else APIs

        with (
            patch("analyzers.pose.Path.is_file", return_value=True),
            patch("analyzers.pose.importlib.import_module", side_effect=module),
        ):
            run, _ = run_provider(MMPoseProvider("c.py", "m.pth"), SOURCE, 1)
        self.assertEqual(run["status"], "failed")
        self.assertIn("model load", run["errors"][0])


class IdentityRegressionTests(unittest.TestCase):
    def test_phase2_local_references_serialize_identically(self):
        class P:
            name, category, upstream, version, configuration = (
                "p",
                "object_tracking",
                "x",
                "1",
                {},
            )

            def analyze(self, s, t):
                return Result(
                    evidence={
                        "object_detections": [{"id": "d", "entity_id": "e"}],
                        "tracked_entities": [{"id": "e", "detection_ids": ["d"]}],
                    }
                )

        _, result = run_provider(P(), SOURCE, 1, invocation=2)
        prefix = "source-1:object_tracking:p:2:"
        self.assertEqual(
            json.dumps(result.evidence, sort_keys=True),
            json.dumps(
                {
                    "object_detections": [
                        {
                            "id": prefix + "d",
                            "entity_id": prefix + "e",
                            "source_id": "source-1",
                            "run_id": prefix[:-1],
                        }
                    ],
                    "tracked_entities": [
                        {
                            "id": prefix + "e",
                            "detection_ids": [prefix + "d"],
                            "source_id": "source-1",
                            "run_id": prefix[:-1],
                        }
                    ],
                },
                sort_keys=True,
            ),
        )

    def test_cross_run_entity_and_detection_preserved_verbatim(self):
        class P:
            name, category, upstream, version, configuration = (
                "pose",
                "pose",
                "x",
                "1",
                {},
            )

            def analyze(self, s, t):
                return Result(
                    evidence={
                        "pose_samples": [
                            {"id": "p", "entity_id": "old:e", "detection_id": "old:d"}
                        ]
                    }
                )

        _, result = run_provider(P(), SOURCE, 1)
        item = result.evidence["pose_samples"][0]
        self.assertEqual((item["entity_id"], item["detection_id"]), ("old:e", "old:d"))


class SemanticTests(unittest.TestCase):
    def document(self):
        class Y:
            name, category, upstream, version, configuration = (
                "y",
                "object_tracking",
                "x",
                "1",
                {},
            )

            def analyze(self, s, t):
                return Result(
                    evidence={
                        "object_detections": [
                            {
                                "id": "d",
                                "timestamp": 0,
                                "category": "person",
                                "confidence": 0.9,
                                "bounding_box": [0.1, 0.1, 0.9, 0.99],
                                "coordinate_space": "normalized_xyxy",
                                "source_width": 100,
                                "source_height": 200,
                                "provider": "y",
                                "model": "m",
                                "sample_index": 0,
                                "scene_id": "scene-0",
                                "track_id": "1",
                                "entity_id": "e",
                            }
                        ],
                        "tracked_entities": [
                            {
                                "id": "e",
                                "category": "person",
                                "provider": "y",
                                "track_id": "1",
                                "scene_id": "scene-0",
                                "start": 0,
                                "end": 0,
                                "confidence": 0.9,
                                "detection_ids": ["d"],
                            }
                        ],
                    }
                )

        class P:
            name, category, upstream, version, configuration = "p", "pose", "x", "1", {}

            def analyze(self, s, t):
                d = s["_analysis_context"]["object_detections"][0]
                return Result(
                    evidence=build_pose_evidence(
                        [sample(entity=d["entity_id"], detection_id=d["id"])], s
                    )
                )

        with patch(
            "analyzers.media_probe.executable", side_effect=RuntimeError("no probe")
        ):
            return analyze(
                [Path("raw.mp4")],
                providers=[Y(), P()],
                supplied_metadata={
                    "duration": 3,
                    "fps": 30,
                    "width": 100,
                    "height": 200,
                },
            )

    def test_valid_cross_run_pose(self):
        d = self.document()
        self.assertEqual(validate_document(d), [])
        pose = d["evidence"]["pose_samples"][0]
        self.assertIn(":object_tracking:", pose["entity_id"])
        self.assertNotIn(":pose:p:", pose["entity_id"])

    def test_foreign_entity_timestamp_and_scene_rejected(self):
        for mutate in [
            lambda d: d["evidence"]["pose_samples"][0].update(entity_id="missing"),
            lambda d: d["evidence"]["pose_samples"][0].update(scene_id="scene-9"),
            lambda d: d["evidence"]["pose_samples"][0].update(timestamp=2),
        ]:
            d = self.document()
            mutate(d)
            self.assertTrue(validate_document(d))

    def test_duplicate_joint_and_bad_visible_coordinate_rejected(self):
        d = self.document()
        p = d["evidence"]["pose_samples"][0]
        p["keypoints"][1]["name"] = p["keypoints"][0]["name"]
        self.assertTrue(validate_document(d))
        d = self.document()
        d["evidence"]["pose_samples"][0]["keypoints"][0]["x"] = 2
        self.assertTrue(validate_document(d))


if __name__ == "__main__":
    unittest.main()
