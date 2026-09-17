# Workout Remotion Editor v2.1 — User Manual

## 1. Purpose

Workout Remotion Editor is a ChatGPT skill for analyzing workout footage and planning or executing accurate edits. It supports social highlights, set recaps, verified rep counters, observable coaching callouts, struggle-hook narratives, and instructional videos. It creates a structured analysis and paper edit before implementation so editorial claims remain reviewable.

Remotion is the recommended implementation/rendering layer. Other capable video-editing agents or plugins are experimental: use them only if they can honor exact timing, compositing, audio, deterministic export, and final-output QA.

## 2. Install

### From GitHub Actions

1. Visit the repository's **Actions** tab and open the latest successful **Package skill** run.
2. Download the `workout-remotion-editor-skill` artifact.
3. Unzip the downloaded artifact wrapper if needed and locate `skill.zip`.
4. Open ChatGPT and go to **Settings → Skills** (wording/availability can vary by account or workspace).
5. Select **Create/Upload skill**, upload `skill.zip`, and enable it.
6. Confirm the installed skill is named **Workout Remotion Editor**.

The ZIP root must contain `SKILL.md`, `agents/`, `assets/`, `references/`, and `scripts/`; do not upload the whole repository tree as the skill.

### From a clone

Clone the repository and package the contents of `workout-remotion-editor/` at the archive root. Prefer the GitHub Actions artifact because its structure and validation are automated.

## 3. Before starting

Provide footage through a ChatGPT-supported attachment or a filesystem/cloud connector accessible to the editing agent. Keep originals backed up. State, when known:

- target platform and 16:9, 9:16, 1:1, or custom aspect ratio;
- target length and number of versions;
- audience, goal, tone, pacing, brand rules, and call to action;
- caption/language and accessibility requirements;
- music rights and whether source audio should remain;
- privacy constraints and names/metrics that may appear;
- desired format, resolution, FPS, codec, and deadline.

If omitted, the skill states its assumptions. The default delivery is a vertical 1080x1920, 30 fps H.264/AAC MP4 with a clean style, source audio, and no unlicensed music.

## 4. Choose a workflow

### Quick

Use for one short clip or a simple deliverable. It performs metadata inspection, a coarse complete scan, concise paper edit, essential implementation, render, and QA. It never skips factual, safety, licensing, or final-playback checks.

### Standard

Use by default. It performs full structured analysis, a detailed paper edit, overlay and audio plans, validated JSON, implementation, complete render QA, and a delivery report.

### Extended

Use for long/multiple/multi-camera sources, instructional work, detailed movement analysis, or multiple deliverables. It can create proxies/contact sheets, deeper event and rep maps, alternative edits, review checkpoints, and versioned revision rounds.

## 5. Working sequence

1. **Intake:** The skill confirms assets, goal, output, rights, privacy, and mode.
2. **Inventory:** It records duration, FPS, dimensions, rotation, codecs, audio, and integrity issues without changing originals.
3. **Complete scan:** It reviews the entire timeline before selecting highlights.
4. **Analysis:** It marks sets, repetitions when countable, rests, transitions, effort moments, audio, occlusion, and defects with confidence.
5. **Validation:** It saves analysis JSON and runs `validate_analysis.py` against `analysis-schema.json`.
6. **Paper edit:** It returns ordered source/timeline ranges, rationale, audio, transitions, and overlay links for review.
7. **Implementation:** It uses Remotion by preference, or an explicitly experimental capable editor.
8. **QA:** It renders representative stills, watches the complete export with sound, checks technical/editorial/accessibility/licensing criteria, and revises.
9. **Delivery:** It reports paths, settings, analysis/EDL versions, decisions, caveats, and validation/QA results.

Ask to approve the paper edit before rendering when the portrayal, factual claims, duration, or cost matters.

## 6. Specialized workflows

### Honest struggle hook

Ask for a verified high-effort opening. The skill may use slowed movement, pauses, visible shaking, exertion audio, spotting, or abandonment as evidence, but it must not infer injury, pain, or emotional state. After the hook it supplies context and avoids false chronology; replays and reordered moments are labeled where ambiguous.

### Verified rep counter

