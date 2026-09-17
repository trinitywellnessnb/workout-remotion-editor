![Workout Remotion Editor v2.3 — From raw clips to a polished workout video](assets/readme/workout-remotion-editor-banner.jpg)

# Workout Remotion Editor

An open-source ChatGPT Skill that adds workout-specific directing intelligence to Remotion. Version **2.3** combines rep-aware workout analysis with **research-informed social editing intelligence**: truthful hooks, retention-aware pacing, shareability reasoning, platform-native framing, controlled A/B testing, and workout-specific QA.

[Remotion](https://www.remotion.dev/) is the recommended video-building and rendering layer. Other capable video-editing agents or plugins may work experimentally when they can honor the same edit blueprint, timing, overlays, audio policy, reframing, and QA requirements.

## Why use this with Remotion?

**Remotion provides the video-editing tools. Workout Remotion Editor provides the workout-specific directing intelligence.**

A general video editor does not automatically know which workout reps matter, where movement phases begin and end, which joints and equipment must remain visible, when a rep counter should advance, when a coaching cue should appear, or why a viewer might keep watching, save, or share a particular workout moment. Workout Remotion Editor adds that specialized reasoning layer before Remotion builds the video.

It can help Remotion:

- organize footage around exercises, sets, reps, and movement phases;
- find truthful high-effort or visually compelling hook moments;
- choose rep-aware cut points instead of arbitrary timestamps;
- preserve important joints, weights, equipment, and movement visibility in 9:16;
- synchronize requested rep counters with completed visible repetitions;
- time exercise labels, coaching cues, instructional text, captions, and callouts;
- remove setup, rest, and dead time while protecting important working reps;
- apply evidence-weighted hook, pacing, overlay, safe-zone, and transition priors;
- identify a plausible viewer value and share reason such as utility, identity, achievement, humor, conversation, or motivation;
- create controlled edit variants for A/B testing when requested;
- use supplied music and beat information without sacrificing exercise readability;
- preserve accepted portions of an edit during small revisions; and
- perform workout-specific continuity, crop, overlay, audio, synchronization, retention, and render QA.

The goal is not to replace Remotion. It is to make Remotion **workout-aware and social-edit aware**.

![Workout Remotion Editor v2.3 — One skill, all the Remotion tools](https://drive.google.com/uc?export=view&id=1J9Jw9XLz3POrjqLfg037oeBO6ePxvZES)

## What v2.3 adds

### Research-informed social editing intelligence

v2.3 adds an evidence-informed editorial layer based on platform guidance, controlled research, large observational datasets, and fitness-content examples. The research does **not** claim a formula that guarantees virality. Instead, it gives the Skill evidence-weighted starting priors that can be refined through creator-specific testing.

The core idea is simple:

> **Do not edit workout videos to look viral. Edit them to earn the next second of attention and give the viewer a reason to send the video to someone else.**

The Skill can now reason about:

- a specific **viewer promise** and the strongest truthful proof of it;
- meaningful motion and value early in the edit rather than forcing chronological openings;
- a **fast opening → readable body → payoff** pacing curve instead of constant hyper-cutting;
- movement-first editing where **rep comprehension outranks beat sync**;
- share motivations such as utility, identity/community, achievement, humor, conversation, and motivation;
- concise hook text, captions, platform-safe overlays, and exercise-aware vertical framing;
- sparse semantic effects rather than decorative transition overload;
- edit archetypes such as Peak Effort, Workout Montage, Form Fix, Exercise Breakdown, Challenge/Set Story, Relatable Gym, Transformation/Progress, and Training Diary;
- controlled A/B variants that isolate variables such as hook, pacing, CTA, captions, crop, audio, or transition density; and
- performance feedback based on comparable account metrics rather than invented universal algorithm thresholds.

v2.3 also:

- defines a specific viewer promise and maps hook, orientation, progression, payoff, and optional close;
- uses honest curiosity, purposeful pattern changes, earned endings, and loops that cannot falsify rep continuity;
- records evidence, confidence, risks, and optional single-variable variant hypotheses in the blueprint;
- uses comparable first-party analytics for diagnosis while avoiding virality or retention guarantees; and
- adds schema and semantic validation for structured retention plans.

### Read and extend the research

The research behind this addition is included in the repository so users and contributors can inspect it, use it as a reference, challenge assumptions, and extend the evidence base:

- **[Evidence-Based Viral Editing for TikTok and Instagram Workout Videos](docs/research/EVIDENCE_BASED_VIRAL_EDITING.md)** — GitHub-readable Markdown research document.
- **[Retention & Shareability implementation reference](workout-remotion-editor/references/retention-and-shareability.md)** — compact Skill-facing rules derived for v2.3.

When extending the research, preserve the distinction between platform first-party evidence, controlled/peer-reviewed research, observational benchmarks, creator examples, and Skill-level implementation recommendations. Correlation should not be promoted into a universal claim about organic virality.

## What v2.3 preserves

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

v2.3 can route to these upstream skills when relevant and available:

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

These skills are referenced rather than copied into this repository. See [`remotion-skill-routing.md`](workout-remotion-editor/references/remotion-skill-routing.md). The v2.3 editorial layer is documented in [`retention-and-shareability.md`](workout-remotion-editor/references/retention-and-shareability.md).

## First-time setup & use

You do **not** need to know how to code or how Remotion works internally.

1. **Download** — Get the current `skill.zip` from this repository's release/package artifact.
2. **Install** — Open ChatGPT Skills, upload `skill.zip`, and enable **Workout Remotion Editor**.
3. **Connect Remotion** — Enable/connect Remotion in ChatGPT. Remotion is the recommended implementation and rendering layer.
4. **Upload footage** — Add one or more workout clips to your ChatGPT conversation.
5. **Ask for the edit** — Start with: **“Make this workout social media ready.”**

From there, use normal language. For example: **“make it faster,” “open with my hardest successful rep,” “optimize this for saves and shares,” “make a second version with a curiosity hook,” “count the reps in my last set,” “label each exercise,” “add these coaching cues,” “keep more of the final set,”** or **“change only the hook.”**

> **Download Skill → Add to ChatGPT → Connect Remotion → Upload workout clips → Describe the video you want.**

The distributable Skill source lives under `workout-remotion-editor/`.

<details>
<summary><strong>📘 Workout Remotion Editor v2.3 — User Manual</strong></summary>

### Read online

- **[Open the full GitHub-readable manual](docs/USER_MANUAL.md)**

### Download the Word version

- **[Download the archived v2.2 DOCX manual](docs/Workout_Remotion_Editor_v2.2_User_Manual.docx?raw=1)**

### Manual menu

1. [What This Skill Is](docs/USER_MANUAL.md#1-what-this-skill-is)
2. [v2.3 Remotion Skill Integration](docs/USER_MANUAL.md#2-v23-remotion-skill-integration)
3. [Retention & Shareability](docs/USER_MANUAL.md#3-retention-shareability)
4. [Best Way to Prompt It](docs/USER_MANUAL.md#4-best-way-to-prompt-it)
5. [Pacing Modes](docs/USER_MANUAL.md#5-pacing-modes)
6. [Hook & High-Effort Rep Editing](docs/USER_MANUAL.md#6-hook-high-effort-rep-editing)
7. [Rep-Aware & Movement-Phase Editing](docs/USER_MANUAL.md#7-rep-aware-movement-phase-editing)
8. [Rep Counters](docs/USER_MANUAL.md#8-rep-counters)
9. [Exercise Labels, Workout Data & Coaching](docs/USER_MANUAL.md#9-exercise-labels-workout-data-coaching)
10. [Instructional Edits & Animated Callouts](docs/USER_MANUAL.md#10-instructional-edits-animated-callouts)
11. [Glitch Terminology](docs/USER_MANUAL.md#11-glitch-terminology)
12. [Multi-Clip Editing](docs/USER_MANUAL.md#12-multi-clip-editing)
13. [Exercise-Aware 9:16 Reframing](docs/USER_MANUAL.md#13-exercise-aware-916-reframing)
14. [Audio & Music-Aware Editing](docs/USER_MANUAL.md#14-audio-music-aware-editing)
15. [Optional Intelligent Analysis Signals](docs/USER_MANUAL.md#15-optional-intelligent-analysis-signals)
16. [Internal Edit Blueprint](docs/USER_MANUAL.md#16-internal-edit-blueprint)
17. [Official Remotion Workflow in v2.3](docs/USER_MANUAL.md#17-official-remotion-workflow-in-v23)
18. [Revision Stability](docs/USER_MANUAL.md#18-revision-stability)
19. [Quality Control](docs/USER_MANUAL.md#19-quality-control)
20. [Feature Activation Quick Reference](docs/USER_MANUAL.md#20-feature-activation-quick-reference)
21. [Copy-Ready Prompts](docs/USER_MANUAL.md#21-copy-ready-prompts)
22. [Recommended Prompt Template](docs/USER_MANUAL.md#22-recommended-prompt-template)
23. [Practical Tips](docs/USER_MANUAL.md#23-practical-tips)
24. [Technical Notes for v2.3](docs/USER_MANUAL.md#24-technical-notes-for-v23)
25. [One-Sentence Starting Point](docs/USER_MANUAL.md#25-one-sentence-starting-point)

The Markdown manual is intended for fast browsing directly on GitHub. The v2.2 DOCX remains as an archived offline manual; the Markdown manual is authoritative for v2.3.

</details>

## Example prompt

> Make these clips into one fast TikTok workout optimized for retention and shares. Start with my hardest-looking successful rep and make the reason to keep watching clear immediately. Mute the raw camera audio. Glitch through a few reps from the first two exercises, but show most of my final set. Count the final-set reps in the upper left. Put the exercise name up when each exercise starts. During my squat eccentric put “Control the descent” on screen and when I start driving up put “Drive!” Add “Finish Strong” over my last two reps. Keep overlays out of the way of my joints and equipment. Use cyberpunk vertical-slice glitch transitions between exercises, but no RGB/static glitch effects. Keep movement comprehension more important than beat sync. Use the official Remotion skills for implementation, preview the composition in Studio if available, then render the final MP4.

## For developers

The package includes a semantic validator for structured analysis/edit JSON. CI/package validation also checks the Skill structure before publishing `skill.zip`.

The distributable skill is under `workout-remotion-editor/`; public documentation, research, and governance files remain outside the ZIP. No third-party repository is vendored or copied. See [third-party notices](THIRD_PARTY_NOTICES.md) and [open-source notes](workout-remotion-editor/references/open-source-notes.md).

## License

Original project material is licensed under the [MIT License](LICENSE). External projects and user-provided assets remain under their respective licenses and terms.
