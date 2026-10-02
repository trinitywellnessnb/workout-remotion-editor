"""Optional MMPose adapter and provider-agnostic pose evidence derivation.

Pose is estimated image evidence.  This module intentionally does not identify
exercises, assess technique or safety, or count repetitions.
"""

from __future__ import annotations

import hashlib
import importlib
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from analyzers.base import Result, Unavailable

COCO_17 = (
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)
ANGLE_SPECS = {
    "left_elbow_angle": ("left_shoulder", "left_elbow", "left_wrist"),
    "right_elbow_angle": ("right_shoulder", "right_elbow", "right_wrist"),
    "left_knee_angle": ("left_hip", "left_knee", "left_ankle"),
    "right_knee_angle": ("right_hip", "right_knee", "right_ankle"),
    "left_hip_angle": ("left_shoulder", "left_hip", "left_knee"),
    "right_hip_angle": ("right_shoulder", "right_hip", "right_knee"),
    "left_shoulder_angle": ("left_elbow", "left_shoulder", "left_hip"),
    "right_shoulder_angle": ("right_elbow", "right_shoulder", "right_hip"),
}
GROUPS = {
    "upper_limb": ("left_elbow", "right_elbow", "left_wrist", "right_wrist"),
    "lower_limb": ("left_knee", "right_knee", "left_ankle", "right_ankle"),
    "trunk": ("left_shoulder", "right_shoulder", "left_hip", "right_hip"),
}


def _angle(a: dict[str, Any], b: dict[str, Any], c: dict[str, Any]) -> float | None:
    u, v = (a["x"] - b["x"], a["y"] - b["y"]), (c["x"] - b["x"], c["y"] - b["y"])
    denominator = math.hypot(*u) * math.hypot(*v)
    if denominator <= 1e-12:
        return None
    return math.degrees(
        math.acos(max(-1.0, min(1.0, (u[0] * v[0] + u[1] * v[1]) / denominator)))
    )


class OneEuro:
    """Timestamp-aware One Euro filter, kept deliberately responsive."""

    def __init__(
        self, min_cutoff: float = 1.7, beta: float = 0.25, derivative_cutoff: float = 1
    ):
        self.min_cutoff, self.beta, self.derivative_cutoff = (
            min_cutoff,
            beta,
            derivative_cutoff,
        )
        self.t: float | None = None
        self.x: float | None = None
        self.dx = 0.0

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1 / (2 * math.pi * cutoff)
        return 1 / (1 + tau / dt)

    def update(self, value: float, timestamp: float) -> float:
        if self.t is None or timestamp <= self.t:
            self.t, self.x = timestamp, value
            return value
        dt = timestamp - self.t
        derivative = (value - self.x) / dt
        a_d = self._alpha(self.derivative_cutoff, dt)
        self.dx = a_d * derivative + (1 - a_d) * self.dx
        alpha = self._alpha(self.min_cutoff + self.beta * abs(self.dx), dt)
        self.x = alpha * value + (1 - alpha) * self.x
        self.t = timestamp
        return self.x


