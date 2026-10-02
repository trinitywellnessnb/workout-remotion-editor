"""Semantic checks for analyzer-neutral visual evidence; no optional ML imports."""
from __future__ import annotations

from typing import Any

from .visual_evidence import valid_box

VISUAL_COLLECTIONS = ("tracking_intervals", "detections", "tracked_entities",
                      "subject_candidates", "visual_regions", "crop_constraints")


def validate_visual(document: dict[str, Any], seen: set[str]) -> list[str]:
    evidence = document.get("evidence", {})
    errors = []
    sources = {item["id"]: item for item in document["sources"]}
    runs = {item["id"]: item for item in evidence.get("runs", [])}
    intervals = {item["id"]: item for item in evidence.get("tracking_intervals", [])}
    entities = {item["id"]: item for item in evidence.get("tracked_entities", [])}
    detections = {item["id"]: item for item in evidence.get("detections", [])}
    regions = {item["id"]: item for item in evidence.get("visual_regions", [])}
    scenes = {item["id"]: item for item in evidence.get("scenes", [])}
    ordered = {}
    samples = {}
    person_at_sample = set()

    def compatible(a, b):
        return b is not None and a["source_id"] == b["source_id"] and a["run_id"] == b["run_id"]

    def box_errors(item, prefix):
        for key in ("bbox", "minimum_visible_region", "proposed_crop"):
            if key in item and not valid_box(item[key]):
                errors.append(f"{prefix}/{key}: invalid positive normalized xyxy box")

    for collection in VISUAL_COLLECTIONS:
        for index, item in enumerate(evidence.get(collection, [])):
            prefix = f"/evidence/{collection}/{index}"
            if item["id"] in seen:
                errors.append(f"{prefix}/id: duplicate event ID")
            seen.add(item["id"])
            source, run = sources.get(item["source_id"]), runs.get(item["run_id"])
            if source is None or source["duration"] is None:
                errors.append(f"{prefix}: visual evidence requires a known source duration")
                continue
            if not compatible(item, run) or run["category"] != "object_tracking":
                errors.append(f"{prefix}/run_id: incompatible visual analyzer run")
            elif run["status"] in {"failed", "unavailable", "skipped"}:
                errors.append(f"{prefix}: unusable analyzer cannot supply evidence")
            start = item.get("time", item.get("start", item.get("first_seen")))
            end = item.get("time", item.get("end", item.get("last_seen")))
            if start < 0 or end > source["duration"] + 1e-6 or end < start:
                errors.append(f"{prefix}: invalid source-relative timing")
            if collection in {"tracking_intervals", "subject_candidates"} and end <= start:
                errors.append(f"{prefix}: interval end must exceed start")
            box_errors(item, prefix)
            group = (collection, item["source_id"], item["run_id"])
            if collection in {"tracking_intervals", "detections", "visual_regions", "crop_constraints"}:
                previous = ordered.get(group)
                if previous is not None and (start < previous[0] or
                                              collection == "tracking_intervals" and start < previous[1] - 1e-6):
                    errors.append(f"{prefix}: observations must be ordered; tracking intervals cannot overlap")
                ordered[group] = (start, end)
            if collection == "tracking_intervals":
                if item["scene_id"] is not None:
                    scene = scenes.get(item["scene_id"])
                    if (scene is None or scene["source_id"] != item["source_id"]
                            or item["start"] < scene["start"] - 1e-6 or item["end"] > scene["end"] + 1e-6):
                        errors.append(f"{prefix}/scene_id: incompatible supporting scene")
                continue
            interval = intervals.get(item["interval_id"])
            if (not compatible(item, interval) or start < interval["start"] - 1e-6
                    or end > interval["end"] + 1e-6):
                errors.append(f"{prefix}/interval_id: evidence must fit its tracking lifecycle")
            for key, table in (("entity_id", entities),):
                if key in item:
                    target = table.get(item[key])
                    if not compatible(item, target) or target["interval_id"] != item["interval_id"]:
                        errors.append(f"{prefix}/{key}: incompatible tracked entity")
            for key, table in (("entity_ids", entities), ("detection_ids", detections), ("region_ids", regions)):
                for reference in item.get(key, []):
                    target = table.get(reference)
                    if (not compatible(item, target) or target["interval_id"] != item["interval_id"]):
                        errors.append(f"{prefix}/{key}: incompatible evidence reference")
                    elif collection in {"visual_regions", "crop_constraints"} and "time" in target:
                        if abs(target["time"] - item["time"]) > 1e-6:
                            errors.append(f"{prefix}/{key}: region support must share the observation time")
            if collection == "detections":
                key = (item["run_id"], item["sample_index"])
                location = (item["interval_id"], item["time"], item["frame_index"])
                if key in samples and samples[key] != location:
                    errors.append(f"{prefix}: inconsistent sample timing")
                samples[key] = location
                if "entity_id" in item:
                    identity = (key, item["entity_id"])
                    if identity in person_at_sample:
                        errors.append(f"{prefix}: duplicate observation for one entity/sample")
                    person_at_sample.add(identity)
            elif collection == "tracked_entities":
                supported = [detections[ref] for ref in item["detection_ids"] if ref in detections]
                if len(supported) != item["observation_count"]:
                    errors.append(f"{prefix}/observation_count: must equal referenced observations")
                if supported:
                    if (supported[0]["time"] != item["first_seen"] or
                            supported[-1]["time"] != item["last_seen"]):
                        errors.append(f"{prefix}: entity lifetime must match observed endpoints")
                    if any(obs.get("entity_id") != item["id"] for obs in supported):
                        errors.append(f"{prefix}: detections must reference this entity")
                for gap in item["gaps"]:
                    if not item["first_seen"] <= gap["start"] < gap["end"] <= item["last_seen"]:
                        errors.append(f"{prefix}/gaps: gap must fit entity lifetime")
            elif collection == "subject_candidates":
                entity = entities.get(item["entity_id"])
                if entity is not None and entity["category"] != "person":
                    errors.append(f"{prefix}: athlete candidate must refer to a person")
            elif collection == "crop_constraints":
                if "box_coverage" in item and "proposed_crop" not in item:
                    errors.append(f"{prefix}: box coverage requires a proposed crop")
                if "minimum_visible_region" in item and not item["region_ids"]:
                    errors.append(f"{prefix}: minimum region requires supporting visual regions")
    return errors
