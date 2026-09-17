# Official Remotion Skill Routing

Use this reference whenever the edit is being implemented with Remotion. Workout Remotion Editor owns workout-specific editorial decisions. Route implementation details to the appropriate official Remotion skill instead of re-deriving generic Remotion behavior.

## Core routing

- `remotion-best-practices`: default router when unsure which Remotion capability is needed.
- `remotion-create`: create a new Remotion project or composition. If no project exists, scaffold one before implementation. If a project exists, use it rather than creating a duplicate.
- `remotion-markup`: composition structure, animation, layout, typography, media elements, effects, audio, fonts, timing, sequencing, transitions, trimming, playback-rate work, and interactive markup patterns.
- `remotion-multimedia`: browser-side media inspection and metadata through Mediabunny, especially source duration and video dimensions before building the edit blueprint.
- `remotion-captions`: transcription, imported subtitles, caption JSON, caption display, and caption animation. Use Remotion Caption-compatible timing when captions are requested.
- `remotion-interactivity`: structure important authored elements so users can select and modify them in Remotion Studio. Favor this for exercise labels, rep counters, coaching cues, crop controls, title cards, and reusable edit controls.
- `remotion-studio`: preview the composition before final rendering when Studio is available.
- `remotion-render`: final video/still export. Use for requested finished outputs after edit QA passes.
- `remotion-docs`: look up current Remotion APIs, component props, or package guidance when implementation details are uncertain or may have changed.
- `remotion-upgrade`: use only when the current Remotion project or installed Remotion Agent Skills need upgrading.
- `remotion-saas`: use when the user is turning the editor into an application, service, automation, or product rather than editing a one-off video.
- `remotion-maps`: only use if a workout edit genuinely includes route maps, geographic overlays, running/cycling routes, location explainers, or similar map content.

## Video creation rule

When the user asks to create or edit a finished workout video, load the official Remotion creation guidance before implementation. Preserve existing projects when present. Open a preview after creating or changing the video when the environment supports it. Render only when the user asks for a finished video.

## Markup and animation rule

Use frame-driven Remotion animation. Favor `useCurrentFrame()` with Remotion interpolation/easing rather than browser CSS transitions/animations that may not render deterministically. Keep editable keyframes and values close to the markup they affect when practical.

Use Remotion media components and project assets according to current official guidance. Do not invent APIs when current docs can be consulted.

## Timeline rule

Translate the workout edit blueprint into explicit, understandable timeline segments. Keep important sections identifiable, such as Hook, Exercise 1, Transition, Exercise 2, Final Set, Coaching Segment, and Outro.

For sequential edits where shortening one section should move later sections, use Remotion's current ripple-style sequencing patterns. Preserve the workout editor's source-time versus timeline-time mapping so trims, playback-rate changes, counters, captions, and phase-synchronized overlays remain aligned.

## Metadata rule

Before finalizing crop and timing decisions, obtain source duration and video dimensions through Remotion multimedia/Mediabunny when those values are available programmatically. Store them in structured analysis rather than repeatedly probing the same file.

## Caption rule

If captions are requested, use the official Remotion caption workflow. Normalize captions to the Remotion caption structure with text plus millisecond timing and confidence fields where available. Keep captions separate from workout coaching overlays: captions represent spoken content; coaching overlays represent editorial/instructional content.

## Interactivity rule

When the composition is expected to be hand-adjusted later, make high-value objects editable in Studio when feasible:

- rep counter placement and style
- exercise titles
- coaching text
- crop/reframe controls
- hook duration
- section trims
- callout positions
- outro/branding text

Do not sacrifice render reliability merely to make every decorative detail editable.

## Preview and render rule

Preview before the final render when possible. During preview QA, inspect timing, crop safety, overlay collisions, segment joins, source-audio policy, and rep/caption synchronization. Only after the workout QA rules pass should the requested MP4 be rendered.

## Documentation lookup rule

If a requested implementation depends on a Remotion API that is unclear, version-sensitive, or not covered by the active skills, use `remotion-docs` rather than guessing. Keep Workout Remotion Editor focused on editorial logic and let official Remotion guidance remain the implementation authority.
