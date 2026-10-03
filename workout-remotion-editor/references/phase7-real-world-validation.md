# Phase 7 real-world repetition validation

## Status

**Real-world Phase 7 metrics were not produced because no rights-cleared evaluation footage was available.** The checked-in examples and tests are synthetic workflow demonstrations, not accuracy evidence. No `single_arm_dumbbell_row_v2` was created: without development footage, a material rule change cannot be justified. Version 1 remains the sole exercise-specific repetition rule.

## Local dataset and rights

Keep footage under repository-root `evaluation-data/`; Git ignores that directory and common video/audio extensions. Do not force-add media. A manifest may be committed only when its references and non-sensitive metadata are safe to publish. `rights_status` must be `rights_cleared`; `redistribution_allowed` is independent and does not default to true. A hash supports reproducibility but is not proof of consent or licensing. Never record names, contact details, health information, or inferred demographic traits.

Start from `examples/repetition-evaluation/phase7-dataset-manifest.json`. Each stable source ID has a safe relative media reference, split, canonical exercise, optional expected side, one or more view categories, environment category, two independent annotation sidecars, and an adjudication sidecar. Optional fields include SHA-256, byte size, duration, non-sensitive visibility/lighting/cadence notes, and redistribution status. Categories may be unknown and may include front/rear oblique, side, elevation, crop/framing, occlusion, static/handheld camera, and reflection presence.

```bash
python scripts/phase7_evaluation.py validate-manifest examples/repetition-evaluation/phase7-dataset-manifest.json
python scripts/phase7_evaluation.py hash-media ../../evaluation-data/row-development-001.mp4
```

## Independent annotation and adjudication

Generate a checklist separately for each human annotator. Annotators should not inspect machine candidates or one another's labels. A generated file is a starting checklist, not gold:

```bash
python scripts/phase7_evaluation.py annotation-template manifest.json row-development-001 --annotator annotator-a --output annotations/row-development-001-a.json
python scripts/phase7_evaluation.py annotation-template manifest.json row-development-001 --annotator annotator-b --output annotations/row-development-001-b.json
python scripts/phase7_evaluation.py agreement annotations/row-development-001-a.json annotations/row-development-001-b.json --output disagreement.json
python scripts/repetition_evaluation.py validate-adjudication adjudication.json annotations/row-development-001-a.json annotations/row-development-001-b.json
```

Agreement output is explicitly `human_human`: count difference, one-to-one matched/unmatched reps, side/status agreement, and start/top/end differences. It must not be mixed with `machine_human` evaluation error. Preserve both originals and resolve disagreements in a separate adjudication file. Never seed gold from predictions.

## Development comparison and selection

Tunable values are stored in named config documents; the baseline example mirrors v1 without changing production defaults. Each comparison-run JSON contains `config`, a reproducibly generated `analysis`, and adjudicated `gold` documents. Its manifest must contain **development sources only**. Duplicate config IDs and held-out manifests fail closed.

```bash
python scripts/phase7_evaluation.py compare development-manifest.json selection-policy.json run-A.json run-B.json --output development-comparison.json
```

The explicit, versioned precision-first policy provides a precision floor, count-error ceiling, forbidden systematic FP classes, and side-failure rule. Among eligible configurations, ordering is precision, recall, count error, then stable config ID—not F1 alone. Policy values are project decisions grounded in development evidence, not universal targets. Comparison reports retain each config identity and report all Phase 6 metrics plus FN reasons, eligibility, side, and view breakdowns with denominators.

## Freeze and held-out protection

Freeze exactly once after development selection:

```bash
python scripts/phase7_evaluation.py freeze development-comparison.json --source-commit "$(git rev-parse HEAD)" --output frozen-config.json
python scripts/phase7_evaluation.py held-out frozen-config.json held-out-manifest.json held-out-analysis.json held-out-gold/*.json --output held-out-report.json
```

The immutable record contains rule/config identity, complete values, a canonical development-report hash, policy/version, UTC selection time, source commit, and notes. Held-out evaluation accepts only held-out gold and exactly the frozen config identity; it never modifies thresholds. Use `--repeat` after any first inspection so the report states it is no longer a pristine first look. `--real-footage` is allowed only when inputs genuinely came from rights-cleared real footage; absent that flag, output is labeled `synthetic test report`.

Reports include dataset and config identity, split, source/gold/machine counts, TP/FP/FN, precision/recall/F1, count and timing errors, sides, incomplete/uncertain behavior, eligible/ineligible intervals and reason distribution, FP/FN reasons, view denominators, first-look status, warnings, and a concise terminal summary. Never silently remove a poor clip. Describe small groups with their denominator and do not generalize them.

False-positive categories retain setup, pickup, set-down, rerack, partial pull, camera motion, torso repositioning, state bounce, false extremum, track reassignment, wrong side/exercise, temporal boundary, pose failure, and unknown concepts. False-negative categories include sparse sampling, occlusion/missing joints, unresolved side, strict amplitude, missing top/return confirmation, gap reset, unsuitable camera, rejected identity, interval boundary, and unknown. Operator notes remain appropriate in sidecars. Ineligible footage is reported separately and is not silently converted to a false negative unless evaluation policy says so.

## Rule-version and editorial boundaries

A v2 is warranted only when real development results show a clear material rule/configuration or state-machine improvement, designed without held-out results. Tooling changes alone are insufficient. Keep v1 reproducible. Do not add another exercise rule during this validation phase.

Evaluation never promotes candidates. Machine candidates remain evidence; top-level editorial repetitions still require the Phase 6 review-decision and promotion workflow. No measured accuracy level changes that policy.

## Limitations

No local rights-cleared media was present during implementation. The tool consumes reproducible per-config machine analyses rather than rerunning video inference itself, so the operator must record the exact analysis command/commit alongside each run. View and reason assignments require operator judgment. A second real annotator and adjudicator cannot be simulated.
