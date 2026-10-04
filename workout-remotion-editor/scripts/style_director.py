#!/usr/bin/env python3
"""Deterministic natural-language style resolution for workout edit plans.

This module translates an ordinary-language brief into an inspectable style
contract.  It never analyzes pixels and never renders: reviewed editorial
evidence goes in, and a renderer-neutral policy comes out.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


BANDS = {
    "micro": (0.18, 0.35),
    "short": (0.35, 0.70),
    "medium": (0.70, 1.20),
    "anchor": (1.00, 1.80),
    "long": (1.50, 3.00),
    "hero": (1.80, 3.20),
}


def _profile(
    *,
    energy: float,
    pace: float,
    hook: float,
    breathing: float,
    effects: float,
    slow: float,
    setup: float,
    cinematic: float,
    raw: float,
    polish: float,
    rhythm: float,
    bands: dict[str, float],
    curve: list[str],
    transitions: dict[str, float],
    roles: dict[str, float],
    ending: str,
) -> dict[str, Any]:
    return locals()


PROFILES = {
    "viral_shortform": _profile(
        energy=0.9,
        pace=0.92,
        hook=1,
        breathing=0.22,
        effects=0.42,
        slow=0.08,
        setup=0.18,
        cinematic=0.18,
        raw=0.45,
        polish=0.55,
        rhythm=0.9,
        bands={
            "micro": 0.25,
            "short": 0.43,
            "medium": 0.20,
            "anchor": 0.10,
            "hero": 0.02,
        },
        curve=["spike", "rapid", "breath", "rapid", "strong_finish"],
        transitions={"cut": 0.82, "whip": 0.08, "glitch": 0.04, "push_cut": 0.06},
        roles={
            "hook": 0.12,
            "primary_movement": 0.58,
            "complete_rep_anchor": 0.14,
            "setup": 0.08,
            "breather": 0.05,
            "hero": 0.03,
        },
        ending="strong_action",
    ),
    "fast_fitness_montage": _profile(
        energy=0.86,
        pace=0.82,
        hook=0.85,
        breathing=0.28,
        effects=0.3,
        slow=0.1,
        setup=0.2,
        cinematic=0.2,
        raw=0.48,
        polish=0.58,
        rhythm=0.82,
        bands={"short": 0.44, "medium": 0.34, "anchor": 0.18, "hero": 0.04},
        curve=[
            "hook",
            "movement",
            "breath",
            "movement",
            "breath",
            "strongest_final_movement",
        ],
        transitions={"cut": 0.86, "motion_match": 0.09, "whip": 0.05},
        roles={
            "hook": 0.1,
            "primary_movement": 0.58,
            "complete_rep_anchor": 0.2,
            "setup": 0.08,
            "breather": 0.04,
        },
        ending="strong_action",
    ),
    "cinematic_trailer": _profile(
        energy=0.68,
        pace=0.57,
        hook=0.82,
        breathing=0.62,
        effects=0.27,
        slow=0.55,
        setup=0.38,
        cinematic=1,
        raw=0.2,
        polish=0.88,
        rhythm=0.62,
        bands={
            "micro": 0.06,
            "short": 0.18,
            "medium": 0.24,
            "anchor": 0.28,
            "long": 0.16,
            "hero": 0.08,
        },
        curve=["tease", "build", "pause", "escalation", "rapid_climax", "hero_ending"],
        transitions={
            "cut": 0.72,
            "motion_match": 0.12,
            "fade": 0.08,
            "dip_black": 0.08,
        },
        roles={
            "hook": 0.08,
            "environment": 0.1,
            "close_detail": 0.12,
            "primary_movement": 0.38,
            "complete_rep_anchor": 0.18,
            "setup": 0.06,
            "hero": 0.08,
        },
        ending="hero_fade",
    ),
    "epic_dramatic": _profile(
        energy=0.72,
        pace=0.48,
        hook=0.72,
        breathing=0.62,
        effects=0.23,
        slow=0.68,
        setup=0.3,
        cinematic=0.9,
        raw=0.22,
        polish=0.76,
        rhythm=0.55,
        bands={"short": 0.12, "medium": 0.24, "anchor": 0.34, "long": 0.2, "hero": 0.1},
        curve=["establish", "build", "slow_peak", "accelerate", "resolve"],
        transitions={
            "cut": 0.72,
            "motion_match": 0.08,
            "fade": 0.12,
            "dip_black": 0.08,
        },
        roles={
            "hook": 0.06,
            "primary_movement": 0.42,
            "complete_rep_anchor": 0.28,
            "setup": 0.08,
            "breather": 0.07,
            "hero": 0.09,
        },
        ending="dramatic_payoff",
    ),
    "gritty_aggressive": _profile(
        energy=0.94,
        pace=0.78,
        hook=0.9,
        breathing=0.18,
        effects=0.38,
        slow=0.16,
        setup=0.22,
        cinematic=0.25,
        raw=0.82,
        polish=0.35,
        rhythm=0.68,
        bands={
            "micro": 0.2,
            "short": 0.46,
            "medium": 0.21,
            "anchor": 0.11,
            "hero": 0.02,
        },
        curve=["impact", "irregular_drive", "brief_reset", "hard_finish"],
        transitions={"cut": 0.84, "whip": 0.09, "glitch": 0.07},
        roles={
            "hook": 0.1,
            "primary_movement": 0.53,
            "micro_detail": 0.18,
            "setup": 0.1,
            "complete_rep_anchor": 0.07,
            "hero": 0.02,
        },
        ending="hard_cut",
    ),
    "smooth_sweeping": _profile(
        energy=0.38,
        pace=0.3,
        hook=0.42,
        breathing=0.82,
        effects=0.18,
        slow=0.42,
        setup=0.32,
        cinematic=0.62,
        raw=0.25,
        polish=0.72,
        rhythm=0.4,
        bands={"medium": 0.14, "anchor": 0.34, "long": 0.4, "hero": 0.12},
        curve=[
            "establish",
            "steady_movement",
            "gradual_build",
            "sustained_peak",
            "controlled_finish",
        ],
        transitions={
            "cut": 0.5,
            "motion_match": 0.12,
            "cross_dissolve": 0.3,
            "fade": 0.08,
        },
        roles={
            "hook": 0.04,
            "primary_movement": 0.36,
            "complete_rep_anchor": 0.32,
            "setup": 0.1,
            "breather": 0.1,
            "hero": 0.08,
        },
        ending="controlled_finish",
    ),
    "clean_coaching": _profile(
        energy=0.42,
        pace=0.38,
        hook=0.5,
        breathing=0.55,
        effects=0.06,
        slow=0.08,
        setup=0.08,
        cinematic=0.2,
        raw=0.35,
        polish=0.82,
        rhythm=0.38,
        bands={"medium": 0.18, "anchor": 0.54, "long": 0.24, "hero": 0.04},
        curve=[
            "clear_preview",
            "steady_instruction",
            "complete_movement",
            "clear_finish",
        ],
        transitions={"cut": 0.94, "cross_dissolve": 0.06},
        roles={
            "hook": 0.05,
            "primary_movement": 0.33,
            "complete_rep_anchor": 0.54,
            "setup": 0.03,
            "breather": 0.02,
            "hero": 0.03,
        },
        ending="clear_completion",
    ),
    "raw_documentary": _profile(
        energy=0.48,
        pace=0.38,
        hook=0.42,
        breathing=0.72,
        effects=0.04,
        slow=0.04,
        setup=0.58,
        cinematic=0.18,
        raw=1,
        polish=0.22,
        rhythm=0.3,
        bands={"medium": 0.28, "anchor": 0.3, "long": 0.34, "hero": 0.08},
        curve=["context", "workout_progression", "recovery", "movement", "natural_end"],
        transitions={"cut": 0.97, "cross_dissolve": 0.03},
        roles={
            "hook": 0.04,
            "primary_movement": 0.34,
            "complete_rep_anchor": 0.24,
            "setup": 0.18,
            "environment": 0.1,
            "breather": 0.1,
        },
        ending="natural_endpoint",
    ),
    "polished_commercial": _profile(
        energy=0.62,
        pace=0.56,
        hook=0.72,
        breathing=0.48,
        effects=0.2,
        slow=0.32,
        setup=0.26,
        cinematic=0.72,
        raw=0.18,
        polish=1,
        rhythm=0.62,
        bands={
            "short": 0.16,
            "medium": 0.32,
            "anchor": 0.32,
            "long": 0.12,
            "hero": 0.08,
        },
        curve=["hero_hook", "detail", "movement", "polished_build", "deliberate_end"],
        transitions={
            "cut": 0.7,
            "motion_match": 0.2,
            "cross_dissolve": 0.06,
            "fade": 0.04,
        },
        roles={
            "hook": 0.08,
            "primary_movement": 0.4,
            "complete_rep_anchor": 0.2,
            "close_detail": 0.12,
            "setup": 0.08,
            "hero": 0.12,
        },
        ending="product_hero",
    ),
    "rhythmic_music_montage": _profile(
        energy=0.8,
        pace=0.72,
        hook=0.78,
        breathing=0.3,
        effects=0.26,
        slow=0.14,
        setup=0.18,
        cinematic=0.3,
        raw=0.36,
        polish=0.62,
        rhythm=1,
        bands={
            "micro": 0.12,
            "short": 0.38,
            "medium": 0.3,
            "anchor": 0.16,
            "hero": 0.04,
        },
        curve=["pickup", "pulse", "accent", "break", "drop", "resolve"],
        transitions={"cut": 0.86, "motion_match": 0.1, "push_cut": 0.04},
        roles={
            "hook": 0.08,
            "primary_movement": 0.56,
            "complete_rep_anchor": 0.2,
            "setup": 0.08,
            "breather": 0.04,
            "hero": 0.04,
        },
        ending="accent_finish",
    ),
}

CONCEPTS = {
    "viral_shortform": (
        "viral",
        "social media",
        "short form",
        "short-form",
        "reel",
        "tiktok",
    ),
    "fast_fitness_montage": (
        "fast",
        "punchy",
        "energetic",
        "fitness montage",
        "workout montage",
        "sports",
    ),
    "cinematic_trailer": ("cinematic", "movie", "trailer"),
    "epic_dramatic": ("epic", "dramatic", "huge"),
    "gritty_aggressive": ("gritty", "aggressive", "hard hitting"),
    "smooth_sweeping": ("smooth", "sweeping", "slower"),
    "clean_coaching": ("clean", "coaching", "instructional", "professional"),
    "raw_documentary": ("raw", "documentary", "real workout", "authentic"),
    "polished_commercial": ("commercial", "polished", "advert"),
    "rhythmic_music_montage": ("rhythmic", "beat", "music montage"),
}


def _hits(text: str, phrases: tuple[str, ...]) -> int:
    return sum(
        1 for phrase in phrases if re.search(r"\b" + re.escape(phrase) + r"\b", text)
    )


def _weighted(profiles: dict[str, float]) -> dict[str, Any]:
    total = sum(profiles.values()) or 1
    weights = {k: round(v / total, 4) for k, v in profiles.items()}
    numeric = (
        "energy",
        "pace",
        "hook",
        "breathing",
        "effects",
        "slow",
        "setup",
        "cinematic",
        "raw",
        "polish",
        "rhythm",
    )
    result = {
        key: round(sum(PROFILES[p][key] * w for p, w in weights.items()), 4)
        for key in numeric
    }
    for key in ("bands", "transitions", "roles"):
        names = {n for p in weights for n in PROFILES[p][key]}
        result[key] = {
            n: round(sum(PROFILES[p][key].get(n, 0) * w for p, w in weights.items()), 4)
            for n in names
        }
        result[key] = dict(sorted(result[key].items(), key=lambda x: (-x[1], x[0])))
    dominant = max(weights, key=weights.get)
    result.update(
        weights=weights,
        curve=deepcopy(PROFILES[dominant]["curve"]),
        ending=PROFILES[dominant]["ending"],
    )
    return result


def resolve_style(
    request: str, overrides: dict[str, Any] | None = None, seed: int | str = 0
) -> dict[str, Any]:
    """Resolve language and optional explicit controls into a normalized contract."""
    text = " ".join(request.lower().replace("-ish", "").split())
    scores = {name: float(_hits(text, phrases)) for name, phrases in CONCEPTS.items()}
    # Contextual phrases carry more meaning than isolated tokens.
    if "social media ready" in text:
        scores["viral_shortform"] += 1.2
        scores["fast_fitness_montage"] += 1
    if "sports commercial" in text:
        scores["polished_commercial"] += 2
        scores["fast_fitness_montage"] += 0.7
    if "movie trailer" in text:
        scores["cinematic_trailer"] += 2
    scores = {k: v for k, v in scores.items() if v}
    if not scores:
        scores = {"fast_fitness_montage": 0.6, "viral_shortform": 0.4}
    if re.search(r"\b(a little|slightly|somewhat) cinematic\b", text):
        scores["cinematic_trailer"] = min(scores.get("cinematic_trailer", 0), 0.45)
    plan = _weighted(scores)
    decisions: list[str] = [
        f"Detected {name.replace('_', ' ')} language." for name in scores
    ]
    forbidden: set[str] = set()
    if re.search(r"\b(very|really) fast\b|lots of short clips", text):
        plan["pace"] = min(1, plan["pace"] + 0.18)
        plan["bands"]["short"] = plan["bands"].get("short", 0) + 0.2
        decisions.append("Strong speed modifier shortens the general rhythm.")
    if (
        "longer clips" in text
        or "don't cut too quickly" in text
        or "dont cut too quickly" in text
    ):
        plan["pace"] = min(plan["pace"], 0.42)
        plan["bands"]["long"] = plan["bands"].get("long", 0) + 0.25
    if re.search(r"(not too flashy|no fancy transitions)", text):
        plan["effects"] = min(plan["effects"], 0.08)
        forbidden.update({"glitch", "whip", "push_cut", "zoom_impact"})
    if re.search(r"\b(no|without|don't use|dont use) glitch", text):
        forbidden.add("glitch")
    slow_disabled = bool(
        re.search(r"\b(no|without|don't use|dont use) slow[ -]?motion", text)
    )
    if slow_disabled:
        plan["slow"] = 0
    if (
        "more setup" in text
        or "adjusting equipment" in text
        or "room to breathe" in text
    ):
        plan["setup"] = min(1, plan["setup"] + 0.3)
    if "fewer setup" in text or "less setup" in text:
        plan["setup"] = max(0, plan["setup"] - 0.3)
    heavy_breathe = bool(re.search(r"(heavy|final|last) reps? breathe", text))
    final_slow = bool(
        re.search(r"slow (down )?(the )?(strongest )?(final|last) rep", text)
    )
    chronology = (
        "strict"
        if re.search(r"(everything|keep it|stay) chronological", text)
        else "source_group_strict"
    )
    if forbidden:
        plan["transitions"] = {
            k: v for k, v in plan["transitions"].items() if k not in forbidden
        }
    explicit = dict(overrides or {})
    if explicit.get("preferred_transitions"):
        allowed = list(explicit["preferred_transitions"])
        plan["transitions"] = {x: 1 / len(allowed) for x in allowed}
    forbidden.update(explicit.get("forbidden_transitions", []))
    plan["transitions"] = {
        k: v for k, v in plan["transitions"].items() if k not in forbidden
    } or {"cut": 1}
    phases = _phases(text, plan["weights"])
    platform = (
        "tiktok"
        if "tiktok" in text
        else "instagram_reel"
        if "instagram" in text or "reel" in text
        else "youtube_short"
        if "youtube" in text or "shorts" in text
        else "vertical_social"
    )
    minimum = float(
        explicit.get("minimum_clip_length", 0.18 if plan["pace"] > 0.7 else 0.35)
    )
    maximum = float(explicit.get("maximum_clip_length", 3.2))
    if minimum > maximum:
        raise ValueError("minimum clip length cannot exceed maximum clip length")
    return {
        "schema_version": "1.0",
        "request": request,
        "seed": str(seed),
        "detected_style_concepts": list(scores),
        "profile_weights": plan["weights"],
        "intent": {
            k: plan[k]
            for k in (
                "energy",
                "pace",
                "hook",
                "breathing",
                "effects",
                "slow",
                "setup",
                "cinematic",
                "raw",
                "polish",
                "rhythm",
            )
        },
        "platform_bias": platform,
        "pacing_curve": plan["curve"],
        "style_phases": phases,
        "clip_duration_profile": {
            "bands": {
                k: {"min": BANDS[k][0], "max": BANDS[k][1], "weight": v}
                for k, v in plan["bands"].items()
            },
            "minimum": minimum,
            "maximum": maximum,
            "repetition_limit": 3,
        },
        "shot_role_targets": plan["roles"],
        "transition_policy": {
            "palette": plan["transitions"],
            "frequency": round(plan["effects"], 3),
            "forbidden": sorted(forbidden),
            "semantic_only": True,
        },
        "time_remapping": {
            "enabled": not slow_disabled,
            "slow_motion_amount": plan["slow"],
            "fast_motion_amount": max(0, plan["pace"] - 0.55),
            "maximum_slowdown": float(explicit.get("maximum_slowdown", 0.4)),
            "source_fps_floor_for_strong_slowdown": 50,
            "active_movement_default_rate": 1.0,
            "final_rep_slowdown": final_slow,
        },
        "hook_strategy": _hook_strategy(max(plan["weights"], key=plan["weights"].get)),
        "setup_breather_policy": {
            "amount": round(plan["setup"], 3),
            "duration_range": [0.3, 1.0],
            "maximum_share": 0.25,
        },
        "ending_emphasis": "slow_final_rep" if final_slow else plan["ending"],
        "anchor_policy": {"heavy_reps_breathe": heavy_breathe, "complete_reps": True},
        "chronology_strictness": chronology,
        "rep_visibility": "complete_anchors",
        "source_audio": (
            "preserve"
            if re.search(
                r"(keep|preserve|use) (the )?(source|camera|original) audio", text
            )
            else "muted"
        ),
        "priority_order": [
            "source_chronology",
            "explicit_user_instructions",
            "reviewed_movement",
            "movement_visibility",
            "target_duration",
            "style",
            "decorative_transitions",
        ],
        "overrides": explicit,
        "decision_reasons": decisions,
    }


def _phases(text: str, weights: dict[str, float]) -> list[dict[str, Any]]:
    if re.search(r"(tiktok|viral) (hook|at first).*(cinematic|after)", text):
        return [
            {"start": 0, "end": 0.15, "style": "viral_shortform"},
            {"start": 0.15, "end": 0.85, "style": "cinematic_trailer"},
            {
                "start": 0.85,
                "end": 1,
                "style": "cinematic_trailer",
                "purpose": "hero_ending",
            },
        ]
    if re.search(r"fast at first.*(slow|cinematic).*(end|after)", text):
        return [
            {"start": 0, "end": 0.6, "style": "fast_fitness_montage"},
            {"start": 0.6, "end": 1, "style": "smooth_sweeping"},
        ]
    return [{"start": 0, "end": 1, "style": max(weights, key=weights.get)}]


def _hook_strategy(dominant: str) -> dict[str, Any]:
    kind = {
        "viral_shortform": "immediate_high_motion",
        "cinematic_trailer": "dramatic_teaser",
        "epic_dramatic": "hero_or_build",
        "gritty_aggressive": "impact_detail",
        "clean_coaching": "clear_movement_preview",
    }.get(dominant, "strong_reviewed_movement")
    return {
        "type": kind,
        "target_seconds": 1.0,
        "trusted_candidates": [
            "user_selected",
            "reviewed_high_effort_looking",
            "late_set",
            "unusual_angle",
            "explosive_motion",
        ],
        "replay_counter": "suppress",
        "preserve_identity": True,
    }


def duration_sequence(
    style: dict[str, Any], count: int, roles: list[str] | None = None
) -> list[dict[str, Any]]:
    """Return deterministic, bounded, non-monotonous duration-band choices."""
    bands = style["clip_duration_profile"]["bands"]
    names = list(bands)
    weighted = [n for n in names for _ in range(max(1, round(bands[n]["weight"] * 20)))]
    result, previous, run = [], None, 0
    for index in range(count):
        role = roles[index] if roles and index < len(roles) else "primary_movement"
        digest = hashlib.sha256(
            f"{style['seed']}:{index}:{role}:{','.join(names)}".encode()
        ).digest()
        band = (
            "hero"
            if role == "hero" and "hero" in bands
            else "anchor"
            if "anchor" in role and "anchor" in bands
            else weighted[int.from_bytes(digest[:4], "big") % len(weighted)]
        )
        run = run + 1 if band == previous else 1
        if run > style["clip_duration_profile"]["repetition_limit"]:
            band = names[(names.index(band) + 1) % len(names)]
            run = 1
        low, high = bands[band]["min"], bands[band]["max"]
        fraction = int.from_bytes(digest[4:8], "big") / 2**32
        duration = max(
            style["clip_duration_profile"]["minimum"],
            min(
                style["clip_duration_profile"]["maximum"], low + (high - low) * fraction
            ),
        )
        result.append({"band": band, "duration": round(duration, 3), "role": role})
        previous = band
    return result


def speed_curve(
    style: dict[str, Any],
    *,
    moment: float = 0.5,
    source_fps: float | None = None,
    requested: bool = False,
) -> dict[str, Any]:
    """Create a renderer-neutral smooth dramatic slowdown, conservatively."""
    enabled = style["time_remapping"]["enabled"] and (
        requested or style["time_remapping"]["slow_motion_amount"] >= 0.35
    )
    if not enabled:
        return {
            "type": "constant",
            "keyframes": [{"position": 0, "rate": 1.0}, {"position": 1, "rate": 1.0}],
            "reason": "not_requested_by_profile",
        }
    floor = style["time_remapping"]["source_fps_floor_for_strong_slowdown"]
    minimum = style["time_remapping"]["maximum_slowdown"]
    conservative = source_fps is None or source_fps < floor
    minimum = max(minimum, 0.7 if conservative else 0.4)
    return {
        "type": "smooth_dramatic_center",
        "interpolation": "cubic_bezier",
        "landmark_source": "reviewed_event" if requested else "clip_center",
        "keyframes": [
            {"position": 0, "rate": 1.0},
            {"position": max(0, moment - 0.25), "rate": 0.78},
            {"position": moment, "rate": round(minimum, 2)},
            {"position": min(1, moment + 0.25), "rate": 0.78},
            {"position": 1, "rate": 1.0},
        ],
        "source_fps": source_fps,
        "conservative_for_source_fps": conservative,
        "optical_flow": False,
    }


def transition_choice(style: dict[str, Any], index: int, role: str) -> str:
    """Choose sparsely and deterministically from the allowed semantic palette."""
    if index == 0:
        return "none"
    policy = style["transition_policy"]
    digest = hashlib.sha256(
        f"{style['seed']}:transition:{index}:{role}".encode()
    ).digest()
    draw = int.from_bytes(digest[:4], "big") / 2**32
    # Cuts are the baseline. Effects are candidates only at a section-like role
    # boundary and then only at the profile's declared frequency.
    boundary = role in {"hook", "setup", "breather", "environment", "hero"}
    effects = [
        (name, weight) for name, weight in policy["palette"].items() if name != "cut"
    ]
    if not boundary or not effects or draw >= policy["frequency"]:
        return "cut"
    total = sum(weight for _, weight in effects)
    target = (int.from_bytes(digest[4:8], "big") / 2**32) * total
    cumulative = 0.0
    for name, weight in effects:
        cumulative += weight
        if target <= cumulative:
            return name
    return effects[-1][0]


def apply_style(
    edit_plan: dict[str, Any],
    style: dict[str, Any],
    source_fps: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Attach style decisions without changing Phase 9 selection or chronology."""
    result = deepcopy(edit_plan)
    clips = result.get("clips", [])
    roles = [
        "hook"
        if c.get("role") == "hook_replay"
        else "complete_rep_anchor"
        if c.get("role") == "primary"
        else c.get("role", "breather")
        for c in clips
    ]
    timings = duration_sequence(style, len(clips), roles)
    for index, clip in enumerate(clips):
        clip["style_timing"] = timings[index]
        clip["time_remap"] = speed_curve(
            style,
            source_fps=(source_fps or {}).get(str(clip.get("source_id"))),
            requested=bool(
                style["time_remapping"]["final_rep_slowdown"]
                and index == len(clips) - 1
            ),
        )
        # Preserve Phase 9's primary playback and identity. A renderer consumes the curve.
        clip["transition"] = transition_choice(style, index, roles[index])
    result["style_director"] = style
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("--seed", default="0")
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    resolved = resolve_style(
        args.request,
        json.loads(args.overrides.read_text()) if args.overrides else None,
        args.seed,
    )
    output = json.dumps(resolved, indent=2) + "\n"
    args.output.write_text(output) if args.output else print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
