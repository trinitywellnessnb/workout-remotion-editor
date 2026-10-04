#!/usr/bin/env python3
"""Deterministic rep-aware paper-edit planning.

Only reviewed editorial repetitions (or explicitly trusted user repetitions) are
eligible.  Machine ``rep_candidates`` are intentionally never read here.
The returned JSON is an inspectable Director contract; rendering stays in
Remotion and counter events stay in :mod:`rep_counter_timeline`.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


REASONS = {
    "first_rep", "early_context", "last_rep", "final_effort", "requested_rep",
    "all_reps_short_set", "representative_middle", "hook", "continuity_padding",
}


def _reviewed(repetition: dict[str, Any]) -> bool:
    return (
        repetition.get("review_decision") in {"accept", "adjust"}
        and bool(repetition.get("complete", True))
    ) or repetition.get("trust") == "user_supplied"


def _scope_key(rep: dict[str, Any]) -> tuple[str, str, str, str]:
    """Use confirmed sets only; never fabricate a set from temporal gaps."""
    return (
        str(rep["source_id"]),
        str(rep.get("exercise_id") or rep.get("segment_id") or "exercise"),
        str(rep.get("set_id") if rep.get("set_confirmed") else ""),
        str(rep.get("side") or ""),
    )


def _indices(count: int, config: dict[str, Any]) -> list[int]:
    override = config.get("selection", "default")
    amount = config.get("reps_per_scope")
    if override in {"all", "whole_set", "no_cuts"}:
        return list(range(count))
    if override == "last":
        return list(range(max(0, count - int(amount or 3)), count))
    if override == "first_last":
        return sorted({0, count - 1}) if count else []
    if amount is not None:
        amount = max(0, min(count, int(amount)))
        first = (amount + 1) // 2
        return list(range(first)) + list(range(count - (amount - first), count))
    if count < 5:
        return list(range(count))
    if count == 10:
        return [0, 1, 2, 7, 8, 9]
    mode = config.get("mode", "standard")
    level = config.get("scope", "movement")
    if count > 12 and mode not in {"long", "extended"}:
        return [0, 1, 2, count - 4, count - 3, count - 2, count - 1]
    fraction = 0.60 if level == "set" and mode in {"long", "extended"} else 0.40
    if mode == "quick":
        fraction = 0.30
    target = max(2, min(count, round(count * fraction)))
    first = (target + 1) // 2
    return list(range(first)) + list(range(count - (target - first), count))


def _reason(position: int, count: int, config: dict[str, Any]) -> str:
    if config.get("selection") in {"all", "whole_set", "no_cuts"}:
        return "requested_rep"
    if count < 5:
        return "all_reps_short_set"
    if position == 0:
        return "first_rep"
    if position < 3:
        return "early_context"
    if position == count - 1:
        return "last_rep"
    if position >= count - 3:
        return "final_effort"
    return "representative_middle"


def _selection(rep: dict[str, Any], position: int, count: int, config: dict[str, Any]) -> dict[str, Any]:
    start, end = float(rep["start"]), float(rep["end"])
    pre = min(0.40, max(0.0, float(config.get("pre_roll", 0.25))))
    post = min(0.40, max(0.0, float(config.get("post_roll", 0.25))))
    low = float(rep.get("segment_start", 0))
    high = float(rep.get("segment_end", end + post))
    return {
        "source_id": rep["source_id"],
        "source_group_id": rep.get("source_group_id", rep["source_id"]),
        "exercise_id": rep.get("exercise_id") or rep.get("segment_id"),
        "segment_id": rep.get("segment_id"),
        "set_id": rep.get("set_id") if rep.get("set_confirmed") else None,
        "editorial_repetition_id": rep["id"],
        "source_rep_index": rep.get("source_rep_number", position + 1),
        "side": rep.get("side"),
        "source_start": start,
        "source_end": end,
        "selected_source_start": max(low, start - pre),
        "selected_source_end": min(high, end + post),
        "reason": _reason(position, count, config),
        "complete_rep": True,
        "source_sequence_index": position + 1,
        "display_sequence_index": None,
        "occurrence": "primary",
        "transition_padding": {"pre": pre, "post": post},
        "counter_eligible": True,
    }


def _merge(selections: list[dict[str, Any]], gap: float) -> list[dict[str, Any]]:
    clips: list[dict[str, Any]] = []
    for item in selections:
        previous = clips[-1] if clips else None
        consecutive = previous and item["source_sequence_index"] == previous["source_sequence_end"] + 1
        same = previous and all(item[k] == previous[k] for k in ("source_id", "source_group_id", "exercise_id", "set_id", "side"))
        close = previous and item["selected_source_start"] - previous["source_end"] <= gap
        if same and consecutive and close:
            previous["source_end"] = max(previous["source_end"], item["selected_source_end"])
            previous["source_sequence_end"] = item["source_sequence_index"]
            previous["editorial_repetition_ids"].append(item["editorial_repetition_id"])
            previous["selection_reasons"].append(item["reason"])
        else:
            clips.append({
                "id": f"primary-{item['editorial_repetition_id']}",
                "source_id": item["source_id"], "source_group_id": item["source_group_id"],
                "exercise_id": item["exercise_id"], "set_id": item["set_id"], "side": item["side"],
                "source_start": item["selected_source_start"], "source_end": item["selected_source_end"],
                "source_sequence_start": item["source_sequence_index"],
                "source_sequence_end": item["source_sequence_index"],
                "editorial_repetition_ids": [item["editorial_repetition_id"]],
                "selection_reasons": [item["reason"]], "role": "primary", "playback_rate": 1.0,
                "transition": "cut" if clips else "none",
            })
    return clips


def validate_edit_plan(plan: dict[str, Any]) -> None:
    seen_primary: set[str] = set()
    last: dict[str, float] = {}
    selected = {x["editorial_repetition_id"] for x in plan.get("selected_repetitions", [])}
    for clip in plan.get("clips", []):
        start, end, rate = float(clip["source_start"]), float(clip["source_end"]), float(clip["playback_rate"])
        if start < 0 or end <= start or rate <= 0:
            raise ValueError("invalid source range or playback rate")
        if clip.get("role") == "primary":
            group = str(clip["source_group_id"])
            if group in last and start < last[group]:
                raise ValueError("reverse chronology within source group")
            last[group] = end
            for rep_id in clip.get("editorial_repetition_ids", []):
                if rep_id not in selected:
                    raise ValueError("clip references an unselected repetition")
                if rep_id in seen_primary:
                    raise ValueError("duplicate primary repetition")
                seen_primary.add(rep_id)
        elif clip.get("role") == "hook_replay":
            ids = clip.get("editorial_repetition_ids", [])
            if len(ids) != 1 or ids[0] not in selected:
                raise ValueError("hook replay must retain a selected repetition identity")
    if any(c.get("role") == "primary" and c.get("playback_rate") != 1.0 for c in plan.get("clips", [])):
        raise ValueError("active primary repetitions cannot be sped up by default")


def build_rep_aware_plan(analysis: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = dict(config or {})
    repetitions = list(analysis.get("repetitions") or [])
    # Presence in this explicitly named configuration field is itself the user
    # trust decision; do not require callers to redundantly annotate each row.
    repetitions.extend(dict(r, trust="user_supplied") for r in config.get("trusted_repetitions", []))
    reviewed = [dict(r) for r in repetitions if _reviewed(r)]
    if not reviewed:
        return {"rep_aware": False, "fallback": "legacy_scene_activity_manual", "clips": config.get("legacy_clips", []),
                "selected_repetitions": [], "omitted_repetitions": [], "expected_duration": 0.0}
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for rep in reviewed:
        groups[_scope_key(rep)].append(rep)
    selected: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    for key, reps in groups.items():
        reps.sort(key=lambda r: (float(r["start"]), float(r["end"]), str(r["id"])))
        keep = set(_indices(len(reps), config))
        for pos, rep in enumerate(reps):
            if pos in keep:
                selected.append(_selection(rep, pos, len(reps), config))
            else:
                omitted.append({"editorial_repetition_id": rep["id"], "source_id": rep["source_id"],
                                "exercise_id": key[1], "source_rep_index": rep.get("source_rep_number", pos + 1),
                                "reason": "user_request" if config.get("selection") else "middle_rep_reduction"})
    selected.sort(key=lambda x: (x["source_group_id"], x["source_start"], x["editorial_repetition_id"]))
    target = config.get("target_duration")
    if target is not None:
        target = max(0.0, float(target))
        # Preserve whole reps: remove redundant middle selections before ever
        # shortening a selected movement cycle.
        while sum(x["selected_source_end"] - x["selected_source_start"] for x in selected) > target:
            optional = next((x for x in selected if x["reason"] == "representative_middle"), None)
            if optional is None:
                break
            selected.remove(optional)
            omitted.append({"editorial_repetition_id": optional["editorial_repetition_id"],
                            "source_id": optional["source_id"], "exercise_id": optional["exercise_id"],
                            "source_rep_index": optional["source_rep_index"], "reason": "duration_limit"})
    display_counts: dict[tuple[str, str], int] = defaultdict(int)
    for item in selected:
        stream = (str(item["exercise_id"]), str(item.get("side") or ""))
        display_counts[stream] += 1
        item["display_sequence_index"] = display_counts[stream]
    clips = _merge(selected, float(config.get("merge_gap", 0.5)))
    if config.get("hook") and selected:
        late = selected[-3:]
        hook = max(late, key=lambda x: (x["source_end"] - x["source_start"], x["source_sequence_index"]))
        clips.insert(0, {
            "id": f"hook-{hook['editorial_repetition_id']}", "source_id": hook["source_id"],
            "source_group_id": hook["source_group_id"], "exercise_id": hook["exercise_id"],
            "set_id": hook["set_id"], "side": hook["side"], "source_start": hook["selected_source_start"],
            "source_end": hook["selected_source_end"], "editorial_repetition_ids": [hook["editorial_repetition_id"]],
            "selection_reasons": ["hook", "late_set_hook_candidate"], "role": "hook_replay",
            "playback_rate": 1.0, "counter_eligible": False, "transition": "cut",
        })
    transition = max(0.0, float(config.get("transition_duration", 0.0)))
    timeline = 0.0
    for clip in clips:
        clip["timeline_start"] = timeline
        clip["duration"] = (clip["source_end"] - clip["source_start"]) / clip["playback_rate"]
        timeline += clip["duration"]
        if clip is not clips[-1]:
            timeline = max(0.0, timeline - transition)
    rest_decisions = []
    for rest in config.get("rest_intervals", []):
        duration = float(rest["end"]) - float(rest["start"])
        if duration <= float(config.get("short_rest_threshold", 2.0)):
            rest_decisions.append({**rest, "action": "skip", "reason": "short_rest"})
        elif config.get("fast_forward_rest"):
            rest_decisions.append({**rest, "action": "fast_forward", "playback_rate": float(config.get("rest_playback_rate", 4.0)),
                                   "reason": "compressed_rest"})
        else:
            keep = min(duration, max(1.0, min(2.0, float(config.get("long_rest_context", 1.5)))))
            rest_decisions.append({**rest, "action": "trim", "selected_start": float(rest["end"]) - keep,
                                   "selected_end": float(rest["end"]), "reason": "long_rest_orientation"})
    plan = {"rep_aware": True, "policy": {"mode": config.get("mode", "standard"), "scope": config.get("scope", "movement")},
            "selected_repetitions": selected, "omitted_repetitions": omitted, "clips": clips,
            "expected_duration": timeline, "transition_duration": transition,
            "rest_decisions": rest_decisions,
            "rep_counter": {"enabled": bool(config.get("rep_counter", False)), "replay_behavior": "suppress"}}
    validate_edit_plan(plan)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_rep_aware_plan(json.loads(args.analysis.read_text()), json.loads(args.config.read_text()) if args.config else {})
    output = json.dumps(result, indent=2) + "\n"
    args.output.write_text(output) if args.output else print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
