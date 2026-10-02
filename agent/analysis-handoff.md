# Director analysis handoff

The Director prepares evidence during INSPECT, reviews all media, chooses direction, and hands the evidence to Workout Remotion Editor at DELEGATE_SKILL. The Editor makes workout-specific decisions; Remotion composes and renders the accepted blueprint.

## Run from a repository checkout

Python 3.10+ is required. No new package is required by this wrapper.

~~~sh
python agent/scripts/prepare_analysis.py raw.mp4 --output-dir runs/workout-001
python workout-remotion-editor/scripts/validate_analysis.py runs/workout-001/analysis.json
~~~

Multiple files share a source-relative analysis document:

~~~sh
python agent/scripts/prepare_analysis.py squat.mp4 row.mp4 --output-dir runs/workout-002 --mode standard --timeout 300
~~~

Supported options: --title, --mode quick|standard|extended, --timeout (per tool invocation), --duration (positive manual fallback for one input), --skip-scene, and --skip-activity. Detailed detector/sampling configuration remains in the shared analyze_video.py entrypoint; this wrapper uses its defaults.

The output directory must not exist. This prevents replacement of source files or prior analysis jobs. Analyzer commands are non-destructive and use the shared bounded subprocess interfaces. A failed output write removes artifacts created by this invocation. A valid handoff is published only after analysis.json is written.

## Artifacts and status

analysis.json uses the one canonical scripts/analysis-schema.json contract inside Workout Remotion Editor. It contains source mappings, optional evidence, provenance, and empty editorial segments.

handoff.json is an orchestration manifest, separate from analysis JSON. It contains source IDs/paths/durations and timing-verification flags, evidence counts, provider run statuses/diagnostics, an analysis_file path relative to the job directory, and editor_review_required: true.

Its stage and next_state are INSPECT: preparing evidence does not establish that footage was visually reviewed. Its status is ready_for_visual_review when timed machine evidence exists, otherwise manual_review_required. Neither status means editing, QA, or rendering is complete.

| Provider status | Director action |
| --- | --- |
| success | Offer validated evidence to the Editor; review the footage. |
| partial | Preserve available evidence and read diagnostics; manually cover missing signals. |
| no_results | Treat the detector's empty result as empty evidence, not proof of no workout activity. |
| unavailable | Continue visual/manual analysis without installing packages automatically. |
| failed | Preserve other providers' evidence; use diagnostics and manual analysis. |
| skipped | Respect the stated limitation/opt-out; do not infer absent activity. |

Exit 0 means both validated analysis and handoff were written; missing/failing optional tools are represented in runs and do not change that success code. Exit 2 means preparation/input/output failure; do not consume a partial package. Missing command/Python capability requires the same visual/manual fallback in the Workspace Agent.

## Editor and Remotion handoff

1. Resolve analysis_file relative to the handoff directory and run the bundled validator before consuming supplied or modified artifacts.
2. Visually inspect all source clips. Keep source_id/path mappings intact when referencing evidence; source numbering follows input order.
3. Select direction, then pass the user request, source files, and validated analysis.json to Workout Remotion Editor.
4. Let the Editor produce reviewed segments/repetitions/overlays. Retain machine evidence/provenance separately from editorial decisions; never mutate it into assertions about workout sets or removable footage.
5. Verify sources flagged timing_requires_verification (including manual-duration fallback and unverifiable timestamp origins) before creating any timed editorial events. Validate the completed analysis/edit JSON before IMPLEMENT_REMOTION.
6. Convert accepted source seconds to frames once at the composition boundary, then complete normal Director QA, repair, render, and delivery.

No automated footage deletion, workout judgment, render, hosted agent registration, or future analyzer is implemented by this command. The restored blueprint supplies those orchestration responsibilities to a configured Workspace Agent.

## Tests

~~~sh
python -m unittest discover -s tests -p 'test_director.py' -v
ruff check agent/scripts workout-remotion-editor/scripts tests
python -m compileall -q agent/scripts workout-remotion-editor/scripts
~~~

Core CI runs the command with no optional packages/executables and checks failure cleanup, manifest routing, source preservation, and validation. The optional media job verifies the Director command against generated video with real analyzers.
