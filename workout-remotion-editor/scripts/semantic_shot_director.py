#!/usr/bin/env python3
"""Evidence-backed semantic shot selection for workout edits.

The director consumes already-derived evidence. Scores are deterministic ranking
supports, not calibrated probabilities; unknown is a first-class result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

ROLES = (
    "primary_movement",
    "complete_rep_anchor",
    "partial_movement_detail",
    "hook_candidate",
    "hero_shot",
    "setup",
    "equipment_adjustment",
    "equipment_loading",
    "equipment_pickup",
    "approach_station",
    "walk_between_movements",
    "stance_setup",
    "grip_setup",
    "transition_breather",
    "environment_context",
    "recovery",
    "rest",
    "close_detail",
    "exercise_transition",
    "ending_candidate",
    "replay",
    "dead_time",
    "unusable",
    "unknown",
)

STYLE_ROLE_WEIGHTS = {
    "viral_shortform": {
        "hook_candidate": 1.0,
        "primary_movement": 0.95,
        "partial_movement_detail": 0.76,
        "close_detail": 0.7,
        "equipment_pickup": 0.55,
        "transition_breather": 0.35,
        "ending_candidate": 0.8,
    },
    "fast_fitness_montage": {
        "primary_movement": 1,
        "complete_rep_anchor": 0.82,
        "hook_candidate": 0.9,
        "close_detail": 0.55,
        "setup": 0.32,
        "ending_candidate": 0.7,
    },
    "cinematic_trailer": {
        "environment_context": 0.76,
        "setup": 0.62,
        "close_detail": 0.85,
        "complete_rep_anchor": 0.9,
        "walk_between_movements": 0.65,
        "hero_shot": 1,
        "ending_candidate": 0.9,
    },
    "epic_dramatic": {
        "complete_rep_anchor": 0.95,
        "hero_shot": 1,
        "primary_movement": 0.8,
        "transition_breather": 0.55,
        "ending_candidate": 0.95,
    },
    "smooth_sweeping": {
        "complete_rep_anchor": 1,
        "walk_between_movements": 0.72,
        "setup": 0.58,
        "environment_context": 0.58,
        "hero_shot": 0.82,
    },
    "gritty_aggressive": {
        "close_detail": 0.92,
        "equipment_loading": 0.9,
        "equipment_pickup": 0.82,
        "primary_movement": 1,
        "hook_candidate": 0.95,
    },
    "clean_coaching": {
        "complete_rep_anchor": 1,
        "primary_movement": 0.9,
        "stance_setup": 0.35,
        "grip_setup": 0.35,
        "setup": 0.1,
    },
    "raw_documentary": {
        "approach_station": 0.72,
        "walk_between_movements": 0.75,
        "setup": 0.8,
        "primary_movement": 1,
        "recovery": 0.65,
        "exercise_transition": 0.7,
    },
    "polished_commercial": {
        "hero_shot": 1,
        "close_detail": 0.85,
        "primary_movement": 0.82,
        "equipment_loading": 0.55,
        "ending_candidate": 0.9,
    },
}

GRAMMARS = {
    "viral_shortform": [
        "hook_candidate",
        "primary_movement",
        "close_detail",
        "primary_movement",
        "transition_breather",
        "primary_movement",
        "ending_candidate",
    ],
    "cinematic_trailer": [
        "environment_context",
        "setup",
        "close_detail",
        "complete_rep_anchor",
        "walk_between_movements",
        "primary_movement",
        "hero_shot",
        "ending_candidate",
    ],
    "raw_documentary": [
        "approach_station",
        "setup",
        "primary_movement",
        "recovery",
        "walk_between_movements",
        "setup",
        "primary_movement",
    ],
}

BREATHERS = {
    "setup",
    "equipment_adjustment",
    "walk_between_movements",
    "transition_breather",
    "environment_context",
    "recovery",
    "rest",
    "exercise_transition",
}
MICRO = {
    "partial_movement_detail",
    "close_detail",
    "equipment_pickup",
    "equipment_loading",
}


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def role_overrides(prompt: str) -> dict[str, Any]:
    """Resolve explicit role requests. Explicit suppression always wins."""
    p = prompt.lower()
    force, suppress = set(), set()
    rules = [
        (
            r"only (?:show )?(?:the )?(?:lifts|lifting|workout movements)",
            {"primary_movement", "complete_rep_anchor"},
            BREATHERS | {"close_detail"},
        ),
        (
            r"no (?:clips of me )?walking|don.t show .*walking",
            set(),
            {"walk_between_movements", "approach_station"},
        ),
        (
            r"(?:use|show) (?:more )?(?:machine |equipment )?adjust",
            {"equipment_adjustment"},
            set(),
        ),
        (
            r"(?:show|use) (?:me )?loading (?:the )?(?:plates|weights)",
            {"equipment_loading"},
            set(),
        ),
        (r"(?:more|use) (?:close[- ]?ups|detail)", {"close_detail"}, set()),
        (
            r"more full[- ]body",
            {"complete_rep_anchor", "primary_movement"},
            {"close_detail"},
        ),
        (r"(?:more setup|show more setup)", {"setup"}, set()),
        (r"(?:no|don.t show) rest", set(), {"rest", "recovery"}),
        (r"nonstop", set(), BREATHERS),
        (
            r"actual workout|real workout|not an ad",
            {"setup", "primary_movement", "exercise_transition"},
            set(),
        ),
        (
            r"moving around|between exercises",
            {"walk_between_movements", "approach_station"},
            set(),
        ),
        (
            r"like a movie|cinematic",
            {"environment_context", "close_detail", "hero_shot"},
            set(),
        ),
    ]
    for pattern, add, remove in rules:
        if re.search(pattern, p):
            force |= add
            suppress |= remove
    force -= suppress
    return {"force": sorted(force), "suppress": sorted(suppress)}


def classify_roles(e: dict[str, Any]) -> list[dict[str, Any]]:
    """Return supported role candidates without manufacturing certainty."""
    s: dict[str, tuple[float, list[str]]] = {}

    def add(role: str, score: float, *reasons: str) -> None:
        old = s.get(role, (0.0, []))
        s[role] = (_clamp(old[0] + score), old[1] + [r for r in reasons if r])

    labelled = e.get("reviewed_role") or e.get("user_role_label")
    if labelled in ROLES:
        add(labelled, 0.9, "reviewed_or_user_role_label")

    duration = float(
        e.get(
            "duration", float(e.get("source_end", 0)) - float(e.get("source_start", 0))
        )
    )
    motion = float(e.get("motion", 0))
    person = float(e.get("person_visibility", 0))
    activity = float(e.get("activity", motion))
    if e.get("unusable") or float(e.get("severe_blur", 0)) > 0.85:
        add("unusable", 0.95, "explicit_unusable_or_severe_blur")
    if e.get("editorial_rep_ids"):
        add("complete_rep_anchor", 0.82, "reviewed_editorial_rep")
        add("primary_movement", 0.15, "reviewed_editorial_rep")
    if activity > 0.55 and person > 0.45:
        add("primary_movement", 0.42 + 0.25 * activity, "visible_active_subject")
    interaction = e.get("interaction")
    mapping = {
        "adjust": "equipment_adjustment",
        "load": "equipment_loading",
        "pickup": "equipment_pickup",
        "grip": "grip_setup",
        "stance": "stance_setup",
    }
    if interaction in mapping and float(e.get("interaction_support", 0.6)) >= 0.45:
        add(mapping[interaction], 0.62, "localized_person_equipment_interaction")
        add("setup", 0.25, "setup_interaction")
    if e.get("approaching_equipment"):
        add("approach_station", 0.72, "approach_track")
    if e.get("walking") and e.get("between_exercises"):
        add("walk_between_movements", 0.78, "between_exercise_walk")
    if e.get("recovery_label"):
        add("recovery", 0.82, "reviewed_or_user_recovery_label")
    if e.get("rest_label"):
        add("rest", 0.85, "reviewed_or_user_rest_label")
    if not e.get("person_present", person > 0.05) and e.get("scene_context"):
        add("environment_context", 0.7, "context_without_primary_subject")
    if e.get("detail_scale") or float(e.get("subject_scale", 0)) > 0.82:
        add("close_detail", 0.65, "tight_detail_scale")
    if duration >= 0.8 and motion > 0.68 and person > 0.55:
        add("hook_candidate", 0.54 + 0.2 * motion, "immediate_clear_motion")
    if (
        e.get("editorial_rep_ids")
        and float(e.get("framing", 0.5)) > 0.65
        and float(e.get("occlusion", 0)) < 0.25
    ):
        add("hero_shot", 0.72, "complete_motion_strong_framing")
    if e.get("source_final") and (activity > 0.3 or e.get("fade_friendly")):
        add("ending_candidate", 0.7, "source_final_resolve")
    if e.get("replay_of"):
        add("replay", 1, "explicit_replay")
    if (
        duration >= 1
        and activity < 0.08
        and not e.get("scene_context")
        and not e.get("rest_label")
    ):
        add("dead_time", 0.78, "low_activity_without_context")
    ranked = [
        {"role": r, "support_score": v[0], "reasons": sorted(set(v[1]))}
        for r, v in s.items()
        if v[0] >= 0.3
    ]
    ranked.sort(key=lambda x: (-x["support_score"], x["role"]))
    if not ranked or ranked[0]["support_score"] < 0.45:
        ranked.append(
            {
                "role": "unknown",
                "support_score": 0.5,
                "reasons": ["insufficient_semantic_support"],
            }
        )
    return ranked


def quality(e: dict[str, Any]) -> dict[str, Any]:
    """Transparent editorial usability score; values are heuristic ranks."""
    duration = float(e.get("duration", 0))
    crop = float(e.get("crop_viability", 0.5))
    components = {
        "subject_visibility": _clamp(e.get("person_visibility", 0.5)),
        "anatomy_visibility": _clamp(e.get("anatomy_visibility", 0.5)),
        "equipment_visibility": _clamp(e.get("equipment_visibility", 0.5)),
        "crop_viability": _clamp(crop),
        "framing_headroom": _clamp(e.get("framing", 0.5)),
        "track_stability": _clamp(e.get("track_stability", 0.5)),
        "movement_completeness": _clamp(e.get("movement_completeness", 0.5)),
        "camera_stability": _clamp(1 - float(e.get("camera_motion_excess", 0))),
        "duration_usability": _clamp(
            min(duration / 0.7, 1) * min(1, 4 / max(duration, 0.01))
        ),
        "trim_safety": _clamp(e.get("trim_safety", 0.5)),
        "overlay_usability": _clamp(e.get("overlay_usability", 0.5)),
    }
    penalties = {
        "occlusion_penalty": _clamp(e.get("occlusion", 0)),
        "blur_penalty": _clamp(e.get("severe_blur", 0)),
    }
    base = sum(components.values()) / len(components)
    overall = _clamp(
        base - 0.18 * penalties["occlusion_penalty"] - 0.18 * penalties["blur_penalty"]
    )
    concerns = [k.removesuffix("_penalty") for k, v in penalties.items() if v > 0.45]
    if crop < 0.4:
        concerns.append("poor_vertical_crop")
    if components["overlay_usability"] < 0.35:
        concerns.append("limited_overlay_safe_region")
    return {
        **components,
        **penalties,
        "overall_rank_score": overall,
        "quality_concerns": concerns,
    }


def build_candidate(e: dict[str, Any]) -> dict[str, Any]:
    start, end = (
        float(e.get("source_start", 0)),
        float(e.get("source_end", e.get("duration", 0))),
    )
    if end <= start:
        raise ValueError("source_end must be after source_start")
    roles = classify_roles({**e, "duration": end - start})
    q = quality({**e, "duration": end - start})
    selected = next((x["role"] for x in roles if x["support_score"] >= 0.55), "unknown")
    fps = float(e.get("source_fps", 30))
    cid = (
        e.get("candidate_id")
        or "shot-"
        + hashlib.sha1(
            f"{e.get('source_id')}:{start:.3f}:{end:.3f}".encode()
        ).hexdigest()[:10]
    )
    return {
        "candidate_id": cid,
        "source_id": e.get("source_id"),
        "scene_id": e.get("scene_id"),
        "source_interval": {"start": start, "end": end},
        "exercise_id": e.get("exercise_id"),
        "editorial_rep_ids": list(e.get("editorial_rep_ids", [])),
        "entity_id": e.get("entity_id"),
        "role_candidates": roles,
        "selected_role": selected,
        "shot_quality": q,
        "motion_level": _clamp(e.get("motion", 0)),
        "crop_viability": q["crop_viability"],
        "overlay_safe_regions": list(e.get("overlay_safe_regions", [])),
        "duration_limits": {
            "minimum_safe": min(0.7, end - start),
            "maximum_meaningful": end - start,
            "recommended": [min(0.7, end - start), min(2.4, end - start)],
        },
        "time_remap_compatibility": {
            "normal": True,
            "fast": end - start >= 0.35,
            "slow": fps >= 48 and end - start >= 1,
            "speed_ramp": fps >= 48 and end - start >= 1.2,
        },
        "continuity_group": e.get("continuity_group", e.get("source_id")),
        "source_sequence": e.get("source_sequence"),
        "duplication_group": e.get("duplication_group")
        or (
            f"rep:{e['editorial_rep_ids'][0]}"
            if e.get("editorial_rep_ids")
            else f"{e.get('source_id')}:{e.get('scene_id')}"
        ),
        "evidence_references": list(e.get("evidence_references", [])),
        "source_fps": fps,
    }


def compatibility(
    candidate: dict[str, Any], profile_weights: dict[str, float], prompt: str = ""
) -> dict[str, Any]:
    overrides = role_overrides(prompt)
    role = candidate["selected_role"]
    weighted = sum(
        weight * STYLE_ROLE_WEIGHTS.get(profile, {}).get(role, 0.18)
        for profile, weight in profile_weights.items()
    ) / max(sum(profile_weights.values()), 0.001)
    if role in overrides["force"]:
        weighted += 0.35
    if role in overrides["suppress"]:
        weighted = 0
    handheld_tolerance = sum(
        w
        for p, w in profile_weights.items()
        if p in {"gritty_aggressive", "raw_documentary", "viral_shortform"}
    )
    motion_penalty = candidate["shot_quality"]["camera_stability"]
    style_score = _clamp(
        weighted * (0.75 + 0.25 * (handheld_tolerance or motion_penalty))
    )
    return {
        "style_rank_score": style_score,
        "forced": role in overrides["force"],
        "suppressed": role in overrides["suppress"],
    }


def select_shots(
    candidates: list[dict[str, Any]],
    style_contract: dict[str, Any],
    prompt: str = "",
    limit: int = 12,
) -> dict[str, Any]:
    """Select diverse, truthful candidates using a soft visual grammar."""
    profiles = style_contract.get("profile_weights", {"fast_fitness_montage": 1})
    dominant = max(profiles, key=profiles.get)
    grammar = GRAMMARS.get(dominant, GRAMMARS["viral_shortform"])
    overrides = role_overrides(prompt)
    pool = []
    for c0 in candidates:
        c = deepcopy(c0)
        comp = compatibility(c, profiles, prompt)
        c["style_compatibility"] = comp
        c["ranking_score"] = _clamp(
            0.62 * c["shot_quality"]["overall_rank_score"]
            + 0.38 * comp["style_rank_score"]
        )
        if (
            c["selected_role"] not in {"unusable", "dead_time"}
            and not comp["suppressed"]
        ):
            pool.append(c)
    selected, omitted, used_dupes = [], [], set()
    max_micro = 3 if dominant == "viral_shortform" else 2
    micro_run = setup_count = 0
    for desired in grammar + ["primary_movement"] * limit:
        choices = [
            c
            for c in pool
            if c["candidate_id"] not in {x["candidate_id"] for x in selected}
            and (
                c["selected_role"] == desired
                or desired in [r["role"] for r in c["role_candidates"]]
            )
        ]
        choices.sort(
            key=lambda c: (
                -c["ranking_score"],
                c["source_interval"]["start"],
                c["candidate_id"],
            )
        )
        choice = next(
            (c for c in choices if c["duplication_group"] not in used_dupes), None
        )
        if not choice:
            continue
        role = choice["selected_role"]
        if role in MICRO and micro_run >= max_micro:
            continue
        if (
            role in BREATHERS
            and setup_count >= max(1, (len(selected) + 2) // 3)
            and role not in overrides["force"]
        ):
            continue
        choice["selection_reasons"] = sorted(
            set(
                (["style_role_match"] if desired == role else ["supported_role_match"])
                + (["best_vertical_crop"] if choice["crop_viability"] > 0.75 else [])
                + (["complete_rep_anchor"] if choice["editorial_rep_ids"] else [])
            )
        )
        selected.append(choice)
        used_dupes.add(choice["duplication_group"])
        micro_run = micro_run + 1 if role in MICRO else 0
        setup_count += role in BREATHERS
        if len(selected) >= limit:
            break
    # Truth beats grammar: primary chronology is source ordered; only an explicit hook replay can precede it.
    hooks = [c for c in selected if c["selected_role"] == "replay"]
    body = [c for c in selected if c not in hooks]
    # A supplied cross-source sequence represents known capture/workout order.
    # Otherwise keep grammar order across sources while ordering each source
    # below in validation; filename sorting is not chronology evidence.
    if body and all(c.get("source_sequence") is not None for c in body):
        body.sort(key=lambda c: (c["source_sequence"], c["source_interval"]["start"]))
    else:
        positions = {c["candidate_id"]: i for i, c in enumerate(body)}
        body.sort(key=lambda c: positions[c["candidate_id"]])
        for source in {c["source_id"] for c in body}:
            indexes = [i for i, c in enumerate(body) if c["source_id"] == source]
            ordered = sorted(
                (body[i] for i in indexes), key=lambda c: c["source_interval"]["start"]
            )
            for i, c in zip(indexes, ordered):
                body[i] = c
    selected = hooks[:1] + body
    chosen = {c["candidate_id"] for c in selected}
    for c in pool:
        if c["candidate_id"] not in chosen:
            reason = (
                "near_duplicate"
                if c["duplication_group"] in used_dupes
                else "lower_rank_or_grammar_fit"
            )
            omitted.append({"candidate_id": c["candidate_id"], "reason": reason})
    return {
        "style_profile": dominant,
        "role_overrides": overrides,
        "shots": selected,
        "omitted": omitted,
        "validation": validate_sequence(selected),
        "fallback_used": not bool(candidates),
    }


def validate_sequence(shots: list[dict[str, Any]]) -> dict[str, Any]:
    violations = []
    last: dict[str, float] = {}
    for c in shots:
        source, start = c["source_id"], c["source_interval"]["start"]
        replay = c["selected_role"] == "replay" or bool(c.get("replay_of"))
        if source in last and start < last[source] and not replay:
            violations.append(
                {"candidate_id": c["candidate_id"], "code": "reverse_source_chronology"}
            )
        if not replay:
            last[source] = max(start, last.get(source, start))
    sequenced = [
        c.get("source_sequence")
        for c in shots
        if c["selected_role"] != "replay" and c.get("source_sequence") is not None
    ]
    if len(sequenced) > 1 and any(b < a for a, b in zip(sequenced, sequenced[1:])):
        violations.append({"code": "reverse_cross_source_sequence"})
    return {"valid": not violations, "violations": violations}


def role_aware_transition(left: str, right: str, style: str) -> str:
    if (
        left == "environment_context"
        and right == "close_detail"
        and style in {"cinematic_trailer", "smooth_sweeping"}
    ):
        return "cross_dissolve"
    if left in BREATHERS and right in {"primary_movement", "complete_rep_anchor"}:
        return "cut"
    if left in {"primary_movement", "complete_rep_anchor"} and right in {
        "primary_movement",
        "complete_rep_anchor",
    }:
        return "motion_match" if style == "smooth_sweeping" else "cut"
    if left == "hero_shot" and right in {"hero_shot", "ending_candidate"}:
        return "fade" if "cinematic" in style else "cut"
    return "cut"


def direct(
    evidence: list[dict[str, Any]],
    style_contract: dict[str, Any],
    prompt: str = "",
    limit: int = 12,
) -> dict[str, Any]:
    candidates = [build_candidate(e) for e in evidence]
    result = select_shots(candidates, style_contract, prompt, limit)
    result["shot_candidates"] = candidates
    result["schema_version"] = "1.0"
    result["score_semantics"] = "support_and_ranking_scores_not_probabilities"
    result["fallback"] = (
        "phase9_rep_selection_then_scene_activity_chronology"
        if not result["shots"]
        else None
    )
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("evidence", type=Path)
    p.add_argument("style", type=Path)
    p.add_argument("--prompt", default="")
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    result = direct(
        json.loads(a.evidence.read_text()), json.loads(a.style.read_text()), a.prompt
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    a.output.write_text(payload) if a.output else print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
