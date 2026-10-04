# Semantic Shot Director (Phase 11)

## Purpose and boundary

The Semantic Shot Director decides **what kind of source moment a candidate can
serve** before Remotion decides how to render it. It consumes existing scene,
activity, anonymous person/equipment track, pose/crop, user-label, and reviewed
Phase 9 repetition evidence. It does not decode a video again, identify people,
create repetitions, or diagnose pain, fatigue, safety, form, ROM, or failure.
Its scores are transparent editorial support/ranking heuristics—not calibrated
probabilities or aesthetic truth.

```text
source evidence -> role candidates -> quality components -> style fit
  -> diversity/continuity selection -> inspectable sequence plan -> Remotion
```

Run `scripts/semantic_shot_director.py EVIDENCE.json STYLE.json --prompt "..."`.
The evidence input is a JSON array. The style contract is the output of
`style_director.py`. The output retains every normalized `shot_candidate`, the
selected sequence, omissions and reasons, overrides, and chronology validation.

## Roles and conservative evidence

The normalized vocabulary includes `primary_movement`, `complete_rep_anchor`,
`partial_movement_detail`, `hook_candidate`, `hero_shot`, `setup`,
`equipment_adjustment`, `equipment_loading`, `equipment_pickup`,
`approach_station`, `walk_between_movements`, `stance_setup`, `grip_setup`,
`transition_breather`, `environment_context`, `recovery`, `rest`,
`close_detail`, `exercise_transition`, `ending_candidate`, `replay`,
`dead_time`, `unusable`, and `unknown`.

A candidate keeps multiple role candidates with support scores and evidence
reasons. `unknown` is retained when nothing has adequate support. Reviewed
editorial repetition IDs strongly support a complete-rep anchor and remain
traceable; raw machine rep candidates never become editorial truth. Localized,
supported person/equipment interaction may support adjustment, loading, pickup,
grip, or stance setup. Walking requires between-exercise context. Environment,
recovery, and rest require context or labels rather than merely low motion.
Slow motion is never interpreted as failure.

## Quality and compatibility

`shot_quality` exposes subject, working-anatomy and equipment visibility; 9:16
crop viability; framing headroom; track and camera stability; movement
completeness; duration usability; trim safety; overlay usability; occlusion and
blur penalties; an overall rank; and quality concerns. Working anatomy remains
a higher crop priority than face centering. Overlay regions are inputs rather
than a permanently reserved corner.

General usability is separate from style compatibility. Stable complete reps
rank well for coaching; dynamic details can rank well for gritty or viral work;
cinematic plans value environment, detail, complete reps, walking, hero, and
ending candidates; raw plans value natural approach/setup/exercise/recovery
progression. Handheld motion is tolerated more by gritty, raw, and viral
profiles, but severe blur remains a usability penalty.

Each candidate publishes minimum safe, maximum meaningful, and recommended
duration bounds. Phase 10 must sample within those bounds. Slow motion and speed
ramps require sufficient duration and at least 48 fps; normal speed remains
available. This prevents a duration preset from destroying a meaningful shot.

## Selection, breathers, continuity, and explanations

Selection uses a soft profile grammar, never a mandatory universal montage.
Setup, adjustment, walking, environment, recovery, and longer stable moments can
be deliberate breathers. A ratio guard prevents setup/breathers from crowding
out workout action, and micro-detail runs are capped before an anchor is sought.
Candidates sharing a reviewed rep or duplication group are suppressed unless a
shot is explicitly a replay. Diversity arises from role grammar and duplicate
groups; it is not forced when evidence is scarce.

Non-replay moments from a source are sorted and validated in source order.
Only explicit replay candidates may travel backward, such as a truthful hook
replay. This prevents semantic preference from producing later -> earlier ->
later source movement. Source chronology also supplies plausible walking/setup
bridges; the director never invents a bridge across unrelated evidence.
Role-aware transition guidance considers both neighbors (for example,
environment to detail may dissolve in cinematic work, while setup to movement
usually cuts). Motion/screen-direction metadata can be added by a future
provider; continuity remains a soft preference, never fabricated evidence.

Selected shots include concise `selection_reasons`; omitted shots name duplicate
or lower grammar/rank fit; source interval, rep IDs, replay status, quality
concerns, role supports, and style fit remain inspectable. These are decision
records, not hidden reasoning.

## Natural-language overrides and fallback

Explicit requests win over style: “only show the lifts,” “no walking clips,”
“use machine adjustments,” “show me loading the plates,” “more close-ups,”
“more full-body,” “no rest,” “nonstop,” “real workout, not an ad,” and “make it
look like a movie” force or suppress corresponding roles. Suppression wins on a
conflict.

Sparse semantic evidence does not block rendering. Fall back to Phase 9 reviewed
rep selection, then scene/activity evidence and source chronology. Candidate
creation is pure and deterministic, reuses derived evidence, and introduces no
ML dependency or repeated decoding. A future semantic provider may populate the
same evidence boundary without changing the contract.

## Limitations

The heuristics cannot truly understand an unlabeled interaction, visual beauty,
intent, screen direction, or physiological effort. Exposure is not scored
without supplied evidence. Duplicate groups are an approximation based on rep,
scene/source, or caller-provided grouping. Human review and the actual frames
remain authoritative.
