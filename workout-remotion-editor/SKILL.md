---
name: workout-remotion-editor
description: Analyze raw workout footage and produce evidence-based paper edits, edit decision lists, overlays, coaching callouts, rep counters, and render-ready video plans. Use for fitness-video editing, workout highlights, exercise tutorials, struggle hooks, movement/rep analysis, Remotion compositions, or QA and revision of workout edits.
---

# Workout Remotion Editor v2.1

Turn workout footage into an accurate, useful edit without inventing events. Treat the source media, user brief, and verified analysis as authoritative. Recommend Remotion for implementation and rendering; another capable video-editing agent or plugin may execute the plan experimentally if it can preserve timing, overlays, audio, and QA requirements.

## Operating contract

1. Preserve source files. Never overwrite them.
2. Inspect available media metadata and the full timeline before choosing moments.
3. Separate observations from inferences. Do not diagnose pain, injury, intent, or technique from appearance alone.
4. Create an analysis artifact that conforms to `scripts/analysis-schema.json`, then run `scripts/validate_analysis.py`.
5. Produce a paper edit before implementation. Every cut and overlay must trace to evidence, the brief, or a clearly labeled creative choice.
6. Obtain confirmation before destructive work, publishing, or materially changing the athlete's portrayal.
7. Use frame-accurate timing: `frame = round(seconds * fps)`; use the composition FPS consistently.
8. Render, inspect, and revise. A successful command is not visual QA.

## Intake and mode

Collect or infer, then state: input paths, desired platform/aspect ratio, duration, audience, purpose, tone, branding, captions, music policy, privacy needs, output format, and deadline. Ask only blocking questions. Default to 1080x1920, 30 fps, H.264 MP4, source audio retained, no unlicensed music, and an accessible clean visual style.

Choose a mode:

- **Quick** — one short source or simple request; metadata, coarse scan, concise paper edit, one implementation/render pass, essential QA.
- **Standard** — default; full scan, structured analysis, detailed paper edit, overlays/captions, render, and complete QA.
- **Extended** — multiple/long sources, instruction, detailed movement review, or many deliverables; proxy/index sources, deeper event and rep analysis, variants, review checkpoints, and documented revision rounds.

Never let Quick mode bypass factual, safety, licensing, or final-output checks.

## Workflow

### 1. Inventory and inspect

Record each asset's path or stable ID, duration, frame rate, dimensions, rotation, codecs, audio channels/sample rate, and notable integrity issues. Generate proxies or contact sheets when useful. Preserve variable-frame-rate caveats and normalize only in derived files.

### 2. Analyze the complete footage

Read `references/workout-analysis.md`. Scan the entire timeline before selecting. Identify exercise/set boundaries, repetitions when countable, setup/rest/transitions, high-effort or struggle moments, instructional details, usable audio, occlusion, camera changes, and technical problems. Attach confidence and evidence to uncertain claims.

Computer vision and audio analysis are optional aids, not truth. PySceneDetect may propose shot boundaries; MoveNet/BlazePose-style pose estimates may propose landmarks; MediaPipe-style state machines may propose repetitions; librosa or Essentia may propose beat/onset/audio events. Verify proposals against the footage.

Create JSON with `project`, `sources`, `segments`, and optional `repetitions`, `audio_events`, `issues`, and `notes`. Validate it:

```bash
python workout-remotion-editor/scripts/validate_analysis.py analysis.json
```

### 3. Build the paper edit

Read `references/editorial-rules.md`. Define hook, context, progression, payoff, and close/CTA as appropriate. Provide an ordered EDL containing stable source ID, source in/out, timeline in/out, rationale, audio treatment, transition, and linked overlays. Keep handles around selected moments. Prefer motivated cuts; do not imply false chronology, counts, performance, or outcomes.

Workflow patterns:

- **Struggle hook:** open on a verified high-effort moment, quickly provide context, then show the honest build/payoff. Never fabricate a failed rep or sensationalize possible injury.
- **Rep counter:** define an observable cycle and state thresholds, count only completed verified cycles, display uncertainty rather than guessing, and reconcile on-screen count with the analysis.
- **Coaching overlay:** show one concise, observable cue at a time, time it to relevant evidence, avoid diagnosis, and use neutral language such as “consider” or “aim for.”
- **Instructional video:** establish the movement and goal, show setup, execution and key checkpoints, include common observable errors only when supported, then recap. Use replays/freeze frames without disguising chronology.

### 4. Design overlays and implementation

Read `references/overlays-and-output.md`. Produce an overlay schedule with IDs, text/value, exact interval, anchor/placement, style, animation, and evidence link. Keep text inside safe areas, legible, high contrast, and clear of the athlete and platform UI. Captions must reflect speech, not invented dialogue.

When using Remotion, probe media first, define deterministic typed input props, base timing on frames, preload media/fonts, sequence layers explicitly, avoid nondeterminism, and render a representative still plus the final video. Pin dependencies in the implementation project. If another editor is used, require equivalent deterministic timing and reviewability.

### 5. QA and revise

Read `references/qa-and-revisions.md`. Check editorial truth, source/sequence timing, rep counts, overlay text and safe areas, captions, audio peaks/sync, transitions, dropped/black frames, licensing, privacy, encoding, output dimensions/FPS/duration, and playback. Watch the entire rendered deliverable at least once. Return the output path, settings, analysis/EDL location, key editorial choices, caveats, and validation/QA results.

## Required reference loading

- Read `references/editorial-rules.md` for every edit.
- Read `references/workout-analysis.md` for analysis, rep counting, or coaching.
- Read `references/overlays-and-output.md` for visual treatments or rendering.
- Read `references/qa-and-revisions.md` before delivery or revision.
- Read `references/open-source-notes.md` before selecting third-party tools, assets, music, or code.

## Boundaries

Do not present coaching as medical advice; diagnose injury; alter the athlete's body or performance deceptively; use biometric/identity inference; expose private metadata; use unlicensed music, fonts, footage, or code; or silently discard uncertainty. Escalate visible possible injury, ambiguous counts that matter, missing rights, corrupt media, and contradictions in the brief.
