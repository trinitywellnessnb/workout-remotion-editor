import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "workout-remotion-editor" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from timeline_composer import compile_timeline, to_remotion_props, validate_timeline


def shot(i, role="primary_movement", source="a.mp4", start=None, reps=None, **extra):
    start = i * 2.0 if start is None else start
    return {
        "candidate_id": f"c{i}",
        "source_id": source,
        "source_path": source,
        "source_interval": {"start": start, "end": start + 1.5},
        "selected_role": role,
        "exercise_id": extra.pop("exercise_id", "squat"),
        "editorial_rep_ids": reps or [],
        "source_fps": extra.pop("source_fps", 60),
        "selection_reasons": ["fixture"],
        **extra,
    }


def compile_shots(shots, prompt="Make this social media ready", target=None, seed=4):
    return compile_timeline(
        {"shots": shots}, prompt=prompt, target_duration=target, seed=seed
    )


def test_one_shot_exact_mapping_and_muted_audio():
    plan = compile_shots([shot(0, reps=["r1"])])
    seg = plan["timeline"]["segments"][0]
    assert seg["source_start"] == 0 and seg["composition_start"] == 0
    assert seg["source_to_composition"]["source_origin"] == 0
    assert plan["source_audio"] == "muted" and seg["display_rep_numbers"] == [1]


def test_multiple_sources_keep_upstream_order_and_frame_adapter():
    plan = compile_shots([shot(0, source="b.mp4"), shot(0, source="a.mp4")])
    assert [x["source_id"] for x in plan["timeline"]["segments"]] == ["b.mp4", "a.mp4"]
    props = to_remotion_props(plan)
    assert props["durationInFrames"] > 0 and props["sourceAudioMuted"] is True
    assert props["clips"][0]["sourceStartFrame"] == 0


def test_hook_replay_preserves_identity_without_counting_twice():
    shots = [
        shot(2, "replay", reps=["r2"], replay_of="r2", start=4),
        shot(0, reps=["r1"]),
        shot(2, reps=["r2"], start=4),
    ]
    plan = compile_shots(shots)
    assert plan["timeline"]["segments"][0]["replay_type"] == "hook_replay"
    assert plan["timeline"]["segments"][0]["display_rep_numbers"] == []
    assert [s["display_rep_numbers"] for s in plan["timeline"]["segments"]] == [
        [],
        [1],
        [2],
    ]


def test_duplicate_primary_rep_is_rejected():
    plan = compile_shots([shot(0, reps=["r1"]), shot(1, reps=["r2"])])
    plan["timeline"]["segments"][1]["rep_ids"] = ["r1"]
    assert "duplicate_primary_rep" in {
        x["code"] for x in validate_timeline(plan)["errors"]
    }


@pytest.mark.parametrize("target", [15, 30, 60, None])
def test_duration_targets_and_no_target(target):
    plan = compile_shots(
        [
            shot(i, role="close_detail" if i % 3 == 0 else "primary_movement")
            for i in range(12)
        ],
        target=target,
    )
    assert plan["timeline"]["target_duration_seconds"] > 0
    assert plan["validation"]["valid"]


@pytest.mark.parametrize(
    "prompt,profile",
    [
        ("make it TikTok viral", "viral_shortform"),
        ("cinematic movie trailer", "cinematic_trailer"),
        ("smooth sweeping", "smooth_sweeping"),
        ("gritty aggressive", "gritty_aggressive"),
    ],
)
def test_styles_affect_timeline(prompt, profile):
    plan = compile_shots(
        [shot(i, "close_detail" if i == 1 else "primary_movement") for i in range(4)],
        prompt,
    )
    assert profile in plan["style_profiles"]
    assert all(s["style_phase"] for s in plan["timeline"]["segments"])


def test_hybrid_has_multiple_style_phases():
    plan = compile_shots(
        [shot(i) for i in range(6)],
        "Start fast at first and make the end cinematic dramatic",
    )
    assert len({s["style_phase"]["style"] for s in plan["timeline"]["segments"]}) == 2


def test_no_slow_motion_negation_wins():
    plan = compile_shots([shot(0, reps=["r1"])], "cinematic but no slow motion")
    assert plan["timeline"]["segments"][0]["time_remap"] is None


