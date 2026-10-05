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


def click_track(path: Path, duration=65.0, period=0.5):
    rate = 1000
    samples = [0] * int(duration * rate)
    for n in range(int(duration / period)):
        start = int(n * period * rate)
        for j in range(min(20, len(samples) - start)):
            samples[start + j] = int(
                (28000 if n % 4 == 0 else 18000) * math.sin(2 * math.pi * j / 20)
            )
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, rate, len(samples), "NONE", ""))
        out.writeframes(b"".join(struct.pack("<h", x) for x in samples))


def downbeat_document(*, meter="4/4", support=0.9):
    value = evidence(12)
    value.update(
        analysis_contract_version="3.0",
        analysis_quality="high",
        provider={"name": "fixture", "version": "1"},
        provider_capabilities=list(sa.DOWNBEAT_CAPABILITIES),
        downbeats_available=True,
        meter=meter,
        meter_support=support if meter else None,
        meter_support_kind="provider_score" if meter else None,
        downbeats=[
            {
                "timestamp": 0.0,
                "bar_index": 0,
                "support": support,
                "support_kind": "provider_score",
                "provider": "fixture",
            },
            {
                "timestamp": 2.0,
                "bar_index": 1,
                "support": support,
                "support_kind": "provider_score",
                "provider": "fixture",
            },
        ],
    )
    for i, beat in enumerate(value["beats"]):
        beat["beat_within_bar"] = i % 4 + 1 if meter else None
    return value


def test_registry_fail_closed_and_auto_does_not_select_downbeat(monkeypatch, tmp_path):
    path = tmp_path / "short.wav"
    click_track(path, 4)
    registry = sa.provider_registry()
    assert not registry["downbeat"]["available"]
    assert sa.analyze_soundtrack(path, "downbeat")["status"] == "unavailable"
    monkeypatch.setattr(sa.LibrosaProvider, "available", property(lambda self: False))
    assert (
        sa.analyze_soundtrack(path, "auto")["provider"]["name"]
        == sa.PcmWavProvider.name
    )


def test_chunked_long_track_is_bounded_deduplicated_and_source_relative(tmp_path):
    path = tmp_path / "long.wav"
    click_track(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    result = sa.analyze_soundtrack(
        path,
        "baseline",
        long_track_threshold_seconds=60,
        chunk_seconds=30,
        chunk_overlap_seconds=2,
    )
    assert result["provider"]["name"] == sa.ChunkedPcmWavProvider.name
    assert result["chunk_report"]["chunks_processed"] == 3
    assert result["chunk_report"]["peak_decoded_samples_estimate"] <= 34000
    times = [x["timestamp"] for x in result["beats"]]
    assert len(times) == 130  # overlap did not lose or duplicate any 120 BPM beat
    assert times == sorted(set(times)) and all(0 <= t <= 65 for t in times)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    assert not sa.validate_analysis(result)


def test_chunk_failure_isolated_and_temp_files_removed(monkeypatch, tmp_path):
    path = tmp_path / "long.wav"
    click_track(path)
    original, calls = sa.PcmWavProvider.analyze, {"count": 0}

    def fail_once(self, chunk):
        calls["count"] += 1
        return (
            sa._empty("failed", self.name, self.version, "fixture")
            if calls["count"] == 2
            else original(self, chunk)
        )

    monkeypatch.setattr(sa.PcmWavProvider, "analyze", fail_once)
    before = set(Path("/tmp").glob("tmp*.wav"))
    result = sa.ChunkedPcmWavProvider(chunk_seconds=30, overlap_seconds=2).analyze(path)
    assert (
        result["status"] == "partial" and result["chunk_report"]["failed_chunks"] == 1
    )
    assert set(Path("/tmp").glob("tmp*.wav")) == before


@pytest.mark.parametrize("meter", ["3/4", "4/4", "6/8", None])
def test_valid_downbeats_meter_optional_and_variable_tempo(meter):
    value = downbeat_document(meter=meter)
    value["tempo_regions"] = [
        {"start": 0, "end": 6, "bpm": 90, "provenance": "fixture"},
        {"start": 6, "end": 12, "bpm": 120, "provenance": "fixture"},
    ]
    if meter == "3/4":
        for i, beat in enumerate(value["beats"]):
            beat["beat_within_bar"] = i % 3 + 1
    assert not sa.validate_analysis(value)


def test_invalid_downbeats_are_rejected_without_assuming_four_four():
    value = downbeat_document(meter=None)
    value["downbeats"][1]["timestamp"] = -1
    value["downbeats"][1]["support_kind"] = "probability"
    assert {"invalid_downbeat_timestamp", "invalid_downbeat_provenance"} <= set(
        sa.validate_analysis(value)
    )
    value = downbeat_document()
    value["meter_support_kind"] = None
    assert "meter_without_support_semantics" in sa.validate_analysis(value)


def test_quality_gated_sync_and_natural_language():
    strong = downbeat_document()
    result = sync_timeline(
        plan(),
        strong,
        soundtrack=audio_meta(),
        prompt="Change exercises on the downbeat and use the song phrasing more",
    )
    assert "downbeats" in result["music_sync"]["capabilities_used"]
    assert "bar_positions" in result["music_sync"]["capabilities_used"]
    weak = downbeat_document(support=0.1)
    weak["analysis_quality"] = "low"
    weak["beat_confidence"] = 0.1
    weak["beat_confidence_kind"] = "normalized_support_score"
    weak_result = sync_timeline(
        plan(), weak, soundtrack=audio_meta(), prompt="Use only the big downbeats"
    )
    assert weak_result["music_sync"]["effective_mode"] == "subtle"
    assert resolve_music_intent("Build for two bars, then hit the final rep.")[
        "bar_aware"
    ]


def test_provider_disagreement_is_not_fused():
    value = downbeat_document()
    value["diagnostics"] = [
        "rhythm_provider_disagreement:fixture_vs_librosa",
        "authoritative_provider:fixture",
    ]
    result = sync_timeline(plan(), value, soundtrack=audio_meta(), mode="moderate")
    assert result["music_sync"]["selected_rhythm_provider"]["name"] == "fixture"
    assert result["music_sync"]["fallback_path"] == value["diagnostics"]
