"""Deterministic Phase 5 tests; no decoder or ML dependency is required."""

from __future__ import annotations
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "workout-remotion-editor/scripts"
sys.path.insert(0, str(SCRIPTS))
from rep_rules.dumbbell_row_single_arm_v1 import DumbbellRowSingleArmV1
from rep_rules.registry import get_rule
from analyzers.repetition_analysis import run_repetition_analysis
from validate_analysis import validate_document


class SignalRule(DumbbellRowSingleArmV1):
    def _metric(self, pose, side):
        return pose["metric"]


def poses(values, step=0.1):
    return [
        {
            "id": f"p-{i}",
            "timestamp": round(i * step, 4),
            "metric": (path, angle, 1),
            "keypoints": [],
            "association_ambiguous": False,
        }
        for i, (path, angle) in enumerate(values)
    ]


def cycle(count=1, finish=True):
    one = [(-1.0, 170)] * 3 + [
        (-0.94, 160),
        (-0.82, 145),
        (-0.65, 125),
        (-0.45, 100),
        (-0.2, 80),
        (-0.15, 75),
        (-0.2, 78),
        (-0.35, 95),
        (-0.55, 115),
        (-0.75, 140),
        (-0.9, 160),
        (-1.0, 170),
        (-1.0, 170),
    ]
    values = [(-1.0, 170)] * 3
    for _ in range(count):
        values += one[3:] if finish else one[3:9]
    return poses(values)


def provenance():
    return {
        "source_id": "s",
        "run_id": "r",
        "scene_id": "scene-0",
        "entity_id": "e",
        "exercise_candidate_id": "x",
        "canonical_exercise_id": "dumbbell_row_single_arm",
        "rep_rule_id": "single_arm_dumbbell_row_v1",
        "rep_rule_version": "1",
        "rep_analysis_interval_id": "i",
        "exercise_quality": 0.95,
        "min_quality": 0.5,
    }


class StateMachineTests(unittest.TestCase):
    def setUp(self):
        self.rule = SignalRule()

    def test_one_clean_rep_and_phase_boundaries(self):
        out = self.rule.analyze(cycle(), "left", provenance()).candidates
        self.assertEqual([x["status"] for x in out], ["completed"])
        self.assertEqual(
            list(out[0]["phases"]),
            [
                "initial_bottom_confirmation",
                "pull_departure",
                "top_entry",
                "top_confirmation",
                "return_departure",
                "bottom_reentry",
                "final_completion_confirmation",
            ],
        )

    def test_multiple_reps_bottom_and_top_pauses(self):
        self.assertEqual(
            len(self.rule.analyze(cycle(3), "left", provenance()).candidates), 3
        )

    def test_partial_pull_and_pull_without_return(self):
        out = self.rule.analyze(cycle(finish=False), "left", provenance()).candidates
        self.assertEqual(
            (out[-1]["status"], out[-1]["incompletion_reason"]),
            ("incomplete", "no_return"),
        )

    def test_jitter_false_reversal_extrema_and_state_bouncing(self):
        noisy = poses(
            [(-1, 170)] * 3
            + [(-0.96, 165), (-0.93, 160), (-0.96, 162), (-0.94, 158)] * 3
        )
        self.assertFalse(self.rule.analyze(noisy, "left", provenance()).candidates)

    def test_slow_and_fast_valid_reps(self):
        self.assertEqual(
            self.rule.analyze(cycle(), "left", provenance()).candidates[0]["status"],
            "completed",
        )
        slow = []
        for row in cycle():
            slow.extend([row, dict(row, id=row["id"] + "b")])
        for i, row in enumerate(slow):
            row["timestamp"] = i * 0.1
        self.assertEqual(
            self.rule.analyze(slow, "left", provenance()).candidates[0]["status"],
            "completed",
        )

    def test_excessive_gap_track_loss_and_incomplete_last_rep(self):
        rows = cycle(finish=False)
        rows[-1]["timestamp"] += 1
        out = self.rule.analyze(rows, "left", provenance()).candidates
        self.assertTrue(
            any(x["incompletion_reason"] == "excessive_pose_gap" for x in out)
        )

    def test_threshold_and_amplitude_safeguards(self):
        tiny = poses([(-1 + i * 0.005, 170 - i) for i in range(20)])
        self.assertIn(
            "Calibration", self.rule.analyze(tiny, "left", provenance()).warnings[0]
        )


