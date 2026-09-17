# Workout Remotion Editor

An open-source ChatGPT skill for turning workout footage into truthful, frame-accurate paper edits, overlay plans, coaching treatments, rep counters, and render-ready videos. Version **2.1** emphasizes complete-footage review, structured/validated analysis, editorial integrity, accessibility, licensing, and end-to-end render QA.

[Remotion](https://www.remotion.dev/) is the recommended implementation and rendering layer because its frame-based React model supports deterministic, reviewable video work. Other capable video-editing agents or plugins may work **experimentally** when they can preserve exact source timing, overlays, audio, output settings, and QA requirements.

## What it does

- Quick, Standard, and Extended workflows for projects of different complexity.
- Full-timeline source analysis and evidence-linked selection.
- Honest struggle hooks, verified rep counters, neutral coaching overlays, and instructional structures.
- JSON Schema plus a Python validator for analysis artifacts.
- Paper-edit, overlay, audio, render, delivery, and revision checks.
- Progressive-disclosure references so the core skill remains efficient.

The skill does not include an editor, Remotion, pose models, footage, music, or third-party source code.

## Install in ChatGPT Skills

1. Open this repository's latest successful **Package skill** workflow run.
2. Download its `workout-remotion-editor-skill` artifact and unzip the artifact wrapper if necessary; keep the packaged file named `skill.zip`.
3. In ChatGPT, open **Settings → Skills** (the label can vary by plan/workspace) and choose **Create/Upload skill**.
4. Upload `skill.zip` without adding another parent directory. `SKILL.md` must be at the root of the uploaded archive.
5. Enable **Workout Remotion Editor** for the conversation or workspace.
6. Start a chat, attach accessible workout media (or provide paths in a connected environment), and invoke it with `$workout-remotion-editor` plus your brief.

For a local/manual package:

```bash
git clone https://github.com/trinitywellnessnb/workout-remotion-editor.git
cd workout-remotion-editor
python -m zipfile -c skill.zip workout-remotion-editor/*
```

When packaging manually, ensure hidden files are not needed and that the archive contains the *contents* of `workout-remotion-editor/` at its root. The workflow is the canonical packaging route. See the [user manual](docs/USER_MANUAL.md) for detailed use.

## Example prompts

### Quick

> Use `$workout-remotion-editor` in Quick mode. Turn this single deadlift clip into a truthful 20-second vertical highlight. Keep source audio, add minimal captions, and give me the paper edit before rendering.

### Standard

> Use `$workout-remotion-editor` in Standard mode on these workout clips. Make a 45-second 9:16 edit for Instagram, analyze the full footage, validate the analysis JSON, build an evidence-linked EDL and overlays, then render and perform complete QA.

### Extended

> Use `$workout-remotion-editor` in Extended mode for this multi-camera training session. Create a selects map, a 90-second main edit and 30-second variant, verified rep notes, caption and audio plans, review checkpoints, and documented revision rounds.

### Struggle hook

> Find a genuine high-effort moment and use it as a struggle hook without implying injury or failure. Reveal context quickly, preserve honest chronology after the hook, and label any replay or reordering.

### Rep counter

> Add a rep counter to this squat set. Define the observable rep cycle first, verify every completed repetition manually, do not count partial reps, and make the on-screen counter match the validated analysis.

### Coaching overlay

> Create neutral coaching overlays for this lift. Tie each cue to visible evidence and exact times, show one concise cue at a time, state camera limitations, and avoid diagnosis or claims that cannot be seen.

### Instructional video

> Build an instructional video from these clips: goal and setup, execution, visible checkpoints, supported common errors, replay/freeze-frame callouts, and recap. Clearly label illustrative or reordered footage and include captions and accessibility QA.

## Validation

```bash
python -m json.tool workout-remotion-editor/scripts/analysis-schema.json >/dev/null
python workout-remotion-editor/scripts/validate_analysis.py path/to/analysis.json
python /opt/codex/skills/.system/skill-creator/scripts/quick_validate.py workout-remotion-editor
```

`validate_analysis.py` uses `jsonschema` when available and otherwise performs built-in core structural and semantic checks. CI validates the schema and script, smoke-tests valid and invalid examples, validates the skill package, and uploads `skill.zip`.

## Project layout

The distributable skill is under `workout-remotion-editor/`; public documentation and project governance files stay outside the ZIP. No third-party repository is vendored or copied. See [third-party notices](THIRD_PARTY_NOTICES.md) and [open-source notes](workout-remotion-editor/references/open-source-notes.md).

## License

Original project material is licensed under the [MIT License](LICENSE). External projects and user-provided assets remain under their respective licenses and terms.
