import hashlib
import math
import struct
import sys
import wave
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "workout-remotion-editor" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import soundtrack_analysis as sa
from music_sync import resolve_music_intent, sync_timeline
from test_phase13_music_sync import audio_meta, evidence, plan


def wav(path, beats=(0.2, 0.7, 1.2, 1.7), duration=2.2):
    rate = 8000
    samples = [0.0] * int(duration * rate)
    for n, t in enumerate(beats):
        for j in range(160):
            samples[int(t * rate) + j] = (0.9 if n % 4 == 0 else 0.5) * math.sin(
                2 * math.pi * 500 * j / rate
            )
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, rate, len(samples), "NONE", ""))
        out.writeframes(b"".join(struct.pack("<h", int(x * 32767)) for x in samples))


def rich(duration=20):
    value = evidence(duration)
    value.update(
        analysis_quality="high",
        beat_confidence=0.82,
        beat_confidence_kind="normalized_support_score",
        provider_capabilities=list(sa.ADVANCED_CAPABILITIES),
        tempo_regions=[
            {"start": 0, "end": 8, "bpm": 90, "provenance": "fixture"},
            {"start": 8, "end": 20, "bpm": 120, "provenance": "fixture"},
        ],
        sections=[
            {"id": "section_1", "start": 0, "end": 4, "descriptor": "low"},
            {"id": "section_2", "start": 4, "end": 20, "descriptor": "high"},
        ],
        downbeats=[
            {
                "timestamp": 4.08,
                "strength": 0.9,
                "provenance": "fixture",
                "bar_index": 1,
            }
        ],
        downbeats_available=True,
    )
    for i, beat in enumerate(value["beats"]):
        beat["bar_position"] = i % 3 + 1
    return value


def test_registry_and_optional_advanced(monkeypatch, tmp_path):
    path = tmp_path / "a.wav"
    wav(path)
    monkeypatch.setattr(sa.LibrosaProvider, "available", property(lambda self: False))
    registry = sa.provider_registry()
    assert registry["baseline"]["available"] and not registry["advanced"]["available"]
    assert (
        sa.analyze_soundtrack(path, "auto")["provider"]["name"]
        == sa.PcmWavProvider.name
    )
    missing = sa.analyze_soundtrack(path, "advanced")
    assert missing["status"] == "unavailable"


def test_auto_falls_back_after_advanced_failure(monkeypatch, tmp_path):
    path = tmp_path / "a.wav"
    wav(path)
    monkeypatch.setattr(sa.LibrosaProvider, "available", property(lambda self: True))
    monkeypatch.setattr(
        sa.LibrosaProvider,
        "analyze",
        lambda self, p: sa._empty("failed", "librosa", "x", "boom"),
    )
    result = sa.analyze_soundtrack(path, "auto")
    assert result["provider"]["name"] == sa.PcmWavProvider.name
    assert "fallback_to_baseline" in result["diagnostics"]


def test_custom_partial_metadata_and_source_unchanged(tmp_path):
    path = tmp_path / "a.wav"
    wav(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    class Partial:
        name, version, capabilities = "test", "1", ["onset_detection"]

        def analyze(self, _):
            value = sa._empty("partial", self.name, self.version, "beats_unavailable")
            value.update(
                duration=2.2,
                onsets=[{"timestamp": 0.2, "strength": 0.5, "provenance": "test"}],
            )
            return value

    result = sa.analyze_soundtrack(path, Partial())
    assert result["status"] == "partial" and result["source_sha256"] == before
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_cache_is_content_provider_and_config_addressed(tmp_path):
    path = tmp_path / "a.wav"
    cache = tmp_path / "cache"
    wav(path)
    one = sa.analyze_soundtrack(path, "baseline", cache_dir=cache)
    two = sa.analyze_soundtrack(path, "baseline", cache_dir=cache)
    assert one["source_sha256"] == two["source_sha256"]
    assert "analysis_cache_hit" in two["diagnostics"]
    assert len(list(cache.glob("*.json"))) == 1


def test_tempo_regions_preserve_variable_timing_and_ambiguity():
    times = [0, 0.667, 1.334, 2.001, 2.501, 3.001, 3.501, 4.001]
    regions, curve = sa._tempo_regions(times, 4.5, "fixture")
    assert len(regions) == 2 and regions[0]["bpm"] == pytest.approx(90, abs=1)
    assert regions[1]["bpm"] == pytest.approx(120, abs=1) and len(curve) == 7
    assert sa._beat_support(times[:4], [0.8] * 4) > 0.7


def test_validation_confidence_and_no_fabricated_meter():
    value = rich()
    assert value["meter"] if "meter" in value else None is None
    assert not sa.validate_analysis(value)
    value["beat_confidence_kind"] = None
    assert "invalid_beat_confidence" in sa.validate_analysis(value)


def test_quality_gate_preserves_timeline():
    source, weak = plan(), rich()
    weak.update(analysis_quality="insufficient", beat_confidence=0.1)
    result = sync_timeline(
        source, weak, soundtrack=audio_meta(), prompt="Make this work with the music"
    )
    assert result["timeline"] == source["timeline"]
    assert result["music_sync"]["reason"] == "insufficient_analysis_quality"


def test_section_downbeat_priority_and_natural_language():
    analysis = rich()
    result = sync_timeline(
        plan(),
        analysis,
        soundtrack=audio_meta(),
        prompt="Make the exercise changes hit on the downbeat",
    )
    reasons = [x.get("reason") for x in result["music_sync"]["adjustments"]]
    assert result["validation"]["valid"]
    assert resolve_music_intent(
        "Follow the song sections and only use the big musical hits."
    )["section_aware"]
    assert (
        resolve_music_intent("Ignore the song structure and keep the current edit.")[
            "mode"
        ]
        == "off"
    )
    assert any(
        x in reasons for x in ("strong_downbeat_selected", "beat_outside_safe_margin")
    )


def test_loudness_is_measurement_only():
    result = sync_timeline(
        plan(), rich(), soundtrack={**audio_meta(), "volume": 0.37}, mode="off"
    )
    assert result["soundtrack"]["volume"] == 0.37