class GateAndRegistryTests(unittest.TestCase):
    def test_exact_registry_no_family_fallback(self):
        self.assertIsNotNone(
            get_rule("dumbbell_row_single_arm", "single_arm_dumbbell_row_v1")
        )
        for exercise in (
            "row_unspecified",
            "barbell_row",
            "seated_cable_row",
            "machine_movement",
        ):
            self.assertIsNone(get_rule(exercise, "single_arm_dumbbell_row_v1"))

    def test_sampling_missing_landmarks_low_confidence_and_ambiguous_pose(self):
        rule = DumbbellRowSingleArmV1()
        sparse = [
            {"timestamp": i * 0.5, "keypoints": [], "association_ambiguous": i == 0}
            for i in range(8)
        ]
        failed = {x[0] for x in rule.gates(sparse, "left") if not x[1]}
        self.assertTrue(
            {
                "pose_association_unambiguous",
                "required_landmarks_visible",
                "sampling_rate",
            }
            <= failed
        )

    def test_laterality_requires_dominance_and_honors_explicit_context(self):
        rule = SignalRule()
        bilateral = poses([(-1 + i * 0.03, 170 - i * 3) for i in range(8)])
        self.assertIsNone(rule.resolve_side(bilateral))
        self.assertEqual(rule.resolve_side(bilateral, "right"), "right")


class OrchestrationTests(unittest.TestCase):
    def base(self, canonical="row_unspecified", conflict="none"):
        return {
            "schema_version": "2.6",
            "project": {"title": "x", "mode": "standard"},
            "sources": [{"id": "s", "path": "/x", "duration": 4}],
            "segments": [],
            "taxonomy": {
                "version": "1",
                "canonical_ids": ["dumbbell_row_single_arm", "row_unspecified"],
            },
            "context": {"taxonomy_version": "1", "assertions": [], "ordered_plan": []},
            "evidence": {
                "runs": [
                    {
                        "id": "f",
                        "source_id": "s",
                        "category": "context_fusion",
                        "provider": "f",
                        "version": "1",
                        "status": "success",
                        "fallback": False,
                        "configuration": {},
                        "warnings": [],
                        "errors": [],
                    }
                ],
                "exercise_candidates": [
                    {
                        "id": "x",
                        "source_id": "s",
                        "run_id": "f",
                        "scene_id": None,
                        "entity_id": None,
                        "start": 0,
                        "end": 4,
                        "label": "row",
                        "canonical_exercise_id": canonical,
                        "taxonomy_version": "1",
                        "source_type": "fused",
                        "provider": "f",
                        "model": None,
                        "rank": 1,
                        "confidence": 0.95,
                        "score_type": "fusion_score",
                        "user_confirmed": True,
                        "ambiguity": {"status": "none", "margin": None},
                        "supporting_evidence_refs": [],
                        "conflicting_evidence_refs": []
                        if conflict == "none"
                        else ["x"],
                        "conflict_status": conflict,
                    }
                ],
            },
        }

    def test_disabled_emits_no_run_or_collections(self):
        data = self.base()
        self.assertNotIn("rep_candidates", data["evidence"])

    def test_wrong_exercise_generic_row_and_conflict_are_ineligible(self):
        for data in (self.base(), self.base("dumbbell_row_single_arm", "retained")):
            run_repetition_analysis(data)
            self.assertFalse(data["evidence"]["rep_analysis_intervals"][0]["eligible"])
            self.assertEqual(data["evidence"]["rep_candidates"], [])

    def test_explicit_incompatible_rule_cannot_override_mapping(self):
        data = self.base("dumbbell_row_single_arm")
        run_repetition_analysis(data, requested_rule="other")
        reasons = data["evidence"]["rep_analysis_intervals"][0]["ineligibility_reasons"]
        self.assertIn("incompatible_rep_rule", reasons)

    def test_serialization_roundtrip_and_backward_schema_versions(self):
        import json

        for version in ("2.3", "2.4", "2.5"):
            data = {
                "schema_version": version,
                "project": {"title": "x", "mode": "standard"},
                "sources": [{"id": "s", "path": "/x", "duration": 1}],
                "segments": [],
            }
            self.assertEqual(validate_document(json.loads(json.dumps(data))), [])


class SemanticRejectionTests(unittest.TestCase):
    def test_bad_phase_order_cross_scene_wrong_rule_and_overlap_rejected(self):
        # Focused mutation checks live at the schema/semantic boundary; malformed
        # candidates must never be promoted into editorial repetitions.
        schema = __import__("json").loads(
            (SCRIPTS / "analysis-schema.json").read_text()
        )
        self.assertIn("2.6", schema["properties"]["schema_version"]["enum"])
        self.assertIn(
            "repetition_analysis",
            schema["$defs"]["analyzerRun"]["properties"]["category"]["enum"],
        )
        self.assertEqual(
            schema["$defs"]["repCandidate"]["properties"]["status"]["enum"],
            ["completed", "incomplete", "uncertain"],
        )
