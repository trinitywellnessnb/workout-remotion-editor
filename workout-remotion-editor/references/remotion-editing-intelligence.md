# Remotion Editing Intelligence

Use this reference when translating the internal edit blueprint into Remotion structure.

## 1. Paper edit before implementation

Treat the internal edit blueprint as a machine-checkable paper edit. Resolve source ranges, intended order, playback speed, overlays, crop behavior, and transitions before writing final timeline code.

Do not let rendering code become the place where editorial decisions are improvised.

## 2. Choose timeline behavior deliberately

For sequential workout edits where shortening one segment should move every later segment, prefer ripple-style sequencing. Current Remotion guidance uses `TransitionSeries` for this behavior.

Use independently positioned clips only when one element's timing should not automatically shift later clips.

Keep meaningful editable workout segments identifiable: Hook, Exercise 1, Transition, Exercise 2, Final Set, Outro, etc.

## 3. Favor explicit editable segments

When an edit is expected to be revised interactively, favor explicit authored timeline segments rather than hiding every clip inside opaque generated loops. This makes duration, trim, and transition changes easier to inspect and modify locally.

Do not over-apply this rule to repetitive decorative elements that are not timeline-editing targets.

## 4. Separate source time from timeline time

Track both:

- source-relative range: what part of the uploaded file is used
- timeline-relative range: where that segment appears in the final composition

Speed changes modify the mapping between these domains. Rep counters and movement-phase overlays should remain bound to source events and then transformed into timeline timing through the segment's playback-rate mapping.

## 5. Transition discipline

Use transitions only between meaningful segments. A transition should not hide an uncertain cut or make separated reps appear continuous.

For normal edits, prefer cuts, short fades, or subtle transitions. Use the skill's cyberpunk vertical-slice transition only when explicitly requested or already established as the edit's style.

## 6. Beat-aware placement

If beat timestamps exist, use them as candidate landing points rather than mandatory positions. Major structural cuts may land on strong beats; rapid glitch fragments may use subdivisions.

Never time-stretch a working rep solely to force beat alignment unless the user explicitly requests stylized retiming.

## 7. Revision locality

Preserve accepted timeline sections. If the user asks to change only the hook, isolate changes to the hook and any directly dependent transition/duration math. Ripple behavior may shift later timestamps, but later source selections, overlays, and editorial decisions should remain unchanged.

## 8. Render lint mindset

Before the final render, treat the composition as something that should pass a lint-like editorial check:

- all segment ranges are valid
- no source range is negative or past source duration
- timeline order is valid
- no unintended overlaps/gaps
- playback rates are positive and intentional
- requested overlays reference valid segments/reps/phases
- source audio policy is respected
- intended output dimensions and fps are valid

Use the bundled `scripts/validate_analysis.py` to validate structured analysis/edit data when such JSON is created.

## 9. Compose with the official Remotion Agent Skills

Do not treat Workout Remotion Editor as a replacement for Remotion's official implementation skills. Use `remotion-skill-routing.md` to route implementation work.

In particular:

- use `remotion-create` for project/composition creation
- use `remotion-markup` for timeline, animation, layout, media, timing, and effects
- use `remotion-multimedia` for media metadata and browser-side inspection
- use `remotion-captions` for spoken captions/subtitles
- use `remotion-interactivity` when high-value edit controls should remain adjustable in Studio
- use `remotion-studio` for preview and visual inspection
- use `remotion-render` for the final requested export
- use `remotion-docs` for version-sensitive API questions
- use `remotion-upgrade` only when the project or installed skills need an upgrade
- use `remotion-saas` only for app/product architecture
- use `remotion-maps` only when the workout content genuinely needs geographic visualization

Workout Remotion Editor should decide *what* the workout edit should be. The official Remotion skills should remain authoritative for *how* that edit is implemented in Remotion.
