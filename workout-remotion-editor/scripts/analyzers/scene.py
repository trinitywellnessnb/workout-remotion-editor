"""PySceneDetect adapter, executed in a timeout-controlled worker."""
from __future__ import annotations

import importlib.util
from importlib import metadata
import json
import sys
from pathlib import Path
from typing import Any

from .base import Result, Unavailable, command


class Scene:
    name = "pyscenedetect"
    category = "scene"
    upstream = "https://github.com/Breakthrough/PySceneDetect"
    version: str | None = None

    def __init__(self, detector: str = "adaptive", threshold: float | None = None,
                 min_scene_seconds: float = 0.5, backend: str = "pyav"):
        self.configuration = {"detector": detector, "threshold": threshold,
                              "min_scene_seconds": min_scene_seconds, "backend": backend}

    def analyze(self, source: dict[str, Any], timeout: float) -> Result:
        if importlib.util.find_spec("scenedetect") is None:
            raise Unavailable("PySceneDetect is not installed")
        for distribution in ("scenedetect-headless", "scenedetect"):
            try:
                self.version = metadata.version(distribution)
                break
            except metadata.PackageNotFoundError:
                continue
        if self.configuration["backend"] == "pyav":
            try:
                self.configuration["backend_version"] = metadata.version("av")
            except metadata.PackageNotFoundError:
                self.configuration["backend_version"] = None
        if source["duration"] is None:
            return Result(status="skipped", warnings=["Scene analysis requires known duration."])
        worker = Path(__file__).with_name("scene_worker.py")
        data = json.loads(command([sys.executable, str(worker), source["path"],
                                   json.dumps(self.configuration)], timeout))
        self.version = data["version"]
        if not self.version.startswith("0.7."):
            raise ValueError(f"unsupported PySceneDetect version: {self.version}; install 0.7.1")
        detector = self.configuration["detector"]
        scenes, boundaries = [], []
        warnings = ["Scene boundaries are evidence only; neither sets nor confirmed decoding defects."]
        for index, (start, end) in enumerate(data["scenes"]):
            # PySceneDetect ends its final range at last PTS + one nominal frame.
            # For VFR this can exceed the probed video end by a fraction of a sample.
            if index == len(data["scenes"]) - 1 and end > source["duration"]:
                tolerance = data.get("nominal_frame_seconds", 1 / source["fps"] if source.get("fps") else 1e-3)
                if end <= source["duration"] + tolerance + 1e-6:
                    warnings.append(
                        f"Final scene end {end:.6f}s bounded to probed duration "
                        f"{source['duration']:.6f}s (nominal-frame end estimate).")
                    end = source["duration"]
            scenes.append({"id": f"{source['id']}:scene:{index}", "start": start, "end": end,
                           "detector": detector, "reason": "Detected shot range; not a workout set."})
            if index:
                boundaries.append({"id": f"{source['id']}:boundary:{index}", "time": start,
                                   "detector": detector,
                                   "kind": "fade_candidate" if detector == "threshold" else "hard_cut_candidate",
                                   "reason": "Brightness threshold transition." if detector == "threshold"
                                   else "Visual discontinuity candidate; confirm against footage."})
        if data.get("decode_failures", 0):
            warnings.append(f"{data['decode_failures']} frames failed to decode; evidence may be incomplete.")
        if not boundaries:
            warnings.append("No useful internal shot boundaries detected; continue visual analysis.")
        return Result(status="partial" if data.get("decode_failures", 0) else "success" if boundaries else "no_results",
                      evidence={"scenes": scenes, "scene_boundaries": boundaries}, warnings=warnings)
