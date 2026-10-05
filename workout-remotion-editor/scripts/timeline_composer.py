#!/usr/bin/env python3
"""Compile upstream editorial decisions into a deterministic render timeline.

The composer deliberately does not analyse pixels or invent repetitions.  It
turns Phase 9 selections, Phase 10 style contracts and Phase 11 candidates into
the last renderer-neutral contract before Remotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from semantic_shot_director import (
    BREATHERS,
    MICRO,
    role_aware_transition,
    role_overrides,
)
from style_director import duration_sequence, resolve_style, speed_curve

ALLOWED_TRANSITIONS = {
    "none",
    "cut",
    "motion_match",
    "cross_dissolve",
    "fade",
    "dip_black",
    "whip",
    "glitch",
    "push_cut",
}
ACTIVE_ROLES = {"primary", "primary_movement", "complete_rep_anchor"}


def _interval(shot: dict[str, Any]) -> tuple[float, float]:
    interval = shot.get("source_interval", {})
    return (
        float(interval.get("start", shot.get("source_start", 0))),
        float(interval.get("end", shot.get("source_end", 0))),
    )


def _role(shot: dict[str, Any]) -> str:
    role = (
        shot.get("selected_role")
        or shot.get("shot_role")
        or shot.get("role")
        or "unknown"
    )
    return (
        "hook_replay" if role in {"replay", "hook"} or shot.get("replay_of") else role
    )


def _normalize(inputs: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    semantic = inputs.get("semantic_plan", {}).get("shots") or inputs.get("shots")
    if semantic:
        return [dict(x) for x in semantic], "semantic_shot_candidates"
    rep = inputs.get("rep_plan", {}).get("clips") or inputs.get("clips")
    if rep:
        return [dict(x) for x in rep], "phase9_rep_plan"
    analysis = inputs.get("analysis", {})
    scenes = analysis.get("scenes") or analysis.get("activity_candidates") or []
    if scenes:
        return [
            dict(x, role=x.get("role", "primary_movement")) for x in scenes
        ], "scene_activity_candidates"
    return [dict(x) for x in inputs.get("manual_clips", [])], "manual_clips"


def _default_target(shots: list[dict[str, Any]], style: dict[str, Any]) -> float:
    available = sum(max(0, _interval(s)[1] - _interval(s)[0]) for s in shots)
    movements = len({s.get("exercise_id") for s in shots if s.get("exercise_id")})
    social = 30 if style.get("platform_bias") == "vertical_social" else 24
    return round(
        min(max(6.0, movements * 4.0, available * 0.72), social, available or 15), 3
    )


def _transition(
    left: dict[str, Any],
    right: dict[str, Any],
    style: dict[str, Any],
    omitted_jump: bool,
) -> dict[str, Any]:
    dominant = max(style["profile_weights"], key=style["profile_weights"].get)
    kind = role_aware_transition(_role(left), _role(right), dominant)
    palette = style["transition_policy"]["palette"]
    if omitted_jump and "glitch" in palette:
        kind = "glitch"
    elif omitted_jump and dominant == "cinematic_trailer" and "motion_match" in palette:
        kind = "motion_match"
    if kind not in palette and kind != "cut":
        kind = max(palette, key=palette.get)
    overlap = kind in {
        "cross_dissolve",
        "fade",
        "motion_match",
        "whip",
        "glitch",
        "push_cut",
    }
    duration = (
        0.0
        if kind in {"none", "cut"}
        else (0.08 if kind in {"glitch", "whip"} else 0.18)
    )
    return {
        "type": kind,
        "duration_seconds": duration,
        "model": "overlap" if overlap else "cut",
    }


def _phase(style: dict[str, Any], index: int, count: int) -> dict[str, Any]:
    position = (index + 0.5) / max(1, count)
    phases = style.get("style_phases") or [{"start": 0, "end": 1, "style": "default"}]
    selected = next(
        (p for p in phases if float(p["start"]) <= position <= float(p["end"])),
        phases[-1],
    )
    curve = style.get("pacing_curve", ["movement"])
    label = curve[min(len(curve) - 1, int(position * len(curve)))]
    return {
        "style": selected["style"],
        "label": label,
        "normalized_position": round(position, 4),
    }


def _remap(
    shot: dict[str, Any], style: dict[str, Any], is_last_active: bool
) -> tuple[float, dict[str, Any] | None, list[str]]:
    role, reasons = _role(shot), []
    policy = style["time_remapping"]
    if not policy["enabled"]:
        return 1.0, None, reasons
    fps = shot.get("source_fps")
    if is_last_active and (
        policy.get("final_rep_slowdown")
        or style.get("ending_emphasis") in {"slow_final_rep", "dramatic_payoff"}
    ):
        curve = speed_curve(
            style,
            moment=float(shot.get("meaningful_action_position", 0.55)),
            source_fps=float(fps) if fps else None,
            requested=True,
        )
        if curve.get("conservative_for_source_fps"):
            reasons.append("slowdown_limited_by_source_fps")
        return (
            1.0,
            {**curve, "curve_type": curve.get("type"), "type": "dramatic_bell_curve"},
            reasons,
        )
    if role in BREATHERS and policy.get("fast_motion_amount", 0) > 0.05:
        return (
            round(min(2.0, 1 + policy["fast_motion_amount"]), 3),
            None,
            ["setup_fast_motion"],
        )
    return 1.0, None, reasons


def _mapped_duration(
    source_duration: float, rate: float, remap: dict[str, Any] | None
) -> float:
    if not remap:
        return source_duration / rate
    points = remap.get("points") or remap.get("curve") or remap.get("keyframes") or []
    samples = [
        (float(p.get("position", 0)), float(p.get("speed", p.get("rate", 1))))
        for p in points
        if isinstance(p, dict)
    ]
    if len(samples) < 2:
        return source_duration / rate
    # Integrate reciprocal speed over normalized source position. This makes
    # source→composition duration exact for the declared piecewise-linear
    # curve rather than using an unsafe arithmetic mean.
    factor = sum(
        (right[0] - left[0]) * ((1 / left[1]) + (1 / right[1])) / 2
        for left, right in zip(samples, samples[1:])
    )
    return source_duration * factor


def _rep_fields(
    shot: dict[str, Any], display: dict[tuple[str, str], int]
) -> tuple[list[str], list[int], list[int]]:
    ids = list(
        shot.get("editorial_rep_ids") or shot.get("editorial_repetition_ids") or []
    )
    source_nums = list(shot.get("source_rep_numbers") or [])
    if not source_nums and ids and shot.get("source_sequence_start"):
        source_nums = list(
            range(
                int(shot["source_sequence_start"]),
                int(shot.get("source_sequence_end", shot["source_sequence_start"])) + 1,
            )
        )
    shown: list[int] = []
    if _role(shot) != "hook_replay":
        key = (str(shot.get("exercise_id") or "exercise"), str(shot.get("side") or ""))
        for _ in ids:
            display[key] += 1
            shown.append(display[key])
    return ids, source_nums, shown


def compile_timeline(
    inputs: dict[str, Any],
    *,
    prompt: str = "",
    target_duration: float | None = None,
    aspect_ratio: str = "9:16",
    fps: int = 30,
    seed: int | str = 0,
) -> dict[str, Any]:
    """Compile exact ranges and composition timing from normalized inputs."""
    style = inputs.get("style") or resolve_style(prompt, seed=seed)
    shots, fallback = _normalize(inputs)
    if not shots:
        raise ValueError("no source footage candidates")
    # Upstream order is authoritative. Only remove unusable/dead-time and user-suppressed roles.
    prompt_roles = role_overrides(prompt)
    suppressed = set(
        inputs.get("semantic_plan", {}).get("role_overrides", {}).get("suppress", [])
    ) | set(prompt_roles["suppress"])
    shots = [s for s in shots if _role(s) not in {"dead_time", "unusable"} | suppressed]
    target = float(
        target_duration
        or inputs.get("target_duration")
        or _default_target(shots, style)
    )
    roles = [_role(s) for s in shots]
    desired = duration_sequence(style, len(shots), roles)
    # Keep complete rep anchors whole; trim optional roles at safe supplied boundaries.
    prepared = []
    for shot, choice in zip(shots, desired):
        start, end = _interval(shot)
        if end <= start:
            raise ValueError("source start must be before source end")
        role = _role(shot)
        full = end - start
        duration = (
            full
            if role in ACTIVE_ROLES
            and (shot.get("editorial_rep_ids") or shot.get("editorial_repetition_ids"))
            else min(full, choice["duration"])
        )
        if role in MICRO:
            duration = min(duration, 0.7)
        prepared.append((shot, start, start + duration, choice))
    # Prevent detail spam even for scene/manual fallback inputs that have not
    # passed through the Phase 11 grammar. A slower style permits fewer.
    max_micro = int(
        style.get("overrides", {}).get(
            "maximum_consecutive_micro_clips", 3 if style["intent"]["pace"] > 0.7 else 2
        )
    )
    controlled, micro_run = [], 0
    for item in prepared:
        micro_run = micro_run + 1 if _role(item[0]) in MICRO else 0
        if micro_run <= max_micro:
            controlled.append(item)
    prepared = controlled

    # Budget removes lowest-value optional footage, never mutilates complete reps.
    def total(items: list[tuple]) -> float:
        return sum(x[2] - x[1] for x in items)

    priority = {
        "rest": 0,
        "dead_time": 0,
        "setup": 1,
        "walk_between_movements": 2,
        "environment_context": 2,
        "close_detail": 3,
        "partial_movement_detail": 3,
        "hero_shot": 4,
        "ending_candidate": 5,
        "primary_movement": 8,
        "complete_rep_anchor": 9,
        "hook_replay": 10,
    }
    while len(prepared) > 1 and total(prepared) > target * 1.08:
        removable = [
            (priority.get(_role(x[0]), 6), i)
            for i, x in enumerate(prepared)
            if not (
                _role(x[0]) in ACTIVE_ROLES
                and (
                    x[0].get("editorial_rep_ids")
                    or x[0].get("editorial_repetition_ids")
                )
            )
            and _role(x[0]) not in set(prompt_roles["force"])
        ]
        if not removable:
            break
        prepared.pop(min(removable)[1])
    last_active = max(
        (i for i, x in enumerate(prepared) if _role(x[0]) in ACTIVE_ROLES), default=-1
    )
    segments, display = [], defaultdict(int)
    cursor = 0.0
    for i, (shot, start, end, choice) in enumerate(prepared):
        rate, remap, remap_reasons = _remap(shot, style, i == last_active)
        source_duration = end - start
        comp_duration = _mapped_duration(source_duration, rate, remap)
        omitted_jump = False
        if i:
            prev = prepared[i - 1][0]
            omitted_jump = (
                prev.get("source_id") == shot.get("source_id")
                and prev.get("source_sequence_end")
                and shot.get("source_sequence_start")
                and int(shot["source_sequence_start"])
                > int(prev["source_sequence_end"]) + 1
            )
            tin = _transition(prev, shot, style, omitted_jump)
            cursor -= tin["duration_seconds"] if tin["model"] == "overlap" else 0
        else:
            tin = {"type": "none", "duration_seconds": 0.0, "model": "cut"}
        ids, source_nums, shown = _rep_fields(shot, display)
        replay = "hook_replay" if _role(shot) == "hook_replay" else None
        protected = bool(
            ids
            or replay
            or shot.get("user_required")
            or shot.get("identity_critical")
            or shot.get("locked_boundary")
        )
        supplied_margin = shot.get("flexible_trim_margin")
        default_margin = 0.0 if protected else min(0.2, source_duration * 0.12)
        before_margin = float(shot.get("safe_trim_margin_before", supplied_margin if supplied_margin is not None else default_margin))
        after_margin = float(shot.get("safe_trim_margin_after", supplied_margin if supplied_margin is not None else default_margin))
        segment = {
            "segment_id": str(
                shot.get("candidate_id") or shot.get("id") or f"segment-{i + 1:03d}"
            ),
            "source_id": str(shot.get("source_id", "source")),
            "source_path": shot.get("source_path"),
            "source_start": round(start, 6),
            "source_end": round(end, 6),
            "source_duration": round(source_duration, 6),
            "composition_start": round(cursor, 6),
            "composition_end": round(cursor + comp_duration, 6),
            "composition_duration": round(comp_duration, 6),
            "playback_rate": rate,
            "time_remap": remap,
            "shot_role": _role(shot),
            "selected_candidate_id": shot.get("candidate_id"),
            "style_phase": _phase(style, i, len(prepared)),
            "exercise_id": shot.get("exercise_id"),
            "rep_ids": ids,
            "source_rep_numbers": source_nums,
            "display_rep_numbers": shown,
            "continuity_group": shot.get("continuity_group")
            or shot.get("source_group_id")
            or shot.get("source_id"),
            "replay_type": replay,
            "transition_in": tin,
            "transition_out": None,
            "overlay_regions": shot.get("overlay_safe_regions") or ["top", "bottom"],
            "rep_counter_eligible": bool(ids) and replay is None,
            "counter_events": [],
            "selection_reasons": list(shot.get("selection_reasons") or [])
            + remap_reasons,
            "source_to_composition": {
                "source_origin": round(start, 6),
                "composition_origin": round(cursor, 6),
                "playback_rate": rate,
                "time_remap": remap,
            },
            "rhythmic_cut_opportunity": bool(
                shot.get("rhythmic_cut_opportunity", True)
            ),
            "beat_lockable_boundary": True,
            "transition_safe_boundary": bool(shot.get("transition_safe_boundary", True)),
            "boundary_lock": "locked" if protected else "flexible",
            "timing_priority": "truth" if protected else "style_then_music",
            "safe_trim_margin_before": round(max(0.0, before_margin), 6),
            "safe_trim_margin_after": round(max(0.0, after_margin), 6),
            "flexible_trim_margin": round(max(0.0, min(before_margin, after_margin)), 6),
        }
        if segment["rep_counter_eligible"]:
            step = comp_duration / len(shown)
            segment["counter_events"] = [
                {
                    "rep_id": rep_id,
                    "display_number": number,
                    "composition_time": round(cursor + step * (event_index + 1), 6),
                }
                for event_index, (rep_id, number) in enumerate(zip(ids, shown))
            ]
        segments.append(segment)
        cursor = segment["composition_end"]
    for i, seg in enumerate(segments):
        seg["transition_out"] = (
            segments[i + 1]["transition_in"]
            if i + 1 < len(segments)
            else {"type": "none", "duration_seconds": 0.0, "model": "cut"}
        )
    result = {
        "schema_version": "1.0",
        "seed": str(seed),
        "style_request": prompt,
        "style_profiles": style["profile_weights"],
        "source_audio": style.get("source_audio", "muted"),
        "fallback_level": fallback,
        "timeline": {
            "duration_seconds": round(cursor, 6),
            "target_duration_seconds": target,
            "fps": int(fps),
            "aspect_ratio": aspect_ratio,
            "segments": segments,
        },
    }
    result["validation"] = validate_timeline(result)
    if not result["validation"]["valid"]:
        raise ValueError(
            "invalid timeline: "
            + ", ".join(x["code"] for x in result["validation"]["errors"])
        )
    result["summary"] = summarize(result)
    result["content_hash"] = hashlib.sha256(
        json.dumps(result["timeline"], sort_keys=True).encode()
    ).hexdigest()
    return result


def validate_timeline(plan: dict[str, Any], tolerance: float = 0.25) -> dict[str, Any]:
    errors, warnings, seen, last = [], [], set(), {}
    segments = plan.get("timeline", {}).get("segments", [])
    for i, s in enumerate(segments):
        sid = s.get("segment_id")
        if not s.get("source_id"):
            errors.append({"code": "missing_source", "segment_id": sid})
        if float(s.get("source_start", 0)) >= float(s.get("source_end", 0)):
            errors.append({"code": "invalid_source_range", "segment_id": sid})
        if float(s.get("playback_rate", 0)) <= 0:
            errors.append({"code": "invalid_playback_rate", "segment_id": sid})
        tr = s.get("transition_in", {})
        if (
            tr.get("type") not in ALLOWED_TRANSITIONS
            or float(tr.get("duration_seconds", 0)) < 0
            or float(tr.get("duration_seconds", 0))
            >= float(s.get("composition_duration", 0))
        ):
            errors.append({"code": "impossible_transition", "segment_id": sid})
        if i and float(tr.get("duration_seconds", 0)) >= float(
            segments[i - 1].get("composition_duration", 0)
        ):
            errors.append({"code": "impossible_transition", "segment_id": sid})
        if float(s.get("composition_start", 0)) < 0 or float(
            s.get("composition_end", 0)
        ) <= float(s.get("composition_start", 0)):
            errors.append({"code": "invalid_composition_range", "segment_id": sid})
        if i:
            prev = segments[i - 1]
            expected = float(prev["composition_end"]) - (
                float(tr["duration_seconds"]) if tr.get("model") == "overlap" else 0
            )
            if abs(float(s["composition_start"]) - expected) > 1e-5:
                errors.append({"code": "transition_timing_mismatch", "segment_id": sid})
        group = str(s.get("continuity_group"))
        replay = s.get("replay_type") == "hook_replay"
        if group in last and float(s["source_start"]) < last[group] and not replay:
            errors.append({"code": "reverse_chronology", "segment_id": sid})
        if not replay:
            last[group] = float(s["source_end"])
        for rep in s.get("rep_ids", []):
            if replay and s.get("rep_counter_eligible"):
                errors.append(
                    {"code": "hook_replay_counter_enabled", "segment_id": sid}
                )
            elif not replay and rep in seen:
                errors.append({"code": "duplicate_primary_rep", "segment_id": sid})
            elif not replay:
                seen.add(rep)
        if s.get("rep_counter_eligible") and not s.get("display_rep_numbers"):
            errors.append(
                {"code": "counter_event_outside_visible_segment", "segment_id": sid}
            )
        for event in s.get("counter_events", []):
            if (
                not float(s["composition_start"])
                <= float(event.get("composition_time", -1))
                <= float(s["composition_end"])
            ):
                errors.append(
                    {"code": "counter_event_outside_visible_segment", "segment_id": sid}
                )
        remap = s.get("time_remap")
        if remap:
            points = remap.get("keyframes", [])
            if len(points) < 2 or any(
                not 0 <= float(p.get("position", -1)) <= 1
                or float(p.get("rate", 0)) <= 0
                for p in points
            ):
                errors.append({"code": "incompatible_time_remap", "segment_id": sid})
    actual = float(plan.get("timeline", {}).get("duration_seconds", 0))
    if segments and abs(actual - float(segments[-1]["composition_end"])) > 1e-5:
        errors.append({"code": "final_duration_mismatch"})
    target = plan.get("timeline", {}).get("target_duration_seconds")
    if target and actual > float(target) * 1.1 + tolerance:
        warnings.append({"code": "target_exceeded_to_preserve_required_content"})
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def to_remotion_props(plan: dict[str, Any]) -> dict[str, Any]:
    """Pure adapter: no ranking, selection, chronology or style decisions."""
    timeline = plan["timeline"]
    fps = int(timeline["fps"])
    soundtrack = plan.get("soundtrack")
    return {
        "fps": fps,
        "durationInFrames": math.ceil(timeline["duration_seconds"] * fps),
        "aspectRatio": timeline["aspect_ratio"],
        "sourceAudioMuted": plan.get("source_audio", "muted") == "muted",
        "soundtrack": None if not soundtrack else {
            "src": soundtrack.get("src"),
            "from": round(float(soundtrack.get("offset_seconds", 0)) * fps),
            "trimStartFrame": round(float(soundtrack.get("trim_start_seconds", 0)) * fps),
            "trimEndFrame": round(float(soundtrack.get("trim_end_seconds", 0)) * fps),
            "volume": soundtrack.get("volume", 1),
            "fadeInFrames": round(float(soundtrack.get("fade_in_seconds", 0)) * fps),
            "fadeOutFrames": round(float(soundtrack.get("fade_out_seconds", 0)) * fps),
            "loop": bool(soundtrack.get("loop", False)),
            "shortfallPolicy": soundtrack.get("shortfall_policy", "leave_silence"),
        },
        "clips": [
            {
                "id": s["segment_id"],
                "src": s["source_path"],
                "sourceStartFrame": round(s["source_start"] * fps),
                "sourceEndFrame": round(s["source_end"] * fps),
                "from": round(s["composition_start"] * fps),
                "durationInFrames": max(1, round(s["composition_duration"] * fps)),
                "playbackRate": s["playback_rate"],
                "timeRemap": s["time_remap"],
                "transitionIn": s["transition_in"],
                "overlays": {
                    "safeRegions": s["overlay_regions"],
                    "repCounter": {
                        "enabled": s["rep_counter_eligible"],
                        "repIds": s["rep_ids"],
                        "displayNumbers": s["display_rep_numbers"],
                    },
                },
            }
            for s in timeline["segments"]
        ],
    }


def summarize(plan: dict[str, Any]) -> dict[str, Any]:
    segments = plan["timeline"]["segments"]
    roles, transitions = (
        Counter(s["shot_role"] for s in segments),
        Counter(s["transition_in"]["type"] for s in segments[1:]),
    )
    return {
        "final_duration_seconds": plan["timeline"]["duration_seconds"],
        "segments": len(segments),
        "movements": len({s["exercise_id"] for s in segments if s["exercise_id"]}),
        "hooks": roles["hook_replay"],
        "setup_breathers": sum(roles[x] for x in BREATHERS),
        "complete_rep_anchors": roles["complete_rep_anchor"] + roles["primary"],
        "micro_detail_shots": sum(roles[x] for x in MICRO),
        "transitions": dict(sorted(transitions.items())),
        "slow_motion_segments": [s["segment_id"] for s in segments if s["time_remap"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prompt", default="")
    parser.add_argument("--target-duration", type=float)
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--seed", default="0")
    args = parser.parse_args()
    plan = compile_timeline(
        json.loads(args.input.read_text()),
        prompt=args.prompt,
        target_duration=args.target_duration,
        aspect_ratio=args.aspect_ratio,
        fps=args.fps,
        seed=args.seed,
    )
    payload = json.dumps(plan, indent=2, sort_keys=True) + "\n"
    args.output.write_text(payload) if args.output else print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
