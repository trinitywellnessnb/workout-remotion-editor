# Workout Remotion Editor v2.3 — User Manual & Prompting Guide

Workout-specific editorial intelligence for ChatGPT, designed to direct Remotion and compatible video-editing tools.

## What changed in v2.3

v2.3 preserves the complete rep-aware workout intelligence and official Remotion routing from v2.2, then adds an evidence-informed retention and shareability layer. It plans a truthful viewer promise, purposeful narrative beats, an earned payoff, a supported reason to share, optional honest looping, controlled variants, and analytics-informed revision—without engagement bait or performance guarantees.

## 1. What This Skill Is
Workout Remotion Editor v2.3 analyzes one or more exercise clips, decides what should appear in the edit, and delegates implementation to Remotion or another compatible editor. It reasons about exercises, working sets, repetitions, movement phases, high-effort moments, useful setup footage, exercise visibility, editorial pacing, and teaching overlays before the timeline is built.

Default behavior: one vertical 9:16 social-media-ready MP4, source audio muted, a truthful visually compelling hook when supported, and important technique kept readable.

## 2. v2.3 Remotion Skill Integration
Workout Remotion Editor decides **what** the workout edit should be; Remotion's official skills remain authoritative for **how** it is implemented.

- `remotion-best-practices` — general router.
- `remotion-create` — project/composition creation.
- `remotion-markup` — composition structure, media, timing, typography, animation, effects, trimming, playback rate, transitions.
- `remotion-multimedia` — media metadata through Mediabunny.
- `remotion-captions` — spoken captions/subtitles.
- `remotion-interactivity` — Studio-editable controls.
- `remotion-studio` — preview and visual inspection.
- `remotion-render` — final export.
- `remotion-docs` — current/version-sensitive API lookup.
- `remotion-upgrade` — project/skill upgrades when necessary.
- `remotion-saas` — app/service/product architecture.
- `remotion-maps` — only when workout content genuinely needs geographic visualization.

These upstream skills are routed to when available; they are not copied into this skill.

## 3. Retention & Shareability
The new layer optimizes for sustained understanding rather than empty watch time. It defines a target audience and one-sentence viewer promise, maps the hook/orientation/progression/payoff/close, and chooses a supported share reason: utility, identity/community, achievement/story, conversation, or delight/craft.

Hooks must be immediately legible and truthful. Curiosity must be paid off. Pattern changes need a purpose. Loops may not invent an extra rep or false continuity. Calls to action must match real value, and the skill never promises virality or treats changing platform heuristics as facts.

When analytics exist, the user's comparable performance data outranks generic editing heuristics. For A/B tests, change one principal variable per pair, assign stable variant IDs, and define the decision metric before publication when possible.

## 4. Best Way to Prompt It
Use: **Goal + Pacing + Hook + Coverage + Overlays + Audio/Style + Anything that must remain unchanged.** You do not need to write Remotion code.

## 5. Pacing Modes
- **Quick — ~10–25 sec:** aggressive compression, immediate activity, short rep selections, almost no dead time.
- **Standard — ~20–40 sec:** default for “make this social media ready”; balances retention with workout coverage.
- **Extended — ~40–75 sec:** more working-set content while still removing unnecessary dead time.

These are soft targets. Explicit instructions and truthful workout representation outrank runtime.

## 6. Hook & High-Effort Rep Editing
The skill can compare visible repetitions and look for increased rep duration, slower effort phases, sticking regions, brief stalls, shaking, visible exertion, late-set position, and successful completion. A slow rep is evidence, not proof of failure. If no trustworthy high-effort moment exists, use another truthful compelling opening.

## 7. Rep-Aware & Movement-Phase Editing
Examples: squat descent → bottom → ascent → standing completion; bench lowering → bottom/chest region → press → lockout; curl extension → concentric → peak → eccentric return; row reach → pull → contraction → return; deadlift setup → pull → lockout → descent/reset. Phase information can drive cuts, counters, crops, coaching timing, and overlays without showing phase labels unless requested.

## 8. Rep Counters
Rep counters are opt-in and should advance on completed visible reps. If reps are too obscured to count reliably, omit an uncertain automatic count. User-supplied counts may be synchronized to visible completions.

## 9. Exercise Labels, Workout Data & Coaching
Exercise labels, sets/reps, user-supplied load, rest, supersets/circuits, tempo, RPE/RIR, and workout structure may be displayed when supplied or reliably known. Never guess load or RPE/RIR from appearance. User-provided coaching language takes priority and should be timed to the relevant movement phase when possible.

