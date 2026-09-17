# Workout Remotion Editor

An open-source ChatGPT Skill for turning raw workout footage into truthful, rep-aware, social-media-ready video edits. Version **2.2** combines workout-specific editorial intelligence with explicit routing into the official Remotion Agent Skills for implementation, preview, interactivity, captions, multimedia inspection, documentation lookup, and rendering.

[Remotion](https://www.remotion.dev/) is the recommended implementation/rendering layer. Other capable video-editing agents or plugins may work experimentally when they can honor the same edit blueprint, timing, overlays, audio policy, reframing, and QA requirements.

## What v2.2 does

- Analyzes multiple workout clips before building the edit.
- Reasons about exercises, sets, reps, movement phases, high-effort hooks, cut points, setup/rest, and exercise-aware 9:16 reframing.
- Supports Quick (~10–25s), Standard (~20–40s), and Extended (~40–75s) pacing.
- Supports synchronized rep counters, exercise labels, user-supplied workout data, coaching cues, instructional overlays, animated callouts, captions, music-aware cuts, and revision-local changes.
- Keeps source audio muted by default unless explicitly preserved.
- Uses optional scene, pose, rep-state, beat/onset, and motion signals as evidence when available.
- Maintains a structured paper edit/edit blueprint and semantic validator for machine-readable analysis.
- Performs final continuity, crop, overlay, audio, synchronization, and render QA.

## Official Remotion Agent Skills integration

Workout Remotion Editor decides **WHAT** belongs in the workout edit. The official Remotion skills remain authoritative for **HOW** the edit is implemented in Remotion.

v2.2 routes to these upstream skills when relevant and available:

- `remotion-best-practices`
- `remotion-create`
- `remotion-markup`
- `remotion-multimedia`
- `remotion-captions`
- `remotion-interactivity`
- `remotion-studio`
- `remotion-render`
- `remotion-docs`
- `remotion-upgrade`
- `remotion-saas`
- `remotion-maps`

They are referenced/routed to rather than copied into this repository. See [`remotion-skill-routing.md`](workout-remotion-editor/references/remotion-skill-routing.md).

## Install in ChatGPT

1. Download the current `skill.zip` package from the repository's packaging workflow/release artifact.
2. Open ChatGPT Skills and upload `skill.zip`.
3. Enable Workout Remotion Editor.
4. Connect/enable Remotion (recommended) or another compatible video-editing tool.
5. Upload workout footage and ask for an edit.

The distributable Skill source lives under `workout-remotion-editor/`.

<details>
<summary><strong>📘 Workout Remotion Editor v2.2 — User Manual</strong></summary>

### Read online

- **[Open the full GitHub-readable manual](docs/USER_MANUAL.md)**

### Download the Word version

- **[Download the original DOCX manual](docs/Workout_Remotion_Editor_v2.2_User_Manual.docx?raw=1)**

### Manual menu

1. [What This Skill Is](docs/USER_MANUAL.md#1-what-this-skill-is)
2. [v2.2 Remotion Skill Integration](docs/USER_MANUAL.md#2-v22-remotion-skill-integration)
3. [Best Way to Prompt It](docs/USER_MANUAL.md#3-best-way-to-prompt-it)
4. [Pacing Modes](docs/USER_MANUAL.md#4-pacing-modes)
5. [Hook & High-Effort Rep Editing](docs/USER_MANUAL.md#5-hook--high-effort-rep-editing)
6. [Rep-Aware & Movement-Phase Editing](docs/USER_MANUAL.md#6-rep-aware--movement-phase-editing)
7. [Rep Counters](docs/USER_MANUAL.md#7-rep-counters)
8. [Exercise Labels, Workout Data & Coaching](docs/USER_MANUAL.md#8-exercise-labels-workout-data--coaching)
9. [Instructional Edits & Animated Callouts](docs/USER_MANUAL.md#9-instructional-edits--animated-callouts)
10. [Glitch Terminology](docs/USER_MANUAL.md#10-glitch-terminology)
11. [Multi-Clip Editing](docs/USER_MANUAL.md#11-multi-clip-editing)
12. [Exercise-Aware 9:16 Reframing](docs/USER_MANUAL.md#12-exercise-aware-916-reframing)
13. [Audio & Music-Aware Editing](docs/USER_MANUAL.md#13-audio--music-aware-editing)
14. [Optional Intelligent Analysis Signals](docs/USER_MANUAL.md#14-optional-intelligent-analysis-signals)
15. [Internal Edit Blueprint](docs/USER_MANUAL.md#15-internal-edit-blueprint)
16. [Official Remotion Workflow in v2.2](docs/USER_MANUAL.md#16-official-remotion-workflow-in-v22)
17. [Revision Stability](docs/USER_MANUAL.md#17-revision-stability)
18. [Quality Control](docs/USER_MANUAL.md#18-quality-control)
19. [Feature Activation Quick Reference](docs/USER_MANUAL.md#19-feature-activation-quick-reference)
20. [Copy-Ready Prompt Library](docs/USER_MANUAL.md#20-copy-ready-prompts)
21. [Recommended Prompt Template](docs/USER_MANUAL.md#21-recommended-prompt-template)
22. [Practical Tips](docs/USER_MANUAL.md#22-practical-tips)
23. [Technical Notes for v2.2](docs/USER_MANUAL.md#23-technical-notes-for-v22)
24. [One-Sentence Starting Point](docs/USER_MANUAL.md#24-one-sentence-starting-point)

The Markdown manual is intended for fast browsing directly on GitHub. The DOCX file is included so users who download or clone the repository also have the formatted Word version available offline.

</details>

## Fastest prompt

> Make this workout social media ready.

That invokes the default Standard workflow: one vertical social edit, source audio muted, truthful high-effort hook when available, dead time removed, and exercise visibility preserved.

## Full v2.2 example

> Make these clips into one fast TikTok workout. Start with my hardest-looking successful rep. Mute everything. Glitch through a few reps from the first two exercises, but show most of my final set. Count the final-set reps in the upper left. Put the exercise name up when each exercise starts. During my squat eccentric put “Control the descent” on screen and when I start driving up put “Drive!” Add “Finish Strong” over my last two reps. Keep overlays out of the way of my joints and equipment. Use cyberpunk vertical-slice glitch transitions between exercises, but no RGB/static glitch effects. Use the official Remotion skills for implementation, preview the composition in Studio if available, then render the final MP4.

## Validation

The package includes a semantic validator for structured analysis/edit JSON. CI/package validation should also validate the Skill structure before publishing `skill.zip`.

## Project layout

The distributable skill is under `workout-remotion-editor/`; public documentation and governance files remain outside the ZIP. No third-party repository is vendored or copied. See [third-party notices](THIRD_PARTY_NOTICES.md) and [open-source notes](workout-remotion-editor/references/open-source-notes.md).

## License

Original project material is licensed under the [MIT License](LICENSE). External projects and user-provided assets remain under their respective licenses and terms.
