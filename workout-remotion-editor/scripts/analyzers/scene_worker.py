"""Private worker using only PySceneDetect's documented public API."""
from __future__ import annotations

import json
import sys


def main() -> None:
    import scenedetect
    from scenedetect import AdaptiveDetector, ContentDetector, ThresholdDetector, detect

    if not scenedetect.__version__.startswith("0.7."):
        raise ValueError("PySceneDetect 0.7.x is required; install the tested 0.7.1 release")
    config = json.loads(sys.argv[2])
    detectors = {"adaptive": AdaptiveDetector, "content": ContentDetector, "threshold": ThresholdDetector}
    options = {"min_scene_len": float(config["min_scene_seconds"])}
    if config["threshold"] is not None:
        key = "adaptive_threshold" if config["detector"] == "adaptive" else "threshold"
        options[key] = config["threshold"]
    scenes = detect(sys.argv[1], detectors[config["detector"]](**options),
                    backend=config["backend"], show_progress=False)
    print(json.dumps({"version": scenedetect.__version__,
                      "scenes": [[float(start.seconds), float(end.seconds)] for start, end in scenes]},
                     allow_nan=False))


if __name__ == "__main__":
    main()
