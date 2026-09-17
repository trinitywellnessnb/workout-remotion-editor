# Workout Remotion Director v1.0 — Workflow

## State machine

```text
INGEST
  -> INSPECT
  -> DIRECT
  -> DELEGATE_SKILL
  -> IMPLEMENT_REMOTION
  -> QA
       -> PASS -> RENDER -> DELIVER
       -> REPAIRABLE -> REPAIR_IF_NEEDED -> QA
       -> BLOCKED -> REPORT_BLOCKER
```

The normal workflow is autonomous. Routine creative choices are not approval gates.

## INGEST

**Entry:** The user provides workout media and an edit request.

**Responsibility:** Capture explicit requirements, supplied media, requested platform/format, requested audio behavior, overlays/data, and any revision constraints.

**Exit:** Enough information exists to inspect the media. Missing optional preferences use defaults rather than triggering questions.

**Failure:** If no usable media exists for a request that requires footage, report the missing source requirement.

## INSPECT

**Entry:** Media is available.

**Responsibility:** Inspect all supplied clips before selecting a direction. Identify evidence relevant to exercises, sets/reps, movement phases, visually compelling moments, dead time, framing constraints, and source quality without overstating uncertain detections.

**Exit:** The footage can support at least one truthful edit direction.

**Failure:** If the footage is unreadable or cannot support the requested result, either choose a truthful reduced-scope direction or report the blocker.

## DIRECT

**Entry:** Footage inspection is complete.

**Responsibility:** Select one strongest truthful creative direction. For social edits, establish a useful viewer promise and choose a plausible hook/pacing/share-value strategy. Preserve movement comprehension over decorative pacing.

**Exit:** One direction is selected and ready for specialized workout planning.

**Failure:** Only contradictory explicit requirements or an unsupported required claim should interrupt the flow when omission/reframing cannot solve the problem.

## DELEGATE_SKILL

**Entry:** Creative direction is selected.

**Responsibility:** Use Workout Remotion Editor v2.3 for workout-specific analysis, edit-blueprint decisions, rep/movement-aware cuts, research-informed retention/shareability, overlays, reframing, and workout-specific constraints.

**Exit:** A sufficiently detailed edit blueprint exists for implementation.

**Failure:** If the Skill is unavailable, do not impersonate it. Continue only if genuinely available capabilities can still satisfy the request truthfully; otherwise report the dependency blocker.

## IMPLEMENT_REMOTION

**Entry:** Edit blueprint is ready.

**Responsibility:** Route implementation to the relevant official Remotion skills/capabilities for composition, timing, media manipulation, animation, captions, preview, and render preparation.

**Exit:** A composition/output exists that can be checked.

**Failure:** If Remotion implementation is unavailable, a blueprint may be delivered as a fallback, but it is not a finished video.

## QA

**Entry:** An implemented composition or verification render exists.

**Responsibility:** Check technical integrity and workout correctness, including movement visibility, crop stability, anatomy/equipment occlusion, counters/labels, source/timeline synchronization, continuity, audio policy, text readability, effect restraint, and render integrity.

**Exit paths:**

- **PASS:** proceed to final render.
- **REPAIRABLE:** proceed to automatic repair.
- **BLOCKED:** report the blocker when no truthful/technical repair path remains.

## REPAIR_IF_NEEDED

**Entry:** QA identifies a repairable defect.

**Responsibility:** Correct the defect without changing explicit user intent or inventing facts. Valid automatic repairs include:

- moving/removing overlays that cover relevant anatomy or equipment;
- correcting unsafe or misleading crops;
- fixing source-to-timeline timing;
- removing accidental source-audio leakage when muted audio is expected;
- improving unreadable text placement;
- removing unsupported rep counters or labels;
- fixing obvious composition/render errors;
- reducing/removing transitions or effects that obscure movement or falsely imply continuity.

**Bound:** Every repeated repair must have a meaningful new hypothesis. Do not repeat the same failed action. After a small number of materially different attempts still cannot clear the same blocker, stop and report it rather than looping indefinitely.

**Exit:** Return to QA.

## RENDER

**Entry:** QA passes.

**Responsibility:** Render the requested final deliverable automatically. The default is one finished 9:16 social-ready MP4 unless the user requested another format.

**Exit:** A finished output exists and is available for delivery.

**Failure:** Attempt a technically meaningful repair when possible; otherwise report the render blocker without claiming completion.

## DELIVER

**Entry:** Final render succeeds.

**Responsibility:** Return the finished video plus a concise description of material decisions or limitations. Avoid burying the deliverable under implementation detail.

## REPORT_BLOCKER

A blocker report should identify what prevented completion, what stage failed, and whether a truthful blueprint/partial artifact exists. It should not convert ordinary creative uncertainty into a request for user approval.

## A/B branch

A/B is opt-in. When explicitly requested, branch after DIRECT or after an accepted baseline edit. Change one major hypothesis at a time, such as hook, pacing, CTA, caption treatment, crop strategy, audio treatment, or transition density. Run each requested variant through QA and render independently.