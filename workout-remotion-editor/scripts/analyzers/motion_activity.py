"""Auto-Editor levels are signals, never an instruction to remove footage."""
from __future__ import annotations

import re
import subprocess
from fractions import Fraction
from typing import Any

from .base import Result, command, executable, number


def parse_levels(text: str) -> list[float]:
    lines = text.strip().splitlines()
    if not lines or lines[0].strip() != "@start":
        raise ValueError("Auto-Editor levels output lacks @start marker")
    values = [number(line.strip()) for line in lines[1:] if line.strip()]
    if any(value < 0 or value > 1 for value in values):
        raise ValueError("Auto-Editor level outside [0, 1]")
    return values


def regions(values: list[float], rate: Fraction, duration: float, threshold: float,
            method: str, source_id: str, stream: int = 0) -> list[dict[str, Any]]:
    """Map a contiguous logical sampling grid to seconds exactly once.

    Discard the initial synthetic zero motion sample rather than calling it rest.
    Do not extrapolate evidence past the observed sample coverage.
    """
    if not values:
        return []
    first = 1 if method == "motion" else 0
    if first >= len(values):
        return []
    step = 1 / rate
    ranges: list[dict[str, Any]] = []
    begin = first
    active = values[first] >= threshold
    for index in range(first + 1, len(values) + 1):
        if index < len(values) and (values[index] >= threshold) == active:
            continue
        start, end = float(begin * step), min(float(index * step), duration)
        if end > start:
            kind = ("motion_active" if active else "low_motion") if method == "motion" else (
                "audio_active" if active else "audio_inactive")
            ranges.append({
                "id": f"{source_id}:{method}:{stream}:{len(ranges)}", "start": start, "end": end,
                "type": kind, "threshold": threshold, "mean_level": sum(values[begin:index]) / (index - begin),
                "stream": stream,
                "reason": f"Auto-Editor {method} level {'at/above' if active else 'below'} {threshold}; "
                          "not an exercise, speech, or rest classification.",
            })
        if index < len(values):
            begin, active = index, values[index] >= threshold
    return ranges


def dead_time_candidates(activity: list[dict[str, Any]], minimum: float) -> list[dict[str, Any]]:
    """Low motion can suggest review; quiet audio alone cannot establish dead time."""
    candidates = []
    for signal in activity:
        if signal["type"] == "low_motion" and signal["end"] - signal["start"] >= minimum:
            candidates.append({
                "id": f"{signal['id']}:candidate", "start": signal["start"], "end": signal["end"],
                "signal_ids": [signal["id"]],
                "reason": "Sustained low motion: review for possible setup/recovery/dead time. "
                          "May contain coaching, equipment adjustment, static holds, or pre-lift preparation. "
                          "Editor decides retain/remove/shorten/speed-ramp after reviewing footage.",
            })
    return candidates


class MotionActivity:
    name = "auto-editor"
    category = "motion_activity"
    upstream = "https://github.com/WyattBlue/auto-editor"
    version: str | None = None

    def __init__(self, motion_threshold: float = 0.02, audio_threshold: float = 0.04,
                 timebase: str = "30/1", minimum_candidate_seconds: float = 2.0):
        self.configuration = {"motion_threshold": motion_threshold, "audio_threshold": audio_threshold,
                              "timebase": timebase, "minimum_candidate_seconds": minimum_candidate_seconds,
                              "motion_stream": 0, "audio_streams": "all",
                              "width": 400, "blur": 9, "cache": False}

    def analyze(self, source: dict[str, Any], timeout: float) -> Result:
        binary = executable("auto-editor")
        version_text = command([binary, "--version"], timeout, 1024 * 1024).strip()
        match = re.search(r"\b31\.6\.0\b", version_text)
        self.version = match.group() if match else version_text
        if not match:
            raise ValueError(f"unsupported Auto-Editor version: {version_text}; install tested 31.6.0")
        if source["duration"] is None:
            return Result(status="skipped", warnings=["Activity analysis requires known duration."])
        metadata = source.get("metadata", {})
        if not metadata.get("timestamp_origin_verified", False):
            return Result(status="skipped", warnings=[
                "Stream timestamp origins are unknown or non-zero; refusing potentially shifted activity evidence."])
        rate = Fraction(self.configuration["timebase"])
        activity, warnings, errors = [], [], []
        methods = [("motion", 0, self.configuration["motion_threshold"])]
        methods.extend(("audio", stream, self.configuration["audio_threshold"])
                       for stream in range(metadata.get("audio_streams", 0)))
        for method, stream, threshold in methods:
            try:
                method_spec = f"{method}:stream={stream}"
                if method == "motion":
                    method_spec += ",width=400,blur=9"
                output = command([binary, "levels", source["path"], "--edit", method_spec,
                                  "--timebase", self.configuration["timebase"],
                                  "--display", "float", "--no-cache"], timeout)
                values = parse_levels(output)
                coverage = float(Fraction(len(values), 1) / rate)
                tolerance = float(2 / rate)
                if coverage > source["duration"] + tolerance:
                    raise ValueError("levels exceed source duration; timestamp origin/coverage may be wrong")
                if not values:
                    warnings.append(f"No {method} samples for stream {stream}.")
                elif coverage < source["duration"] - tolerance:
                    warnings.append(f"{method} stream {stream} covers only {coverage:.3f}s; tail is unknown.")
                activity.extend(regions(values, rate, source["duration"], threshold,
                                        method, source["id"], stream))
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                errors.append(f"{method} stream {stream}: {exc}")
        if not metadata.get("audio_streams"):
            warnings.append("No audio stream; quiet/speech evidence is unavailable, not inferred.")
        warnings.extend([
            "Motion measures full-frame pixel changes, including camera movement; it is not athlete activity.",
            "Audio inactivity is not absence of coaching. Machine regions need editorial review.",
            "Initial synthetic zero motion sample is excluded; no output footage is edited.",
        ])
        status = "partial" if errors and activity else "failed" if errors else "success" if activity else "no_results"
        return Result(status=status,
                      evidence={"activity_regions": activity,
                                "candidate_dead_time": dead_time_candidates(
                                    activity, self.configuration["minimum_candidate_seconds"])},
                      warnings=warnings, errors=errors)
