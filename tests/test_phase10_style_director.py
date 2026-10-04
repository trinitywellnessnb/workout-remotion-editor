import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location(
    "style_director", ROOT / "workout-remotion-editor/scripts/style_director.py"
)
style = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(style)


class Phase10StyleDirectorTests(unittest.TestCase):
    def r(self, prompt, **overrides):
        return style.resolve_style(prompt, overrides or None, seed=17)

    def test_all_initial_families_are_reachable(self):
        prompts = {
            "viral_shortform": "viral",
            "fast_fitness_montage": "fitness montage",
            "cinematic_trailer": "cinematic trailer",
            "epic_dramatic": "epic dramatic",
            "gritty_aggressive": "gritty aggressive",
            "smooth_sweeping": "smooth sweeping",
            "clean_coaching": "clean coaching",
            "raw_documentary": "raw documentary",
            "polished_commercial": "polished commercial",
            "rhythmic_music_montage": "rhythmic music montage",
        }
        for family, prompt in prompts.items():
            with self.subTest(family=family):
                self.assertIn(family, self.r(prompt)["profile_weights"])

    def test_everyday_social_default_is_balanced(self):
        resolved = self.r("Make this social media ready.")
        self.assertEqual(
            set(resolved["profile_weights"]),
            {"viral_shortform", "fast_fitness_montage"},
        )
        self.assertGreater(resolved["intent"]["pace"], 0.7)
        self.assertLess(resolved["intent"]["effects"], 0.5)

    def test_blends_and_context(self):
        for prompt, expected in [
            ("viral but cinematic", {"viral_shortform", "cinematic_trailer"}),
            ("gritty and cinematic", {"gritty_aggressive", "cinematic_trailer"}),
            ("smooth and epic", {"smooth_sweeping", "epic_dramatic"}),
            ("clean and energetic", {"clean_coaching", "fast_fitness_montage"}),
        ]:
            with self.subTest(prompt=prompt):
                self.assertTrue(expected <= set(self.r(prompt)["profile_weights"]))
        self.assertGreater(
            self.r("movie trailer")["profile_weights"]["cinematic_trailer"], 0.5
        )

    def test_modifiers_and_negations(self):
        fast = self.r("TikTok style and really fast")
        self.assertGreaterEqual(fast["intent"]["pace"], 0.95)
        slight = self.r("a little cinematic and clean")
        self.assertLess(
            slight["profile_weights"]["cinematic_trailer"],
            slight["profile_weights"]["clean_coaching"],
        )
        plain = self.r("dramatic")
        no_flash = self.r("dramatic but not too flashy")
        self.assertLess(no_flash["intent"]["effects"], plain["intent"]["effects"])
        no_glitch = self.r("gritty but no glitch")
        self.assertNotIn("glitch", no_glitch["transition_policy"]["palette"])
        self.assertIn("glitch", no_glitch["transition_policy"]["forbidden"])
        self.assertFalse(
            self.r("epic but don't use slow motion")["time_remapping"]["enabled"]
        )
        self.assertLess(
            self.r("smooth and don't cut too quickly")["intent"]["pace"], 0.5
        )
        self.assertGreater(
            self.r("raw with more setup shots")["setup_breather_policy"]["amount"],
            self.r("raw with fewer setup shots")["setup_breather_policy"]["amount"],
        )

    def test_hybrid_phases(self):
        phases = self.r("TikTok hook but cinematic after that")["style_phases"]
        self.assertEqual(
            [x["style"] for x in phases[:2]], ["viral_shortform", "cinematic_trailer"]
        )
        phases = self.r("Make it fast at first then slow down toward the end")[
            "style_phases"
        ]
        self.assertEqual(phases[-1]["style"], "smooth_sweeping")

    def test_duration_distributions_are_bounded_varied_and_repeatable(self):
        resolved = self.r(
            "Give me lots of short clips with a few longer ones",
            minimum_clip_length=0.3,
            maximum_clip_length=1.9,
        )
        first = style.duration_sequence(resolved, 30)
        second = style.duration_sequence(resolved, 30)
        self.assertEqual(first, second)
        self.assertGreater(len({x["duration"] for x in first}), 10)
        self.assertTrue(all(0.3 <= x["duration"] <= 1.9 for x in first))
        self.assertIn("short", {x["band"] for x in first})
        self.assertTrue({"anchor", "long"} & {x["band"] for x in first})
        self.assertNotEqual(len({x["duration"] for x in first}), 1)

    def test_invalid_explicit_bounds_fail(self):
        with self.assertRaises(ValueError):
            self.r("clean", minimum_clip_length=2, maximum_clip_length=1)

    def test_curves_differ(self):
        curves = [
            tuple(self.r(p)["pacing_curve"])
            for p in ("viral", "epic", "trailer", "workout montage", "smooth")
        ]
        self.assertEqual(len(curves), len(set(curves)))

    def test_transition_semantics_and_frequency(self):
        viral, smooth, cinema = self.r("viral"), self.r("smooth"), self.r("cinematic")
        self.assertEqual(next(iter(viral["transition_policy"]["palette"])), "cut")
        self.assertIn("cross_dissolve", smooth["transition_policy"]["palette"])
        self.assertLess(cinema["transition_policy"]["frequency"], 0.3)
        explicit = self.r(
            "clean", preferred_transitions=["fade"], forbidden_transitions=["glitch"]
        )
        self.assertEqual(explicit["transition_policy"]["palette"], {"fade": 1.0})
        self.assertEqual(style.transition_choice(viral, 1, "primary_movement"), "cut")
        self.assertEqual(style.transition_choice(viral, 0, "hook"), "none")

    def test_speed_remap_normal_bell_curve_and_low_fps(self):
        normal = style.speed_curve(self.r("clean"))
        self.assertEqual(normal["type"], "constant")
        epic = self.r("epic")
        ramp = style.speed_curve(epic, moment=0.6, source_fps=60)
        self.assertEqual(ramp["type"], "smooth_dramatic_center")
        self.assertEqual(ramp["interpolation"], "cubic_bezier")
        self.assertLess(ramp["keyframes"][2]["rate"], ramp["keyframes"][1]["rate"])
        low = style.speed_curve(epic, source_fps=24)
        self.assertGreaterEqual(low["keyframes"][2]["rate"], 0.7)
        self.assertTrue(low["conservative_for_source_fps"])

    def test_shot_roles_setup_hook_and_ending(self):
        raw = self.r("raw like a real workout and use clips of me adjusting equipment")
        self.assertGreater(raw["shot_role_targets"]["setup"], 0.1)
        self.assertEqual(raw["source_audio"], "muted")
        self.assertEqual(self.r("raw, keep camera audio")["source_audio"], "preserve")
        gritty = self.r("gritty and aggressive")
        self.assertEqual(gritty["hook_strategy"]["type"], "impact_detail")
        self.assertTrue(gritty["hook_strategy"]["preserve_identity"])
        self.assertEqual(gritty["hook_strategy"]["replay_counter"], "suppress")
        final = self.r(
            "viral but let the final reps breathe and slow down the strongest final rep"
        )
        self.assertTrue(final["anchor_policy"]["heavy_reps_breathe"])
        self.assertTrue(final["time_remapping"]["final_rep_slowdown"])

    def test_apply_style_preserves_phase9_truth(self):
        edit = {
            "selected_repetitions": [{"editorial_repetition_id": "r1"}],
            "clips": [
                {
                    "id": "hook-r1",
                    "role": "hook_replay",
                    "source_id": "a",
                    "source_group_id": "a",
                    "source_start": 1,
                    "source_end": 2,
                    "playback_rate": 1,
                    "editorial_repetition_ids": ["r1"],
                    "counter_eligible": False,
                },
                {
                    "id": "primary-r1",
                    "role": "primary",
                    "source_id": "a",
                    "source_group_id": "a",
                    "source_start": 1,
                    "source_end": 2,
                    "playback_rate": 1,
                    "editorial_repetition_ids": ["r1"],
                },
            ],
        }
        result = style.apply_style(
            edit, self.r("cinematic and slow down the final rep"), {"a": 24}
        )
        self.assertEqual(
            [c["editorial_repetition_ids"] for c in result["clips"]], [["r1"], ["r1"]]
        )
        self.assertEqual([c["playback_rate"] for c in result["clips"]], [1, 1])
        self.assertFalse(result["clips"][0]["counter_eligible"])
        self.assertTrue(
            result["clips"][-1]["time_remap"]["conservative_for_source_fps"]
        )
        self.assertEqual(
            result["style_director"]["chronology_strictness"], "source_group_strict"
        )

    def test_raw_machine_candidates_never_enter_style_contract(self):
        result = self.r("viral")
        self.assertNotIn("rep_candidates", str(result))

    def test_chronology_override_and_no_automatic_speedup(self):
        resolved = self.r("Keep everything chronological and cinematic")
        self.assertEqual(resolved["chronology_strictness"], "strict")
        self.assertEqual(
            resolved["time_remapping"]["active_movement_default_rate"], 1.0
        )


if __name__ == "__main__":
    unittest.main()