## 10. Instructional Edits & Animated Callouts
Instructional edits can sequence step-by-step teaching points. Supported callouts include arrows, lines, circles, joint markers, ROM indicators, directional indicators, highlighted regions, progress bars, and set indicators when requested. Keep overlays away from important joints, equipment, bar paths, and foot placement.

## 11. Glitch Terminology
- **Glitch clips** — blink-speed fragments of meaningful real rep regions.
- **Glitch transitions** — very fast digital vertical-strip/slice transitions.
- **Glitch effects** — RGB separation, static, distortion, screen tearing, etc.

## 12. Multi-Clip Editing
Analyze all uploaded clips before deciding structure. Identify exercise changes, set boundaries, hook candidates, redundant footage, useful setup, and logical joins. Preserve chronology when supportable; otherwise preserve upload order unless the user specifies another sequence.

## 13. Exercise-Aware 9:16 Reframing
Preserve the anatomy and equipment needed to understand the movement, not merely the face. Prefer stable framing; avoid constant tracking/panning unless it materially improves visibility.

## 14. Audio & Music-Aware Editing
Default: mute all source audio. Do not add replacement music automatically. If a supplied track has beat/onset data, align major cuts, transitions, text punches, and rapid montage cadence when practical. Workout movement readability outranks beat alignment.

## 15. Optional Intelligent Analysis Signals
When available, use scene boundaries, pose/keypoint data, rep state machines, beat/onset analysis, motion evidence, and crop evidence as supporting evidence—not authority. Never claim an analyzer was used unless its signal actually exists.

## 16. Internal Edit Blueprint
Before implementation, build a paper edit containing source clip, source start/end, purpose, exercise/set/rep/phase, playback speed, crop, transition, overlay timing/style, and confidence. Keep source-relative time separate from final timeline time.

## 17. Official Remotion Workflow in v2.3
1. Analyze all footage and build the workout edit blueprint.
2. Use Remotion Multimedia/Mediabunny for needed duration/dimension metadata.
3. Use Remotion Create only when a project/composition must be created; preserve existing projects.
4. Use Remotion Markup for timeline segments, media, frame-driven animation, timing, transitions, and overlays.
5. Use Remotion Captions for spoken captions/subtitles, separate from coaching overlays.
6. Use Remotion Interactivity when counters, labels, crop controls, callouts, hook duration, or section trims should remain editable in Studio.
7. Preview with Remotion Studio when available and inspect crop safety, collisions, timing, joins, audio policy, and synchronization.
8. Use Remotion Docs instead of guessing version-sensitive APIs.
9. Render through Remotion Render after QA passes.

## 18. Revision Stability
Small revision requests should modify the smallest reasonable portion of the accepted edit. “Change only the hook” should not rebuild exercise order, labels, source selections, or style unless required by timing dependencies.

## 19. Quality Control
Verify aspect ratio/resolution, MP4 playback, blank/duplicate frames, audio policy, transitions, crop safety, overlay readability, counter/cue synchronization, immediate hook behavior, intentional speed changes, and honest rep continuity. Validate machine-readable analysis/edit JSON with the bundled semantic validator before final rendering.

## 20. Feature Activation Quick Reference
| Feature | Activate with | Expected behavior |
| --- | --- | --- |
| Default | `Make this social media ready.` | Standard 9:16 edit, muted source audio. |
| Retention plan | `Optimize this for honest retention.` | Defines promise, beat map, payoff, and risks. |
| Shareability | `Make this useful to save and share.` | Selects a supported share reason; no engagement bait. |
| Variant | `Create two hook variants.` | Changes one main hypothesis and labels both variants. |
| Quick | `Quick workout Reel.` | Aggressive 10–25 sec pacing. |
| Extended | `Show more of the workout.` | More rep/set coverage. |
| Hook | `Open with my hardest successful rep.` | Truthful high-effort cold open. |
| Counter | `Count the final set reps.` | Counter synchronized to completed visible reps. |
| Labels | `Label each exercise.` | Timed exercise titles. |
| Coaching | `Add these cues…` | User language timed to movement. |
| Instructional | `Turn this into an instructional Reel.` | Stepwise overlays/callouts. |
| Glitch clips | `Glitch through the reps.` | Blink-speed rep fragments. |
| Glitch transitions | `Use glitch transitions.` | Vertical strip/slice transitions. |
| Glitch effects | `Add RGB/static glitch effects.` | Digital distortion. |
| Keep audio | `Keep the audio in clip 2.` | Overrides mute for that scope. |
| Music sync | `Sync cuts to this song.` | Uses beat/onset evidence when available. |
| Captions | `Add captions from the spoken audio.` | Routes to Remotion Captions. |
| Editable controls | `Make the counter and labels editable in Studio.` | Routes to Remotion Interactivity. |
| Preview | `Open this in Remotion Studio.` | Studio preview workflow. |
| Revision | `Change only the hook.` | Preserves accepted structure elsewhere. |

