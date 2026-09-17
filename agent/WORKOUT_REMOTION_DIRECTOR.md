# Workout Remotion Director v1.0

Workout Remotion Director is an optional ChatGPT Workspace Agent blueprint for a **one and done** workout-video workflow. A user can upload workout footage, give a short request, and let the agent carry the job from inspection through creative direction, specialized workout analysis, Remotion implementation, QA, repair, final render, and delivery.

## What it owns

Workout Remotion Director owns orchestration and routine creative decisions. It decides how to move the job forward and when another layer should take over.

It does not replace either of the systems below:

- **Workout Remotion Editor v2.3** supplies workout-specific and research-informed social-editing intelligence: exercise/set/rep reasoning, movement-aware cuts, truthful hooks, retention/shareability logic, overlays, reframing, edit blueprints, and workout-specific QA constraints.
- **Remotion and its official capabilities** supply generic video implementation and rendering: composition, media timing, animation, captions, preview, and render mechanics.

In short:

```text
Workout Remotion Director -> orchestrates and decides
Workout Remotion Editor    -> understands the workout and edit
Remotion                    -> builds and renders the video
```

## Default experience

For a normal request such as `Make this workout social media ready`, the agent should:

1. inspect all supplied footage;
2. choose the strongest truthful creative direction itself;
3. use Workout Remotion Editor v2.3 for the specialized edit blueprint;
4. route implementation to Remotion;
5. QA the result;
6. automatically repair reasonable problems;
7. complete the final render; and
8. return one strongest finished video.

It should not stop for approval of routine choices such as hook, pacing, crop, transition style, overlay placement, or rep selection. It asks only when a genuine blocker makes a truthful or technically valid completion impossible.

## Defaults

Unless the user overrides them, inherit Workout Remotion Editor v2.3 defaults: one vertical 9:16 social-ready MP4, Standard pacing, muted source-camera audio, truthful visually compelling hook when supported, movement-readable framing, and restrained overlays/effects.

A/B variants are opt-in rather than automatic. When requested, change one major hypothesis at a time.

## Blueprint files

- [`agent-instructions.md`](agent-instructions.md) — copyable Workspace Agent instructions.
- [`workflow.md`](workflow.md) — orchestration state machine, interruption policy, QA, and repair loop.
- [`tool-requirements.md`](tool-requirements.md) — required/optional capabilities and truthful fallbacks.
- [`setup-guide.md`](setup-guide.md) — how to recreate the agent in ChatGPT.
- [`starter-prompts.md`](starter-prompts.md) — one-and-done and advanced examples.

## Distribution

This repository distributes a reproducible Workspace Agent blueprint. It does not claim that this folder is a universal one-click ChatGPT Agent package. Users can copy the instructions and configure the available Workspace Agent features in their ChatGPT environment.

## Compatibility

Workout Remotion Director v1.0 was designed around **Workout Remotion Editor v2.3** and the official Remotion skill/capability model. The Director and Skill have independent version numbers so either layer can evolve without forcing synchronized releases.