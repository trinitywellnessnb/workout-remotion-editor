# Rep-aware edit planning

`scripts/rep_aware_director.py` is the workout-specific Director between review and Remotion. It consumes only top-level, reviewed editorial `repetitions` (or repetitions explicitly marked `trust: user_supplied`). It never promotes raw `evidence.rep_candidates`. If no reviewed structure exists, it returns the legacy scene/activity/manual fallback rather than blocking the edit.

## Deterministic selection policy

Selection is per exercise, confirmed set, and unilateral side. An unconfirmed set label is ignored; the Director does not invent set boundaries.

- Fewer than five reps: retain all.
- Exactly ten: retain 1, 2, 3 and 8, 9, 10.
- More than twelve in default mode: retain the first three and last four.
- Extended movement scope: target about 40% (within the 25–50% range).
- Extended confirmed-set scope: target about 60% (within the 50–75% range).
- Quick mode: target about 30%, with first/last structure and minimal dead time.

Explicit `selection` values `all`, `whole_set`, `no_cuts`, `last`, and `first_last`, plus `reps_per_scope`, override defaults. Selection reasons and omission reasons remain inspectable. A target-duration budget removes an optional representative middle rep before considering any shortening; complete selected reps are preserved.

## Ranges, grouping, and chronology

Each selected repetition records editorial identity, source and display numbers, exercise/segment/set/side, source group, complete source bounds, padded selected bounds, reason, occurrence, and counter eligibility. Pre/post handles default to 0.25 seconds and are capped at 0.40 seconds and at editorial segment boundaries.

Consecutive selected reps from the same source group/scope are merged when the usable gap is small. Omitted middle reps prevent a merge, so the ten-rep policy produces two chronological fragments with a visible cut. Primary fragments in one continuous source group must remain in increasing source order; validation rejects reverse chronology and duplicate primary identities. Distinct original source groups may be reordered. Right-then-left source chronology is retained.

## Hooks, counters, timing, and rest

When requested, a complete final-three selected rep is chosen transparently as a `late_set_hook_candidate`, using duration only as editorial evidence. It is never called failure. The opening occurrence is `hook_replay`, retains the same editorial repetition ID, and is counter-ineligible. Its later `primary` occurrence supplies the one counter event. Source rep numbers (such as 1,2,3,8,9,10) remain audit metadata while displayed numbers are continuous (1–6). Counter display remains explicit opt-in and is rendered by the Phase 8 component, not by the Director.

Expected duration uses padded source duration divided by playback rate and accounts for transition overlap. Primary active reps remain at 1x by default. Short rests (default threshold two seconds) are skipped. Long rests retain a configurable 1–2 second orientation handle before activity resumes, or produce an inspectable `compressed_rest` fast-forward decision. Rest evidence does not confirm a set. Source audio remains muted by the skill default.

The Director produces normalized JSON. React/Remotion components render that timeline and do not perform rep selection.

## Semantic candidates after rep selection

Phase 11 may rank a reviewed repetition as a complete-rep, hero, hook, or ending
candidate, but it cannot manufacture or promote repetitions. Editorial repetition
IDs, padding rules, retained completions, replay/counter suppression, and source
chronology remain authoritative. If semantic evidence is absent, use this Phase 9
plan unchanged.
