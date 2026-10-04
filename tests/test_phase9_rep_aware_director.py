import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
MODULE = ROOT / "workout-remotion-editor/scripts/rep_aware_director.py"
spec = importlib.util.spec_from_file_location("rep_aware_director", MODULE)
director = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(director)
counter_spec = importlib.util.spec_from_file_location(
    "rep_counter_timeline", ROOT / "workout-remotion-editor/scripts/rep_counter_timeline.py"
)
counter = importlib.util.module_from_spec(counter_spec)
assert counter_spec.loader
counter_spec.loader.exec_module(counter)


def reps(count, *, source="a", exercise="row", offset=0, side=None, set_id=None):
    return [{
        "id": f"{source}-{exercise}-{set_id or 'x'}-{side or 'bilateral'}-{i}", "source_id": source,
        "source_group_id": source, "exercise_id": exercise, "segment_id": exercise,
        "start": offset + i * 2.0, "end": offset + i * 2.0 + 1.0,
        "source_rep_number": i + 1, "complete": True, "review_decision": "accept",
        "side": side, "set_id": set_id, "set_confirmed": bool(set_id),
        "segment_start": offset, "segment_end": offset + count * 2.0,
    } for i in range(count)]


class Phase9DirectorTests(unittest.TestCase):
    def build(self, rows, **config):
        return director.build_rep_aware_plan({"repetitions": rows}, config)

    def numbers(self, plan):
        return [x["source_rep_index"] for x in plan["selected_repetitions"]]

    def test_short_exact_ten_and_over_twelve_defaults(self):
        self.assertEqual(self.numbers(self.build(reps(4))), [1, 2, 3, 4])
        self.assertEqual(self.numbers(self.build(reps(10))), [1, 2, 3, 8, 9, 10])
        self.assertEqual(self.numbers(self.build(reps(13))), [1, 2, 3, 10, 11, 12, 13])

    def test_longer_percentage_ranges(self):
        movement = self.build(reps(20), mode="extended", scope="movement")
        set_level = self.build(reps(20), mode="extended", scope="set")
        self.assertTrue(.25 <= len(self.numbers(movement)) / 20 <= .50)
        self.assertTrue(.50 <= len(self.numbers(set_level)) / 20 <= .75)

    def test_explicit_overrides(self):
        self.assertEqual(len(self.numbers(self.build(reps(10), selection="all"))), 10)
        self.assertEqual(self.numbers(self.build(reps(10), selection="last", reps_per_scope=3)), [8, 9, 10])
        self.assertEqual(self.numbers(self.build(reps(10), selection="first_last")), [1, 10])
        self.assertEqual(len(self.numbers(self.build(reps(10), reps_per_scope=2))), 2)

    def test_adjacent_merge_but_omitted_middle_gap_is_a_cut(self):
        plan = self.build(reps(10))
        self.assertEqual(len(plan["clips"]), 2)
        self.assertEqual(plan["clips"][0]["editorial_repetition_ids"], [f"a-row-x-bilateral-{i}" for i in range(3)])
        self.assertEqual(plan["clips"][1]["editorial_repetition_ids"], [f"a-row-x-bilateral-{i}" for i in range(7, 10)])
        self.assertEqual(len(plan["omitted_repetitions"]), 4)

    def test_chronology_validation_and_distinct_source_reorder(self):
        base = self.build(reps(10))
        reversed_plan = dict(base, clips=list(reversed(base["clips"])))
        with self.assertRaisesRegex(ValueError, "reverse chronology"):
            director.validate_edit_plan(reversed_plan)
        reordered = dict(base, clips=[dict(base["clips"][0], source_group_id="b"), base["clips"][1]])
        director.validate_edit_plan(reordered)

    def test_hook_is_late_replay_identity_and_not_counter_eligible(self):
        plan = self.build(reps(10), hook=True, rep_counter=True)
        hook = plan["clips"][0]
        self.assertEqual(hook["role"], "hook_replay")
        self.assertFalse(hook["counter_eligible"])
        self.assertIn(hook["editorial_repetition_ids"][0], self.nested_ids(plan))
        self.assertEqual(len(plan["selected_repetitions"]), 6)

    @staticmethod
    def nested_ids(plan):
        return [x["editorial_repetition_id"] for x in plan["selected_repetitions"]]

    def test_source_and_display_numbers_counter_continuously(self):
        rows = reps(10)
        plan = self.build(rows, hook=True, rep_counter=True)
        selected = plan["selected_repetitions"]
        self.assertEqual([x["source_rep_index"] for x in selected], [1, 2, 3, 8, 9, 10])
        self.assertEqual([x["display_sequence_index"] for x in selected], [1, 2, 3, 4, 5, 6])
        events = counter.build_rep_counter_plan({"repetitions": rows}, plan)["events"]
        self.assertEqual([x["displayed_count"] for x in events], [1, 2, 3, 4, 5, 6])
        self.assertEqual([x["source_rep_number"] for x in events], [1, 2, 3, 8, 9, 10])

    def test_multiple_exercises_sets_and_unconfirmed_set_behavior(self):
        rows = reps(4, exercise="row") + reps(4, exercise="press", offset=20)
        plan = self.build(rows)
        self.assertEqual([x["display_sequence_index"] for x in plan["selected_repetitions"]], [1, 2, 3, 4] * 2)
        sets = reps(4, set_id="s1") + reps(4, set_id="s2", offset=20)
        self.assertEqual(len(self.build(sets)["selected_repetitions"]), 8)
        unconfirmed = reps(10)
        for row in unconfirmed:
            row.update(set_id="machine-gap", set_confirmed=False)
        self.assertEqual(len(self.build(unconfirmed)["selected_repetitions"]), 6)

    def test_unilateral_source_order_is_preserved(self):
        rows = reps(4, side="right") + reps(4, side="left", offset=20)
        selected = self.build(rows)["selected_repetitions"]
        self.assertEqual([x["side"] for x in selected], ["right"] * 4 + ["left"] * 4)

    def test_quick_long_modes_and_complete_reps(self):
        quick = self.build(reps(12), mode="quick")
        long = self.build(reps(12), mode="extended", scope="set")
        self.assertLess(len(quick["selected_repetitions"]), len(long["selected_repetitions"]))
        self.assertTrue(all(x["complete_rep"] for x in long["selected_repetitions"]))

    def test_rest_skip_trim_and_fast_forward(self):
        intervals = [{"source_id": "a", "start": 1, "end": 2}, {"source_id": "a", "start": 3, "end": 13}]
        actions = self.build(reps(4), rest_intervals=intervals)["rest_decisions"]
        self.assertEqual([x["action"] for x in actions], ["skip", "trim"])
        fast = self.build(reps(4), rest_intervals=intervals[1:], fast_forward_rest=True)["rest_decisions"][0]
        self.assertEqual((fast["action"], fast["playback_rate"]), ("fast_forward", 4.0))
        self.assertTrue(all(x["playback_rate"] == 1 for x in self.build(reps(4))["clips"]))

    def test_duration_budget_drops_middle_without_slicing(self):
        plan = self.build(reps(12), mode="extended", scope="set", target_duration=5)
        self.assertTrue(any(x["reason"] == "duration_limit" for x in plan["omitted_repetitions"]))
        self.assertTrue(all(x["complete_rep"] for x in plan["selected_repetitions"]))

    def test_transition_duration_and_duration_estimate(self):
        plan = self.build(reps(10), transition_duration=.2)
        raw = sum(x["duration"] for x in plan["clips"])
        self.assertAlmostEqual(plan["expected_duration"], raw - .2)

    def test_raw_candidates_fail_closed_and_legacy_fallback(self):
        plan = director.build_rep_aware_plan({"evidence": {"rep_candidates": reps(10)}}, {"legacy_clips": [{"id": "manual"}]})
        self.assertFalse(plan["rep_aware"])
        self.assertEqual(plan["clips"], [{"id": "manual"}])

    def test_user_supplied_trusted_repetitions(self):
        rows = reps(4)
        for row in rows:
            row.pop("review_decision")
            row["trust"] = "user_supplied"
        self.assertEqual(len(self.build(rows)["selected_repetitions"]), 4)
        unreviewed = reps(2)
        for row in unreviewed:
            row.pop("review_decision")
        trusted = reps(3, source="trusted")
        for row in trusted:
            row.pop("review_decision")
        plan = director.build_rep_aware_plan({"repetitions": unreviewed}, {"trusted_repetitions": trusted})
        self.assertEqual(len(plan["selected_repetitions"]), 3)

    def test_validation_rejects_duplicate_and_speedup(self):
        plan = self.build(reps(4))
        plan["clips"].append(dict(plan["clips"][0], id="duplicate"))
        with self.assertRaises(ValueError):
            director.validate_edit_plan(plan)
        plan = self.build(reps(4))
        plan["clips"][0]["playback_rate"] = 2
        with self.assertRaisesRegex(ValueError, "sped up"):
            director.validate_edit_plan(plan)


if __name__ == "__main__":
    unittest.main()
