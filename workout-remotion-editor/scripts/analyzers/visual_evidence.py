"""Provider-neutral geometry and conservative scene-local subject candidates.

Scores organize review; they are not calibrated identity probabilities.
No exercise, repetition, technique, or anatomical conclusions are produced.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

CONTEXT_CLASSES = {"bench", "chair", "sports ball"}


def coordinates(box: Any) -> list[float]:
    if isinstance(box, dict):
        return [box[key] for key in ("x1", "y1", "x2", "y2")]
    return list(box)


def valid_box(box: Any) -> bool:
    try:
        values = coordinates(box)
        return (len(values) == 4 and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                      and math.isfinite(v) and 0 <= v <= 1 for v in values)
                and values[0] < values[2] and values[1] < values[3])
    except (KeyError, TypeError, ValueError):
        return False


def box_object(box: Any) -> dict[str, float]:
    if not valid_box(box):
        raise ValueError("invalid normalized xyxy bounding box")
    return dict(zip(("x1", "y1", "x2", "y2"), coordinates(box)))


def area(box: Any) -> float:
    x1, y1, x2, y2 = coordinates(box)
    return (x2 - x1) * (y2 - y1)


def overlap(a: Any, b: Any) -> float:
    ax1, ay1, ax2, ay2 = coordinates(a)
    bx1, by1, bx2, by2 = coordinates(b)
    return max(0, min(ax2, bx2) - max(ax1, bx1)) * max(0, min(ay2, by2) - max(ay1, by1))


def distance(a: Any, b: Any) -> float:
    ax1, ay1, ax2, ay2 = coordinates(a)
    bx1, by1, bx2, by2 = coordinates(b)
    return math.hypot(max(0, ax1 - bx2, bx1 - ax2), max(0, ay1 - by2, by1 - ay2))


def union(boxes: list[Any], padding: float = 0.02) -> dict[str, float]:
    values = [coordinates(box) for box in boxes]
    return box_object([max(0, min(v[0] for v in values) - padding),
                       max(0, min(v[1] for v in values) - padding),
                       min(1, max(v[2] for v in values) + padding),
                       min(1, max(v[3] for v in values) + padding)])


def crop_risks(athlete: Any, equipment: list[Any], crop: Any) -> dict[str, Any]:
    """Box coverage, never anatomical visibility or certified crop safety."""
    if not valid_box(crop) or not valid_box(athlete) or any(not valid_box(b) for b in equipment):
        raise ValueError("invalid crop or subject bounding box")
    coverage = overlap(athlete, crop) / area(athlete)
    flags = []
    if coverage < 1 - 1e-6:
        flags.append("athlete_outside_crop")
    if coordinates(athlete)[3] > coordinates(crop)[3] + 1e-6:
        flags.append("athlete_bottom_cutoff")
    if any(overlap(box, crop) / area(box) < 1 - 1e-6 for box in equipment):
        flags.append("tracked_equipment_outside_crop")
    return {"box_coverage": min(1, max(0, coverage)), "risk_flags": flags}


def derive(samples: list[dict[str, Any]], scenes: list[dict[str, Any]],
           crop: Any = None, equipment_classes: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Normalize worker observations and build auditable scene-local evidence."""
    detections, entities, candidates, regions, constraints = [], [], [], [], []
    explicit = set(equipment_classes or [])
    for scene in scenes:
        scene_samples = [sample for sample in samples if sample["interval_id"] == scene["id"]]
        if not scene_samples:
            continue
        by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_sample: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for sample in scene_samples:
            for index, item in enumerate(sample["detections"]):
                label = item["class_name"]
                track = item.get("track_id")
                entity_id = f"{scene['id']}:track:{track}" if track is not None else None
                detection = {
                    "id": f"sample:{sample['sample_index']}:detection:{index}",
                    "interval_id": scene["id"], "time": sample["time"],
                    "sample_index": sample["sample_index"], "frame_index": sample["frame_index"],
                    "class_id": item["class_id"], "class_name": label,
                    "category": "person" if label == "person" else "unknown_equipment"
                    if label == "unknown_equipment" else "equipment" if label in explicit else "object",
                    "bbox": box_object(item["bbox"]), "confidence": item["confidence"],
                }
                if entity_id is not None:
                    detection["entity_id"] = entity_id
                    by_entity[entity_id].append(detection)
                detections.append(detection)
                by_sample[sample["sample_index"]].append(detection)
        persons = {}
        for entity_id, observations in by_entity.items():
            # A class switch is identity uncertainty, not a reason to invent a label.
            labels = {item["class_name"] for item in observations}
            gaps = []
            cadence = scene.get("sample_interval", 0.2)
            for first, second in zip(observations, observations[1:]):
                if second["time"] - first["time"] > cadence * 1.5 + 1e-6:
                    gaps.append({"start": first["time"], "end": second["time"],
                                 "reason": "Unobserved interval; possible occlusion or subject loss."})
            entity = {
                "id": entity_id, "interval_id": scene["id"],
                "provider_track_id": str(entity_id.split(":track:", 1)[1]),
                "category": observations[0]["category"], "class_name": observations[0]["class_name"],
                "first_seen": observations[0]["time"], "last_seen": observations[-1]["time"],
                "detection_ids": [item["id"] for item in observations],
                "observation_count": len(observations), "sample_coverage": len(observations) / len(scene_samples),
                "gaps": gaps, "issues": ["class_changed"] if len(labels) > 1 else [],
            }
            entities.append(entity)
            if labels == {"person"}:
                persons[entity_id] = observations
        ranking = []
        for entity_id, observations in persons.items():
            coverage = len(observations) / len(scene_samples)
            duration_support = ((observations[-1]["time"] - observations[0]["time"])
                                / max(scene["end"] - scene["start"], 1e-6))
            displacement = sum(distance_centers(a["bbox"], b["bbox"])
                               for a, b in zip(observations, observations[1:]))
            motion_support = min(1, displacement / max(len(observations) - 1, 1) / 0.04)
            nearby = sum(any(other["category"] != "person"
                             and (other["class_name"] in CONTEXT_CLASSES | explicit
                                  or other["category"] == "unknown_equipment")
                             and distance(item["bbox"], other["bbox"]) <= 0.08
                             for other in by_sample[item["sample_index"]]) for item in observations)
            proximity = nearby / len(observations)
            prominence = sum(area(item["bbox"]) for item in observations) / len(observations)
            signals = {"persistence": coverage, "duration": min(1, duration_support),
                       "box_motion": motion_support, "object_proximity": proximity,
                       "prominence": prominence}
            score = (0.45 * coverage + 0.25 * signals["duration"] + 0.15 * motion_support
                     + 0.10 * proximity + 0.05 * prominence)
            ranking.append((score, entity_id, signals))
        ranking.sort(reverse=True)
        winner = None
        for rank, (score, entity_id, signals) in enumerate(ranking):
            margin = score - ranking[1][0] if rank == 0 and len(ranking) > 1 else score
            sufficient = signals["persistence"] >= 0.5 and len(persons[entity_id]) >= 3
            selected = rank == 0 and sufficient and margin >= 0.12
            state = "candidate" if selected else "ambiguous" if sufficient else "unresolved"
            if selected:
                winner = entity_id
            candidates.append({
                "id": f"{scene['id']}:subject:{rank}", "interval_id": scene["id"],
                "start": scene["start"], "end": scene["end"], "entity_id": entity_id,
                "role": "primary_athlete_candidate", "state": state, "score": score,
                "score_semantics": "uncalibrated_heuristic", "confidence": None, "signals": signals,
                "reasons": ["Scene-local persistence and duration dominate the candidate score.",
                            "Motion and object proximity are weak image-space support, not exercise identity.",
                            "Scene-wide ranking prevents a transient larger passerby from changing selection."],
            })
        # Preserve ambiguity; do not pick the largest/most centered alternative.
        selected_entities = [winner] if winner else list(persons)
        # Relevant-object association requires persistence near selected subjects.
        associated = set()
        for entity_id, observations in by_entity.items():
            if observations[0]["category"] == "person":
                continue
            if observations[0]["class_name"] not in CONTEXT_CLASSES | explicit | {"unknown_equipment"}:
                continue
            co_present = sum(any(other.get("entity_id") in selected_entities
                                 and distance(other["bbox"], item["bbox"]) <= 0.08
                                 for other in by_sample[item["sample_index"]]) for item in observations)
            if co_present >= 3 and co_present / len(observations) >= 0.5:
                associated.add(entity_id)
        for sample in scene_samples:
            observations = by_sample[sample["sample_index"]]
            athletes = [item for item in observations if item.get("entity_id") in selected_entities]
            equipment = [item for item in observations if item.get("entity_id") in associated]
            flags = ["primary_athlete_ambiguous"] if not winner else []
            if not athletes:
                flags.append("athlete_track_lost" if selected_entities else "subject_unresolved")
            athlete_region_ids, equipment_region_ids = [], []
            for kind, items, references in (("athlete", athletes, athlete_region_ids),
                                             ("equipment_candidate", equipment, equipment_region_ids)):
                for item in items:
                    region_id = f"{item['id']}:region"
                    regions.append({"id": region_id, "interval_id": scene["id"], "time": sample["time"],
                                    "kind": kind, "bbox": item["bbox"], "entity_ids": [item["entity_id"]],
                                    "detection_ids": [item["id"]],
                                    "reason": "Observed subject box." if kind == "athlete" else
                                    "Persistent nearby object; exercise relevance needs review."})
                    references.append(region_id)
            constraint = {
                "id": f"sample:{sample['sample_index']}:crop", "interval_id": scene["id"],
                "time": sample["time"], "region_ids": athlete_region_ids + equipment_region_ids,
                "risk_flags": flags, "reason": "Sampled box constraints only; review anatomy and undetected implements.",
                "coverage_scope": "sample_only",
            }
            if athletes:
                boxes = [item["bbox"] for item in athletes + equipment]
                required = union(boxes)
                constraint["minimum_visible_region"] = required
                union_id = f"sample:{sample['sample_index']}:union"
                regions.append({"id": union_id, "interval_id": scene["id"], "time": sample["time"],
                                "kind": "crop_required_union", "bbox": required,
                                "entity_ids": [item["entity_id"] for item in athletes + equipment],
                                "detection_ids": [item["id"] for item in athletes + equipment],
                                "reason": "Padded union of observed subjects and candidate relevant objects."})
                constraint["region_ids"].append(union_id)
                if crop is not None:
                    evaluated = crop_risks(union([item["bbox"] for item in athletes], 0),
                                           [item["bbox"] for item in equipment], crop)
                    constraint.update(proposed_crop=box_object(crop), box_coverage=evaluated["box_coverage"])
                    constraint["risk_flags"].extend(evaluated["risk_flags"])
                    if overlap(required, crop) / area(required) < 1 - 1e-6:
                        constraint["risk_flags"].append("required_region_outside_crop")
            constraints.append(constraint)
    return {"detections": detections, "tracked_entities": entities, "subject_candidates": candidates,
            "visual_regions": regions, "crop_constraints": constraints}


def distance_centers(a: Any, b: Any) -> float:
    ax1, ay1, ax2, ay2 = coordinates(a)
    bx1, by1, bx2, by2 = coordinates(b)
    return math.hypot((ax1 + ax2 - bx1 - bx2) / 2, (ay1 + ay2 - by1 - by2) / 2)
