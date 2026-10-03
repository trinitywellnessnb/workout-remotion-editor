"""Deterministic Phase 6 evaluation and promotion tests."""

from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "workout-remotion-editor/scripts"))
from repetition_evaluation import (
    evaluate,
    match_reps,
    prepare_review,
    promote,
    validate_adjudication,
    validate_annotation,
    validate_review,
)


def candidate(cid="p1", start=1.0, end=2.0, status="completed", side="left"):
    return {
        "id": cid,
        "source_id": "s",
        "rep_analysis_interval_id": "i",
        "working_side": side,
        "start": start,
        "end": end,
        "status": status,
        "phases": {"top_confirmation": 1.5},
        "rep_rule_id": "single_arm_dumbbell_row_v1",
        "rep_rule_version": "1",
    }


def analysis(rows=None):
    return {
        "schema_version": "2.6",
        "sources": [{"id": "s", "path": "x", "duration": 10}],
        "segments": [],
        "repetitions": [
            {"id": "old", "source_id": "s", "start": 8, "end": 9, "complete": True}
        ],
        "evidence": {"rep_candidates": rows or [], "rep_analysis_intervals": []},
    }


def gold(reps=None, split="development", aid="a"):
    return {
        "format_version": "1",
        "annotation_id": aid,
        "source_id": "s",
        "media": "x",
        "source_duration": 10,
        "exercise": "row",
        "canonical_exercise_id": "dumbbell_row_single_arm",
        "working_side": "left",
        "evaluation_interval": {"start": 0, "end": 10},
        "rep_analysis_interval_id": "i",
        "split": split,
        "annotator": aid,
        "repetitions": reps
        if reps is not None
        else [
            {
                "id": "g1",
                "status": "completed",
                "side": "left",
                "start": 1.0,
                "top": 1.5,
                "end": 2.0,
            }
        ],
    }


class EvaluationTests(unittest.TestCase):
    def test_perfect_fp_fn_count_timing_and_reasons(self):
        perfect = evaluate(analysis([candidate()]), [gold()])["aggregate"]
        self.assertEqual(
            (perfect["precision"], perfect["recall"], perfect["f1"]), (1, 1, 1)
        )
        self.assertEqual(perfect["exact_count_accuracy"], 1)
        shifted = candidate(start=1.1, end=2.2)
        shifted["false_positive_reason"] = "setup"
        r = evaluate(analysis([shifted, candidate("extra", 3, 4)]), [gold()])
        self.assertEqual(
            (r["aggregate"]["tp"], r["aggregate"]["fp"], r["aggregate"]["fn"]),
            (1, 1, 0),
        )
        self.assertAlmostEqual(
            r["aggregate"]["timing_error_seconds"]["start"]["mean_absolute_error"], 0.1
        )
        self.assertEqual(r["sources"][0]["signed_count_error"], 1)
        self.assertEqual(evaluate(analysis([]), [gold()])["aggregate"]["fn"], 1)

    def test_side_incomplete_uncertain_ineligible_and_empty(self):
        reps = [
            {"id": "g1", "status": "incomplete", "side": "left", "start": 1, "end": 2}
        ]
        r = evaluate(analysis([candidate(status="incomplete")]), [gold(reps)])[
            "aggregate"
        ]
        self.assertEqual(r["incomplete"]["preserved"], 1)
        r = evaluate(
            analysis([candidate(status="completed", side="right")]), [gold(reps)]
        )["aggregate"]
        self.assertEqual(r["incomplete"]["promoted_completed"], 1)
        self.assertEqual(r["side"]["wrong"], 1)
        self.assertEqual(
            evaluate(analysis([candidate(status="uncertain")]), [gold()])["aggregate"][
                "uncertainty"
            ]["gold_completed"],
            1,
        )
        self.assertEqual(
            evaluate(analysis(), [gold([])])["aggregate"]["exact_count_accuracy"], 1
        )

    def test_matching_ambiguous_no_double_and_long(self):
        ps = [candidate("p1", 0.9, 2.1), candidate("p2", 1.1, 2.2)]
        gs = [dict(gold()["repetitions"][0], source_id="s")]
        self.assertEqual(len(match_reps(ps, gs)), 1)
        gs.append(
            {
                "id": "g2",
                "source_id": "s",
                "status": "completed",
                "side": "left",
                "start": 3,
                "end": 4,
            }
        )
        self.assertLessEqual(len(match_reps([candidate("long", 0.5, 4.5)], gs)), 1)

    def test_splits_and_aggregation(self):
        self.assertEqual(
            len(
                evaluate(
                    analysis([candidate()]),
                    [gold(), gold(split="held_out", aid="b")],
                    "held_out",
                )["sources"]
            ),
            1,
        )
        self.assertEqual(
            len(evaluate(analysis([candidate()]), [gold(), gold(aid="b")])["sources"]),
            2,
        )


