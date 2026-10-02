"""Context-first exercise recognition with deterministic, inspectable fusion."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analyzers.base import Result, Unavailable

DEFAULT_TAXONOMY = Path(__file__).parents[1] / "exercise-taxonomy.json"
NEGATIVE_TYPES = {"setup", "transition", "walking", "reracking", "camera_setup",
                  "stretch_or_warmup", "insufficient_motion", "insufficient_pose",
                  "background_entity", "partial_movement", "unknown_nonexercise_activity"}
WEIGHTS = {"explicit_interval": 1.0, "explicit_source": .95, "ordered_plan": .75,
           "registry": .7, "hint": .45, "machine": .4, "action_model": .35,
           "equipment": .15, "pose": .15, "negative": -.35}


def normalize_alias(value: str) -> str:
    """Normalize only safe surface variation; taxonomy controls equivalence."""
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"[-_/]+", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


class Taxonomy:
    def __init__(self, data: dict[str, Any]):
        self.version = data["taxonomy_version"]
        self.entries = {entry["canonical_id"]: entry for entry in data["exercises"]}
        self.aliases: dict[str, list[str]] = {}
        for entry in data["exercises"]:
            for label in [entry["canonical_id"], entry["display_name"], *entry["aliases"]]:
                self.aliases.setdefault(normalize_alias(label), []).append(entry["canonical_id"])
        for label, ids in data.get("ambiguous_aliases", {}).items():
            self.aliases[normalize_alias(label)] = ids
        self.validate()

    @classmethod
    def load(cls, path: Path = DEFAULT_TAXONOMY) -> "Taxonomy":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def validate(self) -> None:
        if not self.version or not self.entries:
            raise ValueError("taxonomy requires a version and exercises")
        for key, entry in self.entries.items():
            expected_rule = "single_arm_dumbbell_row_v1" if key == "dumbbell_row_single_arm" else None
            if key != entry["canonical_id"] or entry.get("rep_rule_id") != expected_rule:
                raise ValueError("canonical IDs must be unique and rep rules must match the exact registry")
            if entry.get("parent_id") and entry["parent_id"] not in self.entries:
                raise ValueError(f"unknown taxonomy parent: {entry['parent_id']}")
        for ids in self.aliases.values():
            if any(item not in self.entries for item in ids):
                raise ValueError("alias references unknown canonical ID")

    def map_label(self, label: str) -> dict[str, Any]:
        normalized = normalize_alias(label)
        matches = list(dict.fromkeys(self.aliases.get(normalized, [])))
        return {"supplied_label": label, "normalized_label": normalized,
                "status": "mapped" if len(matches) == 1 else "ambiguous" if matches else "unmapped",
                "canonical_exercise_id": matches[0] if len(matches) == 1 else None,
                "candidate_ids": matches}


def load_context(path: Path | None, labels: list[str], source_ids: list[str], taxonomy: Taxonomy) -> dict[str, Any]:
    context = {"taxonomy_version": taxonomy.version, "assertions": [], "ordered_plan": []}
    if path:
        raw = json.loads(path.read_text(encoding="utf-8"))
        context = raw.get("context", raw)
    if context.get("taxonomy_version") != taxonomy.version:
        raise ValueError("context taxonomy_version does not match taxonomy")
    if labels:
        if len(source_ids) != 1:
            raise ValueError("--exercise-label is only valid with exactly one source")
        for index, label in enumerate(labels):
            mapped = taxonomy.map_label(label)
            context.setdefault("assertions", []).append({
                "id": f"cli-context-{index + 1}", "source_id": source_ids[0], "scene_id": None,
                "entity_id": None, "start": None, "end": None, "canonical_exercise_id": mapped["canonical_exercise_id"],
                "supplied_label": label, "normalized_label": mapped["normalized_label"],
                "mapping_status": mapped["status"], "mapping_candidates": mapped["candidate_ids"],
                "source": "user_provided", "assertion_type": "explicit_identity", "scope": "source",
                "user_confirmed": True})
    # Normalize file assertions without overwriting the original label.
    for assertion in context.get("assertions", []):
        if assertion.get("source_id") not in source_ids:
            raise ValueError(f"context assertion references unknown source: {assertion.get('source_id')}")
        supplied = assertion.get("supplied_label")
        if supplied and "mapping_status" not in assertion:
            mapped = taxonomy.map_label(supplied)
            assertion.update(normalized_label=mapped["normalized_label"], mapping_status=mapped["status"],
                             mapping_candidates=mapped["candidate_ids"])
            assertion.setdefault("canonical_exercise_id", mapped["canonical_exercise_id"])
        cid = assertion.get("canonical_exercise_id")
        if cid is not None and cid not in taxonomy.entries:
            raise ValueError(f"unknown canonical exercise ID: {cid}")
        if assertion.get("scope") == "interval" and not (
                isinstance(assertion.get("start"), (int, float)) and
                isinstance(assertion.get("end"), (int, float)) and
                assertion["start"] < assertion["end"]):
            raise ValueError("interval assertion requires start < end")
    for item in context.get("ordered_plan", []):
        if item.get("canonical_exercise_id") not in taxonomy.entries:
            raise ValueError(f"ordered plan has unknown canonical ID: {item.get('canonical_exercise_id')}")
    return context


def propose_intervals(document: dict[str, Any], min_duration: float = 2.0) -> list[dict[str, Any]]:
    """Conservative scene-contained workout chunks; never confirmed sets."""
    evidence = document["evidence"]
    scenes = evidence.get("scenes", [])
    active = [x for x in evidence.get("activity_regions", []) if x["type"] == "motion_active"]
    entities = [x for x in evidence.get("tracked_entities", []) if x["category"] == "person"]
    roles = {(x["source_id"], x["entity_id"]): x["role"] for x in evidence.get("entity_roles", [])}
    proposals = []
    for scene in scenes or [{"id": None, "source_id": s["id"], "start": 0, "end": s["duration"]}
                              for s in document["sources"] if s["duration"] is not None]:
        for region in active or [scene]:
            if region["source_id"] != scene["source_id"]:
                continue
            start, end = max(scene["start"], region["start"]), min(scene["end"], region["end"])
            if end - start < min_duration:
                continue
            matches = [e for e in entities if e["source_id"] == scene["source_id"] and
                       e["start"] <= start + .5 and e["end"] >= end - .5 and
                       (not any(key[0] == scene["source_id"] for key in roles) or
                        roles.get((scene["source_id"], e["id"])) == "primary_athlete_candidate")]
            entity = max(matches, key=lambda x: x["end"] - x["start"], default=None)
            proposals.append({"id": f"interval-{len(proposals)+1}", "source_id": scene["source_id"],
                              "scene_id": scene.get("id"), "entity_id": entity and entity["id"],
                              "start": start, "end": end, "type": "interval_candidate",
                              "supporting_evidence_refs": [region["id"]] if isinstance(region.get("id"), str) else [],
                              "exclusion_states": []})
    return proposals


def fuse(document: dict[str, Any], taxonomy: Taxonomy, context: dict[str, Any],
         action_candidates: list[dict[str, Any]] | None = None, top_k: int = 3,
         ambiguity_margin: float = .1) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    intervals = propose_intervals(document)
    # Explicit context must still work when no machine interval exists.
    for assertion in context.get("assertions", []):
        source = next((s for s in document["sources"] if s["id"] == assertion["source_id"]), None)
        source_intervals = [item for item in intervals if item["source_id"] == assertion["source_id"]]
        if (source and assertion.get("scope") == "source" and source["duration"] is not None
                and not source_intervals):
            intervals.append({"id": f"context-interval-{assertion['id']}", "source_id": source["id"],
                              "scene_id": None, "entity_id": assertion.get("entity_id"), "start": 0,
                              "end": source["duration"], "type": "interval_candidate",
                              "supporting_evidence_refs": [], "exclusion_states": []})
        elif assertion.get("start") is not None and assertion.get("end") is not None:
            intervals.append({"id": f"context-interval-{assertion['id']}", "source_id": assertion["source_id"],
                              "scene_id": assertion.get("scene_id"), "entity_id": assertion.get("entity_id"),
                              "start": assertion["start"], "end": assertion["end"], "type": "interval_candidate",
                              "supporting_evidence_refs": [], "exclusion_states": []})
    unique = {(x["source_id"], x.get("scene_id"), x.get("entity_id"), x["start"], x["end"]): x for x in intervals}
    intervals = list(unique.values())
    candidates = []
    ordered_intervals = sorted(intervals, key=lambda item: (item["source_id"], item["start"], item["end"]))
    plan = sorted(context.get("ordered_plan", []), key=lambda item: item["order"])
    for interval_index, interval in enumerate(ordered_intervals):
        scores: dict[str, float] = {}
        support: dict[str, list[str]] = {}
        conflicts: dict[str, list[str]] = {}
        relevant = [a for a in context.get("assertions", []) if a["source_id"] == interval["source_id"] and
                    (a.get("scope") == "source" or (a.get("start", 1e99) < interval["end"] and a.get("end", -1) > interval["start"]))]
        for assertion in relevant:
            cid = assertion.get("canonical_exercise_id")
            if cid:
                key = "explicit_interval" if assertion.get("scope") == "interval" else "explicit_source"
                scores[cid] = max(scores.get(cid, 0), WEIGHTS[key])
                support.setdefault(cid, []).append(f"context:{assertion['id']}")
        if interval_index < len(plan):
            cid = plan[interval_index]["canonical_exercise_id"]
            scores[cid] = max(scores.get(cid, 0), WEIGHTS["ordered_plan"])
            support.setdefault(cid, []).append(f"plan:{plan[interval_index]['order']}")
        for raw in action_candidates or []:
            if raw["source_id"] == interval["source_id"] and raw["start"] < interval["end"] and raw["end"] > interval["start"]:
                cid = raw.get("canonical_exercise_id")
                if cid:
                    scores[cid] = scores.get(cid, 0) + WEIGHTS["action_model"] * raw["confidence"]
                    support.setdefault(cid, []).append(raw["id"])
        # Phase 3 movement can establish a sustained exercise-like bout, but not
        # a specific exercise identity. Keep the canonical result explicitly unknown.
        movement = [item for item in document["evidence"].get("movement_signals", [])
                    if item["source_id"] == interval["source_id"]
                    and item.get("entity_id") == interval.get("entity_id")
                    and interval["start"] <= item["timestamp"] <= interval["end"]
                    and item["signal_type"] == "active_landmark_group" and item["quality"] >= .5]
        if (interval.get("entity_id") is not None and len(movement) >= 3
                and movement[-1]["timestamp"] - movement[0]["timestamp"] >= 2):
            cid = "unknown_exercise"
            scores[cid] = scores.get(cid, 0) + WEIGHTS["machine"] + WEIGHTS["pose"]
            support.setdefault(cid, []).extend(item["id"] for item in movement)
        for cid in list(scores):
            conflicts[cid] = [ref for other, refs in support.items() if other != cid for ref in refs]
        ranked = sorted(scores.items(), key=lambda item: (-min(item[1], 1), item[0]))[:top_k]
        ambiguous = len(ranked) > 1 and ranked[0][1] - ranked[1][1] < ambiguity_margin
        for rank, (cid, score) in enumerate(ranked, 1):
            candidates.append({"id": f"candidate-{len(candidates)+1}", "source_id": interval["source_id"],
                "run_id": "", "scene_id": interval.get("scene_id"), "entity_id": interval.get("entity_id"),
                "start": interval["start"], "end": interval["end"], "label": taxonomy.entries[cid]["display_name"],
                "canonical_exercise_id": cid, "taxonomy_version": taxonomy.version, "source_type": "fused",
                "provider": "deterministic-context-fusion", "model": None, "rank": rank,
                "confidence": round(min(score, 1), 6), "score_type": "fusion_score",
                "user_confirmed": any(a.get("user_confirmed") and a.get("canonical_exercise_id") == cid for a in relevant),
                "ambiguity": {"status": "unresolved" if ambiguous else "none", "margin": round(ranked[0][1]-ranked[1][1], 6) if len(ranked)>1 else None},
                "supporting_evidence_refs": support.get(cid, []), "conflicting_evidence_refs": conflicts.get(cid, []),
                "conflict_status": "retained" if conflicts.get(cid) else "none"})
    return intervals, candidates


@dataclass
class FakeActionProvider:
    status: str = "success"
    candidates: list[dict[str, Any]] | None = None
    name: str = "fake-action-provider"
    category: str = "action_recognition"
    upstream: str = "test-double"
    version: str | None = "1"
    model: str | None = "fake-model"

    @property
    def configuration(self) -> dict[str, Any]:
        return {"model": self.model, "mode": "test"}

    def analyze(self, source: dict[str, Any], timeout: float) -> Result:
        if self.status == "unavailable":
            raise Unavailable("fake dependency unavailable")
        if self.status == "failed":
            raise RuntimeError("fake inference failure")
        if self.model is None:
            raise Unavailable("action model is not configured")
        values = [dict(x) for x in self.candidates or [] if x["source_id"] == source["id"]]
        return Result(status=self.status if self.status != "success" or values else "no_results",
                      evidence={"exercise_candidates": values})
