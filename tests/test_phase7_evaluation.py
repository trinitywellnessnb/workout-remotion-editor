"""Phase 7 safeguards and reporting tests use synthetic data only."""

from __future__ import annotations
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "workout-remotion-editor/scripts"))
from phase7_evaluation import (
    agreement,
    compare_configs,
    freeze_config,
    hash_media,
    held_out_report,
    summary,
    validate_config,
    validate_manifest,
)


def manifest(split="development"):
    return {
        "format_version": "1",
        "dataset_id": "d",
        "dataset_version": "1",
        "footage_type": "synthetic",
        "sources": [
            {
                "source_id": "s",
                "media_reference": "evaluation-data/s.mp4",
                "rights_status": "rights_cleared",
                "redistribution_allowed": False,
                "split": split,
                "exercise_canonical_id": "dumbbell_row_single_arm",
                "expected_side": "left",
                "view_categories": ["side", "tripod-static"],
                "duration_seconds": 4,
                "annotation_files": ["a.json", "b.json"],
                "adjudication_file": "gold.json",
            }
        ],
    }


def annotation(aid="a", split="development", start=1.0):
    return {
        "format_version": "1",
        "annotation_id": aid,
        "source_id": "s",
        "media": "evaluation-data/s.mp4",
        "source_duration": 4,
        "exercise": "row",
        "canonical_exercise_id": "dumbbell_row_single_arm",
        "working_side": "left",
        "view_categories": ["side"],
        "evaluation_interval": {"start": 0, "end": 4},
        "rep_analysis_interval_id": "i",
        "split": split,
        "annotator": aid,
        "repetitions": [
            {
                "id": "g",
                "status": "completed",
                "side": "left",
                "start": start,
                "top": 1.5,
                "end": 2.0,
            }
        ],
    }


def analysis(extra=False, eligible=True):
    rows = [
        {
            "id": "p",
            "source_id": "s",
            "rep_analysis_interval_id": "i",
            "working_side": "left",
            "start": 1.0,
            "end": 2.0,
            "status": "completed",
            "phases": {"top_confirmation": 1.5},
            "rep_rule_id": "single_arm_dumbbell_row_v1",
            "rep_rule_version": "1",
        }
    ]
    if extra:
        rows.append(
            dict(rows[0], id="extra", start=2.5, end=3.0, false_positive_reason="setup")
        )
    return {
        "schema_version": "2.6",
        "sources": [{"id": "s", "path": "x", "duration": 4}],
        "segments": [],
        "repetitions": [],
        "evidence": {
            "rep_candidates": rows,
            "rep_analysis_intervals": [
                {
                    "id": "i",
                    "eligible": eligible,
                    "ineligibility_reasons": [] if eligible else ["low_pose_coverage"],
                }
            ],
        },
    }


def config(cid="A"):
    return {
        "config_id": cid,
        "rule_id": "single_arm_dumbbell_row_v1",
        "rule_version": "1",
        "values": {"minimum_sample_rate": 6.0},
    }


