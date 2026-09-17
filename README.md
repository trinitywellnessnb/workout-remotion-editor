# Workout Remotion Editor

An open-source ChatGPT Skill that adds workout-specific directing intelligence to Remotion. Version **2.2** analyzes raw workout footage, builds a truthful rep-aware edit plan, and routes implementation to the appropriate official Remotion Agent Skills.

[Remotion](https://www.remotion.dev/) is the recommended video-building and rendering layer. Other capable video-editing agents or plugins may work experimentally when they can honor the same edit blueprint, timing, overlays, audio policy, reframing, and QA requirements.

## Why use this with Remotion?

**Remotion provides the video-editing tools. Workout Remotion Editor provides the workout-specific directing intelligence.**

A general video editor does not automatically know which workout reps matter, where movement phases begin and end, which joints and equipment must remain visible, when a rep counter should advance, or when a coaching cue should appear. Workout Remotion Editor adds that specialized layer before Remotion builds the video.

It can help Remotion:

- organize footage around exercises, sets, reps, and movement phases;
- find truthful high-effort or visually compelling hook moments;
- choose rep-aware cut points instead of arbitrary timestamps;
- preserve important joints, weights, equipment, and movement visibility in 9:16;
- synchronize requested rep counters with completed visible repetitions;
- time exercise labels, coaching cues, instructional text, captions, and callouts;
- remove setup, rest, and dead time while protecting important working reps;
- use supplied music and beat information without sacrificing exercise readability;
- preserve accepted portions of an edit during small revisions; and
- perform workout-specific continuity, crop, overlay, audio, synchronization, and render QA.

The goal is not to replace Remotion. It is to make Remotion **workout-aware**.

## What v2.2 does

- Analyzes all supplied workout clips before building the edit.
- Reasons about exercises, sets, reps, movement phases, high-effort hooks, cut points, setup/rest, and exercise-aware reframing.
- Supports Quick (~10–25s), Standard (~20–40s), and Extended (~40–75s) pacing.
- Supports synchronized rep counters, exercise labels, user-supplied workout data, coaching cues, instructional overlays, animated callouts, captions, and music-aware cuts.
- Mutes source audio by default unless the user explicitly preserves it.
- Uses optional scene, pose, rep-state, beat/onset, and motion signals as evidence when available.
- Maintains a structured edit blueprint and semantic validator for machine-readable analysis.
- Supports revision-local changes and final workout-specific QA.

## Official Remotion Agent Skills integration

Workout Remotion Editor decides **WHAT** belongs in the workout edit. The official Remotion skills remain authoritative for **HOW** the edit is implemented in Remotion.

v2.2 can route to these upstream skills when relevant and available:

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

These skills are referenced rather than copied into this repository. See [`remotion-skill-routing.md`](workout-remotion-editor/references/remotion-skill-routing.md).

## First-time setup & use

You do **not** need to know how to code or how Remotion works internally.

1. **Download** — Get the current `skill.zip` from this repository's release/package artifact.
2. **Install** — Open ChatGPT Skills, upload `skill.zip`, and enable **Workout Remotion Editor**.
3. **Connect Remotion** — Enable/connect Remotion in ChatGPT. Remotion is the recommended implementation and rendering layer.
4. **Upload footage** — Add one or more workout clips to your ChatGPT conversation.
5. **Ask for the edit** — Start with: **“Make this workout social media ready.”**

From there, use normal language. For example: **“make it faster,” “open with my hardest successful rep,” “count the reps in my last set,” “label each exercise,” “add these coaching cues,” “keep more of the final set,”** or **“change only the hook.”**

> **Download Skill → Add to ChatGPT → Connect Remotion → Upload workout clips → Describe the video you want.**

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

## Example prompt

> Make these clips into one fast TikTok workout. Start with my hardest-looking successful rep. Mute everything. Glitch through a few reps from the first two exercises, but show most of my final set. Count the final-set reps in the upper left. Put the exercise name up when each exercise starts. During my squat eccentric put “Control the descent” on screen and when I start driving up put “Drive!” Add “Finish Strong” over my last two reps. Keep overlays out of the way of my joints and equipment. Use cyberpunk vertical-slice glitch transitions between exercises, but no RGB/static glitch effects. Use the official Remotion skills for implementation, preview the composition in Studio if available, then render the final MP4.

## For developers

The package includes a semantic validator for structured analysis/edit JSON. CI/package validation also checks the Skill structure before publishing `skill.zip`.

The distributable skill is under `workout-remotion-editor/`; public documentation and governance files remain outside the ZIP. No third-party repository is vendored or copied. See [third-party notices](THIRD_PARTY_NOTICES.md) and [open-source notes](workout-remotion-editor/references/open-source-notes.md).

## License

Original project material is licensed under the [MIT License](LICENSE). External projects and user-provided assets remain under their respective licenses and terms.
