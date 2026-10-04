import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
MODULE = ROOT / "workout-remotion-editor/scripts/rep_counter_timeline.py"
spec = importlib.util.spec_from_file_location("rep_counter_timeline", MODULE)
rep_counter = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(rep_counter)


def rep(identifier, start, end, **updates):
    row = {
        "id": identifier,
        "source_id": "source-a",
        "start": start,
        "end": end,
        "complete": True,
        "review_decision": "accept",
        "confidence": "high",
        "segment_id": "exercise-a",
    }
    row.update(updates)
    return row


def clip(start=0, end=20, timeline=0, rate=1, **updates):
    row = {
        "source_id": "source-a",
        "source_start": start,
        "source_end": end,
        "timeline_start": timeline,
        "playback_rate": rate,
        "exercise_id": "row",
    }
    row.update(updates)
    return row


def plan(clips=None, **config):
    return {
        "clips": clips or [clip()],
        "rep_counter": {"enabled": True, **config},
    }


class Phase8RepCounterTests(unittest.TestCase):
    def build(self, reps, edit=None, fps=30):
        return rep_counter.build_rep_counter_plan({"repetitions": reps}, edit or plan(), fps=fps)

    def test_disabled_is_default(self):
        result = rep_counter.build_rep_counter_plan({"repetitions": [rep("r1", 1, 2)]}, {"clips": [clip()]})
        self.assertEqual(result, {"enabled": False, "events": []})

    def test_machine_candidates_alone_fail_closed(self):
        result = rep_counter.build_rep_counter_plan(
            {"evidence": {"rep_candidates": [rep("machine", 1, 2)]}}, plan()
        )
        self.assertFalse(result["enabled"])
        self.assertEqual(result["reason"], rep_counter.UNAVAILABLE)

    def test_completed_editorial_reps_increment_at_end(self):
        result = self.build([rep("r1", 1, 2), rep("r2", 3, 4)])
        self.assertEqual([e["displayed_count"] for e in result["events"]], [1, 2])
        self.assertEqual([e["composition_time"] for e in result["events"]], [2, 4])

    def test_incomplete_and_unreviewed_are_excluded(self):
        reps = [rep("partial", 1, 2, complete=False), rep("uncertain", 3, 4, review_decision=None)]
        self.assertEqual(self.build(reps)["events"], [])

    def test_uncertain_but_explicitly_reviewed_complete_is_included(self):
        result = self.build([rep("r1", 1, 2, confidence="low", review_decision="adjust")])
        self.assertEqual(len(result["events"]), 1)

    def test_trim_speed_and_slow_mapping(self):
        r = [rep("fast", 7, 8), rep("slow", 21, 22, source_id="source-b")]
        clips = [clip(6, 10, 3, 2), clip(20, 24, 5, 0.5, source_id="source-b")]
        result = self.build(r, plan(clips))
        self.assertEqual([e["composition_time"] for e in result["events"]], [4, 9])

    def test_omitted_and_sliced_reps_are_suppressed(self):
        reps = [rep("omitted", 1, 2), rep("instant", 7, 8), rep("kept", 9, 10)]
        result = self.build(reps, plan([clip(7.9, 12)]))
        self.assertEqual([e["editorial_repetition_id"] for e in result["events"]], ["kept"])

    def test_middle_omission_and_exact_ten_selection_are_continuous(self):
        reps = [rep(f"r{i}", i * 2, i * 2 + 1, source_rep_number=i) for i in range(1, 11)]
        clips = [clip(2, 8, 0), clip(16, 22, 6)]
        events = self.build(reps, plan(clips))["events"]
        self.assertEqual([e["displayed_count"] for e in events], [1, 2, 3, 4, 5, 6])
        self.assertEqual([e["source_rep_number"] for e in events], [1, 2, 3, 8, 9, 10])

    def test_confirmed_sets_reset_only_when_requested(self):
        reps = [rep("a", 1, 2, set_id="s1"), rep("b", 3, 4, set_id="s2")]
        self.assertEqual([e["displayed_count"] for e in self.build(reps)["events"]], [1, 2])
        self.assertEqual([e["displayed_count"] for e in self.build(reps, plan(reset="set"))["events"]], [1, 1])

    def test_exercises_and_sides_are_isolated(self):
        reps = [rep("a", 1, 2, side="left"), rep("b", 3, 4, side="right")]
        self.assertEqual([e["displayed_count"] for e in self.build(reps)["events"]], [1, 1])
        reps[1].pop("side")
        edit = plan([clip(0, 3, 0, exercise_id="row"), clip(3, 5, 3, exercise_id="press")])
        self.assertEqual([e["displayed_count"] for e in self.build(reps, edit)["events"]], [1, 1])

    def test_safe_zone_and_caption_contract(self):
        self.assertEqual(rep_counter.choose_safe_region("bottom-right", captions=True), "top-left")
        self.assertEqual(rep_counter.choose_safe_region("top-right", occupied=["top-right"]), "top-left")
        with self.assertRaises(ValueError):
            rep_counter.choose_safe_region("top-right", occupied=list(rep_counter.REGIONS))

    def test_frame_boundary_rounding_policy(self):
        self.assertEqual(rep_counter.time_to_frame(0.5 / 30 - 0.0001, 30), 0)
        self.assertEqual(rep_counter.time_to_frame(0.5 / 30, 30), 1)
        self.assertEqual(rep_counter.time_to_frame(0.5 / 30 + 0.0001, 30), 1)

    def test_cut_boundary_overlap_and_duplicates_emit_once(self):
        reps = [rep("boundary", 1, 2)]
        clips = [clip(0, 2, 0), clip(2, 4, 2), clip(0, 3, 5)]
        events = self.build(reps, plan(clips))["events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["composition_time"], 2)

    def test_hook_replay_does_not_increment(self):
        reps = [rep("r1", 1, 2), rep("r2", 3, 4)]
        clips = [clip(0, 3, 0, role="hook"), clip(0, 5, 3, role="main")]
        events = self.build(reps, plan(clips))["events"]
        self.assertEqual([e["editorial_repetition_id"] for e in events], ["r1", "r2"])
        self.assertEqual([e["displayed_count"] for e in events], [1, 2])

    def test_reordered_distinct_sources_follow_final_timeline(self):
        reps = [rep("a", 1, 2), rep("b", 1, 2, source_id="source-b")]
        clips = [clip(0, 3, 0, source_id="source-b"), clip(0, 3, 3)]
        events = self.build(reps, plan(clips))["events"]
        self.assertEqual([e["editorial_repetition_id"] for e in events], ["b", "a"])

    def test_long_source_fragments_use_timeline_order(self):
        reps = [rep("early", 1, 2), rep("late", 8, 9)]
        clips = [clip(0, 3, 0), clip(7, 10, 3)]
        self.assertEqual([e["editorial_repetition_id"] for e in self.build(reps, plan(clips))["events"]], ["early", "late"])
        with self.assertRaisesRegex(ValueError, "chronological"):
            self.build(reps, plan(list(reversed(clips))))

    def test_progress_requires_explicit_target(self):
        with self.assertRaisesRegex(ValueError, "target_reps"):
            self.build([rep("r", 1, 2)], plan(mode="progress"))
        event = self.build([rep("r", 1, 2)], plan(mode="progress", target_reps=10))["events"][0]
        self.assertEqual((event["target"], event["display_mode"]), (10, "progress"))

    def test_serialization_and_component_contract(self):
        result = self.build([rep("r", 1, 2)], plan(mode="rep"))
        self.assertEqual(json.loads(json.dumps(result)), result)
        component = (ROOT / "workout-remotion-editor/remotion/RepCounter.tsx").read_text()
        self.assertIn("spring({frame: age, fps", component)
        self.assertNotIn("rep_candidates", component)
        self.assertIn("event.stream_id === activeStream", component)


if __name__ == "__main__":
    unittest.main()