class AnnotationTests(unittest.TestCase):
    def test_valid_invalid_duplicate_bounds_and_side(self):
        self.assertEqual(validate_annotation(gold()), [])
        bad = gold()
        bad["repetitions"] *= 2
        bad["repetitions"][1] = dict(
            bad["repetitions"][1], side="center", start=11, end=12
        )
        errors = validate_annotation(bad)
        self.assertTrue(any("duplicate" in x for x in errors))
        self.assertTrue(any("side" in x for x in errors))
        self.assertTrue(any("bounds" in x for x in errors))

    def test_adjudication_agreement_disagreement_preserves_originals(self):
        a, b = gold(aid="a"), gold(aid="b")
        originals = copy.deepcopy([a, b])
        adj = {
            "annotation_ids": ["a", "b"],
            "repetitions": a["repetitions"],
            "disagreements": [
                {"status": "timing_adjusted", "annotation_ids": ["a", "b"]}
            ],
        }
        self.assertEqual(validate_adjudication(adj, [a, b]), [])
        self.assertEqual([a, b], originals)
        adj["disagreements"][0]["status"] = "magic"
        self.assertTrue(validate_adjudication(adj, [a, b]))


class PromotionTests(unittest.TestCase):
    def review(self, decision="accept", **extra):
        return {
            "format_version": "1",
            "reviewer": "r",
            "decisions": [
                {
                    "candidate_id": "p1",
                    "source_id": "s",
                    "decision": decision,
                    "reviewed_at": "2026-01-01T00:00:00Z",
                    "reason_code": "manual",
                    "note": "",
                    **extra,
                }
            ],
        }

    def test_prepare_accept_traceability_preserve_and_idempotence(self):
        a = analysis([candidate()])
        self.assertIsNone(prepare_review(a)["decisions"][0]["decision"])
        once = promote(a, self.review())
        twice = promote(once, self.review())
        self.assertEqual(len(once["repetitions"]), 2)
        self.assertEqual(once, twice)
        self.assertEqual(once["repetitions"][-1]["source_candidate_id"], "p1")

    def test_reject_unreviewed_incomplete_uncertain_and_mixed(self):
        self.assertEqual(
            len(promote(analysis([candidate()]), self.review("reject"))["repetitions"]),
            1,
        )
        with self.assertRaises(ValueError):
            promote(analysis([candidate()]), prepare_review(analysis([candidate()])))
        self.assertEqual(
            len(
                promote(analysis([candidate(status="incomplete")]), self.review())[
                    "repetitions"
                ]
            ),
            1,
        )
        self.assertEqual(
            len(
                promote(analysis([candidate(status="uncertain")]), self.review())[
                    "repetitions"
                ]
            ),
            2,
        )

    def test_adjust_invalid_unknown_duplicate(self):
        out = promote(
            analysis([candidate()]),
            self.review("adjust", adjusted_start=1.1, adjusted_end=1.9),
        )
        self.assertEqual(
            (out["repetitions"][-1]["start"], out["repetitions"][-1]["end"]), (1.1, 1.9)
        )
        self.assertTrue(
            validate_review(
                self.review("adjust", adjusted_start=3, adjusted_end=2),
                analysis([candidate()]),
            )
        )
        unknown = self.review()
        unknown["decisions"][0]["candidate_id"] = "no"
        self.assertTrue(validate_review(unknown, analysis([candidate()])))
        duplicate = self.review()
        duplicate["decisions"] *= 2
        self.assertTrue(validate_review(duplicate, analysis([candidate()])))


if __name__ == "__main__":
    unittest.main()
