#!/usr/bin/env python3
"""Phase 6 gold annotation, evaluation, review, and editorial promotion tools."""

from __future__ import annotations

import argparse
import copy
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SIDES = {"left", "right", "unknown"}
SPLITS = {"development", "held_out"}
STATUSES = {"completed", "incomplete", "uncertain"}
DECISIONS = {"accept", "reject", "adjust", "mark_incomplete", "mark_uncertain"}
ADJUDICATION_STATUSES = {
    "agreed",
    "timing_adjusted",
    "status_disagreement",
    "rep_missing",
    "false_rep_annotation",
    "side_disagreement",
    "boundary_disagreement",
    "excluded",
}
FP_REASONS = {
    "setup",
    "pickup",
    "set-down",
    "rerack",
    "camera_motion",
    "torso_repositioning",
    "partial_pull",
    "state_bounce",
    "false_extremum",
    "track_reassignment",
    "wrong_side",
    "wrong_exercise_identity",
    "phase_boundary_error",
    "temporal_boundary_error",
    "pose_failure",
    "unknown",
}
FN_REASONS = {
    "sampling_too_sparse",
    "pose_occlusion",
    "wrist_missing",
    "elbow_missing",
    "side_unresolved",
    "amplitude_threshold_too_strict",
    "top_not_confirmed",
    "return_not_confirmed",
    "gap_reset",
    "camera_unsuitable",
    "candidate_identity_rejected",
    "interval_boundary",
    "unknown",
}


def read(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _ranges(
    rows: list[dict[str, Any]], prefix: str, duration: float | None
) -> list[str]:
    errors, seen, last = [], set(), -1.0
    for i, row in enumerate(rows):
        p = f"{prefix}/{i}"
        if not isinstance(row.get("id"), str) or not row["id"]:
            errors.append(f"{p}/id: non-empty ID required")
        elif row["id"] in seen:
            errors.append(f"{p}/id: duplicate ID")
        seen.add(row.get("id"))
        if row.get("status") not in STATUSES:
            errors.append(f"{p}/status: invalid status")
        if row.get("side") not in SIDES:
            errors.append(f"{p}/side: invalid side")
        start, end = row.get("start"), row.get("end")
        if (
            not isinstance(start, (int, float))
            or not isinstance(end, (int, float))
            or start >= end
        ):
            errors.append(f"{p}: start must be less than end")
            continue
        if start < last:
            errors.append(f"{p}: repetitions must be ordered")
        last = start
        if duration is not None and (start < 0 or end > duration):
            errors.append(f"{p}: outside source bounds")
        top = row.get("top")
        if top is not None and not start <= top <= end:
            errors.append(f"{p}/top: outside repetition")
        for name, timestamp in row.get("phases", {}).items():
            if not isinstance(timestamp, (int, float)) or not start <= timestamp <= end:
                errors.append(f"{p}/phases/{name}: outside repetition")
    return errors


def validate_annotation(doc: dict[str, Any]) -> list[str]:
    errors = []
    required = (
        "format_version",
        "annotation_id",
        "source_id",
        "media",
        "exercise",
        "canonical_exercise_id",
        "evaluation_interval",
        "split",
        "annotator",
        "repetitions",
    )
    errors += [f"/{x}: required" for x in required if x not in doc]
    if errors:
        return errors
    if doc["split"] not in SPLITS:
        errors.append("/split: must be development or held_out")
    interval = doc["evaluation_interval"]
    if not isinstance(interval, dict) or interval.get("start", -1) >= interval.get(
        "end", -1
    ):
        errors.append("/evaluation_interval: invalid range")
        return errors
    duration = doc.get("source_duration")
    if duration is not None and interval["end"] > duration:
        errors.append("/evaluation_interval: outside source bounds")
    errors += _ranges(doc["repetitions"], "/repetitions", duration)
    for key in (
        "excluded_intervals",
        "occlusion_intervals",
        "camera_motion_intervals",
        "setup_transitions",
    ):
        for i, row in enumerate(doc.get(key, [])):
            if row.get("start", -1) >= row.get("end", -1):
                errors.append(f"/{key}/{i}: invalid range")
    return errors


def validate_adjudication(
    doc: dict[str, Any], annotations: list[dict[str, Any]]
) -> list[str]:
    errors = []
    ids = {x.get("annotation_id") for x in annotations}
    refs = doc.get("annotation_ids", [])
    if len(refs) < 2 or any(x not in ids for x in refs):
        errors.append("/annotation_ids: at least two known annotations required")
    if (
        len(
            {
                annotations[[x.get("annotation_id") for x in annotations].index(r)].get(
                    "source_id"
                )
                for r in refs
                if r in ids
            }
        )
        > 1
    ):
        errors.append("/annotation_ids: annotations must share a source")
    duration = next(
        (
            x.get("source_duration")
            for x in annotations
            if x.get("annotation_id") in refs
        ),
        None,
    )
    errors += _ranges(doc.get("repetitions", []), "/repetitions", duration)
    for i, item in enumerate(doc.get("disagreements", [])):
        if item.get("status") not in ADJUDICATION_STATUSES:
            errors.append(f"/disagreements/{i}/status: invalid status")
        if any(ref not in ids for ref in item.get("annotation_ids", [])):
            errors.append(f"/disagreements/{i}/annotation_ids: unknown annotation")
    return errors


def _overlap(a: dict[str, Any], b: dict[str, Any]) -> float:
    return max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))


