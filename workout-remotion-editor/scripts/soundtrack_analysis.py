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
import os
import re
import shutil
import struct
import subprocess
import tempfile
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


STATUSES = {"success", "partial", "no_results", "unavailable", "failed", "skipped"}
BASELINE_CAPABILITIES = [
    "decode_wav",
    "global_tempo",
    "beat_grid",
    "onset_detection",
    "accent_detection",
    "energy_curve",
    "peak_measurement",
]
ADVANCED_CAPABILITIES = [
    "decode_wav",
    "decode_compressed_audio",
    "global_tempo",
    "local_tempo",
    "beat_grid",
    "beat_strength",
    "onset_detection",
    "accent_detection",
    "section_detection",
    "energy_curve",
    "integrated_loudness",
    "peak_measurement",
]


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
        "provider_capabilities": [],
        "tempo_curve": [],
        "tempo_regions": [],
        "beat_confidence": None,
        "beat_confidence_kind": None,
        "downbeats": [],
        "bars": [],
        "integrated_loudness": None,
        "loudness_range": None,
        "true_peak": None,
        "analysis_quality": "insufficient",
        "diagnostics": [reason],
    }


class PcmWavProvider:
    """Envelope/onset autocorrelation provider; no optional native packages."""

    name, version = "pcm_wav_envelope", "1.0"
    capabilities = BASELINE_CAPABILITIES

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
            "provider_capabilities": list(self.capabilities),
            "tempo_curve": [],
            "tempo_regions": [],
            "beat_confidence": None,
            "beat_confidence_kind": None,
            "downbeats": [],
            "bars": [],
            "integrated_loudness": None,
            "loudness_range": None,
            "true_peak": round(20 * math.log10(max(abs(x) for x in samples)), 3),
            "analysis_quality": "moderate" if beats else "low",
            "diagnostics": []
            if beats
            else ["tempo_not_reliable", "sections_unavailable"],
        }