def normalize_pose_samples(
    samples: list[dict[str, Any]],
    source: dict[str, Any],
    *,
    threshold: float = 0.25,
    layout: str = "coco_17",
) -> list[dict[str, Any]]:
    """Normalize backend-neutral samples; partial skeletons remain useful."""
    width, height = int(source["width"]), int(source["height"])
    output: list[dict[str, Any]] = []
    last = -1.0
    for sample_index, sample in enumerate(samples):
        timestamp = float(sample["timestamp"])
        if (
            not math.isfinite(timestamp)
            or timestamp < last
            or not 0 <= timestamp <= source["duration"] + 1e-6
        ):
            raise ValueError(
                "pose timestamps must be finite, ordered, and within the source"
            )
        last = timestamp
        for pose_index, pose in enumerate(sample.get("poses", [])):
            points = []
            raw_points = pose.get("keypoints", [])
            raw_scores = pose.get("scores", [])
            for index, name in enumerate(COCO_17):
                if index >= len(raw_points) or raw_points[index] is None:
                    points.append({"name": name, "confidence": 0.0, "state": "missing"})
                    continue
                raw = raw_points[index]
                x, y = float(raw[0]), float(raw[1])
                score = float(raw_scores[index]) if index < len(raw_scores) else 0.0
                if (
                    not all(math.isfinite(v) for v in (x, y, score))
                    or not 0 <= score <= 1
                ):
                    raise ValueError(
                        "pose coordinates and confidence must be finite; confidence must be in [0,1]"
                    )
                if not 0 <= x <= width or not 0 <= y <= height:
                    points.append(
                        {
                            "name": name,
                            "x": x / width,
                            "y": y / height,
                            "confidence": score,
                            "state": "outside_frame",
                        }
                    )
                else:
                    points.append(
                        {
                            "name": name,
                            "x": x / width,
                            "y": y / height,
                            "confidence": score,
                            "state": "visible"
                            if score >= threshold
                            else "low_confidence",
                        }
                    )
            item = {
                "id": f"pose-{sample_index}-{pose_index}",
                "scene_id": str(sample["scene_id"]),
                "timestamp": timestamp,
                "landmark_set": layout,
                "source_width": width,
                "source_height": height,
                "coordinate_space": "display_normalized_xy",
                "association_method": pose.get(
                    "association_method", "pose_only_candidate"
                ),
                "association_confidence": float(
                    pose.get("association_confidence", 0.35)
                ),
                "association_ambiguous": bool(pose.get("association_ambiguous", False)),
                "input_variant": "raw",
                "keypoints": points,
            }
            for key in ("entity_id", "detection_id"):
                if pose.get(key) is not None:
                    item[key] = str(pose[key])
            if pose.get("pose_origin_id") is not None:
                item["pose_origin_id"] = str(pose["pose_origin_id"])
            # Never force an ambiguous result onto an athlete identity.
            if item["association_ambiguous"]:
                item.pop("entity_id", None)
            output.append(item)
    return output


def smooth_pose_samples(
    raw: list[dict[str, Any]], max_gap: float = 0.75
) -> list[dict[str, Any]]:
    filters: dict[tuple[str, str, str, str], OneEuro] = {}
    last_seen: dict[tuple[str, str, str], float] = {}
    result = []
    for sample in raw:
        identity = sample.get("entity_id", sample.get("pose_origin_id", sample["id"]))
        base = (sample["scene_id"], identity)
        smoothed = {
            **sample,
            "id": sample["id"] + "-smoothed",
            "input_variant": "one_euro_smoothed",
            "raw_pose_sample_id": sample["id"],
            "keypoints": [],
        }
        for point in sample["keypoints"]:
            p = dict(point)
            joint = (*base, point["name"])
            if point["state"] == "visible":
                if (
                    sample["timestamp"] - last_seen.get(joint, sample["timestamp"])
                    > max_gap
                ):
                    filters.pop((*joint, "x"), None)
                    filters.pop((*joint, "y"), None)
                for axis in ("x", "y"):
                    filt = filters.setdefault((*joint, axis), OneEuro())
                    p[axis] = filt.update(point[axis], sample["timestamp"])
                last_seen[joint] = sample["timestamp"]
            smoothed["keypoints"].append(p)
        result.append(smoothed)
    return result


