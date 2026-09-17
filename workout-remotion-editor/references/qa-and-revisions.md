# QA and revisions

## Pre-render

- Analysis validates; source IDs and time ranges resolve.
- EDL/edit blueprint has no accidental gaps/overlaps and composition duration matches.
- Reordered events, replays, speed changes, and illustrative footage are clear.
- Every factual overlay traces to footage or the brief.
- Counts match sufficiently visible completed reps or explicit user-supplied counts.
- Captions, spelling, names, units, and CTA are approved.
- Rights and privacy status are known for footage, music, fonts, logos, and code.
- Source-audio policy matches the brief; default workout source audio remains muted unless explicitly preserved.

## Remotion preview QA

When Remotion Studio is available, preview the composition before final rendering. Use the official `remotion-studio` and `remotion-interactivity` guidance where relevant.

Inspect:

- hook begins immediately and remains truthful
- crop preserves required joints/equipment
- exercise labels, counters, captions, coaching cues, and callouts do not collide
- rep counters advance at completed reps
- coaching cues appear during the intended movement phase
- captions represent spoken content and remain visually distinct from coaching overlays
- transition joins do not falsely imply uninterrupted rep continuity
- accelerated setup/rest footage remains understandable
- source audio stays muted/preserved exactly as requested
- Studio-editable controls behave as expected when interactivity was requested

If a Remotion API or component behavior is unclear or version-sensitive, route to `remotion-docs` rather than guessing.

## Render QA

Render representative stills at the hook, dense overlay moments, transitions, counter changes, and end card before the full export when practical. Then inspect the complete final render. Check first/last frame, black/dropped/repeated frames, crops, safe areas, legibility, occlusion, transition artifacts, speed ramps, A/V sync when audio is present, captions, and encoding metadata. Also inspect critical vertical content with platform UI-safe margins.

Do not say “QA passed” unless the entire rendered file was inspected.

## Revision discipline

Treat accepted edit sections as stable. Convert feedback into atomic changes and modify the smallest reasonable portion of the edit.

Examples:

- `Change only the hook` -> preserve later source selections, exercise order, overlays, and style; update only the hook and directly dependent transition/timeline math.
- `Move the rep counter` -> preserve count timing and other overlays; change placement only.
- `Show more of the final set` -> extend/replace only the relevant final-set segment and dependent timing unless the user asks for broader restructuring.

Ripple timing may shift later timestamps, but later editorial decisions should remain unchanged unless they genuinely depend on the revised section.

After trims, playback-rate changes, or FPS changes, revalidate downstream counters, captions, coaching cues, audio automation, transitions, and total duration. Increment versions; never overwrite an approved master without permission.

## Delivery report

Report output paths; resolution/FPS/codec/duration; source and analysis versions when applicable; validation result; QA performed; key creative choices; licensing/attribution notes; and material uncertainty or limitations.

## Retention and shareability QA (v2.3)

Confirm that the opening is immediately legible and fulfills a specific viewer promise; the beat structure advances rather than delays that promise; any reordered opening, replay, or loop preserves chronology and rep counts; the payoff is delivered; and any share reason or CTA is supported by actual utility, identity/community relevance, achievement/story, conversation value, or craft. Do not report virality or retention as guaranteed. For variants, verify stable IDs and one principal changed hypothesis. Treat first-party analytics as diagnostic context, not proof of causation.
