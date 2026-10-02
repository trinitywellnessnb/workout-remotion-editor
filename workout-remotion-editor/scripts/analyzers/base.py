"""Small provider contract and bounded subprocess execution."""
from __future__ import annotations

import copy
import json
import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Protocol


class Unavailable(RuntimeError):
    """An optional executable or Python package is missing."""


@dataclass
class Result:
    status: str = "success"
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    """Legacy providers accept source/timeout; consumes_context providers accept isolated prior evidence."""
    name: str
    category: str
    upstream: str
    version: str | None
    configuration: dict[str, Any]

    def analyze(self, source: dict[str, Any], timeout: float) -> Result: ...


def executable(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise Unavailable(f"{name} is not installed or is not on PATH")
    return path


def command(args: list[str], timeout: float, limit: int = 64 * 1024 * 1024,
            *, env: dict[str, str] | None = None) -> str:
    """Never use a shell; cap output and terminate a timed-out analyzer.

    File-backed output avoids retaining a long video's per-sample stdout in RAM.
    """
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        options = {"env": env} if env is not None else {}
        completed = subprocess.run(args, stdout=output, stderr=errors, timeout=timeout, check=False, **options)
        errors.seek(0)
        diagnostic = errors.read(4096).decode("utf-8", errors="replace")
        if completed.returncode:
            raise RuntimeError(f"{args[0]} exited {completed.returncode}: {diagnostic.strip()}")
        if output.tell() > limit:
            raise RuntimeError(f"{args[0]} output exceeds {limit} bytes")
        output.seek(0)
        return output.read().decode("utf-8")


def number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not a media measurement")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("media measurement must be finite")
    return result


def run_provider(provider: Provider, source: dict[str, Any], timeout: float,
                 invocation: int | None = None,
                 context: dict[str, Any] | None = None) -> tuple[dict[str, Any], Result]:
    configuration: dict[str, Any] = {}
    version: str | None = None

    def identifier() -> str:
        prefix = f"{source['id']}:{provider.category}:{provider.name}"
        return prefix if invocation is None else f"{prefix}:{invocation}"

    try:
        if getattr(provider, "consumes_context", False):
            result = copy.deepcopy(provider.analyze(copy.deepcopy(source), timeout, copy.deepcopy(context or {})))
        else:
            result = copy.deepcopy(provider.analyze(copy.deepcopy(source), timeout))
        run_id = identifier()
        if not isinstance(result, Result):
            raise ValueError("provider must return Result")
        if result.status not in {"success", "partial", "no_results", "unavailable", "failed", "skipped"}:
            raise ValueError("invalid provider status")
        if not isinstance(result.statistics, dict):
            raise ValueError("provider statistics must be an object")
        if not isinstance(result.metadata, dict) or not isinstance(result.evidence, dict):
            raise ValueError("provider metadata and evidence must be objects")
        for messages in (result.warnings, result.errors):
            if not isinstance(messages, list) or any(not isinstance(item, str) for item in messages):
                raise ValueError("provider diagnostics must be lists of strings")
        local_ids = {item["id"] for items in result.evidence.values() if isinstance(items, list)
                     for item in items if isinstance(item, dict) and isinstance(item.get("id"), str)}

        def references(value: Any, key: str = "") -> Any:
            # Only references defined by this result are local. Earlier runs retain their namespace.
            if key in {"entity_id", "scene_id", "interval_id"} and isinstance(value, str) and value in local_ids:
                return f"{run_id}:{value}"
            if key in {"detection_ids", "entity_ids", "region_ids"} and isinstance(value, list):
                return [f"{run_id}:{ref}" if ref in local_ids else ref for ref in value]
            if isinstance(value, dict):
                return {name: references(child, name) for name, child in value.items()}
            if isinstance(value, list):
                return [references(child) for child in value]
            return value

        for collection, items in result.evidence.items():
            if not isinstance(collection, str) or not isinstance(items, list):
                raise ValueError("provider evidence collections must be lists")
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError("provider evidence items must be objects")
                if isinstance(item.get("id"), str):
                    item["id"] = f"{run_id}:{item['id']}"
                if "signal_ids" in item:
                    signal_refs = item["signal_ids"]
                    if not isinstance(signal_refs, list) or any(not isinstance(ref, str) for ref in signal_refs):
                        raise ValueError("signal_ids must be a list of strings")
                    item["signal_ids"] = [f"{run_id}:{ref}" for ref in signal_refs]
                normalized = references(item)
                item.clear()
                item.update(normalized, source_id=source["id"], run_id=run_id)
        # Non-JSON values must not escape the isolation boundary.
        json.dumps({"metadata": result.metadata, "evidence": result.evidence, "statistics": result.statistics}, allow_nan=False)
    except Unavailable as exc:
        result = Result(status="unavailable", warnings=[str(exc)])
    except Exception as exc:  # Provider isolation includes normalization, not only tool execution.
        result = Result(status="failed", errors=[str(exc)])
    # Provenance can also contain malformed upstream values after a tool failure.
    try:
        if provider.version is not None and not isinstance(provider.version, str):
            raise ValueError("provider version must be a string or null")
        version = provider.version
        if not isinstance(provider.configuration, dict):
            raise ValueError("provider configuration must be an object")
        json.dumps(provider.configuration, allow_nan=False)
        configuration = copy.deepcopy(provider.configuration)
    except Exception as exc:
        result = Result(status="failed", errors=result.errors + [f"Invalid provider provenance: {exc}"])
    run_id = identifier()
    run = {
        "id": run_id, "source_id": source["id"], "category": provider.category,
        "provider": provider.name, "version": version, "upstream": provider.upstream,
        "status": result.status, "configuration": configuration,
        "fallback": result.status != "success",
        "warnings": result.warnings, "errors": result.errors,
    }
    if result.statistics:
        run["statistics"] = copy.deepcopy(result.statistics)
    return run, result


def json_output(args: list[str], timeout: float) -> Any:
    return json.loads(command(args, timeout))