def derive_joint_metrics(
    samples: list[dict[str, Any]], threshold: float = 0.25
) -> list[dict[str, Any]]:
    metrics = []
    for sample in samples:
        points = {p["name"]: p for p in sample["keypoints"]}
        for name, joints in ANGLE_SPECS.items():
            values = [points[j] for j in joints]
            if any(
                p["state"] != "visible" or p["confidence"] < threshold for p in values
            ):
                continue
            # Normalized x/y have different pixel scales on non-square sources;
            # recover displayed image-plane geometry before measuring angles.
            scaled = [
                {
                    **p,
                    "x": p["x"] * sample["source_width"],
                    "y": p["y"] * sample["source_height"],
                }
                for p in values
            ]
            value = _angle(*scaled)
            if value is not None:
                metrics.append(
                    {
                        "id": f"metric-{sample['id']}-{name}",
                        "pose_sample_id": sample["id"],
                        "entity_id": sample.get("entity_id"),
                        "scene_id": sample["scene_id"],
                        "timestamp": sample["timestamp"],
                        "metric_name": name,
                        "metric_type": "joint_angle_2d",
                        "value": round(value, 6),
                        "unit": "degrees",
                        "contributing_landmarks": list(joints),
                        "quality": min(p["confidence"] for p in values),
                        "derivation_method": "image_plane_vertex_angle",
                        "input_variant": sample["input_variant"],
                    }
                )
    return metrics


def derive_movement_signals(
    samples: list[dict[str, Any]], threshold: float = 0.25
) -> list[dict[str, Any]]:
    signals, histories = [], defaultdict(list)
    direction_state: dict[tuple[str, str, str], tuple[int, int]] = {}
    for sample in samples:
        identity = sample.get("entity_id", sample.get("pose_origin_id", sample["id"]))
        points = {
            p["name"]: p
            for p in sample["keypoints"]
            if p["state"] == "visible" and p["confidence"] >= threshold
        }
        shoulders, hips = (
            [points.get(x) for x in ("left_shoulder", "right_shoulder")],
            [points.get(x) for x in ("left_hip", "right_hip")],
        )
        scale = None
        if all(shoulders + hips):
            shoulder_mid = (
                sum(p["x"] * sample["source_width"] for p in shoulders) / 2,
                sum(p["y"] * sample["source_height"] for p in shoulders) / 2,
            )
            hip_mid = (
                sum(p["x"] * sample["source_width"] for p in hips) / 2,
                sum(p["y"] * sample["source_height"] for p in hips) / 2,
            )
            scale = math.dist(shoulder_mid, hip_mid)
        for group, names in GROUPS.items():
            present = [points[n] for n in names if n in points]
            if not present or not scale or scale <= 0.01:
                continue
            # Work in displayed pixels so a non-square source does not skew the
            # dimensionless torso normalization.
            center = (
                sum(p["x"] * sample["source_width"] for p in present) / len(present),
                sum(p["y"] * sample["source_height"] for p in present) / len(present),
            )
            key = (sample["scene_id"], identity, group)
            history = histories[key]
            if history:
                old_t, old_center, old_velocity = history[-1]
                dt = sample["timestamp"] - old_t
                if dt > 0:
                    displacement = math.dist(center, old_center) / scale
                    speed = displacement / dt
                    signals.append(
                        {
                            "id": f"movement-{sample['id']}-{group}",
                            "pose_sample_id": sample["id"],
                            "entity_id": sample.get("entity_id"),
                            "scene_id": sample["scene_id"],
                            "timestamp": sample["timestamp"],
                            "signal_type": "normalized_trajectory_speed",
                            "landmark_group": group,
                            "value": round(speed, 6),
                            "unit": "torso_lengths_per_second_image_space",
                            "normalization_basis": "shoulder_to_hip_midpoint_image_distance",
                            "quality": min(p["confidence"] for p in present),
                        }
                    )
                    velocity = (center[1] - old_center[1]) / dt
                    sign = 1 if velocity > 0.015 else -1 if velocity < -0.015 else 0
                    baseline, persistence = direction_state.get(key, (sign, 0))
                    emit_direction = False
                    if sign and baseline and sign != baseline and displacement > 0.02:
                        persistence += 1
                        if persistence >= 2:
                            emit_direction = True
                            baseline, persistence = sign, 0
                    elif sign:
                        baseline, persistence = sign, 0
                    direction_state[key] = (baseline, persistence)
                    # Require meaningful excursion, hysteresis, and two samples
                    # persisting in the new direction.
                    if emit_direction:
                        signals.append(
                            {
                                "id": f"direction-{sample['id']}-{group}",
                                "pose_sample_id": sample["id"],
                                "entity_id": sample.get("entity_id"),
                                "scene_id": sample["scene_id"],
                                "timestamp": sample["timestamp"],
                                "signal_type": "direction_change_candidate",
                                "landmark_group": group,
                                "value": 1,
                                "unit": "candidate",
                                "normalization_basis": "torso_length_and_velocity_hysteresis",
                                "quality": min(p["confidence"] for p in present),
                            }
                        )
                    history.append((sample["timestamp"], center, velocity))
                    continue
            history.append((sample["timestamp"], center, None))
    return signals


