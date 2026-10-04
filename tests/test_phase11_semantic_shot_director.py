import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location(
    "shots", ROOT / "workout-remotion-editor/scripts/semantic_shot_director.py"
)
shots = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(shots)


def ev(i="a", start=0, **kw):
    value = {
        "candidate_id": i,
        "source_id": "source-a",
        "scene_id": i,
        "source_start": start,
        "source_end": start + kw.pop("duration", 1.5),
        "person_visibility": 0.8,
        "anatomy_visibility": 0.8,
        "equipment_visibility": 0.7,
        "crop_viability": 0.8,
        "framing": 0.8,
        "track_stability": 0.8,
        "movement_completeness": 0.8,
        "trim_safety": 0.8,
        "overlay_usability": 0.8,
        "motion": 0.7,
        "activity": 0.7,
    }
    value.update(kw)
    return value


class RoleClassification(unittest.TestCase):
    def role(self, evidence, expected):
        self.assertIn(expected, [x["role"] for x in shots.classify_roles(evidence)])

    def test_primary_and_rep(self):
        self.role(ev(), "primary_movement")
        self.role(ev(editorial_rep_ids=["r1"]), "complete_rep_anchor")

    def test_setup_interactions(self):
        for interaction, role in [
            ("adjust", "equipment_adjustment"),
            ("load", "equipment_loading"),
            ("pickup", "equipment_pickup"),
            ("grip", "grip_setup"),
            ("stance", "stance_setup"),
        ]:
            with self.subTest(role=role):
                self.role(ev(interaction=interaction, interaction_support=0.8), role)

    def test_walk_recovery_environment(self):
        self.role(ev(walking=True, between_exercises=True), "walk_between_movements")
        self.role(ev(recovery_label=True), "recovery")
        self.role(
            ev(person_visibility=0, person_present=False, scene_context=True),
            "environment_context",
        )

    def test_detail_hook_hero_ending(self):
        self.role(ev(detail_scale=True), "close_detail")
        self.role(ev(motion=0.9, activity=0.9), "hook_candidate")
        self.role(ev(editorial_rep_ids=["r1"], framing=0.9, occlusion=0.1), "hero_shot")
        self.role(ev(source_final=True), "ending_candidate")

    def test_dead_unusable_unknown(self):
        self.role(ev(activity=0.01, motion=0.01, person_visibility=0.1), "dead_time")
        self.role(ev(unusable=True), "unusable")
        self.assertEqual(shots.classify_roles({"duration": 0.2})[-1]["role"], "unknown")

    def test_reviewed_labels_cover_normalized_vocabulary(self):
        for role in shots.ROLES:
            with self.subTest(role=role):
                self.role(ev(reviewed_role=role), role)


class QualityAndCompatibility(unittest.TestCase):
    def test_quality_good_bad_and_inspectable(self):
        good = shots.quality(ev())
        cropped = shots.quality(ev(anatomy_visibility=0.1))
        occluded = shots.quality(ev(occlusion=0.9))
        shaky = shots.quality(ev(camera_motion_excess=0.9))
        poor_crop = shots.quality(ev(crop_viability=0.1))
        poor_overlay = shots.quality(ev(overlay_usability=0.1))
        self.assertGreater(good["overall_rank_score"], occluded["overall_rank_score"])
        self.assertLess(cropped["anatomy_visibility"], good["anatomy_visibility"])
        self.assertLess(shaky["camera_stability"], good["camera_stability"])
        self.assertIn("poor_vertical_crop", poor_crop["quality_concerns"])
        self.assertIn("limited_overlay_safe_region", poor_overlay["quality_concerns"])

    def test_duration_and_time_remap(self):
        c = shots.build_candidate(ev(duration=2, source_fps=60))
        self.assertTrue(c["time_remap_compatibility"]["slow"])
        self.assertLessEqual(c["duration_limits"]["recommended"][1], 2)
        self.assertFalse(
            shots.build_candidate(ev(duration=0.4, source_fps=24))[
                "time_remap_compatibility"
            ]["slow"]
        )

    def test_all_major_styles(self):
        candidates = {
            role: shots.build_candidate(
                ev(
                    role,
                    detail_scale=role == "detail",
                    editorial_rep_ids=["r"] if role == "rep" else [],
                    recovery_label=role == "recovery",
                )
            )
            for role in ["detail", "rep", "recovery"]
        }
        for profile in shots.STYLE_ROLE_WEIGHTS:
            with self.subTest(profile=profile):
                self.assertGreaterEqual(
                    shots.compatibility(candidates["rep"], {profile: 1})[
                        "style_rank_score"
                    ],
                    0,
                )


