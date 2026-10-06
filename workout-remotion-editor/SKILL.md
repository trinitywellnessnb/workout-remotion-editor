---
name: workout-remotion-editor
description: Analyze one or more uploaded workout videos and direct Remotion to create polished social-media-ready workout edits. Use for requests such as make this workout social media ready, edit my workout, make a Reel/Short/TikTok, quick/standard/extended workout edits, struggle-rep hooks, glitch clips, cyberpunk glitch transitions, synchronized rep counters, exercise labels, coaching cues, instructional overlays, or combining multiple workout clips. Default to one 9:16 finished MP4 with muted source audio unless the user overrides.
---

# Workout Remotion Editor v2.4

Act as the workout-video director first and the Remotion editor second. Analyze WHAT belongs on the timeline; use installed Remotion capabilities to implement HOW it is trimmed, sequenced, reframed, animated, speed-ramped, overlaid, and rendered.

## Core workflow

1. Inspect all supplied workout footage before committing to an edit. Treat every visual detection as an evidence-based estimate and never invent exercise identity, rep count, struggle/failure, chronology, load, or performance.
2. Read `references/workout-analysis.md` whenever the task requires rep/set analysis, movement-phase reasoning, hook selection, exercise-aware reframing, or a structured edit blueprint.
   For machine-readable exercise identity, also read `references/exercise-recognition.md`; treat candidates and intervals as evidence, never confirmed repetitions or sets. For gold evaluation or promotion into editorial repetitions, read `references/repetition-evaluation.md`; promotion always requires an explicit review sidecar.
3. Read `references/editorial-rules.md` for pacing modes, cut points, speed changes, rep selection, glitch terminology, transitions, and multi-clip structure. For reviewed-rep-driven source selection, chronology validation, hook replay, duration budgeting, and rest handling, also read `references/rep-aware-edit-planning.md`. For ordinary-language style requests, blending, duration distributions, pacing curves, setup/breather policy, semantic transitions, and time remapping, read `references/editing-style-director.md` and run `scripts/style_director.py` before implementation. Read `references/semantic-shot-director.md` and run `scripts/semantic_shot_director.py` when choosing evidence-backed source roles; explicit role requests override style and semantic selection never replaces reviewed-rep truth.
4. Read `references/retention-and-shareability.md` whenever choosing a hook, structuring a short-form narrative, adding a payoff/loop/CTA, comparing variants, or making claims about likely audience response. Treat retention and shareability as hypotheses to test, never guarantees.
5. Read `references/workout-analysis.md` when objective scene, pose, rep-state, beat/onset, motion, or crop signals are available or would materially improve the edit. External analyzers provide evidence, never authority.
6. Read `references/overlays-and-output.md` when the user requests overlays or non-default output, and `references/reviewed-rep-counters.md` for any rep counter.
7. Read `references/remotion-editing-intelligence.md` when translating the paper edit/edit blueprint into Remotion, especially for ripple timelines, source-to-timeline timing, beat-aware cuts, or revision-local changes.
8. Read `references/qa-and-revisions.md` before rendering a requested finished video and for follow-up revisions to an accepted edit.
9. Read `references/remotion-skill-routing.md` whenever Remotion is the implementation layer. Route implementation to the official Remotion skills: best-practices, create, markup, multimedia, captions, interactivity, Studio, render, docs, upgrade, SaaS, and maps when relevant. Do not duplicate their generic implementation knowledge here.
10. Build from the internal edit blueprint. Explicit instructions for the current video override every default in this skill.
11. Read `references/timeline-composer.md` and run `scripts/timeline_composer.py` to compile the final renderer-neutral plan. Treat its exact source/composition ranges, replay identity, transitions, time remapping, and counter contract as authoritative; Remotion must not repeat Director decisions.
12. When the user asks to make/edit/produce the video, render one finished MP4 unless separate outputs are requested. Verify the result before returning it.

## Hard defaults

