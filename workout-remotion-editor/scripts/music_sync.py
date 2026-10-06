#!/usr/bin/env python3
"""Safely align flexible Phase 12 boundaries to normalized music evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from soundtrack_analysis import validate_analysis
from timeline_composer import validate_timeline


MODES = {"off": 0.0, "subtle": 0.10, "moderate": 0.18, "strong": 0.28}
STYLE_FACTORS = {
    "viral_shortform": 1.0,
    "fast_fitness_montage": 1.0,
    "cinematic_trailer": 0.65,
    "smooth_sweeping": 0.35,
    "gritty_aggressive": 1.0,
    "clean_coaching": 0.25,
    "raw_documentary": 0.2,
    "hybrid": 0.7,
}


def resolve_music_intent(prompt: str, explicit: str | None = None) -> dict[str, Any]:
    text = prompt.lower()
    if explicit in MODES:
        mode = explicit
    elif any(
        x in text
        for x in (
            "ignore the beat",
            "no music sync",
            "don't sync this to music",
            "do not sync this to music",
            "do not sync to the beat",
            "ignore the song structure",
            "keep the current edit",
        )
    ):
        mode = "off"
    elif any(
        x in text
        for x in (
            "don't sync every",
            "do not sync every",
            "don't follow every",
            "do not follow every",
        )
    ):
        mode = "subtle"
    elif any(
        x in text
        for x in (
            "cut it to the beat",
            "cut this to the beat",
            "hit harder",
            "with the beat",
            "the beat",
            "on the drop",
            "follow the beat",
            "downbeat",
            "first beat of each measure",
            "first beat of the measure",
            "first beat of each bar",
            "big musical hits",
            "use the big hits",
            "follow the measures",
        )
    ):
        mode = "strong"
    elif any(x in text for x in ("loosely", "loose", "cinematic")):
        mode = "subtle"
    elif any(
        x in text
        for x in (
            "with the music",
            "musical",
            "soundtrack",
            "to this song",
            "song sections",
            "song changes",
            "build with the music",
            "music picks up",
            "fit this song",
            "fit the song",
            "work with the music",
            "fit the song naturally",
            "use the song structure more",
        )
    ):
        mode = "moderate"
    else:
        mode = "off"
    return {
        "mode": mode,
        "transitions_only": "mostly" in text
        and ("transition" in text or "between exercises" in text),
        "avoid_every_cut": "every cut" in text or "every beat" in text,
        "final_rep_on_accent": ("final rep" in text or "last rep" in text)
        and any(x in text for x in ("drop", "hit", "music")),
        "ending_on_music": "ending" in text
        and any(x in text for x in ("music", "drop", "land")),
        "section_aware": any(
            x in text
            for x in (
                "song sections",
                "song changes",
                "build with",
                "music picks up",
                "high-energy",
                "fast part",
                "work with the music",
                "fit this song",
                "use the song structure more",
                "fit the song naturally",
            )
        ),
        "downbeats_only": any(
            x in text
            for x in (
                "downbeat",
                "big musical hits",
                "first beat of each measure",
                "first beat of the measure",
                "first beat of each bar",
                "strongest hits",
                "big hits",
            )
        ) and not any(x in text for x in ("don't use the downbeat", "do not use the downbeat", "ignore the downbeat", "ignore the meter")),
        "bar_aware": any(
            x in text
            for x in (
                "new bar",
                "two bars",
                "song phrasing",
                "next phrase",
                "few beats",
                "first beat of each measure",
                "first beat of the measure",
                "first beat of each bar",
                "four-beat pattern",
                "4-beat pattern",
                "use the bars",
                "follow the measures",
                "next bar",
            )
        ) and not any(x in text for x in ("ignore the bar", "ignore the meter", "don't worry about the downbeat")),
    }


def _style_factor(plan: dict[str, Any]) -> float:
    profiles = plan.get("style_profiles", {})
    if len(profiles) > 1:
        return STYLE_FACTORS["hybrid"]
    dominant = max(profiles, key=profiles.get) if profiles else "clean_coaching"
    return STYLE_FACTORS.get(dominant, 0.55)


def _locked(segment: dict[str, Any]) -> bool:
    return bool(
        segment.get("boundary_lock") == "locked"
        or segment.get("rep_ids")
        or segment.get("rep_counter_eligible")
        or segment.get("replay_type") == "hook_replay"
        or segment.get("user_required")
        or segment.get("identity_critical")
    )


def _reflow(plan: dict[str, Any]) -> None:
    segments, cursor = plan["timeline"]["segments"], 0.0
    for index, segment in enumerate(segments):
        transition = segment["transition_in"]
        if index and transition.get("model") == "overlap":
            cursor -= float(transition["duration_seconds"])
        old_start, old_end = (
            float(segment["composition_start"]),
            float(segment["composition_end"]),
        )
        duration = float(segment["composition_duration"])
        segment["composition_start"] = round(cursor, 6)
        segment["composition_end"] = round(cursor + duration, 6)
        segment["source_to_composition"]["composition_origin"] = segment[
            "composition_start"
        ]
        for event in segment.get("counter_events", []):
            progress = (float(event["composition_time"]) - old_start) / max(
                old_end - old_start, 1e-9
            )
            event["composition_time"] = round(
                cursor + min(1, max(0, progress)) * duration, 6
            )
        cursor = segment["composition_end"]
    plan["timeline"]["duration_seconds"] = round(cursor, 6)


def sync_timeline(
    plan: dict[str, Any],
    analysis: dict[str, Any] | None,
    *,
    soundtrack: dict[str, Any] | None = None,
    prompt: str = "",
    mode: str | None = None,
) -> dict[str, Any]:
    """Return a copy; unavailable/no soundtrack and mode=off are visual no-ops."""
    result = copy.deepcopy(plan)
    intent = resolve_music_intent(prompt, mode)
    report = {
        "mode": intent["mode"],
        "adjustments": [],
        "boundaries_adjusted": 0,
        "locked_boundaries_preserved": 0,
        "largest_boundary_shift": 0.0,
        "hero_rep_aligned": None,
        "analysis_quality": (analysis or {}).get("analysis_quality", "unknown"),
        "effective_mode": intent["mode"],
        "selected_rhythm_provider": (analysis or {}).get("provider"),
        "provider_selection_reason": "normalized_capabilities_and_quality",
        "capabilities_used": [],
        "fallback_path": (analysis or {}).get("diagnostics", []),
    }
    if soundtrack is None or analysis is None:
        result["soundtrack"] = None
        result["music_sync"] = {
            **report,
            "status": "skipped",
            "reason": "no_soundtrack",
        }
        return result
    status = analysis.get("status")
    if validate_analysis(analysis) or status not in {"success", "partial"}:
        result["soundtrack"] = _audio_contract(soundtrack, analysis, result)
        result["music_sync"] = {
            **report,
            "status": "unavailable",
            "reason": f"analysis_{status}",
        }
        return result
    result["soundtrack"] = _audio_contract(soundtrack, analysis, result)
    if intent["mode"] == "off":
        result["music_sync"] = {**report, "status": "skipped", "reason": "sync_off"}
        return result
    offset = float(result["soundtrack"]["offset_seconds"])
    quality = analysis.get("analysis_quality")
    beat_support = analysis.get("beat_confidence")
    # Old Phase 13 documents have no quality field and retain their behavior.
    if quality in {"low", "insufficient"} or (
        beat_support is not None and float(beat_support) < 0.4
    ):
        report["effective_mode"] = "subtle" if quality == "low" else "off"
        report["adjustments"].append({"reason": "beat_confidence_too_low"})
        if report["effective_mode"] == "off":
            result["music_sync"] = {
                **report,
                "status": "skipped",
                "reason": "insufficient_analysis_quality",
            }
            return result
    events = sorted(
        [
            (float(x["start"]) + offset, 1.0, "section")
            for x in analysis.get("sections", [])[1:]
        ]
        + [
            (
                float(x["timestamp"]) + offset,
                float(x.get("support", x.get("strength", x.get("confidence", 1)))),
                "downbeat",
            )
            for x in analysis.get("downbeats", [])
        ]
        + [
            (float(x["timestamp"]) + offset, float(x.get("strength", 0)), "accent")
            for x in analysis.get("accent_events", [])
        ]
        + [
            (float(x["timestamp"]) + offset, float(x.get("strength", 0)), "beat")
            for x in analysis.get("beats", [])
        ]
    )
    downbeat_usable = "downbeats" in analysis.get(
        "provider_capabilities", []
    ) and quality in {"high", "moderate"}
    if not downbeat_usable:
        events = [event for event in events if event[2] != "downbeat"]
    elif analysis.get("downbeats"):
        report["capabilities_used"].append("downbeats")
    if intent["bar_aware"] and "bar_positions" in analysis.get(
        "provider_capabilities", []
    ):
        report["capabilities_used"].append("bar_positions")
    if intent["downbeats_only"]:
        preferred = [x for x in events if x[2] in {"downbeat", "section", "accent"}]
        events = preferred
    segments = result["timeline"]["segments"]
    max_shift = MODES[report["effective_mode"]] * _style_factor(result)
    eligible_seen = 0
    # Each accepted move translates later clips; density cap deliberately prevents every-cut sync.
    for index in range(len(segments) - 1):
        left, right = segments[index], segments[index + 1]
        if _locked(left) or _locked(right):
            report["locked_boundaries_preserved"] += 1
            report["adjustments"].append(
                {
                    "segment_id": left["segment_id"],
                    "reason": "preserved_locked_rep_boundary",
                }
            )
            continue
        if intent["transitions_only"] and (
            left.get("exercise_id") == right.get("exercise_id")
        ):
            continue
        if not left.get("beat_lockable_boundary", True) or not left.get(
            "transition_safe_boundary", True
        ):
            continue
        eligible_seen += 1
        cadence = (
            3
            if intent["avoid_every_cut"] or report["effective_mode"] == "subtle"
            else 2
        )
        if eligible_seen % cadence:
            continue
        boundary = float(right["composition_start"])
        before = float(
            left.get("safe_trim_margin_before", left.get("flexible_trim_margin", 0))
        )
        after = float(
            left.get("safe_trim_margin_after", left.get("flexible_trim_margin", 0))
        )
        allowed = min(max_shift, max(before, after))
        nearby = [
            (abs(t - boundary), t, strength, kind)
            for t, strength, kind in events
            if -before <= t - boundary <= after and abs(t - boundary) <= allowed
        ]
        if not nearby:
            report["adjustments"].append(
                {"segment_id": left["segment_id"], "reason": "beat_outside_safe_margin"}
            )
            continue
        priority = {"section": 4, "downbeat": 3, "accent": 2, "beat": 1}
        distance, target, strength, kind = min(
            nearby, key=lambda x: (-priority.get(x[3], 0), x[0], -x[2], x[1])
        )
        shift = target - boundary
        if abs(shift) < 1e-6:
            continue
        left["composition_duration"] = round(
            float(left["composition_duration"]) + shift, 6
        )
        # Rate changes only optional footage and remains renderer-neutral.
        left["playback_rate"] = round(
            float(left["source_duration"]) / left["composition_duration"], 6
        )
        left["source_to_composition"]["playback_rate"] = left["playback_rate"]
        reason = {
            "beat": "snapped_to_nearby_beat",
            "accent": "aligned_exercise_transition_to_accent",
            "downbeat": "strong_downbeat_selected",
            "section": "section_boundary_selected",
        }[kind]
        left.setdefault("selection_reasons", []).append(reason)
        report["adjustments"].append(
            {
                "segment_id": left["segment_id"],
                "reason": left["selection_reasons"][-1],
                "shift_seconds": round(shift, 6),
                "music_time": round(target - offset, 6),
            }
        )
        report["boundaries_adjusted"] += 1
        report["largest_boundary_shift"] = max(
            report["largest_boundary_shift"], abs(shift)
        )
        _reflow(result)
    # A final-rep request first shifts soundtrack, never the protected rep.
    if intent["final_rep_on_accent"] and events:
        finals = [
            s
            for s in segments
            if s.get("rep_ids") and s.get("replay_type") != "hook_replay"
        ]
        landmarks = (
            [
                (float(x["start"]), 3, "section")
                for x in analysis.get("sections", [])[1:]
            ]
            + [
                (float(x["timestamp"]), 2, "downbeat")
                for x in analysis.get("downbeats", [])
            ]
            + [
                (float(x["timestamp"]), 1, "accent")
                for x in analysis.get("accent_events", [])
            ]
        )
        if finals and landmarks:
            visual = float(
                finals[-1]
                .get("counter_events", [{}])[-1]
                .get("composition_time", finals[-1]["composition_end"])
            )
            current_offset = float(result["soundtrack"]["offset_seconds"])
            safe = [
                x for x in landmarks if abs((x[0] + current_offset) - visual) <= 1.0
            ]
            candidate, _, landmark_kind = min(
                safe or landmarks,
                key=lambda x: (-x[1], abs((x[0] + current_offset) - visual)),
            )
            desired = visual - candidate
            if abs(desired - current_offset) <= 1.0 and desired >= 0:
                result["soundtrack"]["offset_seconds"] = round(desired, 6)
                report["hero_rep_aligned"] = {
                    "segment_id": finals[-1]["segment_id"],
                    "accent_time": candidate,
                    "landmark_kind": landmark_kind,
                    "reason": "aligned_hero_rep_to_section_peak",
                }
                report["adjustments"].append(report["hero_rep_aligned"])
    result["music_sync"] = {**report, "status": "success"}
    result["validation"] = validate_music_sync(result, analysis)
    if not result["validation"]["valid"]:
        raise ValueError(
            "invalid music sync: " + ",".join(result["validation"]["errors"])
        )
    result["content_hash"] = hashlib.sha256(
        json.dumps(
            {"timeline": result["timeline"], "soundtrack": result["soundtrack"]},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return result


def _audio_contract(
    soundtrack: dict[str, Any], analysis: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
    duration, final = (
        float(analysis.get("duration", 0)),
        float(plan["timeline"]["duration_seconds"]),
    )
    user_trim = soundtrack.get("user_trim") or {}
    trim_start = max(0.0, float(user_trim.get("start", 0)))
    trim_end = min(duration, float(user_trim.get("end", duration)), trim_start + final)
    return {
        "id": soundtrack.get("soundtrack_id"),
        "src": soundtrack.get("path"),
        "sha256": soundtrack.get("sha256"),
        "rights_note": soundtrack.get("rights_note"),
        "analysis_provider": analysis.get("provider"),
        "offset_seconds": max(0.0, float(soundtrack.get("desired_start", 0))),
        "trim_start_seconds": trim_start,
        "trim_end_seconds": trim_end,
        "shortfall_policy": "loop" if soundtrack.get("loop") else "leave_silence",
        "loop": bool(soundtrack.get("loop", False)),
        "volume": min(1.0, max(0.0, float(soundtrack.get("volume", 1)))),
        "fade_in_seconds": max(0.0, float(soundtrack.get("fade_in", 0))),
        "fade_out_seconds": max(0.0, float(soundtrack.get("fade_out", 0))),
    }


def validate_music_sync(
    plan: dict[str, Any], analysis: dict[str, Any]
) -> dict[str, Any]:
    errors = [x["code"] for x in validate_timeline(plan)["errors"]]
    audio = plan.get("soundtrack") or {}
    duration = float(analysis.get("duration", 0))
    if float(audio.get("offset_seconds", -1)) < 0:
        errors.append("invalid_soundtrack_offset")
    start, end = (
        float(audio.get("trim_start_seconds", -1)),
        float(audio.get("trim_end_seconds", -1)),
    )
    if not 0 <= start <= end <= duration:
        errors.append("invalid_audio_trim")
    for s in plan["timeline"]["segments"]:
        if _locked(s) and "snapped_to_nearby_beat" in s.get("selection_reasons", []):
            errors.append("locked_boundary_moved")
        if float(s["composition_duration"]) <= 0:
            errors.append("invalid_adjusted_duration")
    by_id = {s["segment_id"]: s for s in plan["timeline"]["segments"]}
    for change in plan.get("music_sync", {}).get("adjustments", []):
        if "shift_seconds" not in change or change.get("segment_id") not in by_id:
            continue
        segment = by_id[change["segment_id"]]
        shift = float(change["shift_seconds"])
        limit = float(
            segment["safe_trim_margin_after"]
            if shift >= 0
            else segment["safe_trim_margin_before"]
        )
        if abs(shift) > limit + 1e-6:
            errors.append("adjustment_outside_safe_margin")
    return {"valid": not errors, "errors": sorted(set(errors))}


def music_summary(plan: dict[str, Any], analysis: dict[str, Any]) -> str:
    sync, soundtrack = plan.get("music_sync", {}), plan.get("soundtrack") or {}
    return "\n".join(
        [
            f"Soundtrack: {analysis.get('duration', 0):.1f} sec",
            f"Estimated BPM: {analysis.get('estimated_bpm') or 'unavailable'}",
            f"Detected beats: {len(analysis.get('beats', []))}",
            f"Strong accents: {len(analysis.get('accent_events', []))}",
            f"Sync mode: {sync.get('mode', 'off')}",
            f"Timeline boundaries adjusted: {sync.get('boundaries_adjusted', 0)}",
            f"Locked boundaries preserved: {sync.get('locked_boundaries_preserved', 0)}",
            f"Largest boundary shift: {sync.get('largest_boundary_shift', 0):.3f} sec",
            f"Soundtrack offset: {soundtrack.get('offset_seconds', 0):+.2f} sec",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--soundtrack", type=Path, required=True)
    parser.add_argument("--prompt", default="")
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = sync_timeline(
        json.loads(args.timeline.read_text()),
        json.loads(args.analysis.read_text()),
        soundtrack=json.loads(args.soundtrack.read_text()),
        prompt=args.prompt,
        mode=args.mode,
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.write_text(payload) if args.output else print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
