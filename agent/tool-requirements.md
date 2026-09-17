# Workout Remotion Director v1.0 — Tool Requirements

## Required for the complete one-and-done workflow

### ChatGPT Workspace Agent environment

A ChatGPT environment that can hold the Director instructions and use the resources/capabilities configured for the agent.

### Workout Remotion Editor

Install/enable **Workout Remotion Editor v2.3** (or a later compatible release). It is the specialized workout and research-informed social-editing intelligence layer.

The Director must not silently replace missing Skill behavior with invented expertise. If the Skill is unavailable, disclose that limitation and continue only when the remaining capabilities can truthfully satisfy the request.

### Remotion implementation/render capability

The complete workflow requires Remotion capabilities sufficient to implement the edit blueprint, verify the composition, and render the requested output. Use official Remotion skills/capabilities when available rather than copying their generic implementation knowledge into this agent.

If rendering is unavailable, the Director may still produce a truthful edit blueprint when useful, but must not claim that a finished video was rendered.

## Remotion capabilities commonly used

Depending on the job, Workout Remotion Editor may route implementation to capabilities such as:

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

Not every job needs every capability.

## Optional inputs/capabilities

Use when requested or materially useful:

- user-supplied music or voiceover;
- captions/transcription capability;
- creator analytics supplied by the user for later A/B learning;
- structured scene, pose, rep-state, beat/onset, or motion evidence;
- user-provided workout data, exercise names, coaching cues, or other factual overlays.

Optional analysis evidence informs the edit; it does not override visible footage, user-provided facts, Workout Remotion Editor confidence rules, or workout truth.

## Audio requirement

The inherited default is to mute/remove source-camera audio. Do not fetch, invent, or add copyrighted replacement music merely because a social edit might benefit from music. Use music/voiceover only when the user supplies it, explicitly requests it through a legitimate available capability, or otherwise provides authorization/context that makes its use appropriate.

## Truthful fallback table

| Missing/uncertain resource | Director behavior |
| --- | --- |
| Workout Remotion Editor unavailable | State that specialized Skill intelligence is unavailable; do not impersonate it. Continue only if the request remains truthfully satisfiable. |
| Remotion implementation unavailable | A truthful edit blueprint may be returned, but do not claim a finished video. |
| Remotion render unavailable | Report the render limitation and return any useful verified intermediate artifact that genuinely exists. |
| Exercise/rep/load/chronology uncertain | Omit or conservatively edit around the uncertain fact rather than inventing it. |
| User-supplied music absent | Keep source audio muted by default and do not invent/download copyrighted music. |
| Optional analyzer unavailable | Fall back to visual analysis and confidence-aware editing. |

## Compatibility

Workout Remotion Director v1.0 was designed against Workout Remotion Editor v2.3. Agent and Skill versions are intentionally independent.