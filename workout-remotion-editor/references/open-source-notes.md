# Open-source and third-party notes

This skill contains original project guidance under MIT. It does not vendor or copy third-party repositories. External projects remain under their respective licenses; review the exact version's license and notices before installing, distributing, or embedding it.

- **PySceneDetect** — optional scene-boundary analysis inspiration/tool. See its upstream repository and license.
- **TensorFlow.js MoveNet and BlazePose** — optional pose-estimation approaches/models. TensorFlow.js, model artifacts, and BlazePose-related implementations may have distinct terms; verify each artifact.
- **MediaPipe-style rep-state concepts** — the generic use of landmark-driven state transitions inspires the rep-counting workflow. No MediaPipe source or model is included.
- **librosa** — optional Python audio/music analysis tool; retain its upstream notices when used/distributed.
- **Essentia** — optional audio-analysis tool; licensing can differ by use/version, so confirm suitability before adoption.
- **Remotion official agent skills** — recommended upstream implementation guidance. They are referenced, not copied or redistributed here; Remotion packages and skills retain their own terms.
- **Ripple-inspired paper-edit/lint concepts** — the auditable paper-edit and timeline-lint workflow is conceptually inspired by Ripple. No Ripple repository content is vendored or copied.

## v2.2 official Remotion integration

v2.2 explicitly composes with the current official Remotion Agent Skill categories published in `remotion-dev/remotion/packages/skills`: best-practices, create, markup, Studio, render, maps, captions, SaaS, interactivity, docs, upgrade, and multimedia.

These upstream skills are routing targets rather than bundled dependencies. Workout Remotion Editor decides the workout-specific editorial plan, then delegates generic Remotion implementation details to the appropriate official skill when it is installed or available. This keeps the package compact and lets current Remotion guidance remain authoritative for composition creation, markup, media handling, captions, editable Studio structure, preview, rendering, API lookup, upgrades, product architecture, and map content.

Record dependency name, version, source URL, license, purpose, and modifications in each downstream project. User footage, music, fonts, logos, stock assets, models, and generated assets require separate rights review.
