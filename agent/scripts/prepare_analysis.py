#!/usr/bin/env python3
"""Prepare validated media evidence and an explicit Director-to-Editor handoff."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parents[2] / "workout-remotion-editor/scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_video import analyze, positive
from analyzers.base import Provider
from analyzers.motion_activity import MotionActivity
from analyzers.scene import Scene
from validate_analysis import EVIDENCE_COLLECTIONS, validate_document


def summarize(document: dict[str, Any]) -> dict[str, Any]:
    """Route generic evidence/status data, without interpreting workout activity."""
    counts = {name: len(document.get("evidence", {}).get(name, [])) for name in EVIDENCE_COLLECTIONS}
    available = any(counts.values())
    return {
        "handoff_version": "1.0",
        "status": "ready_for_visual_review" if available else "manual_review_required",
        "stage": "INSPECT",
        "next_state": "INSPECT",
        "analysis_file": "analysis.json",
        "analysis_schema_version": document["schema_version"],
        "machine_evidence_available": available,
        "evidence_counts": counts,
        "sources": [
            {"source_id": source["id"], "path": source["path"], "duration": source["duration"],
             "timing_requires_verification": source["duration"] is None}
            for source in document["sources"]
        ],
        "analyzer_runs": [
            {key: run[key] for key in ("id", "source_id", "category", "provider", "version",
                                      "status", "fallback", "warnings", "errors")}
            for run in document.get("evidence", {}).get("runs", [])
        ],
        "editor_review_required": True,
        "instructions": [
            "Inspect every source visually before DIRECT; use Workout Remotion Editor for workout judgment.",
            "Pass analysis.json and the user request to the Editor at DELEGATE_SKILL.",
            "Scene boundaries are not workout-set boundaries.",
            "Low motion and quiet audio never authorize removal of meaningful footage.",
            "Keep source-relative seconds canonical; convert accepted timing to frames at Remotion composition.",
            "Unknown duration requires verified probing or manual timing before timed editorial events.",
            "Validate the Editor's completed analysis/edit document before IMPLEMENT_REMOTION.",
        ],
    }


def prepare(sources: list[Path], output_dir: Path, *, title: str = "Workout analysis",
            mode: str = "standard", timeout: float = 300,
            providers: list[Provider] | None = None,
            supplied_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if not sources or any(not source.is_file() for source in sources):
        raise ValueError("provide at least one existing source video")
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError("output directory already exists; choose a new job directory")
    document = analyze(sources, title=title, mode=mode, timeout=timeout,
                       providers=providers, supplied_metadata=supplied_metadata)
    errors = validate_document(document)
    if errors:
        raise ValueError("invalid analysis; do not hand it to the Editor: " + "; ".join(errors))
    handoff = summarize(document)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive directory creation prevents overwriting a source or prior job.
    output_dir.mkdir()
    created: list[Path] = []
    try:
        for filename, data in (("analysis.json", document), ("handoff.json", handoff)):
            path = output_dir / filename
            with path.open("x", encoding="utf-8") as handle:
                created.append(path)
                json.dump(data, handle, indent=2, allow_nan=False)
                handle.write("\n")
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        output_dir.rmdir()
        raise
    return handoff


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path, help="new job directory; never overwritten")
    parser.add_argument("--title", default="Workout analysis")
    parser.add_argument("--mode", choices=["quick", "standard", "extended"], default="standard")
    parser.add_argument("--timeout", type=positive, default=300, help="timeout per tool invocation")
    parser.add_argument("--duration", type=positive, help="manual duration fallback; single input only")
    parser.add_argument("--skip-scene", action="store_true")
    parser.add_argument("--skip-activity", action="store_true")
    args = parser.parse_args()
    if args.duration is not None and len(args.videos) != 1:
        parser.error("--duration requires exactly one input")
    providers: list[Provider] = []
    if not args.skip_scene:
        providers.append(Scene())
    if not args.skip_activity:
        providers.append(MotionActivity())
    try:
        handoff = prepare(args.videos, args.output_dir, title=args.title, mode=args.mode,
                          timeout=args.timeout, providers=providers,
                          supplied_metadata={"duration": args.duration} if args.duration else None)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for run in handoff["analyzer_runs"]:
        print(f"{run['source_id']} {run['provider']}: {run['status']}", file=sys.stderr)
    print(f"{handoff['status']}: {args.output_dir / 'handoff.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
