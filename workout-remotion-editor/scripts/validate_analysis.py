#!/usr/bin/env python3
"""Validate legacy editorial analysis and optional Phase 1 evidence."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).with_name("analysis-schema.json")
COLLECTIONS = ("segments", "repetitions", "audio_events")
EVIDENCE_COLLECTIONS = (
    "scenes",
    "scene_boundaries",
    "activity_regions",
    "candidate_dead_time",
)
OBJECT_COLLECTIONS = (
    "object_detections",
    "tracked_entities",
    "entity_roles",
    "visual_regions",
    "crop_constraints",
)
POSE_COLLECTIONS = (
    "pose_samples",
    "derived_joint_metrics",
    "movement_signals",
    "pose_crop_constraints",
)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON from {path}: {exc}") from exc


def valid_datetime(value: str) -> bool:
    normalized = value.upper()
    if (
        re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)",
            normalized,
        )
        is None
    ):
        return False
    try:
        return (
            datetime.fromisoformat(normalized.replace("Z", "+00:00")).tzinfo is not None
        )
    except ValueError:
        return False


def basic_schema_errors(document: Any, schema: Any = None) -> list[str]:
    """Dependency-free checks for the keywords used by the bundled schema.

    This is deliberately limited to our schema, not a general JSON Schema engine.
    jsonschema remains the recommended validator for arbitrary custom schemas.
    """
    root = load_json(SCHEMA_PATH) if schema is None else schema

    def check(value: Any, spec: dict[str, Any], path: str) -> list[str]:
        errors: list[str] = []
        if "$ref" in spec:
            target = root
            for part in spec["$ref"].removeprefix("#/").split("/"):
                target = target[part]
            errors.extend(check(value, target, path))
        for child in spec.get("allOf", []):
            errors.extend(check(value, child, path))
        if "if" in spec:
            branch = "then" if not check(value, spec["if"], path) else "else"
            errors.extend(check(value, spec.get(branch, {}), path))
        if "not" in spec and not check(value, spec["not"], path):
            errors.append(f"{path}: forbidden value/property")
        if "const" in spec and value != spec["const"]:
            errors.append(f"{path}: must equal {spec['const']!r}")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"{path}: invalid value {value!r}")
        types = spec.get("type", [])
        if isinstance(types, str):
            types = [types]
        number = isinstance(value, (int, float)) and not isinstance(value, bool)
        matches = {
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
            "string": isinstance(value, str),
            "number": number,
            "integer": number and (not math.isfinite(value) or int(value) == value),
            "boolean": isinstance(value, bool),
            "null": value is None,
        }
        if types and not any(matches.get(kind, False) for kind in types):
            return errors + [f"{path}: must have type {types}"]
        if isinstance(value, dict):
            for key in spec.get("required", []):
                if key not in value:
                    errors.append(f"{path}/{key}: required property is missing")
            props = spec.get("properties", {})
            for key, item in value.items():
                if key in props:
                    errors.extend(check(item, props[key], f"{path}/{key}"))
                elif spec.get("additionalProperties") is False:
                    errors.append(f"{path}/{key}: unexpected property")
        if isinstance(value, list):
            if len(value) < spec.get("minItems", 0):
                errors.append(f"{path}: too few items")
            if "maxItems" in spec and len(value) > spec["maxItems"]:
                errors.append(f"{path}: too many items")
            if spec.get("uniqueItems") and len(
                {json.dumps(x, sort_keys=True) for x in value}
            ) != len(value):
                errors.append(f"{path}: duplicate items")
            for index, item in enumerate(value):
                errors.extend(check(item, spec.get("items", {}), f"{path}/{index}"))
        if isinstance(value, str):
            if len(value) < spec.get("minLength", 0):
                errors.append(f"{path}: string is too short")
            if "pattern" in spec and re.search(spec["pattern"], value) is None:
                errors.append(f"{path}: invalid pattern")
            if spec.get("format") == "date-time" and not valid_datetime(value):
                errors.append(f"{path}: invalid date-time")
        if number:
            if "minimum" in spec and value < spec["minimum"]:
                errors.append(f"{path}: below minimum")
            if "exclusiveMinimum" in spec and value <= spec["exclusiveMinimum"]:
                errors.append(f"{path}: below exclusive minimum")
            if "maximum" in spec and value > spec["maximum"]:
                errors.append(f"{path}: above maximum")
        return errors

    return check(document, root, "")


def schema_errors(document: Any, schema: Any) -> list[str]:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        return basic_schema_errors(document, schema)
    formats = FormatChecker()

    @formats.checks("date-time")
    def datetime_format(value: Any) -> bool:
        return not isinstance(value, str) or valid_datetime(value)

    validator = Draft202012Validator(schema, format_checker=formats)
    return [
        f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
        for error in sorted(
            validator.iter_errors(document),
            key=lambda item: str(list(item.absolute_path)),
        )
    ]


def finite_errors(value: Any, path: str = "") -> list[str]:
    if isinstance(value, float) and not math.isfinite(value):
        return [f"{path}: numbers must be finite"]
    if isinstance(value, dict):
        return [
            error
            for key, item in value.items()
            for error in finite_errors(item, f"{path}/{key}")
        ]
    if isinstance(value, list):
        return [
            error
            for index, item in enumerate(value)
            for error in finite_errors(item, f"{path}/{index}")
        ]
    return []


def semantic_errors(document: dict[str, Any]) -> list[str]:
    """Called only after structural validation has succeeded."""
    errors = finite_errors(document)
    if errors:
        return errors
    sources = {source["id"]: source for source in document["sources"]}
    if len(sources) != len(document["sources"]):
        errors.append("/sources: source IDs must be unique")
    seen: set[str] = set()

    def unique(item: dict[str, Any], prefix: str) -> None:
        if item["id"] in seen:
            errors.append(f"{prefix}/id: duplicate event ID {item['id']!r}")
        seen.add(item["id"])

    def bounds(item: dict[str, Any], prefix: str, point: bool = False) -> None:
        source = sources.get(item["source_id"])
        if source is None:
            errors.append(f"{prefix}/source_id: unknown source")
            return
        duration = source["duration"]
        if duration is None:
            errors.append(f"{prefix}: timed evidence requires known source duration")
            return
        start, end = (
            (item["time"], item["time"]) if point else (item["start"], item["end"])
        )
        if not point and end <= start:
            errors.append(f"{prefix}: end must be greater than start")
        if start < 0 or end > duration + 1e-6:
            errors.append(
                f"{prefix}: range {start:g}–{end:g}s exceeds source duration {duration:g}s"
            )

    segments = {item["id"]: item for item in document["segments"]}
    for collection in COLLECTIONS:
        for index, event in enumerate(document.get(collection, [])):
            prefix = f"/{collection}/{index}"
            unique(event, prefix)
            bounds(event, prefix)
            if collection == "repetitions" and event.get("segment_id") is not None:
                if event["segment_id"] not in segments:
                    errors.append(f"{prefix}/segment_id: unknown segment")
                elif segments[event["segment_id"]]["source_id"] != event["source_id"]:
                    errors.append(
                        f"{prefix}/segment_id: segment belongs to another source"
                    )

    evidence = document.get("evidence", {})
    runs = {run["id"]: run for run in evidence.get("runs", [])}
    if len(runs) != len(evidence.get("runs", [])):
        errors.append("/evidence/runs: run IDs must be unique")
    for index, run in enumerate(evidence.get("runs", [])):
        prefix = f"/evidence/runs/{index}"
        if run["source_id"] not in sources:
            errors.append(f"{prefix}/source_id: unknown source")
        if (
            run["status"] in {"unavailable", "failed", "skipped"}
            and not run["fallback"]
        ):
            errors.append(f"{prefix}: unusable analyzer must advertise fallback")
        if run["status"] == "failed" and not run["errors"]:
            errors.append(f"{prefix}: failed analyzer must explain the error")
    for index, source in enumerate(document["sources"]):
        if "probe_run_id" in source:
            run = runs.get(source["probe_run_id"])
            if (
                run is None
                or run["category"] != "media_probe"
                or run["source_id"] != source["id"]
            ):
                errors.append(
                    f"/sources/{index}/probe_run_id: invalid media probe reference"
                )

    # User assertions are deliberately separate from analyzer evidence.
    context = document.get("context")
    taxonomy_ids: set[str] = set()
    taxonomy_version = None
    if context is not None:
        from analyzers.exercise_recognition import Taxonomy

        metadata = document.get("taxonomy")
        if metadata:
            taxonomy_ids, taxonomy_version = (
                set(metadata["canonical_ids"]),
                metadata["version"],
            )
        else:
            taxonomy = Taxonomy.load()
            taxonomy_ids, taxonomy_version = set(taxonomy.entries), taxonomy.version
        if context["taxonomy_version"] != taxonomy_version:
            errors.append("/context/taxonomy_version: unsupported taxonomy version")
        assertion_ids: set[str] = set()
        for index, assertion in enumerate(context["assertions"]):
            prefix = f"/context/assertions/{index}"
            if assertion["id"] in assertion_ids:
                errors.append(f"{prefix}/id: duplicate context assertion ID")
            assertion_ids.add(assertion["id"])
            if assertion["source_id"] not in sources:
                errors.append(f"{prefix}/source_id: unknown source")
            if assertion.get("canonical_exercise_id") not in taxonomy_ids | {None}:
                errors.append(f"{prefix}/canonical_exercise_id: invalid taxonomy ID")
            if assertion.get("mapping_status") == "mapped" and not assertion.get(
                "canonical_exercise_id"
            ):
                errors.append(f"{prefix}: mapped alias requires canonical ID")
            if assertion.get("mapping_status") in {
                "ambiguous",
                "unmapped",
            } and assertion.get("canonical_exercise_id"):
                errors.append(
                    f"{prefix}: ambiguous/unmapped alias cannot claim canonical ID"
                )
            if (assertion.get("start") is None) != (assertion.get("end") is None):
                errors.append(f"{prefix}: interval context requires both start and end")
            if assertion.get("start") is not None:
                bounds(assertion, prefix)
            scene_id = assertion.get("scene_id")
            if scene_id is not None:
                scene = next(
                    (
                        item
                        for item in evidence.get("scenes", [])
                        if item["id"] == scene_id
                    ),
                    None,
                )
                if scene is None or scene["source_id"] != assertion["source_id"]:
                    errors.append(f"{prefix}/scene_id: unknown or cross-source scene")
                elif assertion.get("start") is not None and (
                    assertion["start"] < scene["start"] - 1e-6
                    or assertion["end"] > scene["end"] + 1e-6
                ):
                    errors.append(f"{prefix}: assertion exceeds scene bounds")
            entity_id = assertion.get("entity_id")
            if entity_id is not None:
                entity = next(
                    (
                        item
                        for item in evidence.get("tracked_entities", [])
                        if item["id"] == entity_id
                    ),
                    None,
                )
                if entity is None or entity["source_id"] != assertion["source_id"]:
                    errors.append(f"{prefix}/entity_id: unknown or cross-source entity")
                elif assertion.get("start") is not None and (
                    assertion["end"] <= entity["start"]
                    or assertion["start"] >= entity["end"]
                ):
                    errors.append(f"{prefix}: assertion does not overlap entity")
            if assertion.get("mapping_status") is not None and metadata is not None:
                from analyzers.exercise_recognition import Taxonomy, normalize_alias

                bundled = Taxonomy.load()
                if (
                    set(metadata["canonical_ids"]) == set(bundled.entries)
                    and metadata["version"] == bundled.version
                ):
                    mapped = bundled.map_label(assertion["supplied_label"])
                    if (
                        assertion.get("normalized_label")
                        != normalize_alias(assertion["supplied_label"])
                        or assertion["mapping_status"] != mapped["status"]
                        or assertion.get("canonical_exercise_id")
                        != mapped["canonical_exercise_id"]
                        or assertion.get("mapping_candidates", [])
                        != mapped["candidate_ids"]
                    ):
                        errors.append(
                            f"{prefix}: alias mapping provenance is inconsistent"
                        )
        for index, item in enumerate(context["ordered_plan"]):
            if item["canonical_exercise_id"] not in taxonomy_ids:
                errors.append(f"/context/ordered_plan/{index}: invalid taxonomy ID")

    activity = {item["id"]: item for item in evidence.get("activity_regions", [])}
    ordered: dict[tuple[str, str, str, str, int], tuple[float, float]] = {}
    for collection in EVIDENCE_COLLECTIONS:
        for index, item in enumerate(evidence.get(collection, [])):
            prefix = f"/evidence/{collection}/{index}"
            unique(item, prefix)
            point = collection == "scene_boundaries"
            bounds(item, prefix, point)
            run = runs.get(item["run_id"])
            expected = (
                "scene"
                if collection in {"scenes", "scene_boundaries"}
                else "motion_activity"
            )
            if (
                run is None
                or run["source_id"] != item["source_id"]
                or run["category"] != expected
            ):
                errors.append(f"{prefix}/run_id: incompatible analyzer run")
            elif run["status"] in {"unavailable", "failed", "skipped"}:
                errors.append(f"{prefix}: unusable analyzer cannot supply evidence")
            start = item["time"] if point else item["start"]
            end = start if point else item["end"]
            signal_family = item.get("type", "")
            if collection == "activity_regions":
                signal_family = (
                    "motion"
                    if signal_family in {"low_motion", "motion_active"}
                    else "audio"
                )
            group = (
                collection,
                item["source_id"],
                item["run_id"],
                signal_family,
                item.get("stream", 0),
            )
            previous = ordered.get(group)
            if previous is not None:
                if start < previous[0]:
                    errors.append(
                        f"{prefix}: regions must be ordered by source time within each signal"
                    )
                if collection == "scenes" and start < previous[1] - 1e-6:
                    errors.append(
                        f"{prefix}: scenes from one detector must not overlap"
                    )
            ordered[group] = (start, end)
            if collection == "candidate_dead_time":
                has_low_motion = False
                for signal_id in item["signal_ids"]:
                    signal = activity.get(signal_id)
                    if signal is None:
                        errors.append(f"{prefix}/signal_ids: unknown activity signal")
                    elif (
                        signal["source_id"] != item["source_id"]
                        or signal["run_id"] != item["run_id"]
                        or signal["type"] not in {"low_motion", "audio_inactive"}
                        or signal["start"] > start + 1e-6
                        or signal["end"] < end - 1e-6
                    ):
                        errors.append(
                            f"{prefix}/signal_ids: signal must support this candidate range"
                        )
                    elif signal["type"] == "low_motion":
                        has_low_motion = True
                if not has_low_motion:
                    errors.append(
                        f"{prefix}/signal_ids: candidate requires covering low-motion support"
                    )

    detections = {item["id"]: item for item in evidence.get("object_detections", [])}
    entities = {item["id"]: item for item in evidence.get("tracked_entities", [])}
    regions_by_id = {item["id"]: item for item in evidence.get("visual_regions", [])}
    last_detection_time: dict[tuple[str, str, str], float] = {}
    for collection in OBJECT_COLLECTIONS:
        for index, item in enumerate(evidence.get(collection, [])):
            prefix = f"/evidence/{collection}/{index}"
            unique(item, prefix)
            source = sources.get(item["source_id"])
            run = runs.get(item["run_id"])
            if (
                run is None
                or run["source_id"] != item["source_id"]
                or run["category"] != "object_tracking"
            ):
                errors.append(f"{prefix}/run_id: incompatible object-tracking run")
            elif run["status"] in {"unavailable", "failed", "skipped"}:
                errors.append(f"{prefix}: unusable analyzer cannot supply evidence")
            if source is None:
                errors.append(f"{prefix}/source_id: unknown source")
            if "bounding_box" in item:
                x1, y1, x2, y2 = item["bounding_box"]
                if x2 <= x1 or y2 <= y1:
                    errors.append(
                        f"{prefix}/bounding_box: normalized xyxy bounds must have positive area"
                    )
            if collection == "object_detections":
                if source is not None and (
                    source["duration"] is None
                    or item["timestamp"] > source["duration"] + 1e-6
                ):
                    errors.append(f"{prefix}/timestamp: exceeds source duration")
                if (
                    item.get("entity_id") is not None
                    and item["entity_id"] not in entities
                ):
                    errors.append(f"{prefix}/entity_id: unknown tracked entity")
                elif item.get("entity_id") is not None:
                    entity = entities[item["entity_id"]]
                    if (
                        entity["source_id"],
                        entity["run_id"],
                        entity["scene_id"],
                        entity["track_id"],
                    ) != (
                        item["source_id"],
                        item["run_id"],
                        item["scene_id"],
                        item["track_id"],
                    ):
                        errors.append(
                            f"{prefix}/entity_id: detection and entity provenance disagree"
                        )
                    if (
                        not entity["start"] - 1e-6
                        <= item["timestamp"]
                        <= entity["end"] + 1e-6
                    ):
                        errors.append(
                            f"{prefix}/timestamp: outside tracked entity range"
                        )
                order_key = (item["source_id"], item["run_id"], item["scene_id"])
                if item["timestamp"] < last_detection_time.get(order_key, -1):
                    errors.append(
                        f"{prefix}: detections must be ordered by source time within a scene"
                    )
                last_detection_time[order_key] = item["timestamp"]
            elif collection == "tracked_entities":
                if item["end"] < item["start"]:
                    errors.append(f"{prefix}: entity end precedes start")
                if source is not None and (
                    source["duration"] is None
                    or item["end"] > source["duration"] + 1e-6
                ):
                    errors.append(f"{prefix}: entity range exceeds source duration")
                for ref in item["detection_ids"]:
                    detection = detections.get(ref)
                    if detection is None or detection.get("entity_id") != item["id"]:
                        errors.append(
                            f"{prefix}/detection_ids: invalid entity detection reference"
                        )
            elif collection == "entity_roles":
                entity = entities.get(item["entity_id"])
                if entity is None:
                    errors.append(f"{prefix}/entity_id: unknown tracked entity")
                elif (entity["source_id"], entity["run_id"], entity["scene_id"]) != (
                    item["source_id"],
                    item["run_id"],
                    item["scene_id"],
                ):
                    errors.append(
                        f"{prefix}/entity_id: role and entity provenance disagree"
                    )
            elif collection == "visual_regions":
                if item["end"] < item["start"]:
                    errors.append(f"{prefix}: region end precedes start")
                for ref in item["entity_ids"]:
                    entity = entities.get(ref)
                    if entity is None:
                        errors.append(f"{prefix}/entity_ids: unknown tracked entity")
                    elif (entity["source_id"], entity["run_id"]) != (
                        item["source_id"],
                        item["run_id"],
                    ):
                        errors.append(
                            f"{prefix}/entity_ids: region and entity provenance disagree"
                        )
            elif collection == "crop_constraints":
                entity = entities.get(item["entity_id"])
                if entity is None:
                    errors.append(f"{prefix}/entity_id: unknown tracked entity")
                region = regions_by_id.get(item["region_id"])
                if region is None or item["entity_id"] not in region["entity_ids"]:
                    errors.append(
                        f"{prefix}/region_id: invalid visual-region reference"
                    )
                elif (region["source_id"], region["run_id"]) != (
                    item["source_id"],
                    item["run_id"],
                ):
                    errors.append(
                        f"{prefix}/region_id: constraint and region provenance disagree"
                    )

    pose_samples = {item["id"]: item for item in evidence.get("pose_samples", [])}
    scenes_by_source: dict[str, list[dict[str, Any]]] = {}
    for scene in evidence.get("scenes", []):
        scenes_by_source.setdefault(scene["source_id"], []).append(scene)
    for scenes in scenes_by_source.values():
        scenes.sort(key=lambda scene: scene["start"])
    last_pose_time: dict[tuple[str, str, str, str], float] = {}
    associated_pose_slots: set[tuple[str, str, float]] = set()
    for collection in POSE_COLLECTIONS:
        for index, item in enumerate(evidence.get(collection, [])):
            prefix = f"/evidence/{collection}/{index}"
            unique(item, prefix)
            run = runs.get(item["run_id"])
            if (
                run is None
                or run["source_id"] != item["source_id"]
                or run["category"] != "pose"
            ):
                errors.append(f"{prefix}/run_id: incompatible pose run")
            elif run["status"] not in {"success", "partial"}:
                errors.append(f"{prefix}: unusable pose run cannot supply evidence")
            source = sources.get(item["source_id"])
            if (
                source is None
                or source["duration"] is None
                or item["timestamp"] > source["duration"] + 1e-6
            ):
                errors.append(f"{prefix}/timestamp: outside source duration")
            source_scenes = scenes_by_source.get(item["source_id"], [])
            match = re.fullmatch(r"scene-(\d+)", item["scene_id"])
            if source_scenes and (
                match is None or int(match.group(1)) >= len(source_scenes)
            ):
                errors.append(f"{prefix}/scene_id: unknown source scene")
            elif source_scenes:
                scene = source_scenes[int(match.group(1))]
                if (
                    not scene["start"] - 1e-6
                    <= item["timestamp"]
                    <= scene["end"] + 1e-6
                ):
                    errors.append(f"{prefix}/scene_id: timestamp outside scene bounds")
            pose = (
                item
                if collection == "pose_samples"
                else pose_samples.get(item["pose_sample_id"])
            )
            if collection != "pose_samples" and pose is None:
                errors.append(
                    f"{prefix}/pose_sample_id: unknown supporting pose sample"
                )
            elif pose is not None and (
                pose["source_id"],
                pose["run_id"],
                pose["scene_id"],
                pose["timestamp"],
            ) != (
                item["source_id"],
                item["run_id"],
                item["scene_id"],
                item["timestamp"],
            ):
                errors.append(
                    f"{prefix}/pose_sample_id: supporting pose provenance disagrees"
                )
            elif (
                collection != "pose_samples"
                and pose is not None
                and pose.get("entity_id") != item.get("entity_id")
            ):
                errors.append(
                    f"{prefix}/pose_sample_id: supporting pose entity disagrees"
                )
            entity_id = item.get("entity_id")
            if entity_id is not None:
                entity = entities.get(entity_id)
                if entity is None:
                    errors.append(f"{prefix}/entity_id: unknown tracked entity")
                else:
                    entity_run = runs.get(entity["run_id"])
                    if (
                        entity["source_id"] != item["source_id"]
                        or entity["scene_id"] != item["scene_id"]
                        or entity["category"] != "person"
                    ):
                        errors.append(
                            f"{prefix}/entity_id: incompatible source, scene, or entity category"
                        )
                    if (
                        not entity["start"] - 1e-6
                        <= item["timestamp"]
                        <= entity["end"] + 1e-6
                    ):
                        errors.append(
                            f"{prefix}/entity_id: timestamp outside tracked entity range"
                        )
                    if entity_run is None or entity_run["status"] not in {
                        "success",
                        "partial",
                    }:
                        errors.append(
                            f"{prefix}/entity_id: incompatible analyzer run status"
                        )
            if collection == "pose_samples":
                if source is not None and (
                    item["source_width"] != source.get("width")
                    or item["source_height"] != source.get("height")
                ):
                    errors.append(f"{prefix}: pose dimensions disagree with source")
                names: set[str] = set()
                for point_index, point in enumerate(item["keypoints"]):
                    if point["name"] in names:
                        errors.append(
                            f"{prefix}/keypoints/{point_index}/name: duplicate joint"
                        )
                    names.add(point["name"])
                    has_xy = "x" in point and "y" in point
                    if point["state"] == "missing" and has_xy:
                        errors.append(
                            f"{prefix}/keypoints/{point_index}: missing joint cannot have coordinates"
                        )
                    if point["state"] == "missing" and point["confidence"] != 0:
                        errors.append(
                            f"{prefix}/keypoints/{point_index}: missing joint confidence must be zero"
                        )
                    if point["state"] != "missing" and not has_xy:
                        errors.append(
                            f"{prefix}/keypoints/{point_index}: measured joint requires x and y"
                        )
                    if (
                        point["state"] in {"visible", "low_confidence", "interpolated"}
                        and has_xy
                        and not (0 <= point["x"] <= 1 and 0 <= point["y"] <= 1)
                    ):
                        errors.append(
                            f"{prefix}/keypoints/{point_index}: displayed coordinates must be in [0,1]"
                        )
                if item["association_ambiguous"] and entity_id is not None:
                    errors.append(f"{prefix}: ambiguous pose must remain unassociated")
                slot = (item["scene_id"], entity_id, item["timestamp"])
                if entity_id is not None and item["input_variant"] == "raw":
                    if slot in associated_pose_slots:
                        errors.append(
                            f"{prefix}/entity_id: entity already has raw pose at this timestamp"
                        )
                    associated_pose_slots.add(slot)
                detection_id = item.get("detection_id")
                if detection_id is not None:
                    detection = detections.get(detection_id)
                    if detection is None:
                        errors.append(
                            f"{prefix}/detection_id: unknown originating detection"
                        )
                    elif (
                        detection.get("entity_id"),
                        detection["source_id"],
                        detection["scene_id"],
                        detection["timestamp"],
                    ) != (
                        entity_id,
                        item["source_id"],
                        item["scene_id"],
                        item["timestamp"],
                    ):
                        errors.append(
                            f"{prefix}/detection_id: detection association provenance disagrees"
                        )
                raw_id = item.get("raw_pose_sample_id")
                if raw_id is not None:
                    raw = pose_samples.get(raw_id)
                    if (
                        raw is None
                        or raw["source_id"] != item["source_id"]
                        or raw["run_id"] != item["run_id"]
                        or raw["scene_id"] != item["scene_id"]
                        or raw["timestamp"] != item["timestamp"]
                        or raw.get("entity_id") != entity_id
                        or raw["input_variant"] != "raw"
                    ):
                        errors.append(
                            f"{prefix}/raw_pose_sample_id: invalid cross-scene smoothing reference"
                        )
                key = (
                    item["source_id"],
                    item["run_id"],
                    item["scene_id"],
                    (entity_id or item["id"]) + ":" + item["input_variant"],
                )
                if item["timestamp"] < last_pose_time.get(key, -1):
                    errors.append(f"{prefix}: pose trajectory must be ordered")
                last_pose_time[key] = item["timestamp"]

    all_evidence_ids = {
        item["id"]
        for name, values in evidence.items()
        if name != "runs"
        for item in values
        if isinstance(item, dict) and "id" in item
    }
    all_context_refs = {
        f"context:{item['id']}" for item in (context or {}).get("assertions", [])
    }
    all_context_refs.update(
        f"plan:{item['order']}" for item in (context or {}).get("ordered_plan", [])
    )
    rank_groups: dict[tuple[Any, ...], list[tuple[int, float, str]]] = {}
    for collection in ("interval_candidates", "exercise_candidates"):
        for index, item in enumerate(evidence.get(collection, [])):
            prefix = f"/evidence/{collection}/{index}"
            unique(item, prefix)
            bounds(item, prefix)
            run = runs.get(item["run_id"])
            allowed = (
                {"context_fusion"}
                if collection == "interval_candidates"
                else {"context_fusion", "action_recognition"}
            )
            if (
                run is None
                or run["source_id"] != item["source_id"]
                or run["category"] not in allowed
            ):
                errors.append(f"{prefix}/run_id: incompatible exercise run")
            elif run["status"] not in {"success", "partial"}:
                errors.append(
                    f"{prefix}: unusable run cannot supply candidate evidence"
                )
            scene_id = item.get("scene_id")
            if scene_id is not None:
                scene = next(
                    (x for x in evidence.get("scenes", []) if x["id"] == scene_id), None
                )
                if scene is None or scene["source_id"] != item["source_id"]:
                    errors.append(f"{prefix}/scene_id: unknown source scene")
                elif (
                    item["start"] < scene["start"] - 1e-6
                    or item["end"] > scene["end"] + 1e-6
                ):
                    errors.append(f"{prefix}: candidate crosses scene bounds")
            entity_id = item.get("entity_id")
            if entity_id is not None:
                entity = entities.get(entity_id)
                if entity is None or entity["source_id"] != item["source_id"]:
                    errors.append(f"{prefix}/entity_id: incompatible entity")
                elif item["end"] <= entity["start"] or item["start"] >= entity["end"]:
                    errors.append(
                        f"{prefix}/entity_id: candidate does not overlap entity"
                    )
                elif (
                    collection == "exercise_candidates"
                    and item["source_type"] in {"action_model", "context_heuristic"}
                    and entity["category"] != "person"
                ):
                    errors.append(
                        f"{prefix}/entity_id: machine candidate requires person entity"
                    )
            for ref in item["supporting_evidence_refs"] + item.get(
                "conflicting_evidence_refs", []
            ):
                if ref not in all_evidence_ids | all_context_refs:
                    errors.append(
                        f"{prefix}: unknown support/conflict evidence reference"
                    )
                    continue
                referenced = next(
                    (
                        value
                        for name, values in evidence.items()
                        if name != "runs"
                        for value in values
                        if isinstance(value, dict) and value.get("id") == ref
                    ),
                    None,
                )
                if referenced is not None:
                    if referenced.get("source_id") != item["source_id"]:
                        errors.append(
                            f"{prefix}: evidence reference belongs to another source"
                        )
                    if (
                        referenced.get("entity_id") is not None
                        and item.get("entity_id") is not None
                        and referenced["entity_id"] != item["entity_id"]
                    ):
                        errors.append(
                            f"{prefix}: evidence reference belongs to another entity"
                        )
                    timestamp = referenced.get("timestamp")
                    if (
                        timestamp is not None
                        and not item["start"] - 1e-6 <= timestamp <= item["end"] + 1e-6
                    ):
                        errors.append(
                            f"{prefix}: evidence timestamp is outside candidate interval"
                        )
            if collection == "exercise_candidates":
                if item["taxonomy_version"] != taxonomy_version or item.get(
                    "canonical_exercise_id"
                ) not in taxonomy_ids | {None}:
                    errors.append(f"{prefix}: invalid taxonomy version or canonical ID")
                if item["source_type"] == "action_model" and (
                    not item.get("model") or not item.get("provider")
                ):
                    errors.append(
                        f"{prefix}: action-model candidate requires provider and model"
                    )
                if (
                    item["source_type"] == "user_provided"
                    and item.get("model") is not None
                ):
                    errors.append(
                        f"{prefix}: user-provided candidate cannot claim a model"
                    )
                if (
                    item["conflict_status"] == "none"
                    and item["conflicting_evidence_refs"]
                ):
                    errors.append(
                        f"{prefix}: conflict status disagrees with conflict references"
                    )
                group = (
                    item["run_id"],
                    item["source_id"],
                    item.get("scene_id"),
                    item.get("entity_id"),
                    item["start"],
                    item["end"],
                )
                rank_groups.setdefault(group, []).append(
                    (item["rank"], item["confidence"], prefix)
                )
    for values in rank_groups.values():
        ordered_values = sorted(values)
        ranks = [value[0] for value in ordered_values]
        if len(ranks) != len(set(ranks)):
            errors.append(f"{ordered_values[0][2]}: duplicate rank in candidate group")
        if any(a[1] < b[1] for a, b in zip(ordered_values, ordered_values[1:])):
            errors.append(
                f"{ordered_values[0][2]}: rank ordering must follow descending score"
            )

    exercise_by_id = {x["id"]: x for x in evidence.get("exercise_candidates", [])}
    rep_intervals = {x["id"]: x for x in evidence.get("rep_analysis_intervals", [])}
    for index, item in enumerate(evidence.get("rep_analysis_intervals", [])):
        prefix = f"/evidence/rep_analysis_intervals/{index}"
        unique(item, prefix)
        bounds(item, prefix)
        run = runs.get(item["run_id"])
        candidate = exercise_by_id.get(item["exercise_candidate_id"])
        if (
            run is None
            or run["category"] != "repetition_analysis"
            or run["source_id"] != item["source_id"]
            or run["status"] not in {"success", "partial"}
        ):
            errors.append(
                f"{prefix}/run_id: incompatible or unusable repetition analyzer run"
            )
        if candidate is None or any(
            candidate.get(k) != item.get(k)
            for k in ("source_id", "scene_id", "entity_id", "canonical_exercise_id")
        ):
            errors.append(
                f"{prefix}/exercise_candidate_id: incompatible candidate provenance"
            )
        entity = entities.get(item.get("entity_id"))
        if item["eligible"] and (
            entity is None
            or entity.get("category") != "person"
            or entity.get("source_id") != item["source_id"]
        ):
            errors.append(
                f"{prefix}/entity_id: repetition analysis requires a same-source person"
            )
        if (item.get("canonical_exercise_id"), item.get("rep_rule_id")) != (
            "dumbbell_row_single_arm",
            "single_arm_dumbbell_row_v1",
        ):
            # Ineligible attempts for other exercises may have no rule, but can never claim an incompatible active rule.
            if item.get("rep_rule_id") is not None or item["eligible"]:
                errors.append(f"{prefix}: incompatible exercise/rule mapping")
        failed = [g["reason"] for g in item["gate_results"] if not g["passed"]]
        if item["eligible"] == bool(failed) or failed != item["ineligibility_reasons"]:
            errors.append(f"{prefix}: eligibility and ordered gate results disagree")

    completed_groups: dict[tuple[Any, ...], list[tuple[float, float, str]]] = {}
    phase_order = (
        "initial_bottom_confirmation",
        "pull_departure",
        "top_entry",
        "top_confirmation",
        "return_departure",
        "bottom_reentry",
        "final_completion_confirmation",
    )
    for index, item in enumerate(evidence.get("rep_candidates", [])):
        prefix = f"/evidence/rep_candidates/{index}"
        unique(item, prefix)
        bounds(item, prefix)
        interval = rep_intervals.get(item["rep_analysis_interval_id"])
        candidate = exercise_by_id.get(item["exercise_candidate_id"])
        run = runs.get(item["run_id"])
        if (
            interval is None
            or not interval["eligible"]
            or any(
                interval.get(k) != item.get(k)
                for k in (
                    "source_id",
                    "scene_id",
                    "entity_id",
                    "exercise_candidate_id",
                    "canonical_exercise_id",
                    "rep_rule_id",
                    "rep_rule_version",
                )
            )
            or interval.get("side") != item["working_side"]
        ):
            errors.append(
                f"{prefix}/rep_analysis_interval_id: incompatible interval provenance or side"
            )
        if (
            run is None
            or run["category"] != "repetition_analysis"
            or run["source_id"] != item["source_id"]
        ):
            errors.append(f"{prefix}/run_id: incompatible repetition run")
        if (
            candidate is None
            or candidate.get("canonical_exercise_id") != item["canonical_exercise_id"]
        ):
            errors.append(
                f"{prefix}/exercise_candidate_id: incompatible exercise candidate"
            )
        if (item["canonical_exercise_id"], item["rep_rule_id"]) != (
            "dumbbell_row_single_arm",
            "single_arm_dumbbell_row_v1",
        ):
            errors.append(f"{prefix}: wrong rule/exercise mapping")
        values = [
            item["phases"][name] for name in phase_order if name in item["phases"]
        ]
        interval_start = interval["start"] if interval is not None else item["start"]
        if values != sorted(values) or any(
            t < interval_start - 1e-6 or t > item["end"] + 1e-6 for t in values
        ):
            errors.append(
                f"{prefix}/phases: phases must be source-time ordered and inside the candidate"
            )
        if item["status"] == "completed" and any(
            name not in item["phases"] for name in phase_order
        ):
            errors.append(
                f"{prefix}/phases: completed candidate requires every mandatory phase"
            )
        if item["status"] == "uncertain" and not item["uncertainty_reasons"]:
            errors.append(
                f"{prefix}/uncertainty_reasons: uncertain candidate requires a reason"
            )
        if item["status"] == "incomplete" and not item["incompletion_reason"]:
            errors.append(
                f"{prefix}/incompletion_reason: incomplete candidate requires a reason"
            )
        for ref in item["supporting_evidence_refs"]:
            supporting = pose_samples.get(ref)
            if (
                supporting is None
                or supporting.get("source_id") != item["source_id"]
                or supporting.get("entity_id") != item["entity_id"]
                or supporting.get("scene_id") != item["scene_id"]
                or not item["start"] - 1e-6
                <= supporting.get("timestamp", -1)
                <= item["end"] + 1e-6
            ):
                errors.append(
                    f"{prefix}/supporting_evidence_refs: invalid cross-source/entity/scene/time reference"
                )
        if item["status"] == "completed":
            key = tuple(
                item[x]
                for x in (
                    "source_id",
                    "scene_id",
                    "entity_id",
                    "canonical_exercise_id",
                    "rep_rule_id",
                    "working_side",
                )
            )
            completed_groups.setdefault(key, []).append(
                (item["start"], item["end"], prefix)
            )
    for group in completed_groups.values():
        group.sort()
        for previous, current in zip(group, group[1:]):
            overlap = previous[1] - current[0]
            tolerance = min(
                0.10, 0.1 * min(previous[1] - previous[0], current[1] - current[0])
            )
            if overlap > tolerance + 1e-6:
                errors.append(f"{current[2]}: completed candidates materially overlap")

    plan = document.get("retention_plan", {})
    beat_ids: set[str] = set()
    for index, beat in enumerate(plan.get("beats", [])):
        prefix = f"/retention_plan/beats/{index}"
        if beat["id"] in beat_ids:
            errors.append(f"{prefix}/id: duplicate beat ID")
        beat_ids.add(beat["id"])
        if beat["timeline_end"] <= beat["timeline_start"]:
            errors.append(f"{prefix}: timeline_end must be greater than timeline_start")
    if (
        plan.get("payoff_beat_id") is not None
        and plan["payoff_beat_id"] not in beat_ids
    ):
        errors.append("/retention_plan/payoff_beat_id: unknown retention beat")
    for index, issue in enumerate(document.get("issues", [])):
        if issue.get("source_id") is not None and issue["source_id"] not in sources:
            errors.append(f"/issues/{index}/source_id: unknown source")
    return errors


def validate_document(
    document: Any, schema: Any = None, *, basic: bool = False
) -> list[str]:
    bundled = load_json(SCHEMA_PATH)
    schema = bundled if schema is None else schema
    errors = (
        basic_schema_errors(document, schema)
        if basic
        else schema_errors(document, schema)
    )
    errors.extend(finite_errors(document))
    if not errors and schema == bundled and isinstance(document, dict):
        errors.extend(semantic_errors(document))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path, help="analysis JSON to validate")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH, help="schema path")
    args = parser.parse_args()
    try:
        errors = validate_document(load_json(args.analysis), load_json(args.schema))
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Validation passed: {args.analysis}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