def derive_pose_crop_evidence(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    constraints = []
    for sample in samples:
        if not sample.get("entity_id"):
            continue
        visible = {p["name"]: p for p in sample["keypoints"] if p["state"] == "visible"}
        risks = []
        if any(p["y"] > 0.97 for n, p in visible.items() if n.endswith("ankle")):
            risks.append("ankle_cutoff_risk")
        if any(
            p["x"] < 0.02 or p["x"] > 0.98
            for n, p in visible.items()
            if n.endswith("wrist")
        ):
            risks.append("wrist_cutoff_risk")
        if any(
            p["y"] < 0.02
            for n, p in visible.items()
            if n in {"nose", "left_eye", "right_eye", "left_ear", "right_ear"}
        ):
            risks.append("head_cutoff_risk")
        if risks:
            constraints.append(
                {
                    "id": "pose-crop-" + sample["id"],
                    "entity_id": sample["entity_id"],
                    "pose_sample_id": sample["id"],
                    "scene_id": sample["scene_id"],
                    "timestamp": sample["timestamp"],
                    "type": "pose_landmark_crop_risk",
                    "risk": "medium",
                    "risk_reasons": risks,
                    "required_landmark_group": "working_anatomy_union",
                    "advisory_only": True,
                }
            )
    return constraints


def build_pose_evidence(
    samples: list[dict[str, Any]], source: dict[str, Any], threshold: float = 0.25
) -> dict[str, list[dict[str, Any]]]:
    raw = normalize_pose_samples(samples, source, threshold=threshold)
    smoothed = smooth_pose_samples(raw)
    return {
        "pose_samples": raw + smoothed,
        "derived_joint_metrics": derive_joint_metrics(smoothed, threshold),
        "movement_signals": derive_movement_signals(smoothed, threshold),
        "pose_crop_constraints": derive_pose_crop_evidence(raw),
    }


class MMPoseProvider:
    name, category, upstream = "mmpose", "pose", "OpenMMLab MMPose"

    def __init__(
        self,
        config: str | None,
        checkpoint: str | None,
        device: str = "cpu",
        sample_rate: float = 2,
        mode: str = "cpu_basic",
        threshold: float = 0.25,
        all_persons: bool = False,
        allow_download: bool = False,
    ):
        self.config_path, self.checkpoint = config, checkpoint
        self.device, self.sample_rate, self.mode = device, sample_rate, mode
        self.threshold, self.all_persons, self.allow_download = (
            threshold,
            all_persons,
            allow_download,
        )
        self.version: str | None = None
        self.configuration = {
            "config": config,
            "checkpoint": checkpoint,
            "device": device,
            "sample_rate": sample_rate,
            "mode": mode,
            "keypoint_threshold": threshold,
            "all_persons": all_persons,
            "allow_model_download": allow_download,
            "landmark_set": "coco_17",
        }

    def analyze(self, source: dict[str, Any], timeout: float) -> Result:
        if (
            not self.config_path
            or not self.checkpoint
            or not Path(self.config_path).is_file()
            or not Path(self.checkpoint).is_file()
        ):
            raise Unavailable(
                "MMPose requires explicit local --pose-config and --pose-checkpoint files"
            )
        try:
            mmpose = importlib.import_module("mmpose")
            apis = importlib.import_module("mmpose.apis")
        except ImportError as exc:
            raise Unavailable(
                "mmpose is not installed; continue without pose evidence"
            ) from exc
        self.version = str(getattr(mmpose, "__version__", "unknown"))
        try:
            model = apis.init_model(
                self.config_path, self.checkpoint, device=self.device
            )
            cv2 = importlib.import_module("cv2")
        except Exception as exc:
            return Result(status="failed", errors=[f"MMPose model load failed: {exc}"])
        context = source.get("_analysis_context", {})
        detections = [
            d for d in context.get("object_detections", []) if d["category"] == "person"
        ]
        plan = []
        if detections:
            for d in detections:
                if self.all_persons or d.get("entity_id"):
                    plan.append((d["timestamp"], d["scene_id"], d))
        else:
            step = 1 / self.sample_rate
            t = 0.0
            scenes = sorted(context.get("scenes", []), key=lambda item: item["start"])
            while t <= source["duration"] + 1e-6:
                scene_index = next(
                    (
                        index
                        for index, item in enumerate(scenes)
                        if item["start"] - 1e-6 <= t <= item["end"] + 1e-6
                    ),
                    0,
                )
                plan.append((t, f"scene-{scene_index}", None))
                t += step
        cap, backend, started, samples = (
            cv2.VideoCapture(source["path"]),
            [],
            time.monotonic(),
            [],
        )
        if not cap.isOpened():
            return Result(
                status="failed", errors=["MMPose could not open the source video"]
            )
        try:
            for requested, scene, detection in plan:
                if time.monotonic() - started > timeout:
                    raise TimeoutError("pose analysis exceeded timeout")
                cap.set(cv2.CAP_PROP_POS_MSEC, requested * 1000)
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"frame decode failed at {requested:g}s")
                bbox = (
                    [
                        detection["bounding_box"][0] * source["width"],
                        detection["bounding_box"][1] * source["height"],
                        detection["bounding_box"][2] * source["width"],
                        detection["bounding_box"][3] * source["height"],
                    ]
                    if detection
                    else [0, 0, source["width"], source["height"]]
                )
                results = apis.inference_topdown(model, frame, bboxes=[bbox])
                poses = []
                ambiguous = detection is not None and len(results) != 1
                for result_index, result in enumerate(results):
                    instance = result.pred_instances
                    points, scores = (
                        instance.keypoints[0].tolist(),
                        instance.keypoint_scores[0].tolist(),
                    )
                    pose = {
                        "keypoints": points,
                        "scores": scores,
                        "association_method": "supplied_roi"
                        if detection
                        else "pose_only_candidate",
                        "association_confidence": detection["confidence"]
                        if detection
                        else 0.35,
                        "association_ambiguous": ambiguous,
                        "pose_origin_id": f"{scene}:pose-candidate-{result_index}",
                    }
                    if detection and not ambiguous:
                        pose.update(
                            entity_id=detection.get("entity_id"),
                            detection_id=detection["id"],
                        )
                    poses.append(pose)
                decoded = (
                    float(cap.get(cv2.CAP_PROP_POS_MSEC) or requested * 1000) / 1000
                )
                backend.append(abs(decoded - requested))
                samples.append(
                    {"timestamp": requested, "scene_id": scene, "poses": poses}
                )
        except Exception as exc:
            return Result(status="failed", errors=[f"MMPose inference failed: {exc}"])
        finally:
            cap.release()
        evidence = build_pose_evidence(samples, source, self.threshold)
        digest = hashlib.sha256()
        with Path(self.checkpoint).open("rb") as checkpoint_file:
            for chunk in iter(lambda: checkpoint_file.read(1024 * 1024), b""):
                digest.update(chunk)
        checksum = digest.hexdigest()
        self.configuration["checkpoint_sha256"] = checksum
        raw_count = sum(p["input_variant"] == "raw" for p in evidence["pose_samples"])
        return Result(
            status="success" if raw_count else "no_results",
            evidence=evidence,
            warnings=[
                "Pose scores are model confidence evidence, not calibrated probabilities."
            ],
            performance={
                "requested_samples": len(plan),
                "pose_samples": raw_count,
                "maximum_seek_drift_seconds": max(backend, default=0),
                "device": self.device,
            },
        )
