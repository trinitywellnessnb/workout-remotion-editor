#!/usr/bin/env python3
"""Dependency-free, provider-neutral soundtrack analysis for editorial timing.

The built-in provider intentionally supports PCM WAV only.  It is deterministic,
CPU-only and conservative: missing musical structure is reported as unavailable
rather than guessed.  Richer providers can return the same normalized contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import wave
from pathlib import Path
from typing import Any, Protocol


STATUSES = {"success", "partial", "no_results", "unavailable", "failed", "skipped"}


class AudioAnalysisProvider(Protocol):
    name: str
    version: str

    def analyze(self, path: Path) -> dict[str, Any]: ...


def soundtrack_input(path: Path, **metadata: Any) -> dict[str, Any]:
    """Build the privacy-minimal input record and content-addressable cache key."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "soundtrack_id": metadata.get("soundtrack_id") or digest[:16],
        "path": str(path),
        "sha256": digest,
        "rights_note": metadata.get("rights_note"),
        "user_trim": metadata.get("user_trim"),
        "desired_start": float(metadata.get("desired_start", 0)),
        "volume": float(metadata.get("volume", 1)),
        "fade_in": float(metadata.get("fade_in", 0)),
        "fade_out": float(metadata.get("fade_out", 0)),
        "loop": bool(metadata.get("loop", False)),
    }


def _empty(status: str, provider: str, version: str, reason: str) -> dict[str, Any]:
    return {
        "status": status,
        "provider": {"name": provider, "version": version},
        "duration": 0.0,
        "estimated_bpm": None,
        "beats": [],
        "onsets": [],
        "energy_curve": [],
        "sections": [],
        "accent_events": [],
        "downbeats_available": False,
        "diagnostics": [reason],
    }


class PcmWavProvider:
    """Envelope/onset autocorrelation provider; no optional native packages."""

    name, version = "pcm_wav_envelope", "1.0"

    def analyze(self, path: Path) -> dict[str, Any]:
        try:
            with wave.open(str(path), "rb") as audio:
                channels, rate, width, frames = (
                    audio.getnchannels(),
                    audio.getframerate(),
                    audio.getsampwidth(),
                    audio.getnframes(),
                )
                if width not in (1, 2, 3, 4) or channels < 1 or rate < 1:
                    return _empty(
                        "unavailable", self.name, self.version, "unsupported_pcm"
                    )
                raw = audio.readframes(frames)
        except (wave.Error, EOFError, OSError) as exc:
            return _empty(
                "failed", self.name, self.version, f"decode_failed:{type(exc).__name__}"
            )
        duration = frames / rate
        if duration <= 0:
            return _empty("no_results", self.name, self.version, "empty_audio")
        samples = _mono_samples(raw, width, channels)
        hop = max(1, round(rate * 0.02))
        rms = [
            math.sqrt(
                sum(v * v for v in samples[i : i + hop])
                / max(1, len(samples[i : i + hop]))
            )
            for i in range(0, len(samples), hop)
        ]
        peak = max(rms, default=0)
        if peak < 1e-6:
            result = _empty("no_results", self.name, self.version, "silence")
            result.update(
                duration=round(duration, 6), sample_rate=rate, channels=channels
            )
            return result
        energy = [v / peak for v in rms]
        novelty = [0.0] + [
            max(0.0, energy[i] - energy[i - 1]) for i in range(1, len(energy))
        ]
        threshold = max(0.12, sorted(novelty)[int(len(novelty) * 0.85)])
        candidates = []
        for i in range(1, len(novelty) - 1):
            if (
                novelty[i] >= threshold
                and novelty[i] >= novelty[i - 1]
                and novelty[i] >= novelty[i + 1]
            ):
                t = i * hop / rate
                if not candidates or t - candidates[-1][0] >= 0.18:
                    candidates.append((t, min(1.0, novelty[i] / max(threshold, 1e-9))))
        bpm, beats = _beat_grid(candidates, duration)
        onsets = [
            {"timestamp": round(t, 6), "strength": round(s, 4), "provenance": self.name}
            for t, s in candidates
        ]
        accents = [dict(x, kind="transient") for x in onsets if x["strength"] >= 0.72]
        curve_step = max(1, round(0.25 * rate / hop))
        curve = [
            {
                "timestamp": round(i * hop / rate, 6),
                "energy": round(
                    sum(energy[i : i + curve_step]) / len(energy[i : i + curve_step]), 4
                ),
                "provenance": self.name,
            }
            for i in range(0, len(energy), curve_step)
            if energy[i : i + curve_step]
        ]
        return {
            "status": "success" if beats else "partial",
            "provider": {"name": self.name, "version": self.version},
            "duration": round(duration, 6),
            "sample_rate": rate,
            "channels": channels,
            "estimated_bpm": bpm,
            "beats": beats,
            "onsets": onsets,
            "energy_curve": curve,
            "sections": [],
            "accent_events": accents,
            "downbeats_available": False,
            "diagnostics": []
            if beats
            else ["tempo_not_reliable", "sections_unavailable"],
        }


