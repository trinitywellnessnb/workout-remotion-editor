"""Contracts shared by repetition rules and the generic orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RuleResult:
    candidates: list[dict[str, Any]]
    warnings: list[str]


class RepetitionRule(Protocol):
    rule_id: str
    version: str
    canonical_exercise_id: str

    def resolve_side(
        self, poses: list[dict[str, Any]], explicit_side: str | None = None
    ) -> str | None: ...
    def gates(
        self, poses: list[dict[str, Any]], side: str
    ) -> list[tuple[str, bool, str | None]]: ...
    def analyze(
        self, poses: list[dict[str, Any]], side: str, provenance: dict[str, Any]
    ) -> RuleResult: ...
