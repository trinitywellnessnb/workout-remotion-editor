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
