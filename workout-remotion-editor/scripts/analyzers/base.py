"""Small provider contract and bounded subprocess execution."""
from __future__ import annotations

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


class Provider(Protocol):
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


def command(args: list[str], timeout: float, limit: int = 64 * 1024 * 1024) -> str:
    """Never use a shell; cap output and terminate a timed-out analyzer.

    File-backed output avoids retaining a long video's per-sample stdout in RAM.
    """
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        completed = subprocess.run(args, stdout=output, stderr=errors, timeout=timeout, check=False)
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


def run_provider(provider: Provider, source: dict[str, Any], timeout: float) -> tuple[dict[str, Any], Result]:
    try:
        result = provider.analyze(source, timeout)
    except Unavailable as exc:
        result = Result(status="unavailable", warnings=[str(exc)])
    except Exception as exc:  # Provider isolation: optional tools cannot abort the workflow.
        result = Result(status="failed", errors=[str(exc)])
    run_id = f"{source['id']}:{provider.category}:{provider.name}"
    run = {
        "id": run_id, "source_id": source["id"], "category": provider.category,
        "provider": provider.name, "version": provider.version, "upstream": provider.upstream,
        "status": result.status, "configuration": provider.configuration,
        "fallback": result.status != "success",
        "warnings": result.warnings, "errors": result.errors,
    }
    for items in result.evidence.values():
        for item in items:
            item.update(source_id=source["id"], run_id=run_id)
    return run, result


def json_output(args: list[str], timeout: float) -> Any:
    return json.loads(command(args, timeout))
