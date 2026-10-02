"""Isolated optional local inference using Ultralytics public prediction/tracking APIs."""
from __future__ import annotations

import hashlib
import json
import math
import socket
import sys
import time
from pathlib import Path
from typing import Any


def rotation_degrees(value: Any) -> int:
    angle = float(value or 0)
    nearest = round(angle / 90) * 90
    if not math.isfinite(angle) or abs(angle - nearest) > 1e-3:
        raise ValueError("Only right-angle display rotation is supported")
    return nearest % 360


def run(payload: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    source, config, intervals = payload["source"], payload["configuration"], payload["intervals"]
    # Defense in depth: inference workers have no outbound socket capability.
    def offline(*args, **kwargs):
        raise OSError("Network access is disabled in local workout analysis")
    class LocalSocket(socket.socket):
        connect = offline
        connect_ex = offline
        sendto = offline
    socket.socket = LocalSocket
    socket.create_connection = offline
    socket.getaddrinfo = offline
    import av
    import numpy as np
    import ultralytics
    from ultralytics import YOLO, settings

    if ultralytics.__version__ != "8.4.171":
        raise ValueError("Ultralytics 8.4.171 is required")
    settings.update({"sync": False, "clearml": False, "comet": False, "dvc": False,
                     "mlflow": False, "raytune": False, "tensorboard": False, "wandb": False})
    path = Path(config["model"])
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    stats = {"source_duration": source["duration"], "samples_analyzed": 0, "frames_decoded": 0,
             "samples_skipped": 0, "model": str(path), "model_sha256": digest.hexdigest(),
             "device_requested": config["device"], "device_used": config["device"],
             "requested_sample_fps": config["sample_fps"], "effective_sample_fps": 0.0,
             "inference_seconds": 0.0, "elapsed_seconds": 0.0, "display_width": 0, "display_height": 0}
    warnings, errors, samples = [], [], []
    try:
        model = YOLO(str(path), task="detect")
        if model.task != "detect":
            raise ValueError("Phase 2 requires a detection checkpoint; pose/segment models are deferred")
        unknown = set(config["equipment_classes"]) - set(model.names.values())
        if unknown:
            raise ValueError(f"Equipment labels absent from this model: {sorted(unknown)}")
    except Exception as exc:
        stats["elapsed_seconds"] = time.monotonic() - started
        return {"status": "failed", "errors": [f"Model load/configuration failed: {exc}"],
                "warnings": warnings, "statistics": stats, "samples": []}
    container = av.open(source["path"])
    try:
        stream = container.streams.video[0]
        if stream.start_time is None or stream.time_base is None:
            raise ValueError("Video timestamp origin is unverified; do not guess source timing")
        origin = float(stream.start_time * stream.time_base)
        if abs(origin) > 1e-6 and any(span.get("scene_id") is not None for span in intervals):
            raise ValueError("Nonzero video origin cannot safely align prior scene evidence; "
                             "use --skip-scene for detection only or verify source timing separately")
        angle = rotation_degrees(source.get("rotation", 0))
        interval_index = 0
        next_time = intervals[0]["start"]
        fresh = True
        actual_device = config["device"]
        previous_time = None
        previous_sample_time = None
        epoch = 0
        for frame_index, frame in enumerate(container.decode(stream)):
            stats["frames_decoded"] += 1
            if frame.pts is None:
                raise ValueError("Missing presentation timestamp")
            timestamp = float(frame.pts * frame.time_base) - origin
            if not math.isfinite(timestamp) or timestamp < -1e-6:
                raise ValueError("Invalid source presentation timestamp")
            timestamp = max(0.0, timestamp)
            if previous_time is not None and timestamp <= previous_time:
                raise ValueError("Non-increasing video timestamps")
            previous_time = timestamp
            while interval_index < len(intervals) and timestamp >= intervals[interval_index]["end"] - 1e-9:
                interval_index += 1
                if interval_index < len(intervals):
                    next_time = intervals[interval_index]["start"]
                    fresh = True
                    epoch = 0
                    previous_sample_time = None
            if interval_index >= len(intervals):
                break
            interval = intervals[interval_index]
            if not config["full_frame"] and timestamp + 1e-9 < next_time:
                stats["samples_skipped"] += 1
                continue
            image = frame.to_ndarray(format="bgr24")
            # ffprobe display-matrix rotation is counterclockwise, matching np.rot90.
            if angle:
                image = np.ascontiguousarray(np.rot90(image, k=angle // 90))
            height, width = image.shape[:2]
            stats.update(display_width=width, display_height=height)
            cadence = interval["sample_interval"]
            if previous_sample_time is not None and timestamp - previous_sample_time > cadence * 3:
                # A fresh public lifecycle prevents guessed identity over decoding gaps.
                fresh = True
                epoch += 1
                warnings.append(f"Tracking state reset after a timestamp gap at {timestamp:.6f}s.")
            tracking = interval.get("scene_id") is not None
            options = {"device": actual_device,
                       "imgsz": config["imgsz"], "conf": config["detector_confidence"],
                       "save": False, "show": False, "verbose": False, "half": False}
            inference_started = time.monotonic()
            try:
                result = (model.track(image, persist=not fresh, tracker=config["tracker"] + ".yaml", **options)[0]
                          if tracking else model.predict(image, **options)[0])
            except Exception as exc:
                if actual_device == "cpu":
                    raise RuntimeError(f"Inference failed at {timestamp:.6f}s: {exc}") from exc
                warnings.append(f"Device {actual_device} failed; retrying this and later samples on CPU: {exc}")
                actual_device = "cpu"
                options["device"] = "cpu"
                # A fresh model also releases incompatible device/tracker state.
                model = YOLO(str(path), task="detect")
                epoch += 1
                result = (model.track(image, persist=False, tracker=config["tracker"] + ".yaml", **options)[0]
                          if tracking else model.predict(image, **options)[0])
                fresh = True
            stats["inference_seconds"] += time.monotonic() - inference_started
            items = []
            boxes = result.boxes
            if boxes is not None:
                ids = (boxes.id.cpu().tolist() if tracking and boxes.is_track and boxes.id is not None
                       else [None] * len(boxes))
                for bbox, confidence, class_id, track_id in zip(boxes.xyxyn.cpu().tolist(),
                                                               boxes.conf.cpu().tolist(),
                                                               boxes.cls.cpu().tolist(), ids):
                    items.append({"bbox": bbox, "confidence": confidence, "class_id": int(class_id),
                                  "class_name": result.names[int(class_id)],
                                  "track_id": f"{epoch}:{int(track_id)}" if track_id is not None else None})
            samples.append({"time": timestamp, "frame_index": frame_index, "sample_index": len(samples),
                            "interval_id": interval["id"], "detections": items})
            stats["samples_analyzed"] += 1
            stats["device_used"] = actual_device
            fresh = False
            previous_sample_time = timestamp
            if not config["full_frame"]:
                # Advance the requested grid; observations retain actual PTS.
                grid_index = math.floor((timestamp - interval["start"] + 1e-9) * config["sample_fps"]) + 1
                next_time = interval["start"] + grid_index / config["sample_fps"]
    except Exception as exc:
        errors.append(str(exc))
    finally:
        container.close()
    stats["elapsed_seconds"] = time.monotonic() - started
    stats["effective_sample_fps"] = stats["samples_analyzed"] / source["duration"]
    if samples and samples[-1]["time"] < source["duration"] - max(1 / config["sample_fps"], 0.5):
        warnings.append("Incomplete source coverage; no regions are extrapolated beyond observed samples.")
    return {"status": "partial" if errors and samples else "failed" if errors else "success",
            "samples": samples, "errors": errors, "warnings": warnings, "statistics": stats}


def main() -> None:
    try:
        result = run(json.loads(sys.argv[1]))
    except Exception as exc:
        result = {"status": "failed", "errors": [str(exc)], "warnings": [], "samples": []}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
