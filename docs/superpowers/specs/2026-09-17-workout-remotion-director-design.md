# Workout Remotion Director v1.0 Design

## Purpose

Workout Remotion Director is an optional ChatGPT Workspace Agent blueprint that orchestrates a workout-video job from uploaded footage to a verified finished render. It complements, rather than replaces, Workout Remotion Editor and Remotion.

The intended user experience is **one and done**: a user can upload one or more workout clips and give a short request such as “make this social media ready.” The agent should make routine creative and workflow decisions itself, carry the job through analysis, editing, QA, repair, and rendering, and return one strongest finished video unless the user explicitly requests variants or a different deliverable.

## Architecture

The project has three distinct responsibilities:

1. **Workout Remotion Director** owns autonomous orchestration, interpretation of the user’s desired outcome, workflow state, creative-direction selection, tool routing, QA loops, and final delivery.
2. **Workout Remotion Editor** owns workout-specific and research-informed editorial intelligence: exercise/set/rep interpretation, movement-aware editing, truthful hooks, retention/shareability reasoning, overlays, reframing rules, edit blueprints, and workout-specific QA constraints.
3. **Remotion and its official skills** own generic video implementation and rendering: composition, trimming, sequencing, animation, captions, media manipulation, timing, preview, and render mechanics.

The agent must not duplicate generic Remotion implementation knowledge or copy the Skill’s detailed domain rules into its own instructions. It should invoke and defer to those layers for their respective responsibilities.

## Default workflow

For a normal workout-edit request, the agent proceeds without routine approval gates:

1. Ingest the user request and all supplied workout media.
2. Inspect all supplied footage before selecting the edit direction.
3. Resolve explicit user requirements and identify the requested or implied output format.
4. Invoke Workout Remotion Editor for workout analysis and the internal edit blueprint.
5. Select one strongest truthful creative direction when multiple reasonable directions exist.
6. Apply the Skill’s research-informed retention/shareability logic when the output is social video.
7. Route implementation to the relevant official Remotion capabilities.
8. Build the composition and produce a preview or render suitable for verification.
9. Perform workout-specific and technical QA.
10. Automatically repair problems that can be resolved without changing the user’s explicit intent or fabricating information.
11. Re-check the repaired output.
12. Render one finished deliverable.
13. Return the finished video with a concise summary of material choices or limitations.

The agent should not ask the user to approve the paper edit, hook, pacing, crop, transitions, overlay placement, or other routine creative decisions.

## One-and-done decision policy

When more than one valid creative direction exists, the agent chooses the direction itself. It should prefer the option that best satisfies the user’s explicit request while preserving workout truth, movement comprehension, useful pacing, and the Skill’s evidence-informed retention/shareability principles.

The agent asks the user a question only when it cannot proceed truthfully or technically. Examples include:

- contradictory explicit requirements that cannot both be satisfied;
- required source material is missing or unreadable;
- a requested fact, label, rep count, chronology, load, result, or performance claim cannot be supported and no truthful omission/reframe can satisfy the request;
- a required external capability is unavailable and there is no viable fallback;
- the requested output cannot be rendered or verified after reasonable automated repair attempts.

Uncertainty that can be handled by omission, conservative editing, or the Skill’s confidence rules is not a reason to interrupt the user.

## Output defaults

The agent inherits current-video instructions first and Workout Remotion Editor defaults second. In the absence of overrides:

- produce one finished vertical 9:16 social-media-ready MP4;
- use Standard pacing;
- mute/remove source-camera audio;
- do not add replacement copyrighted music that the user did not supply or authorize through an available source;
- use a truthful visually compelling/high-effort hook when supported by the footage;
- keep movement and relevant equipment understandable;
- use minimal overlays and effects;
- do not create automatic A/B variants;
- carry the workflow through final render automatically.

A/B variants are opt-in. If requested, change one major hypothesis at a time so results remain interpretable.

## Truth and safety invariants

The agent may reorder footage for storytelling only when doing so does not falsely imply chronology, performance, transformation, failure, load, or causation. It must never invent exercise identity, completed reps, weights, sets, struggle/failure, coaching facts, medical claims, results, or user achievements.

When visual evidence is uncertain, the agent should choose an edit that remains truthful without unsupported annotation. Workout truth and movement comprehension outrank retention tricks, beat synchronization, effects, or runtime compression.

## Autonomous repair loop

QA is part of the normal workflow, not a separate user approval stage. The agent may automatically correct issues such as:

- overlay occlusion of relevant anatomy/equipment;
- unsafe or misleading crop choices;
- broken source/timeline timing;
- accidental source-audio leakage when muted audio is expected;
- unreadable text placement;
- unsupported counters or labels that should be omitted;
- obvious render/composition errors;
- transitions/effects that obscure movement or misrepresent continuity.

The repair loop should be bounded. After a small number of meaningful repair attempts, the agent should stop and report the blocking technical issue rather than repeatedly rendering without a new hypothesis.

## Workspace Agent blueprint

The public repository will contain a reproducible blueprint rather than claiming to distribute a universally installable ChatGPT Agent package. The blueprint should include:

- `agent/WORKOUT_REMOTION_DIRECTOR.md` — public overview, responsibilities, architecture, and version.
- `agent/agent-instructions.md` — copyable Workspace Agent instruction set.
- `agent/workflow.md` — orchestration state machine and interruption/repair rules.
- `agent/tool-requirements.md` — required and optional capabilities, including Workout Remotion Editor and Remotion.
- `agent/starter-prompts.md` — representative one-and-done and advanced requests.
- `agent/setup-guide.md` — steps for recreating/configuring the Workspace Agent in ChatGPT.

The repository README should present three usage paths: Skill only, Agent blueprint only, and Agent + Skill. The combined setup is the intended complete experience, while neither option should be falsely described as mandatory when a user only wants the other layer.

## Dependency behavior

The preferred complete configuration is Workout Remotion Director + Workout Remotion Editor + official Remotion skills/capabilities. The agent instructions should detect missing dependencies early.

If Workout Remotion Editor is unavailable, the agent should not silently pretend it has the Skill’s workout-specific rules. It may explain the missing dependency and, where appropriate, continue only with capabilities genuinely available.

If Remotion implementation/rendering is unavailable, the agent may still produce a truthful edit blueprint if useful, but must clearly state that it could not complete the requested finished render.

## Versioning

The initial blueprint version is **Workout Remotion Director v1.0**. Its version is independent from Workout Remotion Editor, which is currently v2.3. Compatibility documentation should name the Skill version used to design/test each agent release rather than forcing the two projects to share version numbers.

## Success criteria

A successful v1.0 blueprint lets a user recreate a ChatGPT Workspace Agent that can receive workout footage plus a short request, make routine creative decisions autonomously, use Workout Remotion Editor for specialized workout/social intelligence, use Remotion for implementation, automatically QA and repair reasonable issues, and return one finished render without routine approval prompts.

The agent remains thin enough that improvements to Workout Remotion Editor or Remotion do not require duplicating those systems inside the agent instructions.