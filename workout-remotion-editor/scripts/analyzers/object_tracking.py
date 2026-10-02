"""Optional local Ultralytics YOLO detection/tracking evidence provider.

This module deliberately stops at visual evidence.  It does not recognize exercises,
count repetitions, infer joints, or choose an editorial crop.
"""
from __future__ import annotations

import importlib
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from analyzers.base import Result, Unavailable


SUPPORTED_EQUIPMENT = {"sports ball", "baseball bat", "tennis racket", "skateboard", "surfboard"}
UNSUPPORTED_GYM_EQUIPMENT = {"dumbbell", "barbell", "kettlebell", "weight plate", "cable handle", "gym machine"}


def _box(values: Iterable[Any], width: int, height: int) -> list[float]:
    raw = [float(value) for value in values]
    if len(raw) != 4 or not all(math.isfinite(value) for value in raw):
        raise ValueError("YOLO bounding box must contain four finite values")
    x1, y1, x2, y2 = raw
    if width <= 0 or height <= 0 or x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
        raise ValueError("YOLO returned an invalid bounding box")
    clipped = [round(max(0.0, min(1.0, x1 / width)), 6),
            round(max(0.0, min(1.0, y1 / height)), 6),
            round(max(0.0, min(1.0, x2 / width)), 6),
            round(max(0.0, min(1.0, y2 / height)), 6)]
    if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
        raise ValueError("YOLO bounding box is outside the source frame")
    return clipped


def normalize_samples(samples: list[dict[str, Any]], source: dict[str, Any], provider: str,
                      model: str) -> dict[str, list[dict[str, Any]]]:
    """Turn backend-neutral samples into analyzer-agnostic evidence collections."""
    detections: list[dict[str, Any]] = []
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    width, height = int(source["width"]), int(source["height"])
    previous_timestamp = -1.0
    for sample_index, sample in enumerate(samples):
        timestamp, scene = float(sample["timestamp"]), int(sample.get("scene", 0))
        if (not math.isfinite(timestamp) or timestamp < previous_timestamp or timestamp < 0
                or timestamp > float(source["duration"]) + 1e-6):
            raise ValueError("YOLO samples must use ordered source-relative timestamps")
        previous_timestamp = timestamp
        for detection_index, raw in enumerate(sample.get("detections", [])):
            confidence = float(raw["confidence"])
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError("YOLO confidence must be between zero and one")
            label = str(raw["category"])
            track_id = raw.get("track_id")
            if track_id is None:
                # Untracked observations remain detections, but are not invented as entities.
                entity_id = None
            else:
                track_id = str(track_id)
                entity_id = f"scene-{scene}:track-{track_id}"
            item = {
                "id": f"detection-{sample_index}-{detection_index}", "timestamp": timestamp,
                "category": label, "confidence": confidence,
                "bounding_box": _box(raw["bounding_box"], width, height),
                "coordinate_space": "normalized_xyxy", "source_width": width,
                "source_height": height, "provider": provider, "model": model,
                "sample_index": sample_index, "scene_id": f"scene-{scene}",
            }
            if track_id is not None:
                item.update(track_id=track_id, entity_id=entity_id)
                grouped[(scene, track_id)].append(item)
            detections.append(item)

    entities: list[dict[str, Any]] = []
    for (scene, track_id), items in grouped.items():
        items.sort(key=lambda item: item["timestamp"])
        category = max({item["category"] for item in items}, key=lambda value: sum(
            item["confidence"] for item in items if item["category"] == value))
        entities.append({
            "id": f"scene-{scene}:track-{track_id}", "category": category,
            "provider": provider, "track_id": track_id, "scene_id": f"scene-{scene}",
            "start": items[0]["timestamp"], "end": items[-1]["timestamp"],
            "confidence": round(sum(item["confidence"] for item in items) / len(items), 6),
            "detection_ids": [item["id"] for item in items],
        })
    return {"object_detections": detections, "tracked_entities": entities}


def derive_visual_evidence(evidence: dict[str, list[dict[str, Any]]], sample_rate: float
                           ) -> dict[str, list[dict[str, Any]]]:
    """Rank scene-local person tracks and emit advisory framing evidence."""
    detections = evidence["object_detections"]
    by_entity = {entity["id"]: [item for item in detections
                                if item.get("entity_id") == entity["id"]]
                 for entity in evidence["tracked_entities"]}
    roles, regions, constraints = [], [], []
    scene_times: dict[str, set[float]] = defaultdict(set)
    for item in detections:
        scene_times[item["scene_id"]].add(item["timestamp"])
    by_scene: dict[str, list[tuple[dict[str, Any], float, list[str]]]] = defaultdict(list)
    for entity in evidence["tracked_entities"]:
        if entity["category"] != "person":
            continue
        items = by_entity[entity["id"]]
        span = max(1 / sample_rate, entity["end"] - entity["start"] + 1 / sample_rate)
        expected = max(1, len(scene_times[entity["scene_id"]]))
        persistence = min(1.0, len(items) / expected)
        areas = [(item["bounding_box"][2] - item["bounding_box"][0]) *
                 (item["bounding_box"][3] - item["bounding_box"][1]) for item in items]
        prominence = sum(areas) / len(areas)
        centers = [((item["bounding_box"][0] + item["bounding_box"][2]) / 2,
                    (item["bounding_box"][1] + item["bounding_box"][3]) / 2) for item in items]
        travel = sum(math.dist(a, b) for a, b in zip(centers, centers[1:]))
        movement = min(1.0, travel / max(0.05, len(items) * 0.04))
        continuity = 1.0 if len(items) < 2 else min(1.0, (len(items) - 1) /
            max(1, round((items[-1]["timestamp"] - items[0]["timestamp"]) * sample_rate)))
        nearby = 0
        for item in items:
            center = centers[items.index(item)]
            if any(other["category"] in SUPPORTED_EQUIPMENT and
                   abs(other["timestamp"] - item["timestamp"]) < .5 / sample_rate and
                   math.dist(center, ((other["bounding_box"][0] + other["bounding_box"][2]) / 2,
                                      (other["bounding_box"][1] + other["bounding_box"][3]) / 2)) < .45
                   for other in detections):
                nearby += 1
        equipment_proximity = nearby / len(items)
        score = (.29 * persistence + .21 * continuity + .18 * movement +
                 .13 * min(1, prominence / .3) + .09 * equipment_proximity)
        # Duration matters independently: a brief close crossing cannot win on area alone.
        score += .1 * min(1, span / 3)
        reasons = [f"persistence={persistence:.2f}", f"continuity={continuity:.2f}",
                   f"movement={movement:.2f}", f"visual_prominence={prominence:.2f}",
                   f"equipment_proximity={equipment_proximity:.2f}", f"observed_seconds={span:.2f}"]
        by_scene[entity["scene_id"]].append((entity, score, reasons))

    for scene, candidates in by_scene.items():
        candidates.sort(key=lambda row: row[1], reverse=True)
        best, score, reasons = candidates[0]
        ambiguous = len(candidates) > 1 and score - candidates[1][1] < .1
        roles.append({"id": f"primary-{scene}", "role": "primary_athlete_candidate",
                      "entity_id": best["id"], "scene_id": scene,
                      "confidence": round(score, 6), "ambiguous": ambiguous,
                      "supporting_reasons": reasons + ([f"close_alternative={candidates[1][0]['id']}"]
                                                        if ambiguous else [])})
        items = by_entity[best["id"]]
        boxes = [item["bounding_box"] for item in items]
        pad = .04
        region = [max(0, min(box[0] for box in boxes) - pad), max(0, min(box[1] for box in boxes) - pad),
                  min(1, max(box[2] for box in boxes) + pad), min(1, max(box[3] for box in boxes) + pad)]
        region_id = f"athlete-region-{scene}"
        regions.append({"id": region_id, "type": "athlete_bounding_region", "entity_ids": [best["id"]],
                        "start": best["start"], "end": best["end"], "bounding_box": region,
                        "coordinate_space": "normalized_xyxy"})
        # Only actual model-supported classes may extend the advisory region.
        equipment = [entity for entity in evidence["tracked_entities"]
                     if entity["scene_id"] == scene and entity["category"] in SUPPORTED_EQUIPMENT]
        if equipment:
            equipment_items = [item for entity in equipment for item in by_entity[entity["id"]]]
            union = [min(region[0], min(item["bounding_box"][0] for item in equipment_items)),
                     min(region[1], min(item["bounding_box"][1] for item in equipment_items)),
                     max(region[2], max(item["bounding_box"][2] for item in equipment_items)),
                     max(region[3], max(item["bounding_box"][3] for item in equipment_items))]
            regions.append({"id": f"athlete-equipment-{scene}", "type": "athlete_equipment_union",
                            "entity_ids": [best["id"], *[entity["id"] for entity in equipment]],
                            "start": best["start"], "end": best["end"], "bounding_box": union,
                            "coordinate_space": "normalized_xyxy"})
        edge = any(box[0] < .02 or box[1] < .02 or box[2] > .98 or box[3] > .98 for box in boxes)
        gaps = any(b["timestamp"] - a["timestamp"] > 2.1 / sample_rate for a, b in zip(items, items[1:]))
        center_travel = sum(math.dist(((a["bounding_box"][0]+a["bounding_box"][2])/2,
                                       (a["bounding_box"][1]+a["bounding_box"][3])/2),
                                      ((b["bounding_box"][0]+b["bounding_box"][2])/2,
                                       (b["bounding_box"][1]+b["bounding_box"][3])/2))
                            for a, b in zip(items, items[1:]))
        risks = (["subject_near_source_edge"] if edge else []) + (["temporary_subject_loss"] if gaps else [])
        if center_travel > .8:
            risks.append("excessive_crop_movement")
        constraints.append({"id": f"crop-{scene}", "entity_id": best["id"], "region_id": region_id,
                            "type": "minimum_visible_region", "risk": "high" if risks else "low",
                            "risk_reasons": risks, "advisory_only": True})
    return {"entity_roles": roles, "visual_regions": regions, "crop_constraints": constraints}


