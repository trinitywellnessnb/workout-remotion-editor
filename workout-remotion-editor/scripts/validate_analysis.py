#!/usr/bin/env python3
"""Validate a Workout Remotion Editor v2.2 analysis JSON file."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).with_name("analysis-schema.json")
COLLECTIONS = ("segments", "repetitions", "audio_events")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc


def schema_errors(document: Any, schema: Any) -> list[str]:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        return basic_schema_errors(document)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = []
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.absolute_path)):
        location = "/" + "/".join(str(part) for part in error.absolute_path)
        errors.append(f"{location or '/'}: {error.message}")
    return errors


def basic_schema_errors(document: Any) -> list[str]:
    """Perform core validation when the optional jsonschema package is unavailable."""
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["/: must be an object"]
    allowed = {"schema_version", "project", "sources", "segments", "repetitions", "audio_events", "issues", "notes"}
    for key in document.keys() - allowed:
        errors.append(f"/{key}: unexpected property")
    for key in ("schema_version", "project", "sources", "segments"):
        if key not in document:
            errors.append(f"/{key}: required property is missing")
    if document.get("schema_version") != "2.2":
        errors.append("/schema_version: must equal '2.2'")
    project = document.get("project")
    if not isinstance(project, dict):
        errors.append("/project: must be an object")
    else:
        if not isinstance(project.get("title"), str) or not project.get("title"):
            errors.append("/project/title: must be a non-empty string")
        if project.get("mode") not in {"quick", "standard", "extended"}:
            errors.append("/project/mode: must be quick, standard, or extended")
    sources = document.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("/sources: must be a non-empty array")
    else:
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                errors.append(f"/sources/{index}: must be an object")
                continue
            if not isinstance(source.get("id"), str) or not source.get("id"):
                errors.append(f"/sources/{index}/id: must be a non-empty string")
            if not isinstance(source.get("path"), str) or not source.get("path"):
                errors.append(f"/sources/{index}/path: must be a non-empty string")
            duration = source.get("duration")
            if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
                errors.append(f"/sources/{index}/duration: must be greater than zero")
    for collection in COLLECTIONS:
        value = document.get(collection, [])
        if not isinstance(value, list):
            errors.append(f"/{collection}: must be an array")
            continue
        for index, event in enumerate(value):
            if not isinstance(event, dict):
                errors.append(f"/{collection}/{index}: must be an object")
                continue
            for key in ("id", "source_id", "start", "end", "confidence"):
                if key not in event:
                    errors.append(f"/{collection}/{index}/{key}: required property is missing")
            if event.get("confidence") not in {"low", "medium", "high"}:
                errors.append(f"/{collection}/{index}/confidence: invalid value")
            if collection != "repetitions" and (not isinstance(event.get("type"), str) or not event.get("type")):
                errors.append(f"/{collection}/{index}/type: must be a non-empty string")
            if collection == "repetitions" and not isinstance(event.get("complete"), bool):
                errors.append(f"/{collection}/{index}/complete: must be boolean")
    return errors


def semantic_errors(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sources = {source["id"]: source for source in document.get("sources", []) if isinstance(source, dict) and "id" in source}
    if len(sources) != len(document.get("sources", [])):
        errors.append("/sources: source IDs must be unique")

    seen: set[str] = set()
    segment_ids = {item.get("id") for item in document.get("segments", []) if isinstance(item, dict)}
    for collection in COLLECTIONS:
        for index, event in enumerate(document.get(collection, [])):
            if not isinstance(event, dict):
                continue
            prefix = f"/{collection}/{index}"
            event_id = event.get("id")
            if event_id in seen:
                errors.append(f"{prefix}/id: event ID {event_id!r} is not unique")
            elif isinstance(event_id, str):
                seen.add(event_id)
            source = sources.get(event.get("source_id"))
            if source is None:
                errors.append(f"{prefix}/source_id: unknown source {event.get('source_id')!r}")
            start, end = event.get("start"), event.get("end")
            if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                if not (math.isfinite(start) and math.isfinite(end)):
                    errors.append(f"{prefix}: times must be finite")
                elif end <= start:
                    errors.append(f"{prefix}: end must be greater than start")
                elif source and end > source["duration"] + 1e-6:
                    errors.append(f"{prefix}/end: exceeds source duration {source['duration']}")
            segment_id = event.get("segment_id")
            if collection == "repetitions" and segment_id is not None and segment_id not in segment_ids:
                errors.append(f"{prefix}/segment_id: unknown segment {segment_id!r}")

    for index, issue in enumerate(document.get("issues", [])):
        if isinstance(issue, dict) and issue.get("source_id") is not None and issue["source_id"] not in sources:
            errors.append(f"/issues/{index}/source_id: unknown source {issue['source_id']!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path, help="analysis JSON to validate")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH, help="schema path")
    args = parser.parse_args()
    try:
        document, schema = load_json(args.analysis), load_json(args.schema)
        errors = schema_errors(document, schema)
        if not errors and isinstance(document, dict):
            errors.extend(semantic_errors(document))
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    print(f"Validation passed: {args.analysis}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