class LibrosaProvider:
    """Optional MIR provider. Imports and external decoding are runtime isolated."""

    name = "librosa"
    capabilities = ADVANCED_CAPABILITIES

    def __init__(self, *, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate, self.hop_length = sample_rate, hop_length
        try:
            import librosa  # type: ignore
        except (ImportError, OSError) as exc:
            self.librosa, self.version, self.import_error = (
                None,
                "unavailable",
                type(exc).__name__,
            )
        else:
            self.librosa, self.version, self.import_error = (
                librosa,
                str(librosa.__version__),
                None,
            )

    @property
    def available(self) -> bool:
        return self.librosa is not None

    def analyze(self, path: Path) -> dict[str, Any]:
        if not self.available:
            return _empty(
                "unavailable",
                self.name,
                self.version,
                "advanced_provider_unavailable:" + str(self.import_error),
            )
        started, decode_path, temporary, decode_backend = (
            time.monotonic(),
            path,
            None,
            "librosa/soundfile",
        )
        try:
            if path.suffix.lower() not in {".wav", ".flac"} and shutil.which("ffmpeg"):
                handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                handle.close()
                temporary = Path(handle.name)
                subprocess.run(
                    [
                        "ffmpeg",
                        "-nostdin",
                        "-y",
                        "-v",
                        "error",
                        "-i",
                        str(path),
                        "-vn",
                        "-ac",
                        "1",
                        "-ar",
                        str(self.sample_rate),
                        "-f",
                        "wav",
                        str(temporary),
                    ],
                    check=True,
                    timeout=300,
                    capture_output=True,
                )
                decode_path, decode_backend = temporary, "ffmpeg"
            y, sr = self.librosa.load(str(decode_path), sr=self.sample_rate, mono=True)
            duration = float(self.librosa.get_duration(y=y, sr=sr))
            if duration <= 0 or not len(y):
                return _empty("no_results", self.name, self.version, "empty_audio")
            onset_env = self.librosa.onset.onset_strength(
                y=y, sr=sr, hop_length=self.hop_length
            )
            onset_frames = self.librosa.onset.onset_detect(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=self.hop_length,
                units="frames",
            )
            tempo, beat_frames = self.librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=self.hop_length,
                units="frames",
            )
            tempo_value = float(tempo.flat[0] if hasattr(tempo, "flat") else tempo)
            beat_times = self.librosa.frames_to_time(
                beat_frames, sr=sr, hop_length=self.hop_length
            )
            onset_times = self.librosa.frames_to_time(
                onset_frames, sr=sr, hop_length=self.hop_length
            )
            env_peak = float(max(onset_env)) if len(onset_env) else 0.0
            strengths = [
                float(onset_env[min(int(f), len(onset_env) - 1)] / env_peak)
                if env_peak
                else 0.0
                for f in beat_frames
            ]
            support = _beat_support([float(x) for x in beat_times], strengths)
            beats = [
                {
                    "timestamp": round(float(t), 6),
                    "index": i,
                    "strength": round(strengths[i], 4),
                    "bar_position": None,
                    "provenance": self.name,
                }
                for i, t in enumerate(beat_times)
            ]
            onsets = [
                {
                    "timestamp": round(float(t), 6),
                    "strength": round(float(onset_env[int(f)] / env_peak), 4)
                    if env_peak
                    else 0.0,
                    "provenance": self.name,
                }
                for t, f in zip(onset_times, onset_frames)
            ]
            accents = [
                dict(x, kind="transient") for x in onsets if x["strength"] >= 0.72
            ]
            rms = self.librosa.feature.rms(y=y, hop_length=self.hop_length)[0]
            rms_peak = float(max(rms)) if len(rms) else 0.0
            curve = _advanced_energy(
                self.librosa, rms, rms_peak, onset_env, sr, self.hop_length
            )
            regions, tempo_curve = _tempo_regions(
                [float(x) for x in beat_times], duration, self.name
            )
            sections = _sections_from_energy(curve, duration, self.name)
            loudness = _ffmpeg_loudness(path)
            quality = (
                "high"
                if len(beats) >= 8 and support >= 0.65
                else "moderate"
                if len(beats) >= 4 and support >= 0.4
                else "low"
                if onsets
                else "insufficient"
            )
            diagnostics = ["advanced_provider_selected", "no_defensible_downbeat"]
            if len(regions) > 1:
                diagnostics.append("variable_tempo_detected")
            if decode_backend == "ffmpeg":
                diagnostics.append("compressed_audio_decoded_via_ffmpeg")
            return {
                "status": "success" if beats else "partial",
                "provider": {"name": self.name, "version": self.version},
                "provider_configuration": {
                    "sample_rate": sr,
                    "hop_length": self.hop_length,
                },
                "decoding_backend": decode_backend,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "analysis_contract_version": "2.0",
                "processing_duration_seconds": round(time.monotonic() - started, 3),
                "duration": round(duration, 6),
                "sample_rate": sr,
                "estimated_bpm": round(tempo_value, 2) if beats else None,
                "alternate_tempo_bpm": round(
                    tempo_value * (2 if tempo_value < 100 else 0.5), 2
                )
                if beats
                else None,
                "tempo_ambiguity": "half_double_candidate_not_resolved"
                if beats
                else None,
                "tempo_curve": tempo_curve,
                "tempo_regions": regions,
                "beats": beats,
                "onsets": onsets,
                "beat_confidence": round(support, 4) if beats else None,
                "beat_confidence_kind": "normalized_support_score",
                "accent_events": accents,
                "downbeats_available": False,
                "downbeats": [],
                "bars": [],
                "meter": None,
                "sections": sections,
                "energy_curve": curve,
                "integrated_loudness": loudness.get("integrated_loudness"),
                "loudness_range": loudness.get("loudness_range"),
                "true_peak": loudness.get("true_peak"),
                "provider_capabilities": list(self.capabilities),
                "analysis_quality": quality,
                "diagnostics": diagnostics + loudness.get("diagnostics", []),
            }
        except Exception as exc:
            # Third-party/native decoder errors must never escape the optional
            # boundary. KeyboardInterrupt/SystemExit still propagate.
            return _empty(
                "failed",
                self.name,
                self.version,
                "advanced_analysis_failed:" + type(exc).__name__,
            )
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def _beat_support(times: list[float], strengths: list[float]) -> float:
    """A labeled support score, not a probability or provider confidence."""
    if len(times) < 3:
        return 0.0
    intervals = [b - a for a, b in zip(times, times[1:]) if b > a]
    mean = sum(intervals) / len(intervals)
    regularity = max(
        0.0,
        1.0
        - (sum(abs(x - mean) for x in intervals) / len(intervals)) / max(mean, 1e-9),
    )
    return min(
        1.0,
        max(0.0, 0.65 * regularity + 0.35 * (sum(strengths) / max(1, len(strengths)))),
    )


