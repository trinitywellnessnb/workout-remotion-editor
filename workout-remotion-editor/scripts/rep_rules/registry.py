"""Exact repetition-rule registry.  Family and parent fallbacks are forbidden."""

from __future__ import annotations

from .dumbbell_row_single_arm_v1 import DumbbellRowSingleArmV1

_RULES = {
    (
        DumbbellRowSingleArmV1.canonical_exercise_id,
        DumbbellRowSingleArmV1.rule_id,
    ): DumbbellRowSingleArmV1
}


def get_rule(canonical_exercise_id: str, rule_id: str):
    rule = _RULES.get((canonical_exercise_id, rule_id))
    return rule() if rule else None


def mappings() -> dict[str, str]:
    return {exercise: rule for exercise, rule in _RULES}