def _mono_samples(raw: bytes, width: int, channels: int) -> list[float]:
    maximum = float(1 << (width * 8 - 1))
    values = []
    if width == 1:
        unpacked = [(x - 128) / 128 for x in raw]
    elif width in (2, 4):
        code = "h" if width == 2 else "i"
        unpacked = [
            x / maximum for x in struct.unpack("<" + code * (len(raw) // width), raw)
        ]
    else:
        unpacked = [
            int.from_bytes(raw[i : i + 3], "little", signed=True) / maximum
            for i in range(0, len(raw) - 2, 3)
        ]
    for i in range(0, len(unpacked), channels):
        frame = unpacked[i : i + channels]
        if frame:
            values.append(sum(frame) / len(frame))
    return values


def _beat_grid(
    onsets: list[tuple[float, float]], duration: float
) -> tuple[float | None, list[dict[str, Any]]]:
    if len(onsets) < 3:
        return None, []
    intervals = [
        b[0] - a[0] for a, b in zip(onsets, onsets[1:]) if 0.3 <= b[0] - a[0] <= 1.0
    ]
    if len(intervals) < 2:
        return None, []
    intervals.sort()
    period = intervals[len(intervals) // 2]
    bpm = 60 / period
    if not 60 <= bpm <= 200:
        return None, []
    first = onsets[0][0]
    count = int((duration - first) / period) + 1
    beats = [
        {
            "timestamp": round(first + i * period, 6),
            "index": i,
            "strength": round(
                min(onsets, key=lambda x: abs(x[0] - (first + i * period)))[1], 4
            ),
            "bar_position": None,
            "provenance": PcmWavProvider.name,
        }
        for i in range(count)
        if first + i * period <= duration
    ]
    return round(bpm, 3), beats


def validate_analysis(value: dict[str, Any]) -> list[str]:
    errors, duration = [], float(value.get("duration", 0))
    if value.get("status") not in STATUSES:
        errors.append("invalid_provider_status")
    bpm = value.get("estimated_bpm")
    if bpm is not None and (not math.isfinite(float(bpm)) or float(bpm) <= 0):
        errors.append("invalid_bpm")
    for name in ("beats", "onsets", "accent_events"):
        last = -1.0
        for event in value.get(name, []):
            t, strength = (
                float(event.get("timestamp", -1)),
                float(event.get("strength", 0)),
            )
            if not math.isfinite(t) or t < 0 or t > duration:
                errors.append(f"invalid_{name}_timestamp")
            if t < last:
                errors.append(f"non_monotonic_{name}")
            if not math.isfinite(strength) or not 0 <= strength <= 1:
                errors.append(f"invalid_{name}_strength")
            if not event.get("provenance"):
                errors.append(f"missing_{name}_provenance")
            last = t
    for section in value.get("sections", []):
        if (
            not 0
            <= float(section.get("start", -1))
            < float(section.get("end", -1))
            <= duration
        ):
            errors.append("invalid_section_range")
    if value.get("downbeats_available") and any(
        b.get("bar_position") is None for b in value.get("beats", [])
    ):
        errors.append("invalid_bar_grouping")
    if value.get("status") == "success" and not (
        value.get("beats") or value.get("onsets")
    ):
        errors.append("success_without_results")
    if value.get("status") in {"unavailable", "failed", "skipped"} and any(
        value.get(name) for name in ("beats", "onsets", "accent_events")
    ):
        errors.append("results_in_inactive_status")
    last_energy = -1.0
    for point in value.get("energy_curve", []):
        t, energy = float(point.get("timestamp", -1)), float(point.get("energy", -1))
        if not math.isfinite(t) or t < last_energy or t < 0 or t > duration:
            errors.append("invalid_energy_timestamp")
        if not math.isfinite(energy) or not 0 <= energy <= 1:
            errors.append("invalid_energy_value")
        last_energy = t
    return sorted(set(errors))


def analyze_soundtrack(
    path: Path, provider: AudioAnalysisProvider | None = None
) -> dict[str, Any]:
    provider = provider or PcmWavProvider()
    result = provider.analyze(path)
    errors = validate_analysis(result)
    if errors:
        result = _empty(
            "failed",
            getattr(provider, "name", "unknown"),
            getattr(provider, "version", "unknown"),
            "validation:" + ",".join(errors),
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("soundtrack", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (
        json.dumps(analyze_soundtrack(args.soundtrack), indent=2, sort_keys=True) + "\n"
    )
    args.output.write_text(payload) if args.output else print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