def match_reps(
    predictions: list[dict[str, Any]],
    gold: list[dict[str, Any]],
    tolerance: float = 0.35,
) -> list[tuple[int, int]]:
    """Deterministic greedy one-to-one matching by overlap then midpoint distance."""
    edges = []
    for pi, pred in enumerate(predictions):
        for gi, truth in enumerate(gold):
            if pred.get("source_id") != truth.get("source_id"):
                continue
            if pred.get("working_side", "unknown") not in (
                truth.get("side"),
                "unknown",
            ):
                continue
            overlap = _overlap(pred, truth)
            distance = abs(
                (pred["start"] + pred["end"] - truth["start"] - truth["end"]) / 2
            )
            # Requiring overlap prevents a long candidate from spanning unrelated reps.
            if overlap > 0 and distance <= max(
                tolerance, (truth["end"] - truth["start"]) / 2
            ):
                edges.append(
                    (
                        -overlap,
                        distance,
                        pred.get("id", ""),
                        truth.get("id", ""),
                        pi,
                        gi,
                    )
                )
    used_p, used_g, matches = set(), set(), []
    for *_score, pi, gi in sorted(edges):
        if pi not in used_p and gi not in used_g:
            used_p.add(pi)
            used_g.add(gi)
            matches.append((pi, gi))
    return sorted(matches)


def _metric(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "mean_absolute_error": None,
            "median_absolute_error": None,
            "p90_absolute_error": None,
        }
    values = sorted(abs(x) for x in values)
    return {
        "mean_absolute_error": statistics.fmean(values),
        "median_absolute_error": statistics.median(values),
        "p90_absolute_error": values[max(0, int(0.9 * len(values)) - 1)],
    }


def evaluate(
    analysis: dict[str, Any],
    gold_sets: list[dict[str, Any]],
    split: str | None = None,
    tolerance: float = 0.35,
    config_id: str | None = None,
) -> dict[str, Any]:
    if split and split not in SPLITS:
        raise ValueError("split must be development or held_out")
    selected = [g for g in gold_sets if split is None or g["split"] == split]
    candidates = analysis.get("evidence", {}).get("rep_candidates", [])
    intervals = {
        x["id"]: x
        for x in analysis.get("evidence", {}).get("rep_analysis_intervals", [])
    }
    sources, timing, totals, fp_reasons = (
        [],
        {x: [] for x in ("start", "top", "end", "duration")},
        {"tp": 0, "fp": 0, "fn": 0},
        {},
    )
    fn_reasons: dict[str, int] = {}
    eligibility = {"eligible_intervals": 0, "ineligible_intervals": 0}
    incomplete = {
        "preserved": 0,
        "promoted_completed": 0,
        "missed": 0,
        "false_incomplete": 0,
    }
    uncertainty = {"gold_completed": 0, "gold_incomplete": 0, "predictions": 0}
    side = {"correct": 0, "wrong": 0, "unresolved": 0}
    ineligibility: dict[str, int] = {}
    ineligibility_outcome = {"correct_conservative": 0, "avoidable_failure": 0}
    for gold_doc in selected:
        source_id, interval_id = (
            gold_doc["source_id"],
            gold_doc.get("rep_analysis_interval_id"),
        )
        preds = [
            x
            for x in candidates
            if x["source_id"] == source_id
            and (
                interval_id is None or x.get("rep_analysis_interval_id") == interval_id
            )
        ]
        completed_g = [
            dict(x, source_id=source_id)
            for x in gold_doc["repetitions"]
            if x["status"] == "completed"
        ]
        completed_p = [x for x in preds if x["status"] == "completed"]
        matches = match_reps(completed_p, completed_g, tolerance)
        tp, fp, fn = (
            len(matches),
            len(completed_p) - len(matches),
            len(completed_g) - len(matches),
        )
        totals["tp"] += tp
        totals["fp"] += fp
        totals["fn"] += fn
        for pi, gi in matches:
            p, g = completed_p[pi], completed_g[gi]
            timing["start"].append(p["start"] - g["start"])
            timing["end"].append(p["end"] - g["end"])
            timing["duration"].append((p["end"] - p["start"]) - (g["end"] - g["start"]))
            pt = p.get("phases", {}).get("top_confirmation")
            gt = g.get("top")
            if pt is not None and gt is not None:
                timing["top"].append(pt - gt)
        unmatched = {i for i in range(len(completed_p))} - {x[0] for x in matches}
        for i in unmatched:
            reason = completed_p[i].get("false_positive_reason", "unknown")
            reason = reason if reason in FP_REASONS else "unknown"
            fp_reasons[reason] = fp_reasons.get(reason, 0) + 1
        unmatched_gold = {i for i in range(len(completed_g))} - {x[1] for x in matches}
        for i in unmatched_gold:
            reason = completed_g[i].get("false_negative_reason", "unknown")
            reason = reason if reason in FN_REASONS else "unknown"
            fn_reasons[reason] = fn_reasons.get(reason, 0) + 1
        known_side = gold_doc.get("working_side", "unknown")
        if known_side != "unknown":
            predicted_sides = {x.get("working_side", "unknown") for x in preds}
            if known_side in predicted_sides:
                side["correct"] += 1
            elif not predicted_sides or predicted_sides == {"unknown"}:
                side["unresolved"] += 1
            else:
                side["wrong"] += 1
        incomplete_g = [
            dict(x, source_id=source_id)
            for x in gold_doc["repetitions"]
            if x["status"] == "incomplete"
        ]
        incomplete_p = [x for x in preds if x["status"] == "incomplete"]
        im = match_reps(incomplete_p, incomplete_g, tolerance)
        incomplete["preserved"] += len(im)
        incomplete["missed"] += len(incomplete_g) - len(im)
        incomplete["false_incomplete"] += len(incomplete_p) - len(im)
        incomplete["promoted_completed"] += sum(
            1 for g in incomplete_g if any(_overlap(p, g) > 0 for p in completed_p)
        )
        uncertain_p = [x for x in preds if x["status"] == "uncertain"]
        uncertainty["predictions"] += len(uncertain_p)
        uncertainty["gold_completed"] += len(
            match_reps(uncertain_p, completed_g, tolerance)
        )
        uncertainty["gold_incomplete"] += len(
            match_reps(uncertain_p, incomplete_g, tolerance)
        )
        interval = intervals.get(interval_id)
        if interval and not interval.get("eligible", True):
            eligibility["ineligible_intervals"] += 1
            for reason in interval.get("ineligibility_reasons", []):
                ineligibility[reason] = ineligibility.get(reason, 0) + 1
            outcome = (
                "avoidable_failure"
                if completed_g or incomplete_g
                else "correct_conservative"
            )
            ineligibility_outcome[outcome] += 1
        else:
            eligibility["eligible_intervals"] += 1
        ge, pe = len(completed_g), len(completed_p)
        sources.append(
            {
                "source_id": source_id,
                "annotation_id": gold_doc.get(
                    "adjudication_id", gold_doc.get("annotation_id")
                ),
                "split": gold_doc["split"],
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "gold_completed_count": ge,
                "predicted_completed_count": pe,
                "absolute_count_error": abs(pe - ge),
                "signed_count_error": pe - ge,
                "view_categories": gold_doc.get("view_categories", ["unknown"]),
                "expected_side": gold_doc.get("working_side", "unknown"),
            }
        )
    tp, fp, fn = totals.values()
    precision = tp / (tp + fp) if tp + fp else (1.0 if not fn else 0.0)
    recall = tp / (tp + fn) if tp + fn else 1.0
    count_errors = [x["absolute_count_error"] for x in sources]
    total_side = sum(side.values())
    eligibility_total = sum(eligibility.values())
    views: dict[str, dict[str, int]] = {}
    side_breakdown: dict[str, dict[str, int]] = {}
    for source in sources:
        for view in source["view_categories"]:
            bucket = views.setdefault(
                view,
                {
                    "source_count": 0,
                    "tp": 0,
                    "fp": 0,
                    "fn": 0,
                    "absolute_count_error": 0,
                },
            )
            bucket["source_count"] += 1
            for key, source_key in (
                ("tp", "true_positives"),
                ("fp", "false_positives"),
                ("fn", "false_negatives"),
                ("absolute_count_error", "absolute_count_error"),
            ):
                bucket[key] += source[source_key]
        sb = side_breakdown.setdefault(
            source["expected_side"], {"source_count": 0, "tp": 0, "fp": 0, "fn": 0}
        )
        sb["source_count"] += 1
        for key, source_key in (
            ("tp", "true_positives"),
            ("fp", "false_positives"),
            ("fn", "false_negatives"),
        ):
            sb[key] += source[source_key]
    for bucket in views.values():
        bucket["precision"] = (
            bucket["tp"] / (bucket["tp"] + bucket["fp"])
            if bucket["tp"] + bucket["fp"]
            else None
        )
        bucket["recall"] = (
            bucket["tp"] / (bucket["tp"] + bucket["fn"])
            if bucket["tp"] + bucket["fn"]
            else None
        )
        bucket["mean_absolute_count_error"] = (
            bucket.pop("absolute_count_error") / bucket["source_count"]
        )
    return {
        "format_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_split": split or "all",
        "config_id": config_id,
        "rule_versions": sorted(
            {f"{x.get('rep_rule_id')}:{x.get('rep_rule_version')}" for x in candidates}
        ),
        "matching": {
            "algorithm": "one_to_one_overlap_midpoint_v1",
            "tolerance_seconds": tolerance,
        },
        "sources": sources,
        "aggregate": {
            **totals,
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0,
            "mean_absolute_count_error": statistics.fmean(count_errors)
            if count_errors
            else 0.0,
            "median_absolute_count_error": statistics.median(count_errors)
            if count_errors
            else 0.0,
            "exact_count_accuracy": sum(x == 0 for x in count_errors)
            / len(count_errors)
            if count_errors
            else 1.0,
            "timing_error_seconds": {k: _metric(v) for k, v in timing.items()},
            "side": {
                **side,
                "accuracy": side["correct"] / total_side if total_side else None,
            },
            "incomplete": incomplete,
            "uncertainty": uncertainty,
            "ineligibility_reasons": ineligibility,
            "ineligibility_outcome": ineligibility_outcome,
            "eligibility": {
                **eligibility,
                "eligibility_rate": eligibility["eligible_intervals"]
                / eligibility_total
                if eligibility_total
                else None,
            },
            "false_positive_reasons": fp_reasons,
            "false_negative_reasons": fn_reasons,
            "performance_by_view": views,
            "performance_by_side": side_breakdown,
        },
    }


def prepare_review(analysis: dict[str, Any], reviewer: str = "") -> dict[str, Any]:
    return {
        "format_version": "1.0",
        "analysis_schema_version": analysis.get("schema_version"),
        "reviewer": reviewer,
        "decisions": [
            {
                "candidate_id": x["id"],
                "source_id": x["source_id"],
                "decision": None,
                "reviewed_at": None,
                "reason_code": None,
                "note": "",
            }
            for x in analysis.get("evidence", {}).get("rep_candidates", [])
        ],
    }


def validate_review(review: dict[str, Any], analysis: dict[str, Any]) -> list[str]:
    candidates = {
        x["id"]: x for x in analysis.get("evidence", {}).get("rep_candidates", [])
    }
    errors = []
    seen = set()
    for i, row in enumerate(review.get("decisions", [])):
        p = f"/decisions/{i}"
        cid = row.get("candidate_id")
        if cid in seen:
            errors.append(f"{p}/candidate_id: duplicate decision")
        seen.add(cid)
        candidate = candidates.get(cid)
        if not candidate:
            errors.append(f"{p}/candidate_id: unknown candidate")
            continue
        if row.get("source_id") != candidate["source_id"]:
            errors.append(f"{p}/source_id: source mismatch")
        if row.get("decision") not in DECISIONS:
            errors.append(f"{p}/decision: invalid or unreviewed decision")
        start = row.get("adjusted_start", candidate["start"])
        end = row.get("adjusted_end", candidate["end"])
        if start >= end or start < 0:
            errors.append(f"{p}: invalid adjusted range")
        source = next(
            (s for s in analysis["sources"] if s["id"] == candidate["source_id"]), None
        )
        if source and source.get("duration") is not None and end > source["duration"]:
            errors.append(f"{p}: adjustment outside source bounds")
        top = row.get("adjusted_top")
        if top is not None and not start <= top <= end:
            errors.append(f"{p}/adjusted_top: outside range")
    return errors


def promote(analysis: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    errors = validate_review(review, analysis)
    if errors:
        raise ValueError("invalid review: " + "; ".join(errors))
    out = copy.deepcopy(analysis)
    candidates = {x["id"]: x for x in out.get("evidence", {}).get("rep_candidates", [])}
    existing = {x.get("source_candidate_id") for x in out.get("repetitions", [])}
    for decision in review["decisions"]:
        c = candidates[decision["candidate_id"]]
        if (
            decision["decision"] not in {"accept", "adjust"}
            or c["status"] == "incomplete"
            or c["id"] in existing
        ):
            continue
        out.setdefault("repetitions", []).append(
            {
                "id": f"editorial-{c['id']}",
                "source_id": c["source_id"],
                "start": decision.get("adjusted_start", c["start"]),
                "end": decision.get("adjusted_end", c["end"]),
                "complete": True,
                "source_candidate_id": c["id"],
                "rep_rule_id": c["rep_rule_id"],
                "rep_rule_version": c["rep_rule_version"],
                "reviewer": review.get("reviewer") or None,
                "reviewed_at": decision.get("reviewed_at"),
                "review_decision": decision["decision"],
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in (
        "validate-annotation",
        "validate-adjudication",
        "evaluate",
        "prepare-review",
        "validate-review",
        "promote",
    ):
        p = sub.add_parser(name)
        p.add_argument("inputs", nargs="+")
        p.add_argument("--output")
        if name == "evaluate":
            p.add_argument("--split", choices=sorted(SPLITS))
            p.add_argument("--config-id")
            p.add_argument("--tolerance", type=float, default=0.35)
        if name == "prepare-review":
            p.add_argument("--reviewer", default="")
    a = parser.parse_args()
    docs = [read(x) for x in a.inputs]
    if a.command == "validate-annotation":
        result = {"errors": validate_annotation(docs[0])}
    elif a.command == "validate-adjudication":
        result = {"errors": validate_adjudication(docs[0], docs[1:])}
    elif a.command == "evaluate":
        result = evaluate(docs[0], docs[1:], a.split, a.tolerance, a.config_id)
    elif a.command == "prepare-review":
        result = prepare_review(docs[0], a.reviewer)
    elif a.command == "validate-review":
        result = {"errors": validate_review(docs[1], docs[0])}
    else:
        result = promote(docs[0], docs[1])
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output:
        Path(a.output).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if "errors" in result and result["errors"]:
        return 1
    if a.command == "evaluate":
        m = result["aggregate"]
        print(
            f"precision={m['precision']:.3f} recall={m['recall']:.3f} F1={m['f1']:.3f}",
            file=__import__("sys").stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
