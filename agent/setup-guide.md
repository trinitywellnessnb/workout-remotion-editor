# Workout Remotion Director v1.0 — Setup Guide

This folder is a reproducible blueprint for a ChatGPT Workspace Agent. It is not presented as a universal one-click Agent package.

## 1. Install the Skill

Install/enable **Workout Remotion Editor v2.3** (or a later compatible version) in the ChatGPT environment where you will use the Director.

The Skill remains the workout-specific intelligence layer. The Director should orchestrate it rather than copy its detailed rules.

## 2. Enable Remotion

Enable the Remotion capabilities available in your ChatGPT environment. The complete one-and-done workflow needs the ability to implement and render the edit, not merely describe it.

Workout Remotion Editor already contains routing guidance for the official Remotion skills/capabilities.

## 3. Create the Workspace Agent

Create a new Workspace Agent using the Agent creation controls available in your ChatGPT workspace.

Recommended name:

```text
Workout Remotion Director
```

Recommended version label in its description:

```text
v1.0 — one-and-done workout video orchestration
```

## 4. Add the instructions

Copy the complete contents of [`agent-instructions.md`](agent-instructions.md) into the Workspace Agent's instruction field.

Attach/enable Workout Remotion Editor and the Remotion capabilities needed for implementation and rendering. Exact Workspace Agent controls can evolve, so use the current ChatGPT controls rather than assuming screenshots or menu names in this document are permanent.

## 5. Confirm dependencies

The complete setup should provide:

```text
Workout Remotion Director -> orchestration
Workout Remotion Editor    -> workout/social editing intelligence
Remotion                    -> implementation and rendering
```

See [`tool-requirements.md`](tool-requirements.md) for fallback behavior when a layer is unavailable.

## 6. Smoke test

Upload several non-sensitive workout clips and use this request:

> I uploaded several workout clips. Make this social media ready. Choose the strongest truthful direction yourself, carry the edit through QA, and return one finished vertical video.

Expected behavior:

- the agent does not ask routine creative questions;
- all supplied clips are inspected before the direction is finalized;
- Workout Remotion Editor supplies the specialized workout/edit intelligence;
- Remotion handles implementation/rendering;
- the output is checked and reasonable defects are repaired automatically;
- the agent returns one finished render, or identifies a genuine blocker rather than pretending completion.

## 7. Verify one-and-done behavior

A successful setup should not routinely stop to ask which hook, crop, pacing, transition, or overlay placement you prefer. Those are Director decisions unless your prompt explicitly specifies them.

It should also not automatically produce A/B versions. Variants are opt-in.

## Troubleshooting

**The agent gives me an edit plan but no video.** Confirm Remotion implementation and render capability is actually available to the Workspace Agent. A plan alone is not the intended complete workflow.

**The agent keeps asking creative questions.** Confirm the full `agent-instructions.md` was copied and that no higher-priority workspace instruction requires approval for those decisions.

**The agent is guessing reps or exercise details.** Stop using that output as factual annotation and confirm Workout Remotion Editor is enabled. The Director instructions require uncertain facts to be omitted or conservatively handled, never invented.

**I only want the Skill.** You do not need to recreate the Director. Workout Remotion Editor can still be used directly.

**I only want the Agent blueprint.** You can recreate the Director, but without Workout Remotion Editor it must not claim the specialized workout intelligence described by the Skill.