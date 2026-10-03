# Optional media analysis

Phase 5 adds opt-in schema 2.6 repetition evidence after pose and exercise fusion. It never changes editorial `repetitions` or rendering; see [repetition-evidence.md](repetition-evidence.md).


Phase 4 preserves the ordered evidence pipeline and adds explicit exercise context, interval proposals, and deterministic candidate fusion after optional pose. The normalized output remains provider-agnostic; provider/model details stay in provenance. See [object-tracking.md](object-tracking.md), [pose-evidence.md](pose-evidence.md), and [exercise-recognition.md](exercise-recognition.md).

External analyzers provide evidence. Workout Remotion Editor makes workout-specific editorial decisions, Workout Remotion Director orchestrates when available, and Remotion implements the accepted edit and renders it.

## Pipeline

RAW VIDEO → media probe → scenes/activity → YOLO identity → MMPose pose/movement → interval candidates → exercise context → deterministic fusion → normalized exercise candidates → Editor → Director → Remotion → QA

Pose remains optional and locally configured. No exercise recognition, rep counting, transcription, segmentation, or visual-quality model is installed by the core environment.

## Developer entry point

From the repository root:

~~~sh
python workout-remotion-editor/scripts/analyze_video.py raw.mp4 -o analysis.json
python workout-remotion-editor/scripts/validate_analysis.py analysis.json
~~~

From an installed Skill directory, use the same commands with the shorter paths:
~~~sh
python scripts/analyze_video.py raw.mp4 -o analysis.json
python scripts/validate_analysis.py analysis.json
~~~

Multiple input files produce one shared document with separate source IDs:
~~~sh
python workout-remotion-editor/scripts/analyze_video.py squat.mp4 row.mp4 -o analysis.json
~~~

The workflow validates the complete JSON before writing it. It never edits input footage. Machine evidence does not populate editorial segments, exercises, sets, repetitions, captions, playback rates, or timeline decisions. New output has empty editorial segments until the Editor evaluates the footage.

The canonical schema is repository-relative
workout-remotion-editor/scripts/analysis-schema.json (scripts/analysis-schema.json inside the Skill).
There is one schema, not an assets copy. The analysis JSON output defaults to analysis.json in the current working directory; it is a generated artifact, not a second schema.

## Optional installation and capability detection

Python 3.10+ runs the scripts. Standard-library operation and visual/manual analysis remain available without any analyzer packages.

Recommended full JSON Schema validation:
~~~sh
python -m pip install jsonschema
~~~

Install ffmpeg/ffprobe using your platform's package manager for probing. Remotion Multimedia/Mediabunny or manually supplied metadata remain available to the existing editorial workflow.

Optional scene detection, tested with PySceneDetect 0.7.1:
~~~sh
python -m pip install -r workout-remotion-editor/scripts/requirements-scene.txt
~~~

This installs scenedetect-headless with PyAV 18.0.0, OpenCV, and NumPy, only when requested. It exposes the same scenedetect module as the desktop package; install one variant, not both. PyAV 18.0.0 is pinned because PyAV 19 changed rational types that PySceneDetect 0.7.1 does not handle. PyAV is the default scene backend for reliable source presentation timestamps, including VFR. --scene-backend opencv is also supported. If the selected backend is missing or fails, the provider reports failure and falls back to visual analysis rather than silently substituting another backend. Some OpenCV/VFR combinations can produce an invalid terminal shot time; strict validation discards such results.

For Auto-Editor, install the tested 31.6.0 official binary from
https://github.com/WyattBlue/auto-editor/releases/tag/31.6.0, or an equivalent platform package of that version. Place auto-editor on PATH. Current upstream no longer publishes its CLI on pip; an old pip release is not the supported interface.

Providers detect packages/executables, record versions, and reject unsupported tool interfaces with a fallback status. There are no automatic downloads or installs during analysis. Subprocesses receive argument arrays without a shell, have a configurable per-invocation timeout, and have an output-size limit. Auto-Editor cache reads/writes are disabled.

## What the tools contribute

PySceneDetect uses its public SceneManager and backend APIs and source-time seconds from its 0.7 timecodes:
- adaptive is the default for footage with substantial movement/camera motion;
- content proposes hard-cut/visual-discontinuity candidates;
- threshold proposes brightness/fade-to-black or fade-from-black boundaries.

~~~sh
python workout-remotion-editor/scripts/analyze_video.py raw.mp4 --scene-detector content
python workout-remotion-editor/scripts/analyze_video.py raw.mp4 --scene-detector threshold --scene-threshold 12
~~~

--scene-threshold has detector-specific units; it is not confidence.
--min-scene-seconds specifies minimum shot duration in seconds.
Threshold boundaries are candidates, not precise fade envelopes or general dissolve detection.
A shot boundary never automatically establishes a workout set or a decoding defect.
No boundaries is a valid no_results state. For VFR, PySceneDetect estimates the final scene end as the last timestamp plus a nominal frame; an overshoot of at most one nominal-frame period is bounded to the probed video duration with a warning. Larger out-of-bounds results fail validation.

Auto-Editor uses only levels, with separate motion and audio measurements:
- motion_active and low_motion describe full-frame pixel changes;
- audio_active and audio_inactive describe loudness, per audio stream;
- sustained low_motion regions become candidate_dead_time ranges linked to their supporting signals.

No export, cutting, speed change, or rendering command is used. Quiet audio alone does not establish dead time. A candidate may contain coaching, equipment adjustments, static holds, recovery, setup context, or pre-lift preparation. The Editor decides whether to retain, remove, shorten, or speed-ramp it after reviewing the footage. The source-audio mute default does not prevent collecting audio evidence.

~~~sh
python workout-remotion-editor/scripts/analyze_video.py raw.mp4 \
  --motion-threshold 0.02 --audio-threshold 0.04 \
  --timebase 30/1 --minimum-candidate-seconds 2 --timeout 300
~~~

The timebase is logical analysis samples per second, independent of source or Remotion FPS. It is recorded as a rational rate and converted once to source seconds. Initial synthetic zero motion is excluded. Short/missing sample coverage is reported, never extrapolated. Media with non-zero or unverifiable stream timestamp origins skips Auto-Editor activity analysis rather than supplying shifted evidence. In those cases, use visual analysis or a separately verified preprocessing workflow; this CLI does not rewrite sources.

## Shared schema and backward compatibility

The single schema validates both legacy 2.3 and new 2.4 documents.
Legacy editorial confidence remains low/medium/high. New evidence is confined to 2.4:
- sources retain metadata, with a probe_run_id linking provenance;
- evidence.runs records source_id, category, provider, version, upstream, configuration, status, fallback, warnings, and errors;
- evidence.scenes and scene_boundaries record source-relative shot ranges and boundary candidates;
- evidence.activity_regions records threshold-based intervals and measured mean levels;
- evidence.candidate_dead_time references supporting signal IDs and explains why review is suggested.

Evidence confidence is optional, numeric in [0,1], or null for unknown.
Neither current adapter invents confidence probabilities. Signal magnitudes and thresholds are measurements, not probabilities of rest, speech, or exercise identity.

Source time always remains in seconds. Remotion converts accepted editorial timing to composition frames once at implementation, separately from source time. Machine evidence never uses final-timeline timestamps.

Validation checks source bounds, finite numbers, IDs, references, provider status, candidate support, and ordering within each source/provider/signal/stream. Overlapping signals and candidate ranges are legal; scenes from the same detector invocation cannot overlap. Active/inactive states of the same motion or audio stream share chronological ordering. Candidate dead time requires covering low-motion evidence; inactive audio can only supplement that support. Unavailable/failed/skipped providers cannot supply evidence.

## Fallback and exit behavior

A run records success, partial, no_results, unavailable, failed, or skipped.
Failed/unavailable/skipped runs explicitly advertise fallback.
Failures cannot silently become high-confidence editorial claims.
Malformed output, including invalid result containers and evidence items, is quarantined while prior valid evidence is preserved. Each provider invocation has a unique run namespace, including its evidence IDs and candidate references; multiple detector configurations can analyze the same source independently.

ffprobe is preferred. Auto-Editor info --json can supply metadata if probing fails; it does not verify stream timestamp origins. For one input, --duration SECONDS supplies a manual duration fallback. If all metadata routes fail, a 2.4 source can have duration: null. No timed evidence or editorial events are accepted until duration is known.

The CLI exits 0 when it writes a valid evidence package, even if all optional providers fail or are missing. Read run statuses to determine available evidence. Invalid arguments, output failures, or an invalid final package return an error. --skip-scene and --skip-activity allow deliberate opt-out.

Without jsonschema, the validator performs dependency-free structural checks for the bundled schema and the same semantic checks. Use jsonschema for full JSON Schema handling, especially custom --schema files. Bundled workout semantic checks apply only to the bundled schema (including an identical supplied copy); unrelated custom schemas use their own structural contract. All documents still reject non-finite numbers.

## Extending later

Implement the small Provider contract in scripts/analyzers/base.py and return Result:
metadata, normalized evidence collections, warnings/errors, and status.
Register the provider in the workflow; add schema definitions, semantics, fixtures, documentation, and independent optional integration tests when its phase is approved.

The category vocabulary anticipates transcript (WhisperX), object_tracking (YOLO),
pose (MMPose), action_recognition (MMAction2), quality (VMAF), and future tracking/segmentation (SAM 2). These names describe extension points only; no future dependencies, provider stubs, or integrations are implemented.

Director can call analyze_video.py and inspect the normalized JSON regardless of installed tools. This checkout documents Director responsibilities in README but does not contain the linked agent/ implementation; Phase 1 does not fabricate it.

## Validation and CI

~~~sh
python -m unittest discover -s tests -p 'test_analysis.py' -v
ruff check workout-remotion-editor/scripts tests
python -m compileall -q workout-remotion-editor/scripts
~~~

Core CI installs jsonschema, PyYAML, and Ruff only, runs semantic fixtures and adapter/CLI fallback tests, and validates/packages skill.zip.

A separate optional integration workflow installs ffmpeg, PySceneDetect with PyAV, and the pinned Auto-Editor binary. It generates tiny synthetic videos to check actual scene/motion/audio signals, VFR timing, unsupported-media fallback, and unchanged input bytes. It installs no ML stacks.

~~~sh
REQUIRE_ANALYZERS=1 python -m unittest discover -s tests -p 'test_integration.py' -v
~~~

## Phase 6 sidecar workflow

`repetition_evaluation.py` validates independent gold annotations and adjudications, evaluates machine candidates by split, prepares/validates review decisions, and explicitly promotes reviewed candidates. Evaluation reports do not belong in production analysis JSON. Held-out reports must not drive threshold changes; production defaults are never mutated by the evaluator. See [repetition-evaluation.md](repetition-evaluation.md).