Specify the exercise and whether partial repetitions should be shown but not counted. The skill defines an observable state cycle, proposes rep boundaries, manually verifies completed cycles, records confidence, and binds displayed count changes to those events. Occluded or ambiguous attempts stay uncertain rather than being guessed.

### Coaching overlays

State whether cues come from a qualified coach/user or should be neutral observations. The skill times one short cue at a time to visible evidence, avoids covering relevant joints/equipment, and notes camera-angle limitations. It does not diagnose injury or replace professional medical/coaching advice.

### Instructional video

Provide the teaching objective and audience level. A typical structure is movement goal, setup, execution, checkpoints, supported visible errors/corrections, and recap. Replays, freezes, illustrative shots, and chronology changes are clearly signaled. Captions and legibility are checked in the final render.

## 7. Understanding outputs

- **Analysis JSON:** machine-checkable sources, segments, reps, events, issues, confidence, and notes.
- **Paper edit/EDL:** exact source in/out and timeline positions, narrative purpose, audio, transitions, speed, and overlays.
- **Overlay schedule:** exact content/value, timing, placement, style/animation, and evidence link.
- **Render:** encoded video plus requested variants/stills.
- **QA/delivery report:** what was checked, technical properties, choices, rights notes, and remaining uncertainty.

The validator checks both JSON Schema and semantic rules such as unique IDs, referenced sources, increasing ranges, source-duration bounds, and repetition-to-segment references.

## 8. Revision requests

Give timecoded, atomic notes: “At 00:14, shorten cue to ‘Drive evenly’” is better than “make it pop.” Separate factual/technical corrections from preferences. After trims or FPS changes, ask the skill to revalidate downstream counters, captions, overlays, audio automation, transitions, and total duration. Keep approved masters and increment filenames.

## 9. Safety, truth, rights, and privacy

The skill must not invent repetitions, results, speech, struggle, chronology, or medical conclusions. It should not expose private metadata or use face/identity/biometric inference. You remain responsible for permission to use the people, footage, music, fonts, logos, models, and code in a release. No dependency or asset becomes licensed merely because an agent can access it.

This repository vendors no third-party repositories. PySceneDetect, TensorFlow.js MoveNet/BlazePose, MediaPipe-style state concepts, librosa, Essentia, official Remotion agent skills, and Ripple-inspired concepts are attributed as optional tools or inspirations. External projects remain under their respective licenses; check exact versions and use cases.

## 10. Troubleshooting

- **Skill not recognized:** ensure `SKILL.md` is at the ZIP root and the folder/archive is named consistently.
- **Full JSON Schema validation:** install `jsonschema`; without it the validator automatically performs core structural and semantic checks.
- **Count is uncertain:** improve the camera view, supply the counting rule, or request a manual review; do not force a number.
- **Variable-frame-rate drift:** create a derived constant-frame-rate proxy and retain the original/source mapping.
- **Overlay is hidden by app UI:** increase safe margins and test on the target platform layout.
- **Render differs between runs:** pin dependencies, remove live network inputs and nondeterminism, and use explicit FPS/frame timing.
- **Music cannot be cleared:** replace it with licensed/user-supplied audio or deliver without music.

## 11. Prompt templates

**Quick:** “Use `$workout-remotion-editor` in Quick mode for a 20-second vertical highlight; preserve truthful chronology and source audio.”

**Standard:** “Use Standard mode; inspect all footage, validate the analysis, present the EDL for approval, render in Remotion, and complete QA.”

**Extended:** “Use Extended mode for these cameras; create a selects map, main/short variants, rep analysis, review checkpoints, and versioned revisions.”

**Struggle hook:** “Open on a verified high-effort moment without implying pain or failure; contextualize it and label any replay/reordering.”

**Rep counter:** “Define and verify the complete rep cycle, exclude partial attempts, and synchronize the counter to validated events.”

**Coaching:** “Add neutral, evidence-linked coaching cues one at a time; acknowledge camera limitations and avoid diagnosis.”

**Instructional:** “Teach setup through execution and recap, using supported examples, labeled replays, captions, and accessibility QA.”
# Workout Remotion Editor v2.1 User Manual & Prompting Guide

For intelligent workout-footage analysis, editorial direction, overlays, and Remotion rendering.

**Core idea:** AI analyzes and directs the workout edit. Remotion implements the edit.

## What this skill is

Workout Remotion Editor v2.1 is a workout-specific video directing skill designed to analyze one or more exercise clips, decide what belongs in the edit, and then use Remotion as the programmatic editing and rendering layer. It is intended for Reels, TikTok, Facebook Reels, YouTube Shorts, and other workout/social video formats.

The skill is not just a collection of transitions. Its job is to understand the workout first—sets, reps, movement phases, high-effort moments, useful setup footage, exercise visibility, and requested teaching content—then translate those decisions into a Remotion timeline.

### Defaults

- One finished vertical video unless you ask otherwise.
- Standard pacing by default.
- Source audio muted unless explicitly preserved.
- Truthful high-effort hook selection when supported by footage.
- Exercise technique remains readable.
- Minimal overlays unless requested.

## Best way to prompt it

Best results come from specifying six things:

1. **Goal** — what should the finished video feel like?
2. **Pacing** — Quick, Standard, Extended, or a custom runtime.
3. **Hook** — what should open the video?
4. **Workout coverage** — which sets/reps matter most?
5. **Overlays** — counters, labels, coaching, guides, callouts.
6. **Audio/style** — muted audio, supplied music, transitions, effects.

Example:

> Make these clips social-media ready. Use Standard pacing. Start with the strongest truthful high-effort rep, then return to the workout in understandable order. Keep the source audio muted. Use clean transitions and preserve exercise technique.

## Pacing modes

### Quick

Typical target: 10–25 seconds. Aggressive compression, immediate activity, short rep selections, almost no dead time.

### Standard

Typical target: 20–40 seconds. Balances retention with fair workout representation.

### Extended

Typical target: 40–75 seconds. Shows substantially more working-set content while still removing dead time.

These are soft targets; truthful workout representation and explicit instructions outrank runtime.

## Hook and struggle-rep editing

The skill can look for visually supportable high-effort moments by comparing reps within a set. Signals can include increased rep duration, a slower effort phase, sticking region, brief stall, shaking, visible exertion, late-set position, and successful completion after increased effort.

It should not assume the final rep is hardest, label intentional slow tempo as failure, or fabricate a struggle moment when none is supportable.

Example:

> Use one struggle/high-effort rep as the hook. Pick the strongest successful rep that is clearly harder than the athlete’s earlier reps. Let it play long enough to feel the effort, then cut back to the beginning of the workout.

## Rep-aware and movement-phase editing

The skill can reason about repetitions as movement phases rather than arbitrary timestamps. This improves cut placement, rep counters, rapid montages, coaching timing, and instructional overlays.

Examples:

- Squat: descent → bottom → ascent → standing completion
- Bench press: lowering → bottom/chest region → press → lockout
- Curl: extension → concentric curl → peak → eccentric return
- Row: reach/extension → pull → contraction → return
- Deadlift: setup → pull → lockout → descent/reset

Phase labels are not automatically displayed unless requested.

## Rep counters

Rep counters are available on request. The count should advance on completed visible reps, not arbitrary time intervals. If reps are too obscured to count reliably, the skill should omit uncertain automatic counts rather than invent them.

Example:

> Count every clearly visible rep in the final set. Put the counter in the upper left, keep it compact, and punch each number on screen exactly as the rep completes. If the count is uncertain, do not invent it.

If you know the count:

> There are 10 reps in this set. Count 1–10 and synchronize the counter to each completed rep. Make reps 9 and 10 slightly more emphatic.

## Exercise labels, workout data, and coaching overlays

Supported on request:

- exercise labels
- sets and reps
- user-supplied load/weight
- rest periods
- supersets/circuits
- tempo
- user-supplied RPE/RIR
- coaching cues
- educational notes

Example:

> Label each exercise when it begins. During the squat eccentric, show “Control the descent.” As I start driving up, replace it with “Drive!” Remove each cue after the relevant movement phase.

## Instructional videos and multi-step guides

For instructional edits, the skill can sequence teaching points over the exercise rather than dumping a long list on screen. It can also support arrows, lines, circles, joint markers, ROM indicators, directional indicators, highlighted regions, progress bars, and set indicators when requested.

Example:

> Turn this into an instructional squat clip. Use these steps: 1) Set your feet, 2) Brace your core, 3) Sit down and back, 4) Keep the whole foot planted, 5) Drive up. Show each instruction only when it becomes relevant. Add a subtle downward arrow during the descent and an upward arrow during the drive.

User-provided teaching language takes priority over generic AI phrasing.

## Glitch terminology

These terms intentionally mean different things:

- **Glitch clips** — blink-speed fragments of meaningful real workout movement.
- **Glitch transitions** — very fast cyberpunk vertical-strip/slice transitions between clips.
- **Glitch effects** — RGB separation, static, distortion, digital noise, screen tearing.

Example:

> Start with one full high-effort rep, then glitch through the first two exercises using very short biomechanically meaningful rep fragments. Use cyberpunk vertical-slice glitch transitions between exercises, but do not add RGB/static glitch effects.

## Multi-clip editing

When several clips are uploaded, the skill should analyze all of them before deciding the structure. It should identify likely exercise changes, set boundaries, repeated footage, hook candidates, useful setup, stronger reps, redundant material, and logical joins.

Useful clips should normally become one continuous video, not a raw concatenation. Preserve chronology when supportable; otherwise preserve upload order unless the user specifies another sequence.

## Reframing and 9:16 cropping

The default output is vertical 9:16, but the crop should be exercise-aware. The goal is not merely to keep the face centered; relevant joints and equipment should remain visible.

Stable framing is preferred. Auto-tracking, panning, and zooming should occur only when they materially improve visibility.

## Audio and music-aware editing

- Default: mute source audio.
- Say `keep the audio` and specify the desired scope to override.
- Replacement music is not automatically added.
- When reliable beat/onset data is available for supplied music, cuts, transitions, text punches, and rapid montage cadence can align to musical events.
- Workout timing outranks beat synchronization.

Example:

> Mute all source audio. Use the music track I supplied. Sync major exercise changes and glitch transitions to strong beats when practical, but do not cut a rep at a bad biomechanical point just to hit the music.

## Optional intelligent analysis signals

When the environment can provide them, the skill can benefit from:

- scene/cut/fade detection
- pose landmarks/keypoints
- rep state-machine evidence
- beat/onset timestamps
- subject/camera motion evidence

These signals provide evidence, not authority. The skill should never claim they were used unless they actually exist. When unavailable, it falls back to careful visual reasoning.

## Internal edit blueprint

Before Remotion builds the composition, the skill can construct an internal paper edit/edit blueprint containing:

- source clip and source start/end time
- editorial purpose
- exercise/set/rep/movement phase when known
- playback speed
- crop/reframe behavior
- transition choice
- overlay text/type/timing/position/animation
- confidence/uncertainty

This improves revision stability.

## Revision commands

Use local revision instructions when most of an edit is already accepted.

Examples:

> Keep everything else exactly as it is. Change only the opening hook: use the final rep from the second exercise instead, and let it play about half a second longer.

> Keep the current edit structure. Show more of the final set, but do not change the hook, exercise order, labels, or transitions.

> Move the rep counter so it does not cover my dumbbell. Do not alter the timing or any other overlay.

## Quality-control behavior

Before a requested finished video is returned, the skill is instructed to verify:

- expected aspect ratio and resolution
- rendered MP4 exists and plays
- no accidental black/blank frames
- no unintended duplicate segments
- source audio remains muted unless preserved
- transitions render correctly
- athlete is not unintentionally cropped
- important joints/equipment remain visible
- overlays are readable and avoid major platform UI zones
- rep counters correspond to visible reps
- instructional overlays appear at appropriate moments
- hook begins immediately when requested
- no unexplained long dead sections
- playback-speed changes look intentional
- compressed rep coverage does not falsely appear uninterrupted

## Prompt library

### Minimal default edit

> Make this workout social media ready.

### Fast TikTok/Reel

> Make these clips into one Quick 9:16 TikTok workout. Mute all source audio. Start with the strongest truthful high-effort rep, then rapidly move through the workout. Keep important joints and weights visible and remove almost all dead time.

### Full v2.1 showcase

> Make these clips into one fast TikTok workout. Start with my hardest-looking successful rep. Mute everything. Glitch through a few reps from the first two exercises, but show most of my final set. Count the final-set reps in the upper left. Put the exercise name up when each exercise starts. During my squat eccentric put “Control the descent” on screen and when I start driving up put “Drive!” Add “Finish Strong” over my last two reps. Keep overlays out of the way of my joints and equipment. Use cyberpunk vertical-slice glitch transitions between exercises, but no RGB/static glitch effects.

### Instructional coaching edit

> Turn this into a clean instructional Reel. Keep enough of each rep to understand the technique. Label the exercise. Add my coaching cues at the relevant movement phases, one at a time. Use arrows only where they clarify direction. Keep the source audio muted and do not add music.

### Extended workout recap

> Make an Extended workout video. Show roughly 50–75% of the reps from complete sets where practical, favoring the beginning and end of each set. Preserve the hardest successful reps. Make any skipped middle reps visually obvious with clean jump cuts so it never looks like an uninterrupted set.

### Music-synced edit

> Use the music track I supplied. Keep workout movement truthful and natural speed. Align exercise changes, transitions, and text punches to strong beats when possible. Use faster beat subdivisions for the rapid montage, but never cut through an important rep phase just to hit a beat.

### Counter + coaching

> Count all reliable completed reps in the final set. Put the counter in the upper left unless that covers the exercise. Show “Control” during the lowering phase and “Drive” during the effort phase. On the last two reps, replace the cue with “Finish Strong.”

## What not to ask it to guess

- exact weight/load when unsupported
- failure versus intentional slow tempo from speed alone
- pain, injury, diagnosis, rehab status, or clinical meaning from appearance
- RPE/RIR unless provided
- chronology when clips do not support an order
- rep counts when repetitions or boundaries are too obscured
- technique judgments presented as certainty when relevant joints are not visible

## Recommended prompt template

```text
Create one [Quick / Standard / Extended] 9:16 workout video from these clips.

HOOK: [what should open the video]
WORKOUT COVERAGE: [which exercises/sets/reps should get more or less screen time]
PACING: [fast, balanced, longer, approximate duration]
OVERLAYS: [rep counter, exercise names, sets/reps/load, coaching cues, instructions, arrows/callouts]
STYLE: [clean, cyberpunk, glitch clips, glitch transitions, minimal, etc.]
AUDIO: [mute source audio / keep specified audio / use supplied music]
IMPORTANT RULES: [anything that must not be changed, anything to preserve, exact wording]

Analyze the footage first, build the edit around truthful visible workout evidence, then use Remotion to implement and render the finished video.
```

## Practical tips

- Upload all workout clips you want considered in the same request when possible.
- State clip order when it matters and is not obvious.
- Supply exact reps/weight/sets when known.
- Provide your preferred coaching language for educational edits.
- Say which sets should receive counters.
- For struggle hooks, specify whether failed reps are acceptable.
- For revisions, explicitly state what must remain unchanged.
- If music is supplied, state whether beat sync should be subtle or aggressive.
- Use `glitch clips`, `glitch transitions`, and `glitch effects` deliberately; they are separate concepts.

## Technical notes

The current v2.1 skill package uses modular progressive loading. Workout analysis, editorial rules, overlays/output, analysis-pipeline concepts, Remotion editing intelligence, open-source integration notes, and QA/revision rules are loaded as needed. A shared analysis-schema vocabulary can be used for machine-readable evidence, and a validation script is included for checking structured analysis/edit data before rendering when such data is produced.

External tools are optional, not hard dependencies. The Skill contains integration concepts inspired by open-source scene detection, pose/keypoint analysis, rep state machines, beat/onset analysis, and Remotion editing patterns. When unavailable, the Skill falls back to visual analysis and conservative inference.

## One-sentence starting point

> Make these workout clips social-media ready with a strong truthful hook, smart rep-aware pacing, clean 9:16 reframing, muted source audio, and any counters/coaching overlays I specify—analyze first, then have Remotion build and render the finished edit.
