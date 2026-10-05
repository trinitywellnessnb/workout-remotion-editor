# Phase 12 timeline composer

## Boundary and architecture

`scripts/timeline_composer.py` is the final editorial compiler between the
rep-aware Director, resolved style, semantic shot Director, and Remotion. It
does not analyze pixels, infer exercises, choose unreviewed repetitions, or
rerank semantic evidence. Upstream order and identities are authoritative.

The deterministic stages are: normalize available inputs; consume resolved
style and semantic candidates; preserve required rep selections; assign style
phases and duration bands; remove low-value optional material when necessary;
trim only to supplied source bounds; compile playback; assign role-aware
transitions; calculate overlap-aware composition time; map overlays and rep
counters; validate; then emit renderer props.

## Normalized timeline

The top-level `timeline` has `duration_seconds`, `target_duration_seconds`,
`fps`, `aspect_ratio`, and ordered `segments`. Every segment records exact
source and composition ranges, playback rate, optional time-remap curve, shot
role/candidate, exercise and reviewed rep identities, source and continuous
display numbers, continuity group, replay identity, transitions, overlay-safe
regions, selection reasons, and an explicit source-to-composition mapping.
The output seed and SHA-256 content hash make reproducibility inspectable.

## Duration and pacing

Phase 10 duration distributions drive optional shot lengths rather than a
single global duration. Complete reviewed-rep anchors remain complete. When a
budget is tight, the composer removes rest/dead time, redundant setup,
walking/context, detail, then secondary hero material before core movement.
It warns rather than damages required content when an exact target is unsafe.
Style phases are attached per segment, including fast-to-cinematic blends.

Micro/detail roles are capped to their meaningful source bounds. Phase 11
already controls dense micro runs and inserts anchors; Phase 12 preserves that
grammar rather than making a new semantic decision.

## Transitions and time mapping

Transitions combine the Phase 10 allowed palette with adjacent Phase 11 roles.
Hard cuts have zero duration. Dissolves, fades, motion matches, whips, and
glitches use overlap timing, so final duration is not a naive sum of clips.
Omitted-middle repetition jumps receive an explicit cut or style-supported
motion/glitch treatment and never imply source continuity.

Normal, constant fast motion, and smooth dramatic time curves are renderer
neutral. Setup/breather material may speed up; active repetitions do not do so
for budget pressure. A requested final-rep slowdown uses a cubic-bezier
1.0 → 0.78 → minimum → 0.78 → 1.0 curve around reviewed action evidence (or a
declared center fallback). Below 50fps, its minimum rate is conservatively
limited and `slowdown_limited_by_source_fps` is recorded. Optical flow is not
invented.

`source_to_composition` is authoritative for counters, captions, coaching, and
future music sync. Optional rhythmic-boundary and flexible-trim fields reserve
that future integration without requiring audio in Phase 12.

## Replays, counters, and overlays

A hook replay carries the same editorial rep ID and `hook_replay` identity but
has counter eligibility disabled. Its chronological primary occurrence counts
normally. Retained source reps such as 1,2,3,8,9,10 therefore display 1–6.
Segments expose safe overlay regions and counter contracts; Remotion only
renders them.

## Fallback and validation

Input fallback order is semantic shots, Phase 9 clips, scene/activity
candidates, then manual clips. Missing all four is a hard error. Validation
rejects invalid ranges/rates, illegal or impossible transitions, negative or
inconsistent composition timing, reverse chronology, duplicate primary reps,
counted hook replays, missing sources, and final-duration inconsistencies.
Target overruns caused by truth-preserving required footage are warnings.

## CLI and Remotion adapter

```bash
python workout-remotion-editor/scripts/timeline_composer.py input.json \
  --prompt "Start TikTok-fast but make the last set cinematic" \
  --target-duration 30 --output timeline.json
```

The JSON includes a human-readable summary. `to_remotion_props()` and
`remotion/timelineAdapter.ts` perform only seconds-to-frame/property mapping.
They never select footage, style, ordering, transitions, or repetitions.

Deterministic viral, cinematic, and mixed fixtures live in
`examples/phase12-timeline-fixtures.json`.

## Phase 13 music timing extension

Phase 13 consumes, rather than duplicates, the Composer's rhythmic-cut fields.
Segments expose locked/flexible boundaries, before/after safe margins,
transition safety, and timing priority. Reviewed reps, hook identity, counters,
and required footage are locked. The music synchronizer may adjust only flexible
composition duration within those margins, then reflows overlap and mappings.
See [Soundtrack intelligence](music-sync.md).

## Phase 14 music structure boundary

The authoritative Phase 12 timeline remains the input to Phase 14. Reliable
section changes, provider-supplied downbeats, accents, and actual variable-tempo
beat timestamps may adjust only boundaries already marked flexible and safe.
Locked reviewed reps, hook replays, counter events, chronology, and required
footage cannot move. Remotion receives only the compiled result and performs no
audio analysis or editorial timing decisions.

## Phase 15 bar-aware boundary

The Composer exposes no provider objects. Phase 15 may use normalized, supported downbeats or bar positions for sparse major boundaries already marked flexible; it may not manufacture boundaries, assume meter, or create perpetual bar cuts. Section roles and style pacing still control density. Locked reps, counters, source chronology, and all source-to-composition mappings remain authoritative.