## 21. Copy-Ready Prompts
### Minimal
> Make this workout social media ready.

### Fast Reel
> Make these clips into one Quick 9:16 TikTok workout. Mute all source audio. Start with the strongest truthful high-effort rep, then rapidly move through the workout. Keep important joints and weights visible and remove almost all dead time.

### Full v2.3 showcase
> Make these clips into one fast TikTok workout. Start with my hardest-looking successful rep. Mute everything. Glitch through a few reps from the first two exercises, but show most of my final set. Count the final-set reps in the upper left. Put the exercise name up when each exercise starts. During my squat eccentric put “Control the descent” on screen and when I start driving up put “Drive!” Add “Finish Strong” over my last two reps. Keep overlays out of the way of my joints and equipment. Use cyberpunk vertical-slice glitch transitions between exercises, but no RGB/static glitch effects. Use the official Remotion skills for implementation, preview the composition in Studio if available, then render the final MP4.

### Instructional
> Turn this into a clean instructional Reel. Keep enough of each rep to understand the technique. Label the exercise. Add my coaching cues at the relevant movement phases, one at a time. Use arrows only where they clarify direction. Keep source audio muted. Make the exercise title, coaching text, and callout positions editable in Remotion Studio if practical.

### Music-synced
> Use the music track I supplied. Keep workout movement truthful and natural speed. Align exercise changes, transitions, and text punches to strong beats when possible. Use faster beat subdivisions for the rapid montage, but never cut through an important rep phase just to hit a beat.

### Captions + coaching
> Keep the spoken audio in this clip and add captions for what I say. Keep captions separate from my coaching overlay. Show “Control” during the lowering phase and “Drive” during the effort phase. Use the Remotion caption workflow and keep both captions and coaching text readable without covering the exercise.

### Revision
> Keep everything else exactly as it is. Change only the opening hook: use the final rep from the second exercise instead, and let it play about half a second longer.

## 22. Recommended Prompt Template
```text
Create one [Quick / Standard / Extended] 9:16 workout video from these clips.
HOOK: [what should open the video]
WORKOUT COVERAGE: [which exercises/sets/reps should get more or less screen time]
PACING: [fast, balanced, longer, approximate duration]
OVERLAYS: [rep counter, exercise names, sets/reps/load, coaching cues, captions, instructions, arrows/callouts]
STYLE: [clean, cyberpunk, glitch clips, glitch transitions, minimal, etc.]
AUDIO: [mute source audio / keep specified audio / use supplied music]
REMOTION: [preview in Studio / make selected elements editable / use captions / other implementation needs]
AUDIENCE & VALUE: [who this is for, why it is useful/shareable, optional CTA]
TESTING: [single variant variable and metric, if requested]
IMPORTANT RULES: [anything that must not be changed, anything to preserve, exact wording]

Analyze the footage first, build the edit around truthful visible workout evidence, then route implementation through the relevant official Remotion skills and render the finished video.
```

## 23. Practical Tips
Upload all clips together when practical; state clip order when it matters; provide known reps, weight, sets, RPE/RIR, and structure rather than asking the system to guess; provide your preferred coaching language; identify which sets should be counted; state whether failed reps may be used as hooks; state what must remain unchanged during revisions; specify subtle vs. aggressive music sync; distinguish glitch clips/transitions/effects; and ask for current Remotion docs when API behavior is uncertain.

## 24. Technical Notes for v2.3
The package remains modular. Workout analysis, editorial rules, overlays/output, analysis-pipeline concepts, Remotion editing intelligence, official Remotion skill routing, open-source notes, and QA/revision rules are progressively loaded as needed. A shared analysis-schema vocabulary and semantic validator remain included.

v2.3 integrates the current official Remotion Agent Skill categories as routing targets rather than cloning their source. External scene, pose, rep-state, beat/onset, and motion tools remain optional evidence.

## 25. One-Sentence Starting Point
> **Make these workout clips social-media ready with a strong truthful hook, smart rep-aware pacing, clean 9:16 reframing, muted source audio, and any counters/coaching/captions I specify—analyze first, then route implementation through the appropriate official Remotion skills, preview if available, and render the finished edit.**
