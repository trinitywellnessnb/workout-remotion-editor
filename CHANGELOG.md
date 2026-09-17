# Changelog

All notable changes to Workout Remotion Editor are documented here.

## [2.2.0] - 2026-09-17

### Added

- Explicit integration/routing for the current official Remotion Agent Skills: best-practices, create, markup, multimedia, captions, interactivity, Studio, render, docs, upgrade, SaaS, and maps when relevant.
- Dedicated `remotion-skill-routing.md` reference that keeps workout-specific editorial decisions separate from generic Remotion implementation guidance.
- Remotion Multimedia/Mediabunny metadata routing for duration and dimensions.
- Remotion Captions routing for spoken captions/subtitles while keeping coaching overlays distinct.
- Remotion Interactivity guidance for Studio-editable counters, exercise labels, crop controls, callouts, hook duration, and section trims.
- Preview-before-render workflow using Remotion Studio when available.
- Current-docs lookup rule for version-sensitive Remotion APIs.
- Rewritten v2.2 user manual and prompt library.

### Changed

- Workout Remotion Editor now explicitly owns WHAT belongs in the workout edit while official Remotion skills own HOW the edit is implemented in Remotion.
- Official Remotion skills are referenced/routed to rather than copied or vendored into the package.

## [2.1.0] - 2026-09-17

### Added

- Public v2.1 ChatGPT skill package with Quick, Standard, and Extended workflows.
- Evidence-linked workout analysis, paper-edit, rep-counter, struggle-hook, coaching-overlay, instructional, output, QA, and revision guidance.
- JSON Schema and semantic Python validator for analysis artifacts.
- Public user manual, open-source attribution, MIT license, and automated validated `skill.zip` packaging.