class YoloObjectTracking:
    name, category, upstream = "ultralytics-yolo", "object_tracking", "Ultralytics"

    def __init__(self, model: str = "yolo11n.pt", device: str = "cpu", sample_rate: float = 2,
                 tracker: str = "bytetrack.yaml", confidence: float = .25, allow_download: bool = False):
        self.version: str | None = None
        self.model, self.device, self.sample_rate = model, device, sample_rate
        self.tracker, self.confidence, self.allow_download = tracker, confidence, allow_download
        self.configuration = {"model": model, "device": device, "sample_rate": sample_rate,
                              "tracker": tracker, "confidence": confidence,
                              "allow_model_download": allow_download, "coordinate_space": "normalized_xyxy"}

    def analyze(self, source: dict[str, Any], timeout: float) -> Result:
        if source.get("duration") is None or not source.get("width") or not source.get("height"):
            return Result(status="skipped", warnings=["Object tracking requires duration and source dimensions."])
        try:
            ultralytics = importlib.import_module("ultralytics")
        except ImportError as exc:
            raise Unavailable("ultralytics is not installed; continue without object tracking") from exc
        self.version = str(getattr(ultralytics, "__version__", "unknown"))
        if not self.allow_download and not Path(self.model).is_file():
            raise Unavailable("YOLO model file is unavailable; automatic downloads are disabled")
        try:
            cv2 = importlib.import_module("cv2")
            model = ultralytics.YOLO(self.model)
        except Exception as exc:
            return Result(status="failed", errors=[f"YOLO model load failed: {exc}"],
                          warnings=["Continue with scene, motion, and manual visual analysis."])
        started = time.monotonic()
        cap = cv2.VideoCapture(source["path"])
        if not cap.isOpened():
            return Result(status="failed", errors=["YOLO could not open the source video"])
        fps = float(source.get("fps") or cap.get(cv2.CAP_PROP_FPS) or 30)
        interval = max(1, round(fps / self.sample_rate))
        inactive_interval = max(interval, round(fps / min(self.sample_rate, .5)))
        scenes = source.get("_analysis_context", {}).get("scenes", [])
        activity = source.get("_analysis_context", {}).get("activity_regions", [])
        boundaries = sorted(item["start"] for item in scenes if item["start"] > 0)
        samples, frame_index, analyzed, skipped, scene_index = [], 0, 0, 0, 0
        try:
            while time.monotonic() - started <= timeout:
                ok, frame = cap.read()
                if not ok:
                    break
                decoder_ms = float(cap.get(cv2.CAP_PROP_POS_MSEC) or 0)
                decoded_timestamp = decoder_ms / 1000
                fallback_timestamp = frame_index / fps
                timestamp = decoded_timestamp if decoded_timestamp > 0 or frame_index == 0 else fallback_timestamp
                if samples:
                    timestamp = max(timestamp, samples[-1]["timestamp"])
                while scene_index < len(boundaries) and timestamp >= boundaries[scene_index]:
                    scene_index += 1
                active = any(item["type"] == "motion_active" and item["start"] <= timestamp < item["end"]
                             for item in activity)
                chosen_interval = interval if active or not activity else inactive_interval
                if frame_index % chosen_interval:
                    skipped += 1
                    frame_index += 1
                    continue
                result = model.track(frame, persist=bool(samples and
                    (not samples or samples[-1]["scene"] == scene_index)), tracker=self.tracker,
                    conf=self.confidence, device=self.device, verbose=False)[0]
                rows = []
                names = result.names
                if result.boxes is not None:
                    for box in result.boxes:
                        class_id = int(box.cls.item())
                        rows.append({"category": str(names[class_id]), "confidence": float(box.conf.item()),
                                     "track_id": int(box.id.item()) if box.id is not None else None,
                                     "bounding_box": box.xyxy[0].tolist()})
                samples.append({"timestamp": min(timestamp, float(source["duration"])),
                                "scene": scene_index, "detections": rows})
                analyzed += 1
                frame_index += 1
            else:
                raise TimeoutError("YOLO analysis exceeded its timeout")
        except Exception as exc:
            return Result(status="failed", errors=[f"YOLO inference failed: {exc}"],
                          warnings=["Object evidence was discarded; the editing pipeline can continue."])
        finally:
            cap.release()
        evidence = normalize_samples(samples, source, self.name, self.model)
        evidence.update(derive_visual_evidence(evidence, self.sample_rate))
        elapsed = time.monotonic() - started
        warnings = ["Stock COCO models do not reliably identify dumbbells, barbells, kettlebells, plates, cable handles, or gym machines."]
        return Result(status="success" if evidence["object_detections"] else "no_results",
                      evidence=evidence, warnings=warnings, metadata={}, errors=[], performance={
                          "analyzed_samples": analyzed, "skipped_frames": skipped,
                          "source_duration": source["duration"],
                          "effective_sample_rate": analyzed / source["duration"],
                          "analysis_duration": elapsed, "device": self.device,
                          "model": self.model, "tracker": self.tracker})
