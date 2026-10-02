"""Private worker using only PySceneDetect's documented public API."""
from __future__ import annotations

import json
import sys


def main() -> None:
    import scenedetect
    from scenedetect import AdaptiveDetector, ContentDetector, SceneManager, ThresholdDetector
    from scenedetect.backends import AVAILABLE_BACKENDS

    if not scenedetect.__version__.startswith("0.7."):
        raise ValueError("PySceneDetect 0.7.x is required; install the tested 0.7.1 release")
    config = json.loads(sys.argv[2])
    detectors = {"adaptive": AdaptiveDetector, "content": ContentDetector, "threshold": ThresholdDetector}
    options = {"min_scene_len": float(config["min_scene_seconds"])}
    if config["threshold"] is not None:
        key = "adaptive_threshold" if config["detector"] == "adaptive" else "threshold"
        options[key] = config["threshold"]
    backend = config["backend"]
    if backend not in AVAILABLE_BACKENDS:
        raise ValueError(f"{backend} backend is not installed; install requirements-scene.txt or select opencv")
    # Instantiate the documented backend directly: open_video/detect can silently
    # substitute OpenCV, which would misstate provenance for timestamp-sensitive inputs.
    video = AVAILABLE_BACKENDS[backend](sys.argv[1])
    manager = SceneManager()
    manager.add_detector(detectors[config["detector"]](**options))
    manager.detect_scenes(video=video, show_progress=False)
    scenes = manager.get_scene_list()
    print(json.dumps({"version": scenedetect.__version__, "backend": backend,
                      "nominal_frame_seconds": float(1 / video.frame_rate),
                      "decode_failures": video.decode_failures,
                      "scenes": [[float(start.seconds), float(end.seconds)] for start, end in scenes]},
                     allow_nan=False))


if __name__ == "__main__":
    main()