class SequencingContinuityDiversity(unittest.TestCase):
    def build(self, evidence, profile, prompt="", limit=12):
        return shots.direct(evidence, {"profile_weights": {profile: 1}}, prompt, limit)

    def fixture(self):
        return [
            ev(
                "env",
                0,
                person_visibility=0,
                person_present=False,
                scene_context=True,
                activity=0.1,
                motion=0.1,
            ),
            ev("walk", 1.5, walking=True, between_exercises=True, activity=0.3),
            ev(
                "adjust", 3, interaction="adjust", interaction_support=0.9, activity=0.2
            ),
            ev("rep1", 4.5, editorial_rep_ids=["r1"], motion=0.8),
            ev("detail", 6, detail_scale=True, motion=0.8),
            ev("rep2", 7.5, editorial_rep_ids=["r2"], motion=0.9, source_final=True),
        ]

    def test_style_changes_selected_roles(self):
        viral = [
            x["selected_role"]
            for x in self.build(self.fixture(), "viral_shortform")["shots"]
        ]
        cinema = [
            x["selected_role"]
            for x in self.build(self.fixture(), "cinematic_trailer")["shots"]
        ]
        raw = [
            x["selected_role"]
            for x in self.build(self.fixture(), "raw_documentary")["shots"]
        ]
        self.assertNotEqual(viral, cinema)
        self.assertIn("environment_context", cinema)
        self.assertIn("walk_between_movements", raw)

    def test_breather_balance_and_micro_limit(self):
        evidence = [
            ev(
                f"d{i}",
                i,
                detail_scale=True,
                motion=0.45,
                activity=0.45,
                duplication_group=f"d{i}",
            )
            for i in range(7)
        ] + [ev("rep", 8, editorial_rep_ids=["r"])]
        result = self.build(evidence, "viral_shortform")
        roles = [x["selected_role"] for x in result["shots"]]
        self.assertLessEqual(sum(r in shots.MICRO for r in roles), 3)
        self.assertIn("complete_rep_anchor", roles)

    def test_duplicate_and_same_rep_suppression(self):
        evidence = [
            ev("one", 0, editorial_rep_ids=["r1"]),
            ev("two", 1, editorial_rep_ids=["r1"]),
            ev("three", 2, editorial_rep_ids=["r2"]),
        ]
        result = self.build(evidence, "clean_coaching")
        groups = [x["duplication_group"] for x in result["shots"]]
        self.assertEqual(len(groups), len(set(groups)))
        self.assertIn("near_duplicate", [x["reason"] for x in result["omitted"]])

    def test_chronology_and_replay_exception(self):
        candidates = [
            shots.build_candidate(ev("late", 3)),
            shots.build_candidate(ev("early", 1)),
        ]
        self.assertFalse(shots.validate_sequence(candidates)["valid"])
        replay = shots.build_candidate(ev("replay", 1, replay_of="late"))
        replay["selected_role"] = "replay"
        self.assertTrue(shots.validate_sequence([candidates[0], replay])["valid"])
        result = shots.select_shots(
            candidates, {"profile_weights": {"viral_shortform": 1}}
        )
        self.assertTrue(result["validation"]["valid"])

    def test_cross_source_sequence_and_bridge(self):
        a = shots.build_candidate(
            ev(
                "walk",
                0,
                source_id="a",
                source_sequence=1,
                walking=True,
                between_exercises=True,
            )
        )
        b = shots.build_candidate(
            ev("next", 0, source_id="b", source_sequence=2, editorial_rep_ids=["r2"])
        )
        result = shots.select_shots([b, a], {"profile_weights": {"raw_documentary": 1}})
        self.assertEqual(
            [x["source_sequence"] for x in result["shots"]],
            sorted(x["source_sequence"] for x in result["shots"]),
        )
        self.assertTrue(result["validation"]["valid"])

    def test_role_aware_transitions(self):
        self.assertEqual(
            shots.role_aware_transition(
                "environment_context", "close_detail", "cinematic_trailer"
            ),
            "cross_dissolve",
        )
        self.assertEqual(
            shots.role_aware_transition(
                "primary_movement", "primary_movement", "smooth_sweeping"
            ),
            "motion_match",
        )


class LanguageFallbackAndRegression(unittest.TestCase):
    def test_role_overrides(self):
        only = shots.role_overrides("Only show the lifts")
        self.assertIn("setup", only["suppress"])
        self.assertIn("setup", shots.role_overrides("show more setup")["force"])
        self.assertIn(
            "walk_between_movements",
            shots.role_overrides("no walking clips")["suppress"],
        )
        self.assertIn(
            "equipment_adjustment",
            shots.role_overrides("use machine adjustments")["force"],
        )
        self.assertIn("close_detail", shots.role_overrides("more close-ups")["force"])
        self.assertIn(
            "close_detail", shots.role_overrides("more full-body")["suppress"]
        )
        self.assertIn(
            "exercise_transition",
            shots.role_overrides("make it feel like a real workout")["force"],
        )
        self.assertIn(
            "hero_shot", shots.role_overrides("make it look like a movie")["force"]
        )

    def test_explicit_suppression_wins(self):
        c = shots.build_candidate(ev(walking=True, between_exercises=True))
        result = shots.select_shots(
            [c], {"profile_weights": {"raw_documentary": 1}}, "no walking clips"
        )
        self.assertEqual(result["shots"], [])

    def test_fallback_sparse_and_no_reps(self):
        result = shots.direct([], {"profile_weights": {"viral_shortform": 1}})
        self.assertTrue(result["fallback_used"])
        self.assertIsNotNone(result["fallback"])
        c = shots.build_candidate(ev())
        self.assertEqual(c["editorial_rep_ids"], [])

    def test_scores_not_probabilities_and_explainability(self):
        result = shots.direct(
            [ev("r", editorial_rep_ids=["rep-1"])],
            {"profile_weights": {"clean_coaching": 1}},
        )
        self.assertIn("not_probabilities", result["score_semantics"])
        self.assertTrue(result["shots"][0]["selection_reasons"])
        self.assertEqual(result["shots"][0]["editorial_rep_ids"], ["rep-1"])


if __name__ == "__main__":
    unittest.main()
