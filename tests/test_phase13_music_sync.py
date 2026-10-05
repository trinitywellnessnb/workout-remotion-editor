import math
import struct
import sys
import wave
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "workout-remotion-editor" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from music_sync import music_summary, resolve_music_intent, sync_timeline
from soundtrack_analysis import (
    PcmWavProvider,
    analyze_soundtrack,
    soundtrack_input,
    validate_analysis,
)
from timeline_composer import compile_timeline, to_remotion_props


def make_click(path, bpm=120, duration=6, offset=0, accent_every=4, silence=False):
    rate = 8000
    values = [0.0] * int(duration * rate)
    if not silence:
        period = 60 / bpm
        beat = 0
        t = offset
        while t < duration:
            amp = 0.95 if beat % accent_every == 0 else 0.55
            for j in range(int(0.025 * rate)):
                if int(t * rate) + j < len(values):
                    values[int(t * rate) + j] = amp * math.sin(
                        2 * math.pi * 700 * j / rate
                    )
            beat += 1
            t += period
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(b"".join(struct.pack("<h", int(x * 32767)) for x in values))


def shot(i, role="close_detail", reps=None, margin=0.3, exercise="squat"):
    return {
        "candidate_id": f"c{i}",
        "source_id": "a",
        "source_path": "a.mp4",
        "source_interval": {"start": i * 2, "end": i * 2 + 1.5},
        "selected_role": role,
        "exercise_id": exercise,
        "editorial_rep_ids": reps or [],
        "source_fps": 60,
        "flexible_trim_margin": margin,
    }


def plan():
    return compile_timeline(
        {"shots": [shot(i, exercise="squat" if i < 3 else "press") for i in range(6)]},
        prompt="fast fitness montage",
        target_duration=20,
    )


def evidence(duration=20):
    beats = [
        {
            "timestamp": i * 0.5 + 0.08,
            "index": i,
            "strength": 0.7,
            "bar_position": None,
            "provenance": "fixture",
        }
        for i in range(40)
        if i * 0.5 + 0.08 <= duration
    ]
    return {
        "status": "success",
        "provider": {"name": "fixture", "version": "1"},
        "duration": duration,
        "estimated_bpm": 120,
        "beats": beats,
        "onsets": [],
        "energy_curve": [],
        "sections": [],
        "accent_events": [dict(beats[8], kind="transient")],
        "downbeats_available": False,
    }


def audio_meta():
    return {
        "soundtrack_id": "test",
        "path": "synthetic.wav",
        "sha256": "abc",
        "volume": 0.7,
        "fade_in": 0.2,
        "fade_out": 0.5,
        "desired_start": 0,
    }


@pytest.mark.parametrize("bpm,tolerance", [(120, 4), (128, 5)])
def test_stable_click_detection(tmp_path, bpm, tolerance):
    path = tmp_path / "click.wav"
    make_click(path, bpm=bpm, duration=8, offset=0.1)
    result = analyze_soundtrack(path)
    assert result["status"] in {"success", "partial"}
    assert result["estimated_bpm"] == pytest.approx(bpm, abs=tolerance)
    assert result["beats"] and not validate_analysis(result)
    assert result["downbeats_available"] is False


def test_offset_and_accented_beats(tmp_path):
    path = tmp_path / "offset.wav"
    make_click(path, offset=0.23)
    result = analyze_soundtrack(path)
    assert result["onsets"][0]["timestamp"] == pytest.approx(0.22, abs=0.04)
    assert result["accent_events"]


@pytest.mark.parametrize("kind", ["short", "silence", "unclear"])
def test_no_clear_beat_is_honest(tmp_path, kind):
    path = tmp_path / f"{kind}.wav"
    make_click(path, duration=0.1 if kind == "short" else 1, silence=kind == "silence")
    result = analyze_soundtrack(path)
    assert result["status"] in {"no_results", "partial"}
    assert result["estimated_bpm"] is None


def test_malformed_and_missing_provider(tmp_path):
    path = tmp_path / "bad.wav"
    path.write_bytes(b"not wave")
    assert analyze_soundtrack(path)["status"] == "failed"

    class Missing:
        name, version = "optional_missing", "1"

        def analyze(self, path):
            return {
                "status": "unavailable",
                "provider": {"name": self.name, "version": self.version},
                "duration": 0,
                "estimated_bpm": None,
                "beats": [],
                "onsets": [],
                "energy_curve": [],
                "sections": [],
                "accent_events": [],
                "downbeats_available": False,
            }

    assert analyze_soundtrack(path, Missing())["status"] == "unavailable"


def test_hash_input_and_partial_provider(tmp_path):
    path = tmp_path / "click.wav"
    make_click(path)
    a = soundtrack_input(path, rights_note="synthetic")
    b = soundtrack_input(path, rights_note="synthetic")
    assert a["sha256"] == b["sha256"] and a["rights_note"] == "synthetic"
    partial = PcmWavProvider().analyze(path)
    partial.update(status="partial", beats=[])
    assert not validate_analysis(partial)


