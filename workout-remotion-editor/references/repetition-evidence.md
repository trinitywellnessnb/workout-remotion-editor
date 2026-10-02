# Repetition evidence (Phase 5)

Phase 5 produces conservative **machine evidence**, not an editorial count. `evidence.rep_candidates` must never be copied automatically to top-level `repetitions`; that existing collection remains reviewed/manual output. No counter, annotation, overlay, or Remotion composition is created.

## Active boundary and CLI

The sole exact mapping is `dumbbell_row_single_arm` → `single_arm_dumbbell_row_v1` (version 1). There is no parent/family fallback: generic, barbell, cable, and machine rows are ineligible. Enable it with `--pose --rep-analysis`; optional controls are `--rep-rule`, `--rep-min-quality`, and `--rep-require-user-confirmation`. Dense sampling of 8–12 Hz is recommended. Disabled analysis emits neither a run nor rep collections. A runtime gate failure emits an ineligible `rep_analysis_interval`, distinguishing “analysis did not run” from eligible zero-rep evidence.

## Gates and laterality

Ordered hard gates require a rank-one exact candidate, no ambiguity/conflict, accepted identity, stable tracked person in one scene, unambiguous association, adequate pose coverage, at least about 6 usable samples/s with median interval ≤0.167 s, mandatory landmarks, compatible view/position, resolved side, specific-variant support, and exact mapping. Identity is accepted from user confirmation or a fused score at the configurable 0.85 policy threshold with specific support. Scores are not probabilities.

Working shoulder, elbow, and wrist are mandatory. Both shoulders and hips are preferred; three valid torso points are the conservative degraded mode. Knees, ankles, and face are not required. Side priority is explicit interval/entity context, then strong unilateral movement dominance. Handedness and screen position are never used. Left/right streams are isolated. A side switch closes a meaningful cycle as incomplete and recalibrates; streams are never mixed.

## Metric, calibration, and states

The compound signal combines torso/shoulder-relative wrist retraction (primary) and elbow flexion (required agreement). Neither alone can establish a rep. Supporting arm dominance, elbow/torso displacement, torso and entity motion, pose confidence, raw/smoothed agreement, regularity, and available camera evidence may validate, reject, or reduce quality, but cannot replace the sequence.

Calibration uses reliable smoothed samples from one source/scene/entity/side, robust 15th/85th percentiles, and raw/smoothed sanity checks. Defaults require about 0.12 torso lengths of path and 25° elbow excursion. Thresholds freeze during an active cycle.

`seeking_bottom → ready_bottom → concentric_pull → top_confirmed → eccentric_return → completed_bottom`

Completion requires bottom, sustained departure, pull, sustained top/turnaround, return, and confirmed bottom. Preserved timestamps are initial bottom confirmation, pull departure, top entry, top confirmation, return departure, bottom re-entry, and final confirmation. A direction change, top-only motion, half pull, or track-loss-interrupted movement cannot complete.

Hysteresis defaults are bottom enter ≤0.15, bottom exit ≥0.25, top enter ≥0.80, top exit ≤0.70. Bottom needs ≥0.15 s and two samples, pull ≥0.20 s, top ≥0.10 s and two samples, return ≥0.20 s, and the full rep ≥0.65 s. There is no normal maximum, so slow reps remain possible. One observation cannot skip states.

## Gaps, outcomes, quality, and false positives

A short tolerated gap is at most `min(0.25 s, 1.5 × nominal interval)` and one interior observation. It lowers quality and cannot independently establish a crossing, top, or completion. Scene/entity/side/candidate/rule changes, absence, ambiguity, excessive gaps, prolonged mandatory-landmark loss, and interval boundaries reset. Meaningful open cycles emit `incomplete` with a reason such as `partial_pull`, `no_return`, `track_loss`, `excessive_pose_gap`, `scene_cut`, `entity_reassignment`, `side_switch`, setup/pickup/set-down/rerack, candidate change, or interval end. Minor noise emits nothing.

`completed` means the ordered structure passed. `incomplete` means structure is missing. `uncertain` is reserved for a structurally complete cycle degraded by an allowable obstruction/gap, marginal top, supporting disagreement, camera contamination, or weak-but-eligible identity.

Quality is a reproducible `[0,1]` **evidence score, not a probability**. It combines identity, association, coverage/regularity, state completeness, amplitude, wrist/elbow agreement, side dominance, torso/camera stability, raw/smoothed agreement, and gap penalties. It cannot override hard gates.

Torso-relative geometry and elbow agreement suppress uniform camera/body translation. Moderate compatible torso motion may reduce quality. Large repositioning that destroys or dominates the reference terminates evidence. This is evidence validation, not form grading. Setup, entering position, pickup, set-down, rerack, short pulls, pauses, local extrema, bouncing, background people, tracker reassignment, wrong exercise/side, and low-confidence skeletons are explicitly rejected by gates and ordered-state requirements.

## Validation, review, and limitations

Semantic validation enforces usable runs, provenance, source/scene/entity/person/side compatibility, bounds, exact mapping, phase order and mandatory phases, outcome reasons, quality ranges, evidence references, duplicates, and completed-rep overlap. Completed reps in one stream may share only `min(0.10 s, 10% of the shorter rep)`; marked incomplete/uncertain alternatives may overlap.

Editors must inspect footage before promoting evidence to editorial repetitions. Image-plane pose remains vulnerable to occlusion, foreshortening, unusual views, clothing, camera motion, and tracking errors. Defaults are conservative starting values, not universal biomechanics. A future phase should validate and tune this isolated rule on consented, diverse real footage.