def test_only_lifts_suppresses_setup_walking_and_detail():
    plan = compile_shots(
        [
            shot(0, "setup"),
            shot(1, "walk_between_movements"),
            shot(2, "close_detail"),
            shot(3, reps=["r1"]),
        ],
        "Only show the lifts",
    )
    assert [s["shot_role"] for s in plan["timeline"]["segments"]] == [
        "primary_movement"
    ]


def test_final_rep_bell_curve_and_fps_safety():
    plan = compile_shots(
        [shot(0, reps=["r1"], source_fps=30)], "Slow down just the last rep"
    )
    seg = plan["timeline"]["segments"][0]
    assert seg["time_remap"]["type"] == "dramatic_bell_curve"
    assert seg["time_remap"]["keyframes"][2]["rate"] >= 0.7
    assert "slowdown_limited_by_source_fps" in seg["selection_reasons"]


def test_setup_speedup_never_fast_forwards_active_rep():
    plan = compile_shots([shot(0, "setup"), shot(1, reps=["r1"])], "really fast TikTok")
    assert plan["timeline"]["segments"][0]["playback_rate"] > 1
    assert plan["timeline"]["segments"][1]["playback_rate"] == 1


def test_transition_overlap_math():
    plan = compile_shots(
        [shot(0, "environment_context"), shot(1, "close_detail")],
        "cinematic movie trailer",
    )
    a, b = plan["timeline"]["segments"]
    tr = b["transition_in"]
    assert b["composition_start"] == pytest.approx(
        a["composition_end"] - tr["duration_seconds"]
    )
    assert plan["timeline"]["duration_seconds"] == b["composition_end"]


def test_omitted_middle_has_deliberate_transition():
    a = shot(0, reps=["r3"], source_sequence_start=3, source_sequence_end=3)
    b = shot(1, reps=["r8"], start=8, source_sequence_start=8, source_sequence_end=8)
    plan = compile_shots([a, b], "cinematic movie trailer")
    assert plan["timeline"]["segments"][1]["transition_in"]["type"] in {
        "motion_match",
        "cut",
    }


def test_fallback_levels():
    manual = {
        "manual_clips": [
            {
                "id": "m",
                "source_id": "x",
                "source_path": "x.mp4",
                "source_start": 0,
                "source_end": 2,
            }
        ]
    }
    assert compile_timeline(manual)["fallback_level"] == "manual_clips"
    scenes = {
        "analysis": {
            "scenes": [
                {"id": "s", "source_id": "x", "source_start": 0, "source_end": 2}
            ]
        }
    }
    assert compile_timeline(scenes)["fallback_level"] == "scene_activity_candidates"


def test_deterministic_output_and_mixed_duration_distribution():
    shots = [shot(i, "close_detail" if i % 2 else "primary_movement") for i in range(8)]
    a, b = compile_shots(shots, seed=91), compile_shots(shots, seed=91)
    assert a == b
    assert len({s["composition_duration"] for s in a["timeline"]["segments"]}) > 1


@pytest.mark.parametrize(
    "mutation,code",
    [
        (
            lambda p: p["timeline"]["segments"][0].update(source_end=0),
            "invalid_source_range",
        ),
        (
            lambda p: p["timeline"]["segments"][0].update(playback_rate=0),
            "invalid_playback_rate",
        ),
        (
            lambda p: p["timeline"]["segments"][0]["transition_in"].update(
                type="sparkles"
            ),
            "impossible_transition",
        ),
        (
            lambda p: p["timeline"]["segments"][0].update(composition_start=-1),
            "invalid_composition_range",
        ),
    ],
)
def test_validator_rejects_invalid_plans(mutation, code):
    plan = compile_shots([shot(0, reps=["r1"])])
    mutation(plan)
    assert code in {x["code"] for x in validate_timeline(plan)["errors"]}


def test_reverse_chronology_rejected():
    plan = compile_shots([shot(0), shot(1)])
    plan["timeline"]["segments"][1]["source_start"] = -1
    assert "reverse_chronology" in {
        x["code"] for x in validate_timeline(plan)["errors"]
    }


def test_fixture_files_compile():
    fixture = (
        Path(__file__).parents[1]
        / "workout-remotion-editor"
        / "examples"
        / "phase12-timeline-fixtures.json"
    )
    data = json.loads(fixture.read_text())
    for row in data["fixtures"]:
        plan = compile_timeline(
            row["input"],
            prompt=row["prompt"],
            target_duration=row["target_duration"],
            seed=12,
        )
        assert (
            plan["validation"]["valid"] and plan["timeline"]["aspect_ratio"] == "9:16"
        )
