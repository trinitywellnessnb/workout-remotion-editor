"""Conservative single-arm dumbbell-row repetition state machine.

Coordinates are image-plane evidence, not a form assessment.  The compound
signal requires torso-relative wrist retraction and elbow-flexion agreement.
"""

from __future__ import annotations

import math
from statistics import median
from typing import Any

from .base import RuleResult


class DumbbellRowSingleArmV1:
    rule_id = "single_arm_dumbbell_row_v1"
    version = "1"
    canonical_exercise_id = "dumbbell_row_single_arm"
    minimum_rate = 6.0
    maximum_interval = 0.167
    bottom_enter, bottom_exit = 0.15, 0.25
    top_enter, top_exit = 0.80, 0.70
    min_bottom, min_pull, min_top, min_return, min_rep = 0.15, 0.20, 0.10, 0.20, 0.65
    min_elbow_excursion = 25.0
    min_path_excursion = 0.12

    @staticmethod
    def _points(pose: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {p["name"]: p for p in pose["keypoints"] if p.get("state") == "visible"}

    @staticmethod
    def _angle(a: dict[str, Any], b: dict[str, Any], c: dict[str, Any]) -> float | None:
        u, v = (a["x"] - b["x"], a["y"] - b["y"]), (c["x"] - b["x"], c["y"] - b["y"])
        d = math.hypot(*u) * math.hypot(*v)
        return (
            None
            if d < 1e-8
            else math.degrees(
                math.acos(max(-1.0, min(1.0, (u[0] * v[0] + u[1] * v[1]) / d)))
            )
        )

    def _metric(
        self, pose: dict[str, Any], side: str
    ) -> tuple[float, float, float] | None:
        p = self._points(pose)
        names = [f"{side}_shoulder", f"{side}_elbow", f"{side}_wrist"]
        if any(n not in p for n in names):
            return None
        shoulder, elbow, wrist = (p[n] for n in names)
        refs = [
            p.get(n)
            for n in ("left_shoulder", "right_shoulder", "left_hip", "right_hip")
        ]
        refs = [x for x in refs if x]
        if len(refs) < 3:
            return None
        torso = max(
            math.hypot(a["x"] - b["x"], a["y"] - b["y"]) for a in refs for b in refs
        )
        if torso < 0.04:
            return None
        # Radial shoulder-relative retraction is camera-translation invariant.
        wrist_path = (
            -math.hypot(wrist["x"] - shoulder["x"], wrist["y"] - shoulder["y"]) / torso
        )
        angle = self._angle(shoulder, elbow, wrist)
        return (wrist_path, angle if angle is not None else 180.0, torso)

    def resolve_side(
        self, poses: list[dict[str, Any]], explicit_side: str | None = None
    ) -> str | None:
        if explicit_side in {"left", "right"}:
            return explicit_side
        amplitudes = {}
        for side in ("left", "right"):
            values = [
                m[0] for pose in poses if (m := self._metric(pose, side)) is not None
            ]
            amplitudes[side] = max(values) - min(values) if len(values) >= 4 else 0
        large, small = sorted(amplitudes, key=amplitudes.get, reverse=True)
        return (
            large
            if amplitudes[large] >= self.min_path_excursion
            and amplitudes[large] >= 1.8 * max(amplitudes[small], 0.02)
            else None
        )

    def gates(
        self, poses: list[dict[str, Any]], side: str
    ) -> list[tuple[str, bool, str | None]]:
        usable = [(p["timestamp"], self._metric(p, side)) for p in poses]
        usable = [(t, m) for t, m in usable if m is not None]
        intervals = [b[0] - a[0] for a, b in zip(usable, usable[1:]) if b[0] > a[0]]
        span = usable[-1][0] - usable[0][0] if len(usable) > 1 else 0
        rate = (len(usable) - 1) / span if span else 0
        path = [m[0] for _, m in usable]
        angles = [m[1] for _, m in usable]
        return [
            (
                "pose_association_unambiguous",
                bool(poses) and all(not p.get("association_ambiguous") for p in poses),
                "ambiguous_pose_association",
            ),
            (
                "required_landmarks_visible",
                len(usable) >= 6,
                "insufficient_required_landmarks",
            ),
            (
                "pose_coverage",
                bool(poses) and len(usable) / len(poses) >= 0.8,
                "insufficient_pose_coverage",
            ),
            (
                "sampling_rate",
                rate >= self.minimum_rate
                and bool(intervals)
                and median(intervals) <= self.maximum_interval,
                "sparse_pose_sampling",
            ),
            (
                "meaningful_path_amplitude",
                bool(path) and max(path) - min(path) >= self.min_path_excursion,
                "insufficient_amplitude",
            ),
            (
                "elbow_flexion_agreement",
                bool(angles) and max(angles) - min(angles) >= self.min_elbow_excursion,
                "insufficient_elbow_excursion",
            ),
        ]

    @staticmethod
    def _quantile(values: list[float], q: float) -> float:
        values = sorted(values)
        pos = (len(values) - 1) * q
        lo = int(pos)
        hi = min(lo + 1, len(values) - 1)
        return values[lo] + (values[hi] - values[lo]) * (pos - lo)

    def analyze(
        self, poses: list[dict[str, Any]], side: str, provenance: dict[str, Any]
    ) -> RuleResult:
        rows = [
            (p["timestamp"], *self._metric(p, side)[:2], p["id"])
            for p in poses
            if self._metric(p, side)
        ]
        paths, angles = [r[1] for r in rows], [r[2] for r in rows]
        plo, phi = self._quantile(paths, 0.15), self._quantile(paths, 0.85)
        ahi, alo = self._quantile(angles, 0.85), self._quantile(angles, 0.15)
        if phi - plo < self.min_path_excursion or ahi - alo < self.min_elbow_excursion:
            return RuleResult([], ["Calibration envelope failed absolute safeguards."])
        signals = []
        for t, path, angle, ref in rows:
            wp = (path - plo) / (phi - plo)
            ep = (ahi - angle) / (ahi - alo)
            signals.append((t, max(0.0, min(1.0, 0.65 * wp + 0.35 * ep)), wp, ep, ref))
        state = "seeking_bottom"
        bottom = []
        top = []
        start = None
        phases = {}
        support = []
        candidates = []
        seq = 0
        peak = 0.0

        def emit(status: str, end: float, reason: str):
            nonlocal seq, start, phases, support, peak
            seq += 1
            complete_components = {
                "exercise_candidate_quality": provenance["exercise_quality"],
                "landmark_coverage": 1.0,
                "temporal_regularity": 1.0,
                "state_completeness": 1.0 if status != "incomplete" else 0.55,
                "amplitude": min(1.0, peak),
                "wrist_elbow_agreement": max(
                    0.0,
                    1.0
                    - median(
                        [
                            abs(x[2] - x[3])
                            for x in signals
                            if (start or 0) <= x[0] <= end
                        ]
                    ),
                ),
            }
            quality = max(
                0.0,
                min(1.0, sum(complete_components.values()) / len(complete_components)),
            )
            actual = (
                "uncertain"
                if status == "completed" and quality < provenance["min_quality"]
                else status
            )
            durations = {}
            for label, a, b in (
                ("concentric_pull", "pull_departure", "top_confirmation"),
                (
                    "eccentric_return",
                    "return_departure",
                    "final_completion_confirmation",
                ),
            ):
                if a in phases and b in phases:
                    durations[label] = round(phases[b] - phases[a], 6)
            candidate = {
                **provenance,
                "id": f"rep-candidate-{provenance['rep_analysis_interval_id']}-{seq}",
                "working_side": side,
                "sequence_index": seq,
                "start": start,
                "end": end,
                "status": actual,
                "completion_reason": reason if actual != "incomplete" else None,
                "incompletion_reason": reason if actual == "incomplete" else None,
                "phases": dict(phases),
                "quality": round(quality, 6),
                "quality_components": complete_components,
                "uncertainty_reasons": ["quality_below_policy"]
                if actual == "uncertain"
                else [],
                "supporting_evidence_refs": list(dict.fromkeys(support)),
                "warnings": [],
                "measured_metrics": {
                    "peak_progress": round(peak, 6),
                    "wrist_path_envelope": round(phi - plo, 6),
                    "elbow_angle_excursion_degrees": round(ahi - alo, 6),
                },
                "observed_amplitude": {"compound_progress": round(peak, 6)},
                "phase_durations": durations,
                "temporal_coverage": 1.0,
                "gap_penalty": 0.0,
            }
            candidates.append(candidate)

        previous = None
        for t, v, wp, ep, ref in signals:
            if (
                previous is not None
                and t - previous
                > min(
                    0.25,
                    1.5 * median([b[0] - a[0] for a, b in zip(signals, signals[1:])]),
                )
                + 1e-6
            ):
                if start is not None and peak >= self.bottom_exit:
                    emit("incomplete", previous, "excessive_pose_gap")
                state = "seeking_bottom"
                start = None
                phases = {}
                support = []
                peak = 0.0
            previous = t
            if state == "seeking_bottom":
                if v <= self.bottom_enter:
                    bottom.append(t)
                else:
                    bottom = []
                if len(bottom) >= 2 and bottom[-1] - bottom[0] >= self.min_bottom:
                    state = "ready_bottom"
                    phases["initial_bottom_confirmation"] = bottom[-1]
            elif state == "ready_bottom" and v >= self.bottom_exit:
                state = "concentric_pull"
                start = t
                phases["pull_departure"] = t
                support = [ref]
                peak = v
            elif state == "concentric_pull":
                support.append(ref)
                peak = max(peak, v)
                if v >= self.top_enter and t - start >= self.min_pull:
                    top.append(t)
                elif top:
                    top = []
                if len(top) >= 2 and top[-1] - top[0] >= self.min_top:
                    state = "top_confirmed"
                    phases.update(top_entry=top[0], top_confirmation=top[-1])
            elif state == "top_confirmed" and v <= self.top_exit:
                state = "eccentric_return"
                phases["return_departure"] = t
                support.append(ref)
            elif state == "eccentric_return":
                support.append(ref)
                if (
                    v <= self.bottom_enter
                    and t - phases["return_departure"] >= self.min_return
                ):
                    phases.update(bottom_reentry=t, final_completion_confirmation=t)
                    if t - start >= self.min_rep:
                        emit("completed", t, "ordered_cycle_complete")
                    else:
                        emit("incomplete", t, "interval_ended")
                    state = "seeking_bottom"
                    start = None
                    phases = {}
                    support = []
                    bottom = [t]
                    top = []
                    peak = 0.0
        if start is not None and peak >= self.bottom_exit + 0.1:
            emit(
                "incomplete",
                signals[-1][0],
                "no_return"
                if state in {"top_confirmed", "eccentric_return"}
                else "partial_pull",
            )
        return RuleResult(candidates, [])
