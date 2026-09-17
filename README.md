
# Workout Remotion Editor + Workout Remotion Director

An open-source workout-video editing project for ChatGPT and Remotion. The project now has two complementary intelligence layers:

- **Workout Remotion Editor v2.3** — the ChatGPT Skill for workout-specific analysis and research-informed social editing intelligence.
- **Workout Remotion Director v1.0** — the optional ChatGPT Workspace Agent blueprint for autonomous, one-and-done orchestration from uploaded footage through QA and final render.

[Remotion](https://www.remotion.dev/) remains the recommended video implementation and rendering layer.

The layers are intentionally separate:

```text
Workout Remotion Director v1.0
Autonomous workflow + creative direction + QA/repair orchestration
                         ↓
Workout Remotion Editor v2.3
Workout analysis + research-informed social editing intelligence
                         ↓
Remotion
Video implementation + composition + rendering
```

The Director does not replace the Skill, and neither replaces Remotion. Each layer has a different job.

## Choose how you want to use the project

### 1. Skill only — Workout Remotion Editor v2.3

Use the **Skill only** when you want workout-specific editing intelligence while remaining more directly involved in the conversation and edit direction.

The Skill analyzes workout footage and helps determine **WHAT** should happen in the edit: exercises, sets, reps, movement phases, truthful hooks, rep-aware cuts, workout-safe framing, counters, coaching overlays, retention/shareability treatments, and workout-specific QA.

Typical workflow:

```text
Upload workout clips
        ↓
Prompt Workout Remotion Editor
        ↓
Skill analyzes footage and builds the edit direction
        ↓
Remotion implements/renders the video
        ↓
Continue prompting for revisions as needed
```

Start with something as simple as:

> **“Make this workout social media ready.”**

Use this option if you primarily want the specialized workout-video intelligence and prefer to direct or revise the process conversationally.

**Setup:** Download/install the current `skill.zip`, enable **Workout Remotion Editor**, connect the relevant Remotion capabilities, upload your workout footage, and describe the edit you want.

The distributable Skill source lives under [`workout-remotion-editor/`](workout-remotion-editor/). See the [v2.3 User Manual](docs/USER_MANUAL.md) for detailed prompting and feature guidance.

### 2. Agent blueprint — Workout Remotion Director v1.0

Use the **Agent blueprint** when you want an autonomous workflow director that makes routine creative and production decisions itself.

Workout Remotion Director owns the workflow: intake, footage inspection, creative-direction selection, delegation, implementation routing, QA, automatic repair decisions, final render, and delivery. Its default experience is **one and done**.

```text
Upload footage + give a short request
        ↓
Director inspects everything
        ↓
Director chooses the strongest truthful direction
        ↓
Director orchestrates implementation
        ↓
QA → automatic repair when needed
        ↓
Final render
        ↓
Finished video
```

The Director does not ask for approval on ordinary choices such as hook, pacing, crop, rep selection, transition restraint, or overlay placement. It should interrupt only when a genuine blocker prevents a truthful or technically valid edit.

The Agent blueprint can be used without installing Workout Remotion Editor, but it must not pretend to have the Skill's full specialized workout-analysis and social-editing rules when that dependency is absent. In that configuration, its primary value is autonomous workflow orchestration using the capabilities actually available to it.

Start with:

> **“I uploaded several workout clips. Make this social media ready. Choose the strongest truthful direction yourself, carry the edit through QA, and return one finished vertical video.”**

**Setup:** Start with [`agent/WORKOUT_REMOTION_DIRECTOR.md`](agent/WORKOUT_REMOTION_DIRECTOR.md), then follow the [`agent/setup-guide.md`](agent/setup-guide.md). The copyable Workspace Agent instructions are in [`agent/agent-instructions.md`](agent/agent-instructions.md).

### 3. Skill + Agent — complete one-and-done workflow

Use **Workout Remotion Director + Workout Remotion Editor + Remotion** together for the complete system this repository is designed to support.

```text
YOU
Upload workout footage + describe the outcome
        ↓
WORKOUT REMOTION DIRECTOR v1.0
Runs the job autonomously and makes routine creative decisions
        ↓
WORKOUT REMOTION EDITOR v2.3
Analyzes the workout and supplies specialized editing intelligence
        ↓
REMOTION
Implements the edit and renders the video
        ↓
DIRECTOR QA
Checks workout truth + technical output and repairs when needed
        ↓
FINAL RENDER
One finished video by default
```

This configuration combines the Director's **one-and-done autonomy** with the Skill's **workout-specific and research-informed editing intelligence** and Remotion's **video-production machinery**.

For a normal request, the intended workflow is:

`INGEST → INSPECT → DIRECT → DELEGATE_SKILL → IMPLEMENT_REMOTION → QA → REPAIR_IF_NEEDED → RENDER → DELIVER`

The user does not need to approve a paper edit, hook, pacing decision, crop, or routine revision before the workflow continues. A/B variants remain opt-in: the default is one strongest truthful finished edit.

Start with:

> **“Make this workout social media ready.”**

That short prompt is enough for the combined system to make routine decisions itself. More specific instructions still override defaults.

**Setup:** Install Workout Remotion Editor first, configure Workout Remotion Director using the [Agent Setup Guide](agent/setup-guide.md), and enable the relevant Remotion capabilities. See [`agent/tool-requirements.md`](agent/tool-requirements.md) for dependency and fallback behavior.

## Why use Workout Remotion Editor with Remotion?

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

### Skill-only setup

1. **Download** — Get the current `skill.zip` from this repository's release/package artifact.
2. **Install** — Open ChatGPT Skills, upload `skill.zip`, and enable **Workout Remotion Editor**.
3. **Connect Remotion** — Enable/connect Remotion in ChatGPT. Remotion is the recommended implementation and rendering layer.
4. **Upload footage** — Add one or more workout clips to your ChatGPT conversation.
5. **Ask for the edit** — Start with: **“Make this workout social media ready.”**

### Agent setup

1. Open the [Workout Remotion Director overview](agent/WORKOUT_REMOTION_DIRECTOR.md).
2. Follow the [Workspace Agent setup guide](agent/setup-guide.md).
3. Use the copyable [Agent instructions](agent/agent-instructions.md).
4. Connect the dependencies described in [Tool Requirements](agent/tool-requirements.md).
5. For the complete workflow, install/enable Workout Remotion Editor and Remotion alongside the Director.

From there, use normal language. For example: **“make it faster,” “open with my hardest successful rep,” “optimize this for saves and shares,” “make a second version with a curiosity hook,” “count the reps in my last set,” “label each exercise,” “add these coaching cues,” “keep more of the final set,”** or **“change only the hook.”**

> **Skill only:** Download Skill → Add to ChatGPT → Connect Remotion → Upload clips → Direct the edit.
>
> **Agent only:** Configure Director → Connect available tools → Upload clips → Give the outcome → Director runs the workflow.
>
> **Skill + Agent:** Install Skill → Configure Director → Connect Remotion → Upload clips → Give the outcome → One-and-done workflow through final render.

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

The distributable Skill is under `workout-remotion-editor/`. The optional Workspace Agent blueprint is under `agent/`. Public documentation, research, and governance files remain outside the Skill ZIP. No third-party repository is vendored or copied. See [third-party notices](THIRD_PARTY_NOTICES.md) and [open-source notes](workout-remotion-editor/references/open-source-notes.md).

The Director and Editor use independent version numbers. The current documented pairing is **Workout Remotion Director v1.0 + Workout Remotion Editor v2.3**.

## License

Original project material is licensed under the [MIT License](LICENSE). External projects and user-provided assets remain under their respective licenses and terms.
