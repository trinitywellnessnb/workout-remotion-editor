#!/usr/bin/env python3
"""Phase 7 dataset onboarding, calibration comparison, freezing, and reporting."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from repetition_evaluation import evaluate, read

SPLITS = {"development", "held_out"}
VIEW_CATEGORIES = {
    "unknown",
    "front-oblique",
    "rear-oblique",
    "side",
    "elevated",
    "low",
    "close-crop",
    "full-body",
    "partial-torso",
    "equipment-occlusion",
    "arm-occlusion",
    "handheld",
    "tripod-static",
    "mirror-present",
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
CONFIG_KEYS = {
    "minimum_fusion_score",
    "minimum_pose_coverage",
    "minimum_sample_rate",
    "minimum_elbow_excursion",
    "minimum_torso_relative_wrist_path",
    "bottom_enter_threshold",
    "bottom_exit_threshold",
    "top_enter_threshold",
    "top_exit_threshold",
    "minimum_concentric_duration",
    "minimum_top_confirmation_duration",
    "minimum_eccentric_duration",
    "minimum_full_rep_duration",
    "allowed_short_gap_tolerance",
    "minimum_quality_evidence_score",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def validate_manifest(doc: dict[str, Any]) -> list[str]:
    """Validate a privacy-minimal manifest without requiring local media to exist."""
    errors: list[str] = []
    for key in ("format_version", "dataset_id", "dataset_version", "sources"):
        if not doc.get(key):
            errors.append(f"/{key}: required")
    if doc.get("footage_type") not in {"real", "synthetic"}:
        errors.append("/footage_type: must be real or synthetic")
    sources = doc.get("sources", [])
    if not isinstance(sources, list) or not sources:
        errors.append("/sources: at least one source required")
        return errors
    seen: set[str] = set()
    for i, source in enumerate(sources):
        p = f"/sources/{i}"
        sid = source.get("source_id")
        if not isinstance(sid, str) or not sid:
            errors.append(f"{p}/source_id: required")
        elif sid in seen:
            errors.append(f"{p}/source_id: duplicate source ID")
        seen.add(sid)
        if source.get("split") not in SPLITS:
            errors.append(f"{p}/split: must be development or held_out")
        if source.get("rights_status") != "rights_cleared":
            errors.append(f"{p}/rights_status: must be rights_cleared")
        if not isinstance(source.get("redistribution_allowed"), bool):
            errors.append(f"{p}/redistribution_allowed: boolean required")
        media = source.get("media_reference")
        if not isinstance(media, str) or not media.strip():
            errors.append(f"{p}/media_reference: required")
        else:
            path = PurePosixPath(media)
            if path.is_absolute() or ".." in path.parts or "://" in media:
                errors.append(f"{p}/media_reference: must be a safe relative reference")
        if source.get("exercise_canonical_id") != "dumbbell_row_single_arm":
            errors.append(f"{p}/exercise_canonical_id: unsupported exercise")
        views = source.get("view_categories", ["unknown"])
        if (
            not isinstance(views, list)
            or not views
            or any(v not in VIEW_CATEGORIES for v in views)
        ):
            errors.append(f"{p}/view_categories: invalid category")
        annotations = source.get("annotation_files", [])
        if not isinstance(annotations, list) or len(annotations) < 2:
            errors.append(f"{p}/annotation_files: two independent annotations required")
        if not source.get("adjudication_file"):
            errors.append(f"{p}/adjudication_file: required")
        duration = source.get("duration_seconds")
        if not isinstance(duration, (int, float)) or duration <= 0:
            errors.append(f"{p}/duration_seconds: positive duration required")
        digest = source.get("media_sha256")
        if digest is not None and (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            errors.append(f"{p}/media_sha256: invalid lowercase SHA-256")
    return errors


def hash_media(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    return {
        "source_filename": path.name,
        "size_bytes": size,
        "sha256": digest.hexdigest(),
    }


def annotation_checklist(
    manifest: dict[str, Any], source_id: str, annotator: str
) -> dict[str, Any]:
    source = next((x for x in manifest["sources"] if x["source_id"] == source_id), None)
    if source is None:
        raise ValueError(f"unknown source: {source_id}")
    return {
        "format_version": "1",
        "annotation_id": f"{source_id}-{annotator}",
        "source_id": source_id,
        "media": source["media_reference"],
        "exercise": "single-arm dumbbell row",
        "canonical_exercise_id": source["exercise_canonical_id"],
        "working_side": source.get("expected_side", "unknown"),
        "evaluation_interval": {"start": 0, "end": source.get("duration_seconds", 0)},
        "split": source["split"],
        "annotator": annotator,
        "repetitions": [],
        "annotation_guidance": "Annotate independently; do not inspect machine predictions.",
    }


def agreement(
    first: dict[str, Any], second: dict[str, Any], tolerance: float = 0.35
) -> dict[str, Any]:
    """Small descriptive human-human report, intentionally separate from evaluation."""
    if first["source_id"] != second["source_id"]:
        raise ValueError("annotations must share a source")
    from repetition_evaluation import match_reps

    a = [
        dict(x, source_id=first["source_id"], working_side=x.get("side", "unknown"))
        for x in first["repetitions"]
    ]
    b = [dict(x, source_id=second["source_id"]) for x in second["repetitions"]]
    matches = match_reps(a, b, tolerance)
    timing = {"start": [], "top": [], "end": []}
    side_agree = status_agree = 0
    for ai, bi in matches:
        left, right = a[ai], b[bi]
        side_agree += left.get("side") == right.get("side")
        status_agree += left.get("status") == right.get("status")
        for field in timing:
            if left.get(field) is not None and right.get(field) is not None:
                timing[field].append(abs(left[field] - right[field]))
    return {
        "metric_scope": "human_human",
        "source_id": first["source_id"],
        "annotator_ids": [first["annotation_id"], second["annotation_id"]],
        "completed_count_difference": abs(
            sum(x["status"] == "completed" for x in a)
            - sum(x["status"] == "completed" for x in b)
        ),
        "matched_repetitions": len(matches),
        "unmatched_repetitions": len(a) + len(b) - 2 * len(matches),
        "side_agreement": side_agree / len(matches) if matches else None,
        "status_agreement": status_agree / len(matches) if matches else None,
        "timing_difference_seconds": {
            k: {"mean_absolute_difference": statistics.fmean(v) if v else None}
            for k, v in timing.items()
        },
    }


def validate_config(config: dict[str, Any]) -> list[str]:
    errors = []
    if not config.get("config_id"):
        errors.append("/config_id: required")
    if config.get("rule_id") != "single_arm_dumbbell_row_v1":
        errors.append("/rule_id: only single_arm_dumbbell_row_v1 is supported")
    values = config.get("values")
    if not isinstance(values, dict) or not values:
        errors.append("/values: non-empty object required")
    elif set(values) - CONFIG_KEYS:
        errors.append("/values: contains unsupported tunable keys")
    return errors


def _policy_eligibility(
    report: dict[str, Any], policy: dict[str, Any]
) -> tuple[bool, list[str]]:
    m, reasons = report["aggregate"], []
    if m["precision"] < policy.get("precision_floor", 0.0):
        reasons.append("precision_below_floor")
    if m["mean_absolute_count_error"] > policy.get(
        "maximum_mean_absolute_count_error", float("inf")
    ):
        reasons.append("count_error_above_ceiling")
    forbidden = set(policy.get("forbidden_false_positive_reasons", []))
    if forbidden & {k for k, v in m.get("false_positive_reasons", {}).items() if v}:
        reasons.append("systematic_false_positive_class")
    if policy.get("require_no_side_failures", True) and m.get("side", {}).get(
        "wrong", 0
    ):
        reasons.append("side_failure")
    return not reasons, reasons


def compare_configs(
    manifest: dict[str, Any], runs: list[dict[str, Any]], policy: dict[str, Any]
) -> dict[str, Any]:
    """Compare precomputed development runs; never accepts held-out sources."""
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError("invalid manifest: " + "; ".join(errors))
    if any(s["split"] != "development" for s in manifest["sources"]):
        raise ValueError(
            "configuration comparison requires a development-only manifest"
        )
    source_ids = {s["source_id"] for s in manifest["sources"]}
    ids = [r.get("config", {}).get("config_id") for r in runs]
    if len(ids) != len(set(ids)) or None in ids:
        raise ValueError("config IDs must be unique")
    rows = []
    for run in runs:
        config = run["config"]
        if validate_config(config):
            raise ValueError("invalid configuration")
        if not run.get("gold") or any(
            g.get("split") != "development" or g.get("source_id") not in source_ids
            for g in run["gold"]
        ):
            raise ValueError(
                "comparison gold must belong to development manifest sources"
            )
        report = evaluate(
            run["analysis"],
            run["gold"],
            split="development",
            config_id=config["config_id"],
        )
        eligible, reasons = _policy_eligibility(report, policy)
        rows.append(
            {
                "config": config,
                "report": report,
                "selection_eligible": eligible,
                "ineligibility_reasons": reasons,
            }
        )
    eligible = [r for r in rows if r["selection_eligible"]]
    selected = (
        max(
            eligible,
            key=lambda r: (
                r["report"]["aggregate"]["precision"],
                r["report"]["aggregate"]["recall"],
                -r["report"]["aggregate"]["mean_absolute_count_error"],
                r["config"]["config_id"],
            ),
        )
        if eligible
        else None
    )
    return {
        "format_version": "1",
        "report_type": "configuration_comparison",
        "evaluation_split": "development",
        "selection_policy": policy,
        "configurations": rows,
        "selected_config_id": selected["config"]["config_id"] if selected else None,
    }


def freeze_config(
    comparison: dict[str, Any], source_commit: str, notes: str = ""
) -> dict[str, Any]:
    if comparison.get("evaluation_split") != "development":
        raise ValueError("only development comparison may freeze a config")
    config_id = comparison.get("selected_config_id")
    row = next(
        (
            x
            for x in comparison["configurations"]
            if x["config"]["config_id"] == config_id
        ),
        None,
    )
    if not row or not row["selection_eligible"]:
        raise ValueError("no eligible selected configuration")
    report = row["report"]
    configuration = json.loads(_canonical(row["config"]["values"]))
    return {
        "format_version": "1",
        "record_type": "frozen_rule_configuration",
        "rule_id": row["config"]["rule_id"],
        "rule_version": row["config"].get("rule_version", "1"),
        "config_id": config_id,
        "configuration": configuration,
        "configuration_sha256": hashlib.sha256(
            _canonical(configuration).encode()
        ).hexdigest(),
        "development_report_sha256": hashlib.sha256(
            _canonical(report).encode()
        ).hexdigest(),
        "selection_policy": comparison["selection_policy"],
        "selection_policy_version": comparison["selection_policy"].get("version", "1"),
        "selected_at": _utc_now(),
        "source_commit": source_commit,
        "notes": notes,
    }


def held_out_report(
    frozen: dict[str, Any],
    analysis: dict[str, Any],
    gold: list[dict[str, Any]],
    *,
    first_look: bool,
    dataset: dict[str, Any],
    real_footage: bool,
) -> dict[str, Any]:
    if frozen.get("record_type") != "frozen_rule_configuration":
        raise ValueError("a frozen configuration is required")
    expected_hash = hashlib.sha256(
        _canonical(frozen.get("configuration")).encode()
    ).hexdigest()
    if frozen.get("configuration_sha256") != expected_hash:
        raise ValueError("frozen configuration has been mutated")
    errors = validate_manifest(dataset)
    if errors:
        raise ValueError("invalid manifest: " + "; ".join(errors))
    if any(source["split"] != "held_out" for source in dataset["sources"]):
        raise ValueError("held-out evaluation requires a held-out-only manifest")
    if any(g.get("split") != "held_out" for g in gold):
        raise ValueError("held-out evaluation accepts held_out gold only")
    if real_footage and dataset.get("footage_type") != "real":
        raise ValueError(
            "real-report flag requires a manifest declared as real footage"
        )
    report = evaluate(analysis, gold, split="held_out", config_id=frozen["config_id"])
    report.update(
        {
            "report_type": "phase7_evaluation",
            "dataset_id": dataset["dataset_id"],
            "dataset_version": dataset["dataset_version"],
            "footage_type": "real" if real_footage else "synthetic",
            "report_label": "real evaluation report"
            if real_footage
            else "synthetic test report",
            "pristine_first_look": first_look,
            "frozen_configuration_sha256": hashlib.sha256(
                _canonical(frozen).encode()
            ).hexdigest(),
            "warnings": []
            if first_look
            else [
                "Held-out results have been inspected previously; this is not a pristine first look."
            ],
        }
    )
    return report


def summary(report: dict[str, Any]) -> str:
    m = report["aggregate"]
    lines = [
        f"{report.get('report_label', 'evaluation report')} ({report['evaluation_split']})",
        f"Config: {report.get('config_id')}",
        f"Clips: {len(report['sources'])}",
        f"Gold reps: {sum(x['gold_completed_count'] for x in report['sources'])}",
        f"Machine reps: {sum(x['predicted_completed_count'] for x in report['sources'])}",
        f"TP/FP/FN: {m['tp']}/{m['fp']}/{m['fn']}",
        f"Precision/recall/F1: {m['precision']:.3f}/{m['recall']:.3f}/{m['f1']:.3f}",
        f"Exact-count accuracy: {m['exact_count_accuracy']:.3f}",
        f"Ineligibility reasons: {m.get('ineligibility_reasons', {})}",
        f"False-positive reasons: {m.get('false_positive_reasons', {})}",
        f"False-negative reasons: {m.get('false_negative_reasons', {})}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("validate-manifest")
    p.add_argument("manifest")
    p = sub.add_parser("hash-media")
    p.add_argument("media")
    p = sub.add_parser("annotation-template")
    p.add_argument("manifest")
    p.add_argument("source_id")
    p.add_argument("--annotator", required=True)
    p = sub.add_parser("agreement")
    p.add_argument("first")
    p.add_argument("second")
    p = sub.add_parser("compare")
    p.add_argument("manifest")
    p.add_argument("policy")
    p.add_argument("runs", nargs="+")
    p = sub.add_parser("freeze")
    p.add_argument("comparison")
    p.add_argument("--source-commit", required=True)
    p = sub.add_parser("held-out")
    p.add_argument("frozen")
    p.add_argument("manifest")
    p.add_argument("analysis")
    p.add_argument("gold", nargs="+")
    p.add_argument("--real-footage", action="store_true")
    p.add_argument("--repeat", action="store_true")
    for command in sub.choices.values():
        command.add_argument("--output")
    args = parser.parse_args()
    if args.command == "validate-manifest":
        result = {"errors": validate_manifest(read(args.manifest))}
    elif args.command == "hash-media":
        result = hash_media(args.media)
    elif args.command == "annotation-template":
        result = annotation_checklist(
            read(args.manifest), args.source_id, args.annotator
        )
    elif args.command == "agreement":
        result = agreement(read(args.first), read(args.second))
    elif args.command == "compare":
        result = compare_configs(
            read(args.manifest), [read(x) for x in args.runs], read(args.policy)
        )
    elif args.command == "freeze":
        result = freeze_config(read(args.comparison), args.source_commit)
    else:
        result = held_out_report(
            read(args.frozen),
            read(args.analysis),
            [read(x) for x in args.gold],
            first_look=not args.repeat,
            dataset=read(args.manifest),
            real_footage=args.real_footage,
        )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if args.command == "held-out":
        print(summary(result), end="", file=__import__("sys").stderr)
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