def _tempo_regions(
    times: list[float], duration: float, provenance: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if len(times) < 4:
        return [], []
    local = [
        60.0 / (times[i + 1] - times[i])
        for i in range(len(times) - 1)
        if times[i + 1] - times[i] > 0.2
    ]
    curve = [
        {"timestamp": round(times[i], 3), "bpm": round(v, 1), "provenance": provenance}
        for i, v in enumerate(local)
    ]
    if not local:
        return [], curve
    regions, start, bucket = [], times[0], [local[0]]
    for i, value in enumerate(local[1:], 1):
        center = sum(bucket) / len(bucket)
        if abs(value - center) / center > 0.08:
            regions.append(
                {
                    "start": round(start, 3),
                    "end": round(times[i], 3),
                    "bpm": round(center, 1),
                    "provenance": provenance,
                }
            )
            start, bucket = times[i], [value]
        else:
            bucket.append(value)
    regions.append(
        {
            "start": round(start, 3),
            "end": round(duration, 3),
            "bpm": round(sum(bucket) / len(bucket), 1),
            "provenance": provenance,
        }
    )
    return regions, curve


def _advanced_energy(
    librosa: Any, rms: Any, peak: float, onset_env: Any, sr: int, hop: int
) -> list[dict[str, Any]]:
    points, step = [], max(1, round(sr / hop / 4))
    for i in range(0, len(rms), step):
        window = rms[i : i + step]
        normalized = (
            float(sum(window) / len(window) / peak) if peak and len(window) else 0.0
        )
        density = float(
            sum(
                1
                for x in onset_env[i : i + step]
                if x > (max(onset_env) * 0.35 if len(onset_env) else 1)
            )
            / max(1, step)
        )
        points.append(
            {
                "timestamp": round(
                    float(librosa.frames_to_time(i, sr=sr, hop_length=hop)), 3
                ),
                "energy": round(min(1.0, normalized), 4),
                "transient_density": round(density, 4),
                "provenance": "librosa",
            }
        )
    return points


def _sections_from_energy(
    curve: list[dict[str, Any]], duration: float, provenance: str
) -> list[dict[str, Any]]:
    """Conservative coarse energy phases; not semantic verse/chorus labels."""
    if duration < 6 or len(curve) < 12:
        return []
    values = [x["energy"] for x in curve]
    low, high = sorted(values)[len(values) // 3], sorted(values)[2 * len(values) // 3]
    labels = []
    for i, value in enumerate(values):
        trend = values[min(len(values) - 1, i + 2)] - values[max(0, i - 2)]
        labels.append(
            "rising"
            if trend > 0.18
            else "falling"
            if trend < -0.18
            else "low"
            if value <= low
            else "high"
            if value >= high
            else "steady"
        )
    sections, start, current = [], 0, labels[0]
    for i, label in enumerate(labels[1:], 1):
        if label != current and i - start >= 4:
            sections.append(
                {
                    "id": f"section_{len(sections) + 1}",
                    "start": curve[start]["timestamp"],
                    "end": curve[i]["timestamp"],
                    "descriptor": current,
                    "provenance": provenance,
                }
            )
            start, current = i, label
    sections.append(
        {
            "id": f"section_{len(sections) + 1}",
            "start": curve[start]["timestamp"],
            "end": round(duration, 3),
            "descriptor": current,
            "provenance": provenance,
        }
    )
    return sections if len(sections) > 1 else []


def _ffmpeg_loudness(path: Path) -> dict[str, Any]:
    if not shutil.which("ffmpeg"):
        return {"diagnostics": ["standards_loudness_unavailable"]}
    try:
        run = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-i",
                str(path),
                "-af",
                "loudnorm=print_format=json",
                "-f",
                "null",
                os.devnull,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        match = re.search(r'\{\s*"input_i".*?\}', run.stderr, re.S)
        data = json.loads(match.group(0)) if match else {}
        return {
            "integrated_loudness": _finite(data.get("input_i")),
            "loudness_range": _finite(data.get("input_lra")),
            "true_peak": _finite(data.get("input_tp")),
            "diagnostics": [] if data else ["standards_loudness_unavailable"],
        }
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {"diagnostics": ["standards_loudness_unavailable"]}


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, 3) if math.isfinite(number) else None


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
    for region in value.get("tempo_regions", []):
        if (
            not 0
            <= float(region.get("start", -1))
            < float(region.get("end", -1))
            <= duration
        ):
            errors.append("invalid_tempo_region")
    confidence = value.get("beat_confidence")
    if confidence is not None and (
        not 0 <= float(confidence) <= 1 or not value.get("beat_confidence_kind")
    ):
        errors.append("invalid_beat_confidence")
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
    path: Path,
    provider: AudioAnalysisProvider | str | None = None,
    *,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Analyze with ``baseline``, ``advanced``, or safe advanced-first ``auto``.

    Passing a provider object retains the Phase 13 extension seam. Explicit
    ``advanced`` never disguises a missing package; ``auto`` records fallback.
    """
    mode = (
        provider
        if isinstance(provider, str)
        else "baseline"
        if provider is None
        else "custom"
    )
    selected: AudioAnalysisProvider
    if mode not in {"baseline", "advanced", "auto", "custom"}:
        raise ValueError("provider must be baseline, advanced, or auto")
    if mode == "baseline":
        selected = PcmWavProvider()
    elif mode == "advanced":
        selected = LibrosaProvider()
    elif mode == "auto":
        candidate = LibrosaProvider()
        selected = candidate if candidate.available else PcmWavProvider()
    else:
        selected = provider  # type: ignore[assignment]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    config = {
        "provider": selected.name,
        "version": selected.version,
        "sample_rate": getattr(selected, "sample_rate", None),
        "hop_length": getattr(selected, "hop_length", None),
    }
    key = hashlib.sha256(
        json.dumps({"source": digest, "config": config}, sort_keys=True).encode()
    ).hexdigest()
    cache_path = cache_dir / f"{key}.json" if cache_dir else None
    if cache_path and cache_path.is_file():
        cached = json.loads(cache_path.read_text())
        if not validate_analysis(cached):
            cached.setdefault("diagnostics", []).append("analysis_cache_hit")
            return cached
    result = selected.analyze(path)
    if (
        mode == "auto"
        and result.get("status") in {"failed", "unavailable"}
        and selected.name != PcmWavProvider.name
    ):
        fallback = PcmWavProvider().analyze(path)
        fallback.setdefault("diagnostics", []).extend(
            ["advanced_provider_unavailable", "fallback_to_baseline"]
        )
        result = fallback
    result["source_sha256"] = digest
    if not result.get("provider_capabilities"):
        result["provider_capabilities"] = list(getattr(selected, "capabilities", []))
    errors = validate_analysis(result)
    if errors:
        result = _empty(
            "failed",
            getattr(selected, "name", "unknown"),
            getattr(selected, "version", "unknown"),
            "validation:" + ",".join(errors),
        )
        result["source_sha256"] = digest
    if cache_path:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def provider_registry() -> dict[str, dict[str, Any]]:
    advanced = LibrosaProvider()
    return {
        "baseline": {
            "provider": PcmWavProvider.name,
            "available": True,
            "capabilities": list(BASELINE_CAPABILITIES),
        },
        "advanced": {
            "provider": advanced.name,
            "version": advanced.version,
            "available": advanced.available,
            "capabilities": list(ADVANCED_CAPABILITIES),
        },
        "auto": {
            "provider": advanced.name if advanced.available else PcmWavProvider.name,
            "available": True,
            "capabilities": list(
                advanced.capabilities if advanced.available else BASELINE_CAPABILITIES
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("soundtrack", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--provider", choices=("baseline", "advanced", "auto"), default="auto"
    )
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    payload = (
        json.dumps(
            analyze_soundtrack(
                args.soundtrack, args.provider, cache_dir=args.cache_dir
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    args.output.write_text(payload) if args.output else print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
