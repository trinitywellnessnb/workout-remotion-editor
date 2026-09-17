# Workout Remotion Director v1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible ChatGPT Workspace Agent blueprint that autonomously orchestrates workout footage from intake through Workout Remotion Editor, Remotion implementation, QA, repair, render, and delivery.

**Architecture:** Keep the agent thin. Workout Remotion Director owns orchestration and routine creative decisions; Workout Remotion Editor v2.3 remains the workout/social editorial intelligence layer; Remotion remains the implementation/rendering layer. The public repo distributes copyable Workspace Agent instructions and setup documentation, not a falsely advertised universal agent package.

**Tech Stack:** Markdown documentation, ChatGPT Workspace Agents, Workout Remotion Editor v2.3, official Remotion skills/capabilities, existing repository validation/CI where applicable.

**Spec:** `docs/superpowers/specs/2026-09-17-workout-remotion-director-design.md`

## Global Constraints

- Default UX is one and done: routine creative decisions do not require approval.
- Carry normal requests through final render automatically.
- Produce one strongest finished edit by default; A/B variants are opt-in.
- Never fabricate workout facts, chronology, performance, load, results, or coaching/medical claims.
- Workout Remotion Director orchestrates; Workout Remotion Editor supplies specialized intelligence; Remotion implements and renders.
- Default finished output inherits Workout Remotion Editor defaults: vertical 9:16 MP4, Standard pacing, muted source-camera audio unless overridden.
- The agent blueprint version is Workout Remotion Director v1.0 and is independent from Workout Remotion Editor v2.3.

---

### Task 1: Public Agent Blueprint and Copyable Instructions

**Files:**
- Create: `agent/WORKOUT_REMOTION_DIRECTOR.md`
- Create: `agent/agent-instructions.md`

**Interfaces:**
- Consumes: `workout-remotion-editor/SKILL.md` and the approved design spec.
- Produces: the public identity/architecture document and the instruction text a user can paste into a ChatGPT Workspace Agent.

- [ ] **Step 1: Write `WORKOUT_REMOTION_DIRECTOR.md`**

Document v1.0 purpose, one-and-done behavior, three-layer architecture, compatibility with Workout Remotion Editor v2.3, default finished-render behavior, and links to the remaining files in `agent/`.

- [ ] **Step 2: Write `agent-instructions.md`**

The instruction set must explicitly encode this state sequence:

```text
INGEST -> INSPECT -> DIRECT -> DELEGATE_SKILL -> IMPLEMENT_REMOTION -> QA -> REPAIR_IF_NEEDED -> RENDER -> DELIVER
```

It must state that routine choices are autonomous, A/B variants are opt-in, unsupported workout facts are omitted rather than invented, and user interruption is reserved for genuine blockers defined by the spec.

- [ ] **Step 3: Self-check for responsibility duplication**

Search both files for generic Remotion implementation tutorials or copied detailed Skill rules. Replace duplication with explicit delegation to Workout Remotion Editor or official Remotion capabilities.

- [ ] **Step 4: Verify required phrases/behaviors are present**

Confirm the files contain all of: `one and done`, `v1.0`, `Workout Remotion Editor v2.3`, `A/B`, `final render`, and the state sequence above.

- [ ] **Step 5: Commit**

```bash
git add agent/WORKOUT_REMOTION_DIRECTOR.md agent/agent-instructions.md
git commit -m "feat: add Workout Remotion Director agent blueprint"
```

### Task 2: Orchestration Workflow and Failure/Repair Rules

**Files:**
- Create: `agent/workflow.md`
- Create: `agent/tool-requirements.md`

**Interfaces:**
- Consumes: state sequence and interruption policy from Task 1.
- Produces: deterministic orchestration guidance and dependency/fallback behavior used by the Workspace Agent configuration.

- [ ] **Step 1: Write the workflow state machine**

Define each state with entry condition, responsibility, exit condition, and failure path. Include the normal path:

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

- [ ] **Step 2: Encode bounded automatic repair**

Document automatic correction for overlay occlusion, unsafe/misleading crops, source/timeline timing errors, accidental source-audio leakage, unreadable text, unsupported counters/labels, render/composition errors, and movement-obscuring transitions. Require a new repair hypothesis before another attempt and stop after repeated attempts fail to materially change the blocker.