- Default output: one vertical 9:16 social-media-ready MP4 for Reels, TikTok, Facebook Reels, and Shorts.
- Default mode: Standard unless the user requests Quick, Extended, or otherwise implies a different pacing target.
- Default audio: mute/remove ALL source audio from ALL clips. Do not add replacement music unless the user provides or requests it.
- Default hook: use a truthful high-effort or visually compelling cold open when a suitable candidate exists; then return to understandable workout order.
- Default retention treatment: start meaningful motion or a useful premise immediately, establish context quickly, create honest forward momentum, and deliver the promised payoff without withholding essential technique.
- Default shareability treatment: prefer specific, useful, relatable, or surprising truth already supported by the footage; never manufacture controversy, transformation, pain, failure, or performance claims.
- Preserve exercise visibility: keep the athlete, relevant joints, weights, and equipment understandable when reframing.
- Keep overlays minimal unless requested. Never obscure important anatomy, bar path, equipment, or foot placement.
- Avoid gratuitous effects, excessive zooming, long dead time, and edits that misrepresent rep continuity.

## Priority order

When objectives conflict, apply this order:

1. Do not misrepresent the workout.
2. Preserve visually important exercise technique.
3. Follow explicit current-video instructions.
4. Preserve accepted portions of an existing edit during revisions.
5. Capture attention quickly.
6. Preserve important working reps.
7. Maintain understandable chronology or upload order when chronology is unknown.
8. Remove dead time and maintain strong pacing.
9. Use transitions/effects to support rather than dominate the footage.
10. Shorten runtime only when higher priorities remain intact.

## Retention and shareability rule

Optimize for the right viewer's sustained understanding, not empty watch time. Record the evidence and confidence behind hook, curiosity, payoff, replay, and sharing decisions in the edit blueprint when they materially affect the cut. Avoid fake loops, bait-and-switch openings, engagement bait, unsafe challenges, shame, unsupported results, and platform-performance promises. If variants are requested, change one major hypothesis at a time and label the difference. Actual audience analytics outrank generic heuristics on later revisions, but never override workout truth or safety.

## Interpretation shortcuts

Interpret natural language without requiring the user to restate the rules.

- `Make this social media ready` -> Standard mode, all defaults, one finished edit.
- `Quick workout Reel` -> Quick mode.
- `Longer workout video` / `show more of the workout` -> Extended mode.
- `One/two struggle reps as the hook` -> select that many strongest truthful high-effort candidates.
- `Glitch clips` -> blink-speed fragments of meaningful rep regions; NOT automatically digital glitch effects.
- `Glitch transitions` -> fast cyberpunk vertical-strip/slice transitions between meaningful clips.
- `Glitch effects` -> RGB separation/static/distortion/screen tearing only when explicitly requested.
- `Keep the audio` -> override the mute default only for the requested scope.
- `Add rep counters` -> opt in to reviewed top-level editorial repetitions only; map retained completions through the final edit timeline, keep displayed numbering continuous, and suppress hook/replay duplicates. Raw machine candidates can never render a counter.
- `Show all reps` / `keep the whole set` / `don't cut any reps` -> retain every reviewed rep in the requested scope.
- `Only show the last 3` / `show first and last rep` / `use 2 reps per movement` -> apply that explicit override per movement or confirmed set.
- `Make this social media ready` -> infer a balanced viral/fitness montage with a strong truthful hook, exercise-heavy semantic role variety, occasional breathers, readable anchors, minimal dead time, and restrained effects.
- `Make it cinematic` -> change both pacing/effects and source-role selection toward supported environment, setup, detail, complete-rep, hero, and ending candidates.
- `Only show the workout movements` -> suppress nonessential setup, environment, walking, rest, recovery, and decorative detail roles.
- `Fast, aggressive and TikTok-ish but slow down the last rep` -> blend viral, athletic, and gritty intent; keep early cuts quick; attach a conservative final-rep speed curve; preserve rep identity and chronology.
- `No glitch` / `no slow motion` / `not too flashy` -> treat the negation as a hard constraint that overrides profile defaults. Do not ask for internal preset names when the language is reasonably resolvable.
- `Add coaching tips/instructions` -> use user-provided guidance and time it to relevant movement phases when supportable.