class Phase7Tests(unittest.TestCase):
    def test_manifest_valid_invalid_duplicate_media_hash_and_ignore(self):
        self.assertEqual(validate_manifest(manifest()), [])
        bad = manifest()
        bad["sources"].append(copy.deepcopy(bad["sources"][0]))
        bad["sources"][0]["media_reference"] = "../private.mp4"
        bad["sources"][0]["media_sha256"] = "no"
        errors = validate_manifest(bad)
        self.assertTrue(any("duplicate" in e for e in errors))
        self.assertTrue(any("safe relative" in e for e in errors))
        self.assertTrue(any("SHA-256" in e for e in errors))
        with tempfile.NamedTemporaryFile() as f:
            f.write(b"abc")
            f.flush()
            self.assertEqual(
                hash_media(f.name)["sha256"],
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )
        ignored = subprocess.run(
            ["git", "check-ignore", "evaluation-data/private.mp4"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        ).returncode
        self.assertEqual(ignored, 0)

    def test_config_comparison_policy_and_development_only(self):
        policy = {
            "version": "1",
            "precision_floor": 0.75,
            "maximum_mean_absolute_count_error": 1,
            "forbidden_false_positive_reasons": [],
            "require_no_side_failures": True,
        }
        result = compare_configs(
            manifest(),
            [
                {
                    "config": config("A"),
                    "analysis": analysis(extra=True),
                    "gold": [annotation()],
                },
                {"config": config("B"), "analysis": analysis(), "gold": [annotation()]},
            ],
            policy,
        )
        self.assertEqual(result["selected_config_id"], "B")
        self.assertEqual(len(result["configurations"]), 2)
        with self.assertRaises(ValueError):
            compare_configs(
                manifest("held_out"),
                [
                    {
                        "config": config(),
                        "analysis": analysis(),
                        "gold": [annotation("a", "held_out")],
                    }
                ],
                policy,
            )
        with self.assertRaises(ValueError):
            compare_configs(
                manifest(),
                [
                    {
                        "config": config(),
                        "analysis": analysis(),
                        "gold": [annotation()],
                    },
                    {
                        "config": config(),
                        "analysis": analysis(),
                        "gold": [annotation()],
                    },
                ],
                policy,
            )
        self.assertTrue(
            validate_config(
                {"config_id": "x", "rule_id": "other", "values": {"bad": 1}}
            )
        )

    def test_freeze_identity_immutability_and_heldout(self):
        policy = {"version": "1", "precision_floor": 0.9}
        comparison = compare_configs(
            manifest(),
            [{"config": config(), "analysis": analysis(), "gold": [annotation()]}],
            policy,
        )
        frozen = freeze_config(comparison, "abc")
        before = copy.deepcopy(frozen)
        report = held_out_report(
            frozen,
            analysis(),
            [annotation("gold", "held_out")],
            first_look=True,
            dataset=manifest("held_out"),
            real_footage=False,
        )
        self.assertEqual(frozen, before)
        self.assertEqual(report["config_id"], "A")
        self.assertEqual(report["report_label"], "synthetic test report")
        self.assertIn("Config: A", summary(report))
        self.assertEqual(
            report["aggregate"]["performance_by_view"]["side"]["source_count"], 1
        )
        repeated = held_out_report(
            frozen,
            analysis(),
            [annotation("gold", "held_out")],
            first_look=False,
            dataset=manifest("held_out"),
            real_footage=False,
        )
        self.assertFalse(repeated["pristine_first_look"])
        self.assertTrue(repeated["warnings"])
        mutated = copy.deepcopy(frozen)
        mutated["configuration"]["minimum_sample_rate"] = 99
        with self.assertRaises(ValueError):
            held_out_report(
                mutated,
                analysis(),
                [annotation("gold", "held_out")],
                first_look=True,
                dataset=manifest("held_out"),
                real_footage=False,
            )
        with self.assertRaises(ValueError):
            held_out_report(
                frozen,
                analysis(),
                [annotation()],
                first_look=True,
                dataset=manifest(),
                real_footage=True,
            )

    def test_agreement_separate_and_timing(self):
        report = agreement(annotation(), annotation("b", start=1.1))
        self.assertEqual(report["metric_scope"], "human_human")
        self.assertEqual(report["matched_repetitions"], 1)
        self.assertAlmostEqual(
            report["timing_difference_seconds"]["start"]["mean_absolute_difference"],
            0.1,
        )

    def test_fn_fp_eligibility_view_side_and_roundtrip(self):
        from repetition_evaluation import evaluate

        gold = annotation()
        gold["repetitions"][0]["false_negative_reason"] = "pose_occlusion"
        report = evaluate(
            analysis(extra=False, eligible=False)
            | {
                "evidence": {
                    "rep_candidates": [],
                    "rep_analysis_intervals": [
                        {
                            "id": "i",
                            "eligible": False,
                            "ineligibility_reasons": ["low_pose_coverage"],
                        }
                    ],
                }
            },
            [gold],
            "development",
            ".35" if False else 0.35,
            "A",
        )
        agg = report["aggregate"]
        self.assertEqual(agg["false_negative_reasons"], {"pose_occlusion": 1})
        self.assertEqual(agg["eligibility"]["ineligible_intervals"], 1)
        self.assertEqual(agg["performance_by_side"]["left"]["source_count"], 1)
        self.assertEqual(json.loads(json.dumps(report)), report)


if __name__ == "__main__":
    unittest.main()
