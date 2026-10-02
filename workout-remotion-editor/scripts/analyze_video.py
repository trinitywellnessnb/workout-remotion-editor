#!/usr/bin/env python3
"""Probe video and collect optional evidence without making editing decisions."""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

from analyzers.base import Provider, run_provider
from analyzers.media_probe import MediaProbe
from analyzers.motion_activity import MotionActivity
from analyzers.scene import Scene
from analyzers.object_tracking import YoloObjectTracking
from analyzers.pose import MMPoseProvider
from validate_analysis import validate_document


def analyze(sources: list[Path], *, title: str = "Workout analysis", mode: str = "standard",
            providers: list[Provider] | None = None, timeout: float = 300,
            supplied_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Director-callable workflow; failures are represented in the shared document."""
    document: dict[str, Any] = {
        "schema_version": "2.4", "project": {"title": title, "mode": mode},
        "sources": [], "segments": [], "evidence": {"runs": []},
        "notes": ["Machine evidence only. Workout Remotion Editor must review footage before editing."],
    }
    for index, path in enumerate(sources):
        source: dict[str, Any] = {"id": f"source-{index + 1}", "path": str(path.resolve()), "duration": None}
        document["sources"].append(source)
        pipeline = [MediaProbe(supplied_metadata), *(providers if providers is not None else [Scene(), MotionActivity()])]
        for invocation, provider in enumerate(pipeline):
            before = copy.deepcopy(document)
            provider_source = source
            if provider.category in {"object_tracking", "pose"}:
                provider_source = {**source, "_analysis_context": {
                    "scenes": [item for item in document["evidence"].get("scenes", [])
                               if item["source_id"] == source["id"]],
                    "activity_regions": [item for item in document["evidence"].get("activity_regions", [])
                                         if item["source_id"] == source["id"]],
                    "object_detections": [item for item in document["evidence"].get("object_detections", [])
                                          if item["source_id"] == source["id"]],
                    "tracked_entities": [item for item in document["evidence"].get("tracked_entities", [])
                                         if item["source_id"] == source["id"]]}}
            run, result = run_provider(provider, provider_source, timeout, invocation=invocation)
            document["evidence"]["runs"].append(run)
            source.update(result.metadata)
            if provider.category == "media_probe":
                source["probe_run_id"] = run["id"]
            for collection, items in result.evidence.items():
                document["evidence"].setdefault(collection, []).extend(items)
            errors = validate_document(document)
            if errors:
                # Quarantine malformed provider output, preserving all prior valid evidence.
                document = before
                source = document["sources"][-1]
                run.update(status="failed", fallback=True, errors=errors, warnings=run["warnings"] + [
                    "Invalid provider output discarded; continue existing visual/manual analysis."])
                document["evidence"]["runs"].append(run)
        # These lists are intentionally independent of editorial segments and timeline timing.
    errors = validate_document(document)
    if errors:
        raise ValueError("Analysis package failed validation: " + "; ".join(errors))
    return document


def positive(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and greater than zero")
    return number


def unit(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0 < number <= 1:
        raise argparse.ArgumentTypeError("must be in (0, 1]")
    return number


def sampling_rate(value: str) -> str:
    try:
        rate = Fraction(value)
        if rate <= 0 or rate > 120:
            raise ValueError
    except (ValueError, ZeroDivisionError) as exc:
        raise argparse.ArgumentTypeError("timebase must be a positive rational rate up to 120") from exc
    return str(rate)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("analysis.json"))
    parser.add_argument("--title", default="Workout analysis")
    parser.add_argument("--mode", choices=["quick", "standard", "extended"], default="standard")
    parser.add_argument("--scene-detector", choices=["adaptive", "content", "threshold"], default="adaptive")
    parser.add_argument("--scene-threshold", type=positive)
    parser.add_argument("--min-scene-seconds", type=positive, default=0.5)
    parser.add_argument("--scene-backend", choices=["opencv", "pyav"], default="pyav")
    parser.add_argument("--motion-threshold", type=unit, default=0.02)
    parser.add_argument("--audio-threshold", type=unit, default=0.04)
    parser.add_argument("--timebase", type=sampling_rate, default="30/1",
                        help="Auto-Editor logical samples/second, independent of source/render fps")
    parser.add_argument("--minimum-candidate-seconds", type=positive, default=2.0)
    parser.add_argument("--timeout", type=positive, default=300, help="timeout per tool invocation")
    parser.add_argument("--duration", type=positive, help="manual duration fallback; single input only")
    parser.add_argument("--skip-scene", action="store_true")
    parser.add_argument("--skip-activity", action="store_true")
    parser.add_argument("--object-tracking", action="store_true",
                        help="enable optional local Ultralytics YOLO evidence")
    parser.add_argument("--yolo-model", default="yolo11n.pt",
                        help="local model path unless --allow-model-download is set")
    parser.add_argument("--yolo-device", default="cpu", help="Ultralytics device, e.g. cpu, mps, 0")
    parser.add_argument("--yolo-sample-rate", type=positive, default=2.0, help="analyzed samples/second")
    parser.add_argument("--yolo-tracker", choices=["bytetrack.yaml", "botsort.yaml"], default="bytetrack.yaml")
    parser.add_argument("--yolo-confidence", type=unit, default=.25)
    parser.add_argument("--allow-model-download", action="store_true",
                        help="permit Ultralytics to fetch a named model (may access the network)")
    parser.add_argument("--pose", action="store_true", help="enable optional local MMPose evidence")
    parser.add_argument("--pose-config", help="local MMPose model config path")
    parser.add_argument("--pose-checkpoint", help="local MMPose checkpoint path")
    parser.add_argument("--pose-device", default="cpu", help="explicit MMPose device (default: cpu)")
    parser.add_argument("--pose-sample-rate", type=positive, default=2.0)
    parser.add_argument("--pose-mode", choices=["cpu_basic", "balanced", "high_accuracy"], default="cpu_basic")
    parser.add_argument("--pose-keypoint-threshold", type=unit, default=.25)
    parser.add_argument("--pose-all-persons", action="store_true")
    args = parser.parse_args()
    if args.duration is not None and len(args.videos) != 1:
        parser.error("--duration requires exactly one input")
    for video in args.videos:
        if not video.is_file():
            parser.error(f"input video does not exist: {video}")
    output = args.output.resolve()
    if any(output == video.resolve() for video in args.videos):
        parser.error("output cannot overwrite a source video")
    providers: list[Provider] = []
    if not args.skip_scene:
        providers.append(Scene(args.scene_detector, args.scene_threshold,
                               args.min_scene_seconds, args.scene_backend))
    if not args.skip_activity:
        providers.append(MotionActivity(args.motion_threshold, args.audio_threshold,
                                        args.timebase, args.minimum_candidate_seconds))
    if args.object_tracking:
        providers.append(YoloObjectTracking(args.yolo_model, args.yolo_device, args.yolo_sample_rate,
                                            args.yolo_tracker, args.yolo_confidence,
                                            args.allow_model_download))
    if args.pose:
        providers.append(MMPoseProvider(args.pose_config, args.pose_checkpoint, args.pose_device,
                                        args.pose_sample_rate, args.pose_mode,
                                        args.pose_keypoint_threshold, args.pose_all_persons,
                                        args.allow_model_download))
    try:
        document = analyze(args.videos, title=args.title, mode=args.mode, providers=providers,
                           timeout=args.timeout,
                           supplied_metadata={"duration": args.duration} if args.duration else None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Validate before writing; atomic replacement avoids a partial analysis file.
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(document, handle, indent=2, allow_nan=False)
            handle.write("\n")
        try:
            temporary.replace(args.output)
        finally:
            temporary.unlink(missing_ok=True)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for run in document["evidence"]["runs"]:
        print(f"{run['source_id']} {run['provider']}: {run['status']}", file=sys.stderr)
    print(f"Validated evidence: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