def test_no_soundtrack_and_off_are_visual_noops():
    original = plan()
    absent = sync_timeline(original, None)
    off = sync_timeline(
        original, evidence(), soundtrack=audio_meta(), prompt="Ignore the beat"
    )
    assert absent["timeline"] == original["timeline"]
    assert off["timeline"] == original["timeline"]
    assert absent["music_sync"]["status"] == "skipped"


@pytest.mark.parametrize("mode", ["subtle", "moderate", "strong"])
def test_snap_modes_preserve_valid_timeline(mode):
    result = sync_timeline(plan(), evidence(), soundtrack=audio_meta(), mode=mode)
    assert result["music_sync"]["status"] == "success"
    assert result["validation"]["valid"]
    assert (
        result["music_sync"]["boundaries_adjusted"]
        < len(result["timeline"]["segments"]) - 1
    )


def test_locked_rep_and_hook_protected_counter_stays_correct():
    source = compile_timeline(
        {"shots": [shot(0, "replay", ["r1"]), shot(1, reps=["r1"]), shot(2)]},
        target_duration=10,
    )
    before = [
        (s["composition_start"], s["composition_end"], s["counter_events"])
        for s in source["timeline"]["segments"][:2]
    ]
    result = sync_timeline(source, evidence(), soundtrack=audio_meta(), mode="strong")
    after = [
        (s["composition_start"], s["composition_end"], s["counter_events"])
        for s in result["timeline"]["segments"][:2]
    ]
    assert before == after
    assert result["timeline"]["segments"][0]["display_rep_numbers"] == []
    assert result["timeline"]["segments"][1]["display_rep_numbers"] == [1]


def test_outside_margin_stays_and_transition_reflows():
    source = compile_timeline(
        {"shots": [shot(i, margin=0.001) for i in range(4)]},
        prompt="cinematic trailer",
        target_duration=10,
    )
    result = sync_timeline(source, evidence(), soundtrack=audio_meta(), mode="strong")
    assert result["music_sync"]["boundaries_adjusted"] == 0
    for a, b in zip(result["timeline"]["segments"], result["timeline"]["segments"][1:]):
        overlap = (
            b["transition_in"]["duration_seconds"]
            if b["transition_in"]["model"] == "overlap"
            else 0
        )
        assert b["composition_start"] == pytest.approx(a["composition_end"] - overlap)


def test_final_rep_uses_offset_not_rep_mutation():
    source = compile_timeline(
        {"shots": [shot(0), shot(1, reps=["r1"])]}, target_duration=10
    )
    rep_before = source["timeline"]["segments"][-1].copy()
    analysis = evidence()
    analysis["accent_events"] = [dict(analysis["beats"][1], kind="transient")]
    result = sync_timeline(
        source,
        analysis,
        soundtrack=audio_meta(),
        prompt="Make the last rep hit on the drop",
    )
    rep_after = result["timeline"]["segments"][-1]
    assert rep_after["source_start"] == rep_before["source_start"]
    assert rep_after["source_end"] == rep_before["source_end"]
    assert result["music_sync"]["hero_rep_aligned"]


def test_trim_fades_offset_and_remotion_contract():
    meta = {
        **audio_meta(),
        "desired_start": 0.4,
        "fade_in": 0.3,
        "fade_out": 0.7,
        "user_trim": {"start": 1, "end": 19},
    }
    result = sync_timeline(plan(), evidence(), soundtrack=meta, mode="off")
    audio = result["soundtrack"]
    assert audio["trim_start_seconds"] == 1
    assert audio["trim_end_seconds"] == pytest.approx(
        1 + result["timeline"]["duration_seconds"]
    )
    props = to_remotion_props(result)
    assert props["soundtrack"]["from"] == 12
    assert props["soundtrack"]["fadeOutFrames"] == 21
    assert props["sourceAudioMuted"] is True


@pytest.mark.parametrize(
    "prompt,mode",
    [
        ("Cut it to the beat.", "strong"),
        ("Make it hit harder with the music.", "strong"),
        ("Don't sync every cut.", "subtle"),
        ("Use the beat mostly between exercises.", "strong"),
        ("Make the last rep hit on the drop.", "strong"),
        ("Keep it cinematic and loosely synced.", "subtle"),
        ("Ignore the beat.", "off"),
        ("No music sync.", "off"),
        ("Start fast and follow the beat, then make the ending cinematic.", "strong"),
    ],
)
def test_natural_language(prompt, mode):
    assert resolve_music_intent(prompt)["mode"] == mode


@pytest.mark.parametrize(
    "style",
    [
        "viral_shortform",
        "fast_fitness_montage",
        "cinematic_trailer",
        "smooth_sweeping",
        "gritty_aggressive",
        "clean_coaching",
        "raw_documentary",
    ],
)
def test_style_sync_is_bounded(style):
    source = plan()
    source["style_profiles"] = {style: 1.0}
    result = sync_timeline(source, evidence(), soundtrack=audio_meta(), mode="strong")
    assert result["validation"]["valid"]
    assert result["music_sync"]["largest_boundary_shift"] <= 0.28


def test_summary_is_inspectable():
    result = sync_timeline(plan(), evidence(), soundtrack=audio_meta(), mode="moderate")
    summary = music_summary(result, evidence())
    assert "Estimated BPM: 120" in summary and "Locked boundaries preserved" in summary