- [ ] **Step 3: Write dependency requirements**

Classify:

```text
Required for complete workflow:
- ChatGPT environment capable of using the configured agent resources
- Workout Remotion Editor Skill
- Remotion implementation/render capability

Optional by request/context:
- user-supplied music or voiceover
- captions
- analytics supplied by the user for later A/B learning
- other supported media-analysis evidence
```

- [ ] **Step 4: Write truthful fallback behavior**

If the Skill is missing, prohibit pretending its workout intelligence is present. If Remotion/rendering is missing, permit a truthful edit blueprint but prohibit claiming a finished render. If footage is uncertain, prefer omission/conservative editing over unsupported annotation.

- [ ] **Step 5: Commit**

```bash
git add agent/workflow.md agent/tool-requirements.md
git commit -m "docs: define agent workflow and tool requirements"
```

### Task 3: Setup and User Entry Points

**Files:**
- Create: `agent/setup-guide.md`
- Create: `agent/starter-prompts.md`

**Interfaces:**
- Consumes: copyable instructions from Task 1 and dependency names from Task 2.
- Produces: a reproducible setup path and representative user-facing prompts.

- [ ] **Step 1: Write the Workspace Agent setup guide**

Explain how to create/configure the Workspace Agent, name it `Workout Remotion Director`, use `agent-instructions.md` as its instructions, attach/enable Workout Remotion Editor, enable the relevant Remotion capabilities, and verify with a non-destructive test request. Avoid claiming a one-click import format unless ChatGPT actually provides one.

- [ ] **Step 2: Add a one-and-done smoke test**

Use this test request verbatim:

```text
I uploaded several workout clips. Make this social media ready. Choose the strongest truthful direction yourself, carry the edit through QA, and return one finished vertical video.
```

Expected behavior: no routine creative questions; inspect all clips; use Skill intelligence; implement through Remotion; QA/repair; return one finished render or identify a genuine blocker.

- [ ] **Step 3: Write starter prompts**

Include concise examples for Standard one-and-done, Quick Reel, longer workout edit, struggle-rep hook, instructional/coaching overlays, rep counters, keep-source-audio override, and explicit A/B hook variants.

- [ ] **Step 4: Commit**

```bash
git add agent/setup-guide.md agent/starter-prompts.md
git commit -m "docs: add agent setup guide and starter prompts"
```

### Task 4: Repository Integration and Verification

**Files:**
- Modify: `README.md`
- Verify: all `agent/*.md`

**Interfaces:**
- Consumes: completed agent blueprint files from Tasks 1-3.
- Produces: discoverable Skill-only, Agent-only, and combined setup paths from the repository landing page.

- [ ] **Step 1: Add an Agent section to README**

Present exactly three paths without ranking users:

```text
Skill only — use Workout Remotion Editor directly for workout-specific editing intelligence.
Agent blueprint — recreate Workout Remotion Director for autonomous workflow orchestration.
Agent + Skill — configure Workout Remotion Director with Workout Remotion Editor and Remotion for the complete one-and-done workflow.
```

Link to `agent/WORKOUT_REMOTION_DIRECTOR.md` and `agent/setup-guide.md`.

- [ ] **Step 2: Verify internal links**

Check that every repository-relative Markdown link added by the agent documentation resolves to an existing file on the branch.

- [ ] **Step 3: Run repository validation**

Run the repository’s existing validation/test commands documented in the current project. Do not invent a new test framework solely for Markdown. Confirm existing Skill validation remains green because the agent is additive and does not alter Skill behavior.

- [ ] **Step 4: Review against success criteria**

Confirm the blueprint supports: short-request intake, autonomous routine decisions, Skill delegation, Remotion delegation, QA, bounded repair, automatic final render, truthful blockers, and one output by default.

- [ ] **Step 5: Commit**

```bash
git add README.md agent/
git commit -m "docs: integrate Workout Remotion Director v1"
```

- [ ] **Step 6: Open or update the pull request**

Use a PR title such as:

```text
Add Workout Remotion Director v1.0 agent blueprint
```

The PR body should explain that the change is additive, does not replace the Skill or Remotion, and introduces the optional one-and-done ChatGPT Workspace Agent blueprint.