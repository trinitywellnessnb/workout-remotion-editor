# Repetition evaluation and editorial promotion

## Purpose and boundaries

Phase 6 evaluates `single_arm_dumbbell_row_v1` against rights-cleared, human-annotated footage. Synthetic fixtures test software behavior only: they are **not** evidence of real-world accuracy. Gold annotations, adjudications, evaluation reports, and review decisions are external sidecars; machine `evidence.rep_candidates` remains separate from human-reviewed top-level editorial `repetitions`. Do not record names or other unnecessary personal information, commit private footage, infer health/form/pain/failure, or tune on held-out data.

## Annotation and adjudication

Copy `examples/repetition-evaluation/annotation-template.json` once per annotator and source. It records source/media reference, duration, exercise and canonical ID, optional entity, side, evaluation interval, split (`development` or `held_out`), completed/incomplete/uncertain attempts, start/top/end and optional phases, exclusions, occlusion, camera motion, setup/transitions, notes, anonymized annotator, and version. Validate with:

```bash
python scripts/repetition_evaluation.py validate-annotation annotation.json
```

Keep annotator A, B, and additional files immutable. An adjudication sidecar references at least two originals, records disagreements (`agreed`, `timing_adjusted`, `status_disagreement`, `rep_missing`, `false_rep_annotation`, `side_disagreement`, `boundary_disagreement`, or `excluded`), notes, and a separate resolved rep list. Validate it with the adjudication followed by all referenced annotation files. Never overwrite an original.

## Evaluation and matching

```bash
python scripts/repetition_evaluation.py evaluate analysis.json adjudicated.json --split development --config-id baseline --output report.json
```

Matching is deterministic, one-to-one, source/interval scoped, side-compatible, and ranked by temporal overlap then midpoint distance (default tolerance 0.35 seconds). Every prediction and gold rep can match once; overlap is required so a long prediction cannot absorb several reps. Reports include source and aggregate completed TP/FP/FN, precision/recall/F1, signed/absolute and aggregate mean/median/exact count error, start/top/end/duration mean/median/p90 absolute timing error, correct/wrong/unresolved side results, incomplete preservation/mis-promotion/misses, uncertain coverage, ineligibility reason codes, and structured false-positive reasons.

Precision is the initial primary release metric because a false visible count is costly, but recall is always reported. Compare named configurations only on `development`; report `held_out` without retuning. Configuration comparison never changes production defaults. A materially changed rule must be introduced and documented as `single_arm_dumbbell_row_v2`, not silently replace v1. This tooling performs no ML training or automatic optimization.

## Review and promotion

```bash
python scripts/repetition_evaluation.py prepare-review analysis.json --reviewer reviewer-a --output review.json
python scripts/repetition_evaluation.py validate-review analysis.json review.json
python scripts/repetition_evaluation.py promote analysis.json review.json --output reviewed-analysis.json
```

Fill each decision as `accept`, `reject`, `adjust`, `mark_incomplete`, or `mark_uncertain`; add UTC `reviewed_at`, a reason code/note, and optional `adjusted_start`, `adjusted_end`, or `adjusted_top`. There is no merge and no automatic split. Unreviewed entries fail validation. Only explicitly accepted/adjusted completed or uncertain candidates promote; incomplete, rejected, uncertain-without-acceptance, and unreviewed candidates do not. Existing editorial reps remain untouched. Candidate linkage makes promotion deterministic, idempotent, and traceable to source, candidate, rule/version, reviewer, and decision.

## Limitations

No footage is bundled. Timing tolerances require development-set study; ineligibility classification and false-positive reasons require human judgment. Evaluation reports are external and current rule thresholds remain unvalidated on real footage until a rights-cleared adjudicated dataset is evaluated.

Phase 7 adds dataset manifests, dual-annotation agreement, precision-first config comparison, immutable freeze records, strict held-out execution, hashing, FN/eligibility/view analysis, and synthetic-versus-real labeling. Follow [phase7-real-world-validation.md](phase7-real-world-validation.md); these additions do not weaken review-based editorial promotion.
