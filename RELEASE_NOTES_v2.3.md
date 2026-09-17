# Workout Remotion Editor v2.3 release notes

## Evidence-informed retention and shareability editing

Version 2.3 preserves the workout-specific analysis, rep and phase intelligence, truthful high-effort hook selection, exercise-aware reframing, overlays, QA, revision locality, and official Remotion Agent Skill routing delivered in v2.2.

It adds a progressive-disclosure retention and shareability reference that helps an editor:

- define a target audience and one-sentence viewer promise;
- structure an edit as hook, orientation, progression, payoff, and optional close;
- use curiosity and pattern changes only when they are honest and purposeful;
- choose a supported reason to share: utility, identity/community, achievement/story, conversation, or delight/craft;
- create earned endings and optional loops without falsifying reps or chronology;
- document evidence, confidence, risks, and single-variable test variants;
- interpret comparable first-party analytics diagnostically rather than promising causation or virality; and
- protect exercise visibility, safety, accessibility, privacy, rights, and editorial truth ahead of attention metrics.

## Structured data and validation

The analysis schema is now version 2.3. It supports optional audience, promise, share-reason, variant, and retention beat data. The semantic validator checks retention beat IDs and time ranges and ensures a payoff reference resolves to a declared beat.

## Documentation and packaging

The README, Markdown user manual, skill metadata, CI fixture, changelog, and QA checklist have been updated for v2.3. The v2.2 DOCX remains in the repository as an explicitly archived manual; the Markdown manual is authoritative for v2.3.

## Upgrade note

Structured analysis files must declare `"schema_version": "2.3"`. Existing v2.2 editorial capabilities remain part of the skill, but v2.2 JSON fixtures should be migrated by updating the schema version; the new `retention_plan` is optional.
