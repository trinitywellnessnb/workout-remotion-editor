"""Optional Ultralytics visual evidence adapter; no weights or upstream code bundled."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import tempfile
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from .base import Result, Unavailable, command
from .visual_evidence import derive, valid_box

TESTED_VERSION = "8.4.171"
TRACKERS = {"bytetrack", "botsort", "ocsort", "deepocsort", "fasttrack", "tracktrack"}


def tracking_intervals(source: dict[str, Any], context: dict[str, Any],
                       sample_fps: float, full_frame: bool) -> tuple[list[dict[str, Any]], list[str]]:
    duration = source["duration"]
    # One detector invocation supplies the segmentation; do not mix overlapping runs.
    available = [item for item in context.get("scenes", []) if item["source_id"] == source["id"]]
    warnings = []
    if available:
        run = available[0]["run_id"]
        available = sorted((item for item in available if item["run_id"] == run), key=lambda s: s["start"])
        bounds = {0.0, duration}
        bounds.update(item["start"] for item in available)
        bounds.update(item["end"] for item in available)
    else:
        bounds = {0.0, duration}
        warnings.append("No scene ranges available; using detection only without persistent identities. Review cuts manually.")
    times = sorted(bounds)
    cadence = 1 / source.get("fps", sample_fps) if full_frame else 1 / sample_fps
    intervals = []
    for index, (start, end) in enumerate(zip(times, times[1:])):
        if end <= start:
            continue
        supporting = next((s for s in available if s["start"] <= start and s["end"] >= end), None)
        intervals.append({"id": f"interval:{index}", "start": start, "end": end,
                          "sample_interval": cadence, "scene_id": supporting["id"] if supporting else None,
                          "reason": "Independent tracking lifecycle; identity never crosses its boundaries."})
    return intervals, warnings


class ObjectTracking:
    name = "ultralytics"
    category = "object_tracking"
    upstream = "https://github.com/ultralytics/ultralytics"
    version: str | None = None
    consumes_context = True

    def __init__(self, model: Path | str, *, device: str = "cpu", tracker: str = "bytetrack",
                 sample_fps: float = 5, full_frame: bool = False,
                 equipment_classes: list[str] | None = None, crop: Any = None):
        self.configuration = {
            "model": str(model), "device": device, "tracker": tracker, "sample_fps": sample_fps,
            "full_frame": full_frame, "equipment_classes": equipment_classes or [], "crop": crop,
            "imgsz": 640, "detector_confidence": 0.1, "coordinate_space": "display_normalized_xyxy",
            "local_only": True, "reid": False, "licensing_route": "separately_licensed_enterprise",
        }

    def analyze(self, source: dict[str, Any], timeout: float,
                context: dict[str, Any] | None = None) -> Result:
        if importlib.util.find_spec("ultralytics") is None:
            raise Unavailable("Ultralytics is not installed; continue visual/manual analysis.")
        self.version = metadata.version("ultralytics")
        if self.version != TESTED_VERSION:
            return Result(status="skipped", warnings=[
                f"Untested Ultralytics {self.version}; install tested {TESTED_VERSION}."])
        if importlib.util.find_spec("av") is None:
            raise Unavailable("PyAV is required for reliable source presentation timestamps.")
        config = dict(self.configuration)
        path = Path(config["model"]).expanduser()
        if not path.is_file() or path.suffix.lower() != ".pt":
            return Result(status="skipped", warnings=[
                "Supply an existing trusted local .pt detection model; automatic downloads are disabled."])
        config["model"] = str(path.resolve())
        self.configuration["model"] = config["model"]
        if source["duration"] is None:
            return Result(status="skipped", warnings=["Tracking requires known source duration."])
        if config["tracker"] not in TRACKERS:
            raise ValueError("unsupported tracker")
        rate = config["sample_fps"]
        if isinstance(rate, bool) or not isinstance(rate, (float, int)) or not math.isfinite(rate) or not 0 < rate <= 120:
            raise ValueError("sample_fps must be finite and in (0, 120]")
        if config["crop"] is not None and not valid_box(config["crop"]):
            raise ValueError("invalid normalized proposed crop")
        intervals, warnings = tracking_intervals(source, context or {}, rate, config["full_frame"])
        worker = Path(__file__).with_name("object_tracking_worker.py")
        with tempfile.TemporaryDirectory(prefix="workout-tracking-") as temporary:
            env = dict(os.environ, YOLO_OFFLINE="true", YOLO_AUTOINSTALL="false",
                       YOLO_CONFIG_DIR=temporary, MPLCONFIGDIR=temporary)
            # Do not inherit credentials for cloud integrations.
            for key in ("ULTRALYTICS_API_KEY", "OPENAI_API_KEY", "WANDB_API_KEY", "COMET_API_KEY"):
                env.pop(key, None)
            payload = {"source": source, "configuration": config, "intervals": intervals}
            data = json.loads(command([sys.executable, str(worker), json.dumps(payload)],
                                      timeout, env=env))
        statistics = data.get("statistics", {})
        warnings.extend(data.get("warnings", []))
        errors = data.get("errors", [])
        status = data.get("status", "success")
        if status in {"failed", "skipped", "unavailable"}:
            return Result(status=status, warnings=warnings, errors=errors, statistics=statistics)
        evidence = derive(data["samples"], intervals, config["crop"], config["equipment_classes"])
        evidence["tracking_intervals"] = intervals
        warnings.extend([
            "Machine evidence only; no exercise, rep, technique, pain, injury, or failure conclusions.",
            "Box coverage is not anatomical visibility; undetected equipment may still be essential.",
            "Sampled tracking can lose identity during crossings or rapid motion; increase cadence if needed.",
        ])
        if status == "success" and not evidence["detections"]:
            status = "no_results"
        return Result(status=status, evidence=evidence, warnings=warnings, errors=errors, statistics=statistics)
