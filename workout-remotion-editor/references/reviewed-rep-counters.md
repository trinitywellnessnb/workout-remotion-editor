# Reviewed repetition counters (Phase 8)

## Truth and activation boundary

A visible counter is **opt-in** and may use only reviewed top-level editorial
`repetitions`. Machine `evidence.rep_candidates` never activates or feeds the
counter. If a counter is requested without promoted repetitions, stop with:
`rep counter unavailable: repetitions have not been editorially reviewed/promoted`.
Completed `accept` and `adjust` decisions count; incomplete or unreviewed attempts
do not. Confidence is retained as editorial context but is not a form, ROM,
failure, pain, or technique judgment.

Use `scripts/rep_counter_timeline.py` to create provider-neutral Remotion props:

```json
{
  "rep_counter": {
    "enabled": true,
    "mode": "rep",
    "reset": "exercise",
    "placement": "top-right",
    "animation_enabled": true,
    "replay_behavior": "suppress"
  }
}
```

Modes are `number` (`1`), `rep` (`REP 1`), and `progress` (`1 / 10`). Progress
requires a positive, explicitly supplied `target_reps`; targets are never inferred.
The default reset is per confirmed exercise. `set` resets require confirmed
`set_id` metadata; activity or scene boundaries are not sets. Sides are separate
streams, so a confirmed left/right switch resets. `continuous` is available only
when explicitly selected.

## Edit-time mapping

Each edit clip declares `source_id`, `source_start`, `source_end`,
`timeline_start`, and positive `playback_rate`. Completion maps as:

`timeline_start + (rep.end - source_start) / playback_rate`

The counter increments at the reviewed completion (`end`), not motion onset, a
top position, or a machine direction change. Frame conversion uses round-half-up:
`floor(time * fps + 0.5)`. Half-open boundary handling ensures adjacent clips do
not both own a cut event.

A completion must survive its selected source window and at least half of the rep
must remain visible (override with a clip's `minimum_rep_visibility` only after
editorial review). Omitted and aggressively sliced reps emit nothing. Events are
sorted in final composition order, so trims, concatenation, speed changes, and
allowed clip reordering remain aligned.

Event identity is the editorial repetition ID. Reused source windows are
deduplicated. Clips marked `hook` or `replay` suppress the counter by default;
the later chronological occurrence can increment once. This prevents a visual
replay from becoming another workout repetition.

Displayed counts are continuous across retained reps. A first-three/last-three
edit therefore shows `1…6`, while each event retains `source_rep_number` (for
example `1,2,3,8,9,10`) for traceability. Showing original numbers is not a
Phase 8 display mode.

## Layout and rendering

The layout contract exposes four safe regions: `top-left`, `top-right`,
`bottom-left`, and `bottom-right`. Supply known anatomy/equipment/instructional
regions through `overlay_layout.occupied_regions`. Captions reserve both bottom
regions. Selection starts at the preferred region, falls back deterministically,
and fails rather than covering content when all regions are reserved. Re-evaluate
these regions after crop/reframe decisions.

`remotion/RepCounter.tsx` receives normalized events only. It contains no analysis
logic, changes value on the precomputed frame, and applies a short FPS-aware scale
pulse. Its compact high-contrast style uses conservative vertical-video margins.
Source audio behavior is unchanged and remains muted by default.

## Limitations

Phase 8 uses deterministic corner reservations, not moving object avoidance.
Editors must provide occupied regions from their crop/visual review. It does not
display original source numbering, infer workout targets, infer sets, or assess
rep quality. The repository provides a component and synthetic event fixture but
is not a standalone Remotion application with Chrome/render dependencies.
