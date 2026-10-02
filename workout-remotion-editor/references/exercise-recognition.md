# Exercise recognition: context first (Phase 4)

Phase 5 activates exactly `dumbbell_row_single_arm` → `single_arm_dumbbell_row_v1`; no generic-row or family fallback exists. See [repetition-evidence.md](repetition-evidence.md).


## Purpose and boundary

Phase 4 turns source-relative context and existing visual evidence into normalized, entity-associated exercise candidates. The flow is **video → probe → scenes/activity → identity/equipment → pose/movement → interval candidates → user context → deterministic fusion → exercise candidates → Editor**. Candidates are evidence, not editorial decisions. This phase does **not** run MMAction2, an RGB classifier, a skeleton classifier, a repetition state machine, set confirmation, form/ROM grading, effort or medical inference.

`repetitions` is never auto-populated. An `interval_candidate` is a recognition window, not a set; a direction change is not a repetition.

## Taxonomy and aliases

`scripts/exercise-taxonomy.json` is taxonomy version `1`. It deliberately covers a small testable set: unknown/generic movement entries and common row, pull, press, squat, hinge, lunge, machine, and bodyweight exercises. Equipment variants remain distinct. Every `rep_rule_id` is `null`.

Alias matching case-folds, trims whitespace, and normalizes safe punctuation/hyphens. Only aliases explicitly present in the taxonomy are equivalent; `DB` is accepted only in defined aliases. A label with zero matches stays unmapped and retains its original spelling. A label with multiple matches returns an ambiguous result and is never guessed.

## User context and precedence

Top-level `context` keeps user/imported facts separate from analyzer `evidence`. Assertions can scope identity or constraints to a source, interval, scene, or entity and retain `supplied_label`, normalized mapping provenance, source, and confirmation. `ordered_plan` provides ordered constraints without requiring Trainerize or any registry.

Precedence is: confirmed interval identity (1.00), confirmed source identity (0.95), ordered plan (0.75), registry/import (0.70), filename/free-text hint (0.45), deterministic machine evidence (0.40), then action-model evidence (0.35). Equipment and pose compatibility can each add 0.15; an exclusion subtracts 0.35. These are transparent **fusion-score weights**, not calibrated probabilities. The current implementation uses explicit identity, ordered-plan, and normalized action-candidate inputs; the remaining documented weights reserve deterministic integration points.

Lower-priority disagreement is retained in `conflicting_evidence_refs`; it is not erased. Supporting refs identify the context assertion, plan item, or machine record used. `conflict_status` must agree with those references.

## Intervals, association, and false-positive controls

Proposals intersect active-motion regions with hard scene bounds, require at least two seconds by default, and select only a persistent person. When roles exist, only `primary_athlete_candidate` is eligible. Proposals never cross hard cuts. Short setup motion is rejected. Unassigned/background people do not contaminate a primary-athlete interval.

The exclusion vocabulary is `setup`, `transition`, `walking`, `reracking`, `camera_setup`, `stretch_or_warmup`, `insufficient_motion`, `insufficient_pose`, `background_entity`, `partial_movement`, and `unknown_nonexercise_activity`. These are conservative candidate/exclusion states, not perfect classifications. Future rolling windows should use 2–4 seconds at roughly 50% overlap and merge only within the same scene and entity with compatible identity, evidence, score stability, and no large track gap.

Exercise generation must use several compatible signals: interval duration, primary entity persistence, pose coverage/quality, sustained relevant movement, body position, temporal consistency, and negative evidence. An isolated elbow bend, walking while carrying weights, or reracking cannot establish an exercise.

## Candidates, top-k, ambiguity, and equipment

`exercise_candidates` is provider-neutral. Each record has one source interval, optional scene/entity, taxonomy identity (nullable for unmapped provider output), label, rank, score, source type, provider/model provenance, confirmation, ambiguity, and support/conflict refs. Fusion returns up to three candidates. A top-1/top-2 fusion-score margin below 0.10 remains ambiguous.

Stock YOLO does not reliably identify dumbbells, barbells, kettlebells, plates, cable handles, or gym machines. Equipment is therefore not mandatory for generic candidates, but a specific equipment-defined variant must not be strongly promoted by pose alone. Prefer `row_unspecified` unless user context, actual/specialized equipment evidence, or another defensible provider supports the variant.

## Action-provider contract and scheduling

Action adapters implement the existing provider protocol and emit normalized `exercise_candidates`; schema fields do not expose MMAction2 internals. `FakeActionProvider` exercises lifecycle behavior without ML dependencies. Statuses are: disabled → omitted/skipped; missing dependency/config/model → `unavailable`; exception → `failed`; valid empty result → `no_results`; some eligible intervals → `partial`; all eligible intervals → `success`.

- **Basic (default):** context, taxonomy, scene/activity, YOLO identity, and pose/movement heuristics; no action classifier.
- **Balanced:** Basic first; a future skeleton classifier may inspect unresolved eligible intervals only.
- **High Accuracy:** Balanced first; a future RGB classifier may inspect still-ambiguous intervals using the same `entity_id` and padded contextual crop. It must not introduce another tracker.

No production action backend is activated in Phase 4. A future skeleton provider should reuse Phase 3 pose samples, entity IDs, interval proposals, taxonomy, and candidate contract before any RGB experiment.

## CLI

```bash
python scripts/analyze_video.py clip.mp4 --exercise-label "One Arm DB Row" -o analysis.json
python scripts/analyze_video.py clip.mp4 --exercise-context context.json \
  --exercise-taxonomy scripts/exercise-taxonomy.json --action-mode basic
```

`--exercise-label` is allowed only for one input, preventing an ambiguous global label. Taxonomy and context are parsed before analyzer execution. `balanced` and `high_accuracy` record future scheduling intent but load no ML framework.

## Phase 5 contract

A future rep rule requires an accepted canonical candidate, score/confirmation policy, required joints and visibility, primary metric/orientation, unilateral/bilateral side, equipment/body position, supported views, and temporal coverage. Only then may: accepted candidate + pose/joint evidence + movement evidence → exercise-specific guarded state machine → candidate repetition → manual/editorial verification. Phase 4 stops before that state machine.

## Licensing/provenance checklist

Before adding any backend, record and verify: framework source/license; dependencies and native runtime; model code/config license; checkpoint terms; training-dataset terms; derivative-model terms; and fixture rights. Do not pin MMAction2 or download checkpoints automatically until official compatibility and every term is verified. Phase 4 adds no action framework or checkpoint and makes no licensing conclusion about one.

## Current limitations

Heuristic interval localization is conservative and does not itself identify an exercise. Ordered-plan alignment is positional and requires credible intervals. Scores are deterministic ranking aids, not probabilities. There is no cross-scene person re-identification, specialized gym-equipment detector, production action model, rep count, confirmed set, or final editorial decision.
