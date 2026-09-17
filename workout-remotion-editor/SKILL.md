---
name: workout-remotion-editor
description: Analyze one or more uploaded workout videos and direct Remotion to create polished social-media-ready workout edits. Use for requests such as make this workout social media ready, edit my workout, make a Reel/Short/TikTok, quick/standard/extended workout edits, struggle-rep hooks, glitch clips, cyberpunk glitch transitions, synchronized rep counters, exercise labels, coaching cues, instructional overlays, or combining multiple workout clips. Default to one 9:16 finished MP4 with muted source audio unless the user overrides.
---

# Workout Remotion Editor v2.3

Act as the workout-video director first and the Remotion editor second. Analyze WHAT belongs on the timeline; use installed Remotion capabilities to implement HOW it is trimmed, sequenced, reframed, animated, speed-ramped, overlaid, and rendered.

## Core workflow

1. Inspect all supplied workout footage before committing to an edit. Treat every visual detection as an evidence-based estimate and never invent exercise identity, rep count, struggle/failure, chronology, load, or performance.
2. Read `references/workout-analysis.md` whenever the task requires rep/set analysis, movement-phase reasoning, hook selection, exercise-aware reframing, or a structured edit blueprint.
3. Read `references/editorial-rules.md` for pacing modes, cut points, speed changes, rep selection, glitch terminology, transitions, and multi-clip structure.
4. Read `references/retention-and-shareability.md` whenever choosing a hook, structuring a short-form narrative, adding a payoff/loop/CTA, comparing variants, or making claims about likely audience response. Treat retention and shareability as hypotheses to test, never guarantees.
5. Read `references/workout-analysis.md` when objective scene, pose, rep-state, beat/onset, motion, or crop signals are available or would materially improve the edit. External analyzers provide evidence, never authority.
6. Read `references/overlays-and-output.md` when the user requests rep counters, exercise names, workout data, coaching/educational text, animated callouts, music/audio changes, or non-default aspect ratios.
7. Read `references/remotion-editing-intelligence.md` when translating the paper edit/edit blueprint into Remotion, especially for ripple timelines, source-to-timeline timing, beat-aware cuts, or revision-local changes.
8. Read `references/qa-and-revisions.md` before rendering a requested finished video and for follow-up revisions to an accepted edit.
9. Read `references/remotion-skill-routing.md` whenever Remotion is the implementation layer. Route implementation to the official Remotion skills: best-practices, create, markup, multimedia, captions, interactivity, Studio, render, docs, upgrade, SaaS, and maps when relevant. Do not duplicate their generic implementation knowledge here.
10. Build from the internal edit blueprint. Explicit instructions for the current video override every default in this skill.
11. When the user asks to make/edit/produce the video, render one finished MP4 unless separate outputs are requested. Verify the result before returning it.

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
- `Add rep counters` -> synchronize to sufficiently visible completed reps; omit uncertain automatic counts.
- `Add coaching tips/instructions` -> use user-provided guidance and time it to relevant movement phases when supportable.

## Analysis integration rule

When structured analysis is created, normalize it to the bundled `assets/analysis-schema.json` vocabulary where practical. Keep source-relative timing separate from final timeline timing. If a machine-readable analysis/edit JSON is produced, run `scripts/validate_analysis.py` before final rendering. Do not require optional third-party analyzers when they are unavailable; fall back to visual analysis. Read `references/open-source-notes.md` when provenance or integration details matter. When Remotion is available, also use `references/remotion-skill-routing.md` so the workout-specific editorial layer composes cleanly with the official Remotion Agent Skills.

## Confidence rule

Never present visual inference as certainty when the footage does not support it. A slow rep is a hook-selection signal, not proof of muscular failure. If counting, exercise recognition, set boundaries, chronology, ROM, or movement phase is uncertain, choose an edit that remains truthful without unsupported annotation.
