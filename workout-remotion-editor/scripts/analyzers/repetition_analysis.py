"""Generic Phase 5 repetition-evidence orchestration.

This module selects and partitions eligible evidence.  Exercise biomechanics
and thresholds live exclusively in ``rep_rules``.
"""

from __future__ import annotations

from typing import Any

from rep_rules.registry import get_rule

DEFAULT_RULE = "single_arm_dumbbell_row_v1"


def _gate(name: str, passed: bool, reason: str) -> dict[str, Any]:
    return {"gate": name, "passed": bool(passed), "reason": None if passed else reason}


def run_repetition_analysis(
    document: dict[str, Any],
    *,
    requested_rule: str | None = None,
    min_quality: float = 0.65,
    require_user_confirmation: bool = False,
    fusion_threshold: float = 0.85,
) -> None:
    evidence = document["evidence"]
    contexts = document.get("context", {}).get("assertions", [])
    entities = {x["id"]: x for x in evidence.get("tracked_entities", [])}
    pose = evidence.get("pose_samples", [])
    intervals = []
    reps = []
    for source in document["sources"]:
        run_id = f"{source['id']}:repetition_analysis:phase5"
        run = {
            "id": run_id,
            "source_id": source["id"],
            "category": "repetition_analysis",
            "provider": "phase5-rule-engine",
            "version": "1",
            "upstream": "built-in",
            "status": "no_results",
            "configuration": {
                "requested_rule": requested_rule,
                "fusion_threshold": fusion_threshold,
                "minimum_quality": min_quality,
                "require_user_confirmation": require_user_confirmation,
            },
            "performance": {},
            "fallback": False,
            "warnings": [],
            "errors": [],
        }
        evidence["runs"].append(run)
        candidates = [
            c
            for c in evidence.get("exercise_candidates", [])
            if c["source_id"] == source["id"] and c.get("source_type") == "fused"
        ]
        # Every top-ranked fused interval is an attempted analysis interval, including rejection.
        for candidate in [c for c in candidates if c["rank"] == 1]:
            canonical = candidate.get("canonical_exercise_id")
            mapped = DEFAULT_RULE if canonical == "dumbbell_row_single_arm" else None
            rule_id = requested_rule or mapped
            rule = get_rule(canonical, rule_id) if rule_id else None
            entity = entities.get(candidate.get("entity_id"))
            scene = candidate.get("scene_id")
            samples = [
                p
                for p in pose
                if p["source_id"] == source["id"]
                and p.get("entity_id") == candidate.get("entity_id")
                and p["scene_id"] == scene
                and candidate["start"] - 1e-6
                <= p["timestamp"]
                <= candidate["end"] + 1e-6
                and p.get("input_variant") == "one_euro_smoothed"
            ]
            if (
                not samples
            ):  # permit raw-only third-party fixtures without mixing variants
                samples = [
                    p
                    for p in pose
                    if p["source_id"] == source["id"]
                    and p.get("entity_id") == candidate.get("entity_id")
                    and p["scene_id"] == scene
                    and candidate["start"] - 1e-6
                    <= p["timestamp"]
                    <= candidate["end"] + 1e-6
                    and p.get("input_variant") == "raw"
                ]
            explicit = next(
                (
                    a.get("working_side")
                    for a in contexts
                    if a.get("source_id") == source["id"]
                    and a.get("working_side") in {"left", "right"}
                    and (a.get("entity_id") in {None, candidate.get("entity_id")})
                ),
                None,
            )
            side = rule.resolve_side(samples, explicit) if rule else None
            strong = candidate["confidence"] >= fusion_threshold and bool(
                candidate["supporting_evidence_refs"]
            )
            accepted = candidate["user_confirmed"] or (
                strong and not require_user_confirmation
            )
            gates = [
                _gate(
                    "selected_top_ranked_candidate",
                    candidate["rank"] == 1,
                    "candidate_not_top_ranked",
                ),
                _gate(
                    "exact_canonical_exercise",
                    canonical == "dumbbell_row_single_arm",
                    "incompatible_exercise",
                ),
                _gate(
                    "ambiguity_resolved",
                    candidate["ambiguity"]["status"] == "none",
                    "unresolved_ambiguity",
                ),
                _gate(
                    "conflict_resolved",
                    candidate["conflict_status"] == "none"
                    and not candidate["conflicting_evidence_refs"],
                    "unresolved_conflict",
                ),
                _gate("accepted_identity", accepted, "identity_not_accepted"),
                _gate(
                    "valid_person_entity",
                    entity is not None and entity.get("category") == "person",
                    "invalid_or_missing_person_entity",
                ),
                _gate(
                    "same_scene",
                    scene is not None
                    and entity is not None
                    and entity.get("scene_id") == scene,
                    "scene_entity_mismatch",
                ),
                _gate(
                    "stable_entity_presence",
                    entity is not None
                    and entity["start"] <= candidate["start"] + 0.05
                    and entity["end"] >= candidate["end"] - 0.05,
                    "unstable_entity_presence",
                ),
                _gate(
                    "exact_rule_mapping",
                    rule is not None and rule_id == mapped,
                    "incompatible_rep_rule",
                ),
                _gate(
                    "working_side_resolved",
                    side in {"left", "right"},
                    "unresolved_working_side",
                ),
            ]
            if rule and side:
                gates += [_gate(n, p, r or n) for n, p, r in rule.gates(samples, side)]
            iid = f"rep-interval-{len(intervals) + 1}"
            failed = [g["reason"] for g in gates if not g["passed"]]
            interval = {
                "id": iid,
                "source_id": source["id"],
                "run_id": run_id,
                "scene_id": scene,
                "entity_id": candidate.get("entity_id"),
                "exercise_candidate_id": candidate["id"],
                "canonical_exercise_id": canonical,
                "rep_rule_id": rule_id,
                "rep_rule_version": rule.version if rule else None,
                "side": side,
                "start": candidate["start"],
                "end": candidate["end"],
                "eligible": not failed,
                "gate_results": gates,
                "ineligibility_reasons": failed,
                "warnings": [],
            }
            intervals.append(interval)
            if not failed:
                provenance = {
                    "source_id": source["id"],
                    "run_id": run_id,
                    "scene_id": scene,
                    "entity_id": candidate["entity_id"],
                    "exercise_candidate_id": candidate["id"],
                    "canonical_exercise_id": canonical,
                    "rep_rule_id": rule_id,
                    "rep_rule_version": rule.version,
                    "rep_analysis_interval_id": iid,
                    "exercise_quality": candidate["confidence"],
                    "min_quality": min_quality,
                }
                result = rule.analyze(samples, side, provenance)
                reps.extend(result.candidates)
                interval["warnings"].extend(result.warnings)
        mine = [x for x in intervals if x["source_id"] == source["id"]]
        run["performance"] = {
            "attempted_intervals": len(mine),
            "eligible_intervals": sum(x["eligible"] for x in mine),
            "rep_candidates": sum(x["source_id"] == source["id"] for x in reps),
        }
        run["status"] = "success" if mine else "no_results"
        run["fallback"] = not any(x["eligible"] for x in mine)
    evidence["rep_analysis_intervals"] = intervals
    evidence["rep_candidates"] = reps
