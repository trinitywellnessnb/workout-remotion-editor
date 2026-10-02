# Open-source and third-party notes

This skill contains original project guidance under MIT. It does not vendor or copy third-party repositories. External projects remain under their respective licenses; review the exact version's license and notices before installing, distributing, or embedding it.

- **PySceneDetect 0.7.1** — optional public-API scene evidence adapter; [upstream](https://github.com/Breakthrough/PySceneDetect/tree/v0.7.1), [BSD-3-Clause license](https://github.com/Breakthrough/PySceneDetect/blob/v0.7.1/LICENSE). No code is copied.
- **PyAV 18.0.0** — optional PySceneDetect decoding backend, BSD-3-Clause; [license](https://github.com/PyAV-Org/PyAV/blob/v18.0.0/LICENSE.txt). Wheels include separately licensed FFmpeg libraries. Pinned for compatibility with PySceneDetect 0.7.1.
- **Auto-Editor 31.6.0** — optional analysis-only levels/info subprocess adapter; [upstream](https://github.com/WyattBlue/auto-editor/tree/31.6.0), [Unlicense](https://github.com/WyattBlue/auto-editor/blob/31.6.0/LICENSE). Release binaries include dependencies with separate licenses. No code or binaries are bundled.
- **FFmpeg/ffprobe** — optional metadata probe and integration-test video generator; [upstream licensing](https://ffmpeg.org/legal.html). Build options affect LGPL/GPL licensing. No executable is bundled.
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

## Phase 2 Ultralytics provenance

Optional Ultralytics 8.4.171 uses public Python detect/track results through an isolated worker. Upstream code and default trained models are AGPL-3.0 or separately Enterprise licensed; this project selected the Enterprise route. Obtain applicable terms before use. Optional subprocess invocation is not a blanket licensing exemption. Original integration code remains MIT; no upstream code/config/weights are copied. See object-tracking.md and THIRD_PARTY_NOTICES.md for obligations and local-only controls.
