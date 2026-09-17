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
