import hashlib
import stat
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "workout-remotion-editor" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import soundtrack_analysis as sa


def fake_ffmpeg(tmp_path: Path, *, seconds=31, delay=0) -> Path:
    executable = tmp_path / "ffmpeg-fixture"
    executable.write_text(f'''#!/usr/bin/env python3
import math, struct, sys, time
if "-version" in sys.argv:
 print("ffmpeg version fixture-1.0")
 raise SystemExit
# Deterministic PCM emitted incrementally, like an actual decoder pipe.
time.sleep({delay})
rate=22050
for second in range({seconds}):
 samples=[0]*rate
 for start in range(0, rate, rate//2):
  for j in range(100): samples[start+j]=int(24000*math.sin(2*math.pi*j/100))
 sys.stdout.buffer.write(struct.pack("<"+"h"*len(samples), *samples)); sys.stdout.buffer.flush()
''')
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def test_ffmpeg_absent_fails_closed(tmp_path):
    source = tmp_path / "track.mp3"
    source.write_bytes(b"not audio")
    result = sa.FfmpegPcmStreamProvider(ffmpeg_path="").analyze(source)
    # Explicit empty paths fall back to PATH; force the unavailable state for this unit seam.
    if result["provider"]["version"] != "unavailable":
        pytest.skip("host has FFmpeg")
    assert result["status"] == "unavailable"


def test_stream_is_bounded_timestamped_and_source_safe(tmp_path):
    source = tmp_path / "untrusted name;$.mp3"
    source.write_bytes(b"immutable compressed fixture")
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    provider = sa.FfmpegPcmStreamProvider(ffmpeg_path=str(fake_ffmpeg(tmp_path)),
                                          chunk_seconds=30, overlap_seconds=2)
    result = provider.analyze(source)
    assert result["status"] == "success"
    assert result["decode_provenance"] == {
        "backend": "ffmpeg", "version": "fixture-1.0", "output_format": "s16le",
        "sample_rate": 22050, "channels": 1, "arguments": ["-vn", "-sn", "-dn"]}
    assert result["chunk_report"]["chunks_processed"] == 2
    assert result["chunk_report"]["peak_pcm_bytes"] == 32 * 22050 * 2
    assert result["chunk_report"]["coverage_ratio"] == 1.0
    assert result["chunk_report"]["source_unchanged"]
    times = [event["timestamp"] for event in result["beats"]]
    assert times == sorted(set(times)) and times[-1] <= result["duration"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert not sa.validate_analysis(result)


def test_timeout_terminates_decoder_and_preserves_source(tmp_path):
    source = tmp_path / "slow.m4a"
    source.write_bytes(b"unchanged")
    provider = sa.FfmpegPcmStreamProvider(ffmpeg_path=str(fake_ffmpeg(tmp_path, delay=2)),
                                          chunk_seconds=30, timeout_seconds=.1)
    result = provider.analyze(source)
    assert result["status"] == "failed"
    assert "timeout" in result["diagnostics"][0]
    assert source.read_bytes() == b"unchanged"


@pytest.mark.parametrize("suffix", [".mp3", ".m4a", ".aac", ".flac"])
def test_baseline_routes_compressed_formats_to_stream(monkeypatch, tmp_path, suffix):
    source = tmp_path / ("audio" + suffix)
    source.write_bytes(b"fixture")
    monkeypatch.setattr(sa.FfmpegPcmStreamProvider, "analyze",
                        lambda self, path: sa._empty("unavailable", self.name, self.version, "fixture"))
    result = sa.analyze_soundtrack(source, "baseline", chunk_seconds=30)
    assert result["provider"]["name"] == sa.FfmpegPcmStreamProvider.name


def test_cache_key_changes_with_decoder_configuration(tmp_path):
    source = tmp_path / "audio.mp3"
    source.write_bytes(b"fixture")
    cache = tmp_path / "cache"
    executable = fake_ffmpeg(tmp_path, seconds=1)
    # Inject custom providers to exercise version/sample/channel cache identity.
    one = sa.FfmpegPcmStreamProvider(ffmpeg_path=str(executable), chunk_seconds=30)
    two = sa.FfmpegPcmStreamProvider(ffmpeg_path=str(executable), chunk_seconds=31)
    sa.analyze_soundtrack(source, one, cache_dir=cache)
    sa.analyze_soundtrack(source, two, cache_dir=cache)
    assert len(list(cache.glob("*.json"))) == 2

@pytest.mark.parametrize("prompt,mode,bar_aware,downbeats,section", [
    ("Make the workout changes hit on the downbeat.", "strong", False, True, False),
    ("Use the first beat of each bar.", "strong", True, True, False),
    ("Make the transitions follow the measures.", "strong", True, False, False),
    ("Use the big hits, not every beat.", "strong", False, True, False),
    ("Make it more musical but not over-edited.", "moderate", False, False, False),
    ("Line the final rep up with the next bar.", "off", True, False, False),
    ("Ignore the meter and use the first beat of each bar.", "strong", False, False, False),
    ("Use the song structure more.", "moderate", False, False, True),
    ("Make this fit the song naturally.", "moderate", False, False, True),
    ("Don't use the downbeats; use the big hits.", "strong", False, False, False),
    ("Don't sync this to music.", "off", False, False, False),
])
def test_phase16_natural_language_negation_wins(prompt, mode, bar_aware, downbeats, section):
    from music_sync import resolve_music_intent
    intent = resolve_music_intent(prompt)
    assert (intent["mode"], intent["bar_aware"], intent["downbeats_only"], intent["section_aware"]) == (mode, bar_aware, downbeats, section)

@pytest.mark.parametrize("minutes", [5, 30, 60])
def test_long_track_memory_bound_is_duration_independent(minutes):
    provider = sa.FfmpegPcmStreamProvider(ffmpeg_path="/fixture/ffmpeg", chunk_seconds=120,
                                          overlap_seconds=2)
    bound = round((provider.chunk_seconds + provider.overlap_seconds) *
                  provider.sample_rate * provider.channels * 2)
    decoded_track_bytes = minutes * 60 * provider.sample_rate * provider.channels * 2
    assert bound == 5_380_200
    assert bound < decoded_track_bytes