## Analysis integration rule

For optional automated evidence, read `references/analysis-pipeline.md` and run `scripts/analyze_video.py` when available. Scene boundaries are not set boundaries, and low-motion regions are not automatically disposable. The Editor evaluates evidence; the Director orchestrates; Remotion composes and renders. When structured analysis is created, normalize it to the bundled `scripts/analysis-schema.json` vocabulary where practical. Keep source-relative timing separate from final timeline timing. If a machine-readable analysis/edit JSON is produced, run `scripts/validate_analysis.py` before final rendering. Do not require optional third-party analyzers when they are unavailable; fall back to visual analysis. Read `references/open-source-notes.md` when provenance or integration details matter. When Remotion is available, also use `references/remotion-skill-routing.md` so the workout-specific editorial layer composes cleanly with the official Remotion Agent Skills.

## Confidence rule

Never present visual inference as certainty when the footage does not support it. A slow rep is a hook-selection signal, not proof of muscular failure. If counting, exercise recognition, set boundaries, chronology, ROM, or movement phase is uncertain, choose an edit that remains truthful without unsupported annotation.

## Phase 13 — optional soundtrack intelligence

When a user supplies a rights-cleared soundtrack, interpret ordinary directions
such as “make this social media ready and cut it to this song,” “use the beat
mostly between exercises,” or “make the final rep hit on the drop.” Do not ask
for BPM or beat timestamps when local analysis can provide evidence. Resolve
negations (“ignore the beat,” “no music sync”) first. Use Phase 13 normalized
analysis and safe-boundary synchronizer; do not move locked reviewed reps,
chronology, hook identity, or counter completions. Never sync every cut by
default. Keep source workout audio muted unless the user explicitly asks for it.
Without a soundtrack—or if its optional provider fails—preserve the Phase 12
visual timeline exactly. Do not download music or assume usage rights. See
`references/music-sync.md` for the provider, input, validation, style, offset,
trim, fade, and renderer contracts.

## Phase 14 — advanced music structure (optional)

When a user supplies a normal rights-cleared song and says “Make this video fit
this song,” select audio analysis through the `auto` registry: prefer the optional
advanced provider and safely retain the Phase 13 PCM-WAV baseline when it is
unavailable. Use declared capabilities only. Prefer reliable section changes,
strong accents, and provider-supplied downbeats; use ordinary beats selectively
and actual beat timestamps for changing tempo. Reduce sync when evidence quality
is weak and preserve the visual timeline when it is insufficient. Never infer
4/4, fabricate downbeats or verse/chorus labels, analyze lyrics, or change user
volume from measured loudness. Workout truth, locked reps, hook identity,
chronology, and counters remain authoritative. See
`references/advanced-music-analysis.md`.

## Phase 15 — defensible downbeats and long tracks (optional)

Use downbeats, bar positions, or meter only when the selected provider declares the matching capability and supplies valid evidence with honest support semantics. Never assume 4/4 or treat grouped bars as semantic phrases. `auto` ignores the fail-closed downbeat adapter until a separately installed, license-cleared backend is configured. On long PCM-WAV sources, use bounded overlapping chunks and deterministic stitching; preserve the source hash and report partial failures. Major exercise/style/hero events may prefer strong downbeats, but small cuts may use beats and music never overrides locked workout truth. See `references/downbeat-bar-analysis.md`.


## Phase 16 soundtrack streaming

For a normal request such as “Make this workout fit the song,” select `auto`; compressed MP3, AAC/M4A, and FLAC sources may use installed FFmpeg through a bounded PCM pipe without user codec terminology. Never install/download a rhythm model. `downbeat` remains fail-closed until an explicitly local, license-cleared model exists. Preserve explicit negation (“ignore the meter”, “don’t use downbeats”, or “don’t sync this to music”), protected reps/counters, source chronology, and soundtrack pitch/speed. See `references/production-rhythm-provider.md`.
