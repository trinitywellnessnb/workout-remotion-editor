#!/usr/bin/env python3
"""Normalize reviewed repetitions onto an edit timeline for Remotion.

This module is deliberately provider-neutral.  It never reads machine
``evidence.rep_candidates``: visible counters are derived solely from reviewed,
top-level editorial ``repetitions``.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


UNAVAILABLE = "rep counter unavailable: repetitions have not been editorially reviewed/promoted"
REGIONS = ("top-left", "top-right", "bottom-left", "bottom-right")


def time_to_frame(seconds: float, fps: float) -> int:
    """Map seconds to the nearest frame, with half frames rounding forward."""
    if seconds < 0 or fps <= 0:
        raise ValueError("seconds must be non-negative and fps must be positive")
    return int(math.floor(seconds * fps + 0.5 + 1e-9))


def choose_safe_region(
    preference: str = "top-right",
    *,
    occupied: list[str] | None = None,
    captions: bool = False,
) -> str:
    """Choose a deterministic corner; captions reserve both bottom corners."""
    if preference not in REGIONS:
        raise ValueError(f"invalid placement: {preference}")
    blocked = set(occupied or [])
    if captions:
        blocked.update(("bottom-left", "bottom-right"))
    order = (preference,) + tuple(x for x in REGIONS if x != preference)
    for region in order:
        if region not in blocked:
            return region
    raise ValueError("no counter safe zone remains after overlay/visual reservations")


def _maps_completion(rep: dict[str, Any], clip: dict[str, Any]) -> bool:
    end = float(rep["end"])
    # Half-open source windows prevent a completion on a shared cut boundary from
    # being emitted by both adjacent clips. The final source endpoint is allowed.
    return float(clip["source_start"]) < end <= float(clip["source_end"])


def _meaningfully_visible(rep: dict[str, Any], clip: dict[str, Any]) -> bool:
    start, end = float(rep["start"]), float(rep["end"])
    duration = end - start
    if duration <= 0 or not _maps_completion(rep, clip):
        return False
    overlap = max(0.0, min(end, float(clip["source_end"])) - max(start, float(clip["source_start"])))
    minimum = float(clip.get("minimum_rep_visibility", 0.5))
    return overlap / duration + 1e-9 >= minimum


def _group(rep: dict[str, Any], clip: dict[str, Any], reset: str) -> tuple[str, ...]:
    exercise = str(clip.get("exercise_id") or rep.get("exercise_id") or rep.get("segment_id") or "exercise")
    side = str(rep.get("side") or clip.get("side") or "")
    values = [exercise, side]
    if reset == "set":
        values.append(str(rep.get("set_id") or clip.get("set_id") or ""))
    elif reset not in {"exercise", "continuous"}:
        raise ValueError("reset must be continuous, exercise, or set")
    return tuple(values) if reset != "continuous" else ("global",)


def build_rep_counter_plan(
    analysis: dict[str, Any], edit_plan: dict[str, Any], *, fps: float = 30
) -> dict[str, Any]:
    """Return serializable Remotion props from reviewed reps and edited clips."""
    config = edit_plan.get("rep_counter", {})
    if not config.get("enabled", False):
        return {"enabled": False, "events": []}
    reps = analysis.get("repetitions")
    if not reps:
        return {"enabled": False, "events": [], "reason": UNAVAILABLE}

    mode = config.get("mode", "number")
    target = config.get("target_reps")
    if mode not in {"number", "rep", "progress"}:
        raise ValueError("rep counter mode must be number, rep, or progress")
    if mode == "progress" and (not isinstance(target, int) or target <= 0):
        raise ValueError("progress mode requires a positive explicit target_reps")
    reset = config.get("reset", "exercise")
    placement = choose_safe_region(
        config.get("placement", "top-right"),
        occupied=edit_plan.get("overlay_layout", {}).get("occupied_regions", []),
        captions=bool(edit_plan.get("overlay_layout", {}).get("captions")),
    )

    candidates: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    chronology: dict[str, float] = {}
    for clip_index, clip in enumerate(edit_plan.get("clips", [])):
        rate = float(clip.get("playback_rate", 1))
        if rate <= 0:
            raise ValueError("clip playback_rate must be positive")
        if clip.get("role") in {"hook", "replay", "hook_replay"} and config.get("replay_behavior", "suppress") == "suppress":
            continue
        source_id = str(clip.get("source_id"))
        source_start = float(clip["source_start"])
        if source_id in chronology and float(clip["source_end"]) <= chronology[source_id]:
            raise ValueError("chronological source fragments cannot be reordered")
        chronology[source_id] = source_start
        for rep in reps:
            if not rep.get("complete") or rep.get("review_decision") not in {"accept", "adjust"}:
                continue
            if rep.get("source_id") != clip.get("source_id") or not _meaningfully_visible(rep, clip):
                continue
            completion = float(clip["timeline_start"]) + (
                float(rep["end"]) - float(clip["source_start"])
            ) / rate
            candidates.append((completion, rep, dict(clip, _clip_index=clip_index)))

    candidates.sort(key=lambda row: (row[0], row[2]["_clip_index"], row[1]["id"]))
    seen: set[str] = set()
    counts: dict[tuple[str, ...], int] = {}
    scope_starts: dict[tuple[str, ...], float] = {}
    events: list[dict[str, Any]] = []
    for completion, rep, clip in candidates:
        rep_id = str(rep["id"])
        if rep_id in seen:
            continue
        seen.add(rep_id)
        group = _group(rep, clip, reset)
        scope_starts.setdefault(group, float(clip["timeline_start"]))
        counts[group] = counts.get(group, 0) + 1
        count = counts[group]
        events.append({
            "id": f"rep-counter-{rep_id}",
            "editorial_repetition_id": rep_id,
            "source_id": rep["source_id"],
            "segment_id": rep.get("segment_id"),
            "set_id": rep.get("set_id"),
            "exercise_id": clip.get("exercise_id") or rep.get("exercise_id"),
            "side": rep.get("side") or clip.get("side"),
            "source_completion": rep["end"],
            "composition_time": completion,
            "frame": time_to_frame(completion, fps),
            "displayed_count": count,
            "source_rep_number": rep.get("source_rep_number"),
            "target": target,
            "display_mode": mode,
            "stream_id": "|".join(group),
            "scope_start_frame": time_to_frame(scope_starts[group], fps),
        })
    return {
        "enabled": True,
        "fps": fps,
        "placement": placement,
        "animation_enabled": config.get("animation_enabled", True),
        "events": events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("edit_plan", type=Path)
    parser.add_argument("--fps", type=float, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_rep_counter_plan(
        json.loads(args.analysis.read_text()), json.loads(args.edit_plan.read_text()), fps=args.fps
    )
    text = json.dumps(result, indent=2) + "\n"
    args.output.write_text(text) if args.output else print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
