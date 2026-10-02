# Phase 2 local visual detection and tracking

YOLO supplies evidence. Workout Remotion Editor chooses the workout edit; the Director orchestrates; Remotion implements reviewed timing/framing; QA checks the rendered result. Machine evidence is never ground truth.

## Licensing and installation

This integration follows the **Enterprise licensing route selected for this project**. Obtain Ultralytics Enterprise terms applicable to the actual code/model use and distribution before enabling it. This document does not assert that a contract has already been purchased or that downstream users are covered.

Original editor/adapter material remains MIT. Ultralytics 8.4.171 code and default trained weights are AGPL-3.0 unless separately licensed. An optional subprocess is a technical boundary, not an automatic copyleft exemption. AGPL can support commercial use with applicable obligations; being open source under MIT alone does not establish compliance for a covered combined work. Alternative AGPL distribution requires review of the whole integration and its source/notice obligations. See https://www.ultralytics.com/license and the versioned https://github.com/ultralytics/ultralytics/blob/v8.4.171/LICENSE.

No upstream code, YAML configurations, binaries, or weights are copied or bundled. Redistribution of any of these would require a separate license/notice/source review, including their dependencies. Output measurements and rendered videos are not automatically AGPL-covered solely because inference produced them.

Optional setup, separately from analyzing footage:
~~~sh
python -m pip install -r workout-remotion-editor/scripts/requirements-tracking.txt
~~~
Provision a trusted local detection checkpoint separately under applicable terms. PyTorch .pt files can execute code during loading: use trusted artifacts. The analyzer accepts existing local .pt files only and will not fetch weights, cloud models, or remote footage. It installs no dependencies at runtime.

## Existing workflow

~~~sh
python workout-remotion-editor/scripts/analyze_video.py workout.mp4 \
  --object-tracking --model /local/models/yolo26n.pt \
  --device cpu --tracker bytetrack --sample-fps 5 -o analysis.json
python workout-remotion-editor/scripts/validate_analysis.py analysis.json
~~~

Omitting --object-tracking retains the Phase 1 workflow. Opt-in without --model is an argument error. A missing package reports unavailable; missing local weights or unsupported package versions report skipped. Model loading/inference errors report failed or partial, with diagnostics, preserving prior valid analysis. Invalid output is quarantined. A valid fallback JSON still produces CLI exit 0.

Current tested upstream is 8.4.171 (October 1, 2026 release). Recheck APIs and licensing before upgrading. The current released model family is YOLO26; YOLO27 is a preview and is not selected.

## Models and devices

- CPU: start with YOLO26n detection, imgsz=640, FP32, 5 analyzed samples/second.
- Apple Silicon: YOLO26n with --device mps when supported; worker retries CPU after an accelerator failure.
- GPU: consider YOLO26s with explicit --device 0, then measure coverage and performance.
- Higher accuracy: optionally choose YOLO26m/l/x, with a higher local compute cost.

No claim of gym accuracy or real-time throughput follows from COCO benchmarks. The YOLO26 CPU speedup reported upstream is for an ONNX benchmark; this phase uses local PyTorch checkpoints. Model choice stays configurable; no massive default or CUDA requirement.

Only detect checkpoints are accepted. Pose and segmentation checkpoints are deferred. Ultralytics technically supports tracking with pose models, but those person-only models do not replace multi-class equipment detection. No keypoints, joint rules, rep counting, or MMPose dependency are implemented.

## Sampling and source timing

Decode frames with optional PyAV and retain their actual presentation timestamps. Source seconds are video PTS minus the video's verified stream origin, not frame_index / average_fps. This supports VFR sampling. Missing, non-increasing, or unverifiable timestamps fail with fallback instead of guessed timing. With a nonzero video origin, prior Phase 1 scene-clock alignment is not assumed: tracking fails conservatively. --skip-scene allows source-relative detection-only evidence in that case.

The first frame at/after each fixed analysis grid point is used. --sample-fps specifies requested cadence; source FPS can limit it. --full-frame-tracking analyzes every decoded frame. Both modes decode sequentially, so sampling reduces inference cost rather than eliminating all decode work.

Rotation-correct frames before inference. Boxes use display-oriented normalized xyxy coordinates; 0..1 spans the displayed video. Non-right-angle rotations are unsupported and reported. Run statistics include displayed dimensions; source width/height remain the coded dimensions. Crop inputs must use the same displayed coordinate space.

Phase 1 scene ranges partition tracking lifecycles. Each scene/cut starts a fresh public tracker lifecycle, even when raw numeric IDs repeat. Tracking intervals record the supporting scene ID. Multiple detector runs are not mixed. If scene evidence is absent, the worker uses detection only, emits no persistent IDs, and keeps subject identity unresolved. Observed person boxes still supply conservative crop regions. The Editor must review cuts; tracking cannot silently span unknown cuts. Large observed timestamp gaps reset tracker state and receive a new identity namespace. No cross-cut identity inference is performed.

Upstream buffers count processed tracker updates, not wall-clock source time; the ByteTrack default buffer of 30 updates is about 6 seconds at 5 FPS. Association and occlusion handling can degrade with sparse samples. Increase cadence for crossings, fast implements, or track loss. There is no promise of continuous crop safety between samples. Adaptive motion-dependent cadence is deferred until it can preserve/test tracker time assumptions. Low motion never establishes rest or disposable footage.

## Supported objects and extensions

Stock COCO detection models support person, bench, chair, sports ball, and several sport objects. They do not have classes for dumbbells, barbells, kettlebells, cable handles, weight plates, squat racks, or specialty gym machines.

Preserve the actual model class_name/class_id. A bench or chair is an object, not automatically workout equipment. Persistent proximity can produce an equipment_candidate region needing editorial review. A missed implement does not create a fake unknown_equipment detection and does not prove absence.

A custom detector may supply its own vocabulary without changing the editor contract:
~~~sh
python workout-remotion-editor/scripts/analyze_video.py workout.mp4 \
  --object-tracking --model /local/models/workout-detector.pt \
  --equipment-class dumbbell --equipment-class cable_handle
~~~
Explicit equipment labels must actually exist in the loaded model's class list. An actual model label unknown_equipment can be retained. No relabeling chair to dumbbell is permitted. Ultralytics track results may omit unmatched detections; these are available tracker observations, not an exhaustive object inventory.

## Primary-athlete candidates

Rank person tracks across each tracking interval, rather than changing the subject on each frame. The uncalibrated score weights persistence 45%, observed duration 25%, box-center displacement 15%, proximity to supported context/custom equipment 10%, and average box area 5%.

Selection requires at least three observed samples, 50% sample coverage, and a 0.12 score margin over the runner-up. A lone track still requires minimum support. Close alternatives remain ambiguous; sparse support is unresolved. The score is an organizing heuristic, not a probability; confidence is null. Reasons and component measurements are serialized for review.

This favors a persistent subject over a briefly larger crossing person, but cannot identify the athlete reliably in every gym. Box motion mixes camera and subject motion; proximity does not prove interaction; reflections and equally persistent people can remain ambiguous. There is no face recognition, biometric identity, or inferred exercise identity. Camera repositioning can break associations; scene cuts/reset lifecycles prevent automatic reconnection.

## Normalized output

Schema 2.5 extends the existing evidence document. Legacy 2.3/2.4 documents still validate. New collections:

- tracking_intervals: source-time lifecycle, supporting scene reference, cadence.
- detections: source seconds, sample/frame references, actual model class, normalized bbox, confidence, optional entity_id.
- tracked_entities: scene-local identity, provider_track_id, observed detection references, lifetime, sample coverage and gaps.
- subject_candidates: primary_athlete_candidate role, state, uncalibrated score, measurements and reasons.
- visual_regions: athlete, equipment_candidate, or padded crop_required_union.
- crop_constraints: sample-specific minimum region, evidence references, optional proposed-crop coverage and risks.

Every item references source_id and analyzer run_id. Internal references are namespaced per invocation; supporting Phase 1 scene IDs keep their existing namespace. Future pose/action providers can refer to these tracked entity IDs without replacing them. There is no separate YOLO final-format document.

Run provenance records model path, requested device/cadence/tracker, coordinate space, software version, and configuration. Statistics record decoded/analyzed/skipped samples, source duration, effective average sampling rate, model hash, actual device, display dimensions, inference and total durations. These measurements are written locally, not transmitted.

## Framing evidence

Workout priorities: working anatomy, athlete, moving implement, necessary foot placement, bar/machine path, context, then face. YOLO boxes only partially support these requirements. Review required joints/paths visually until the dedicated pose phase exists.

To assess an Editor-proposed crop:
~~~sh
python workout-remotion-editor/scripts/analyze_video.py workout.mp4 \
  --object-tracking --model /local/models/yolo26n.pt --crop-region 0.2 0 0.8 1
~~~

--crop-region is normalized display-space x1 y1 x2 y2. It does not choose the final crop or promise a 9:16 fit. The Editor/Remotion must supply the actual aspect-correct crop. Box-area retention is box_coverage, never anatomical visibility percentage.

Risk flags include athlete_bottom_cutoff, athlete_outside_crop, tracked_equipment_outside_crop, athlete_track_lost, primary_athlete_ambiguous, subject_unresolved, and required_region_outside_crop. Minimum regions include a 2% image-space padding and only observed boxes; missing subjects are not extrapolated. Ambiguous candidates produce conservative unions when visible. Empty flags never certify safety.

If a required union cannot fit 9:16, the Editor should consider wider framing, letterboxing, or a different shot. Face-centered cropping must not override workout visibility. Source evidence is mapped through accepted trims/playback rates to timeline frames by the Editor/Director handoff, never authored directly by YOLO.

## What tracking does not determine

No exercise/equipment identity beyond actual model labels, rep count, ROM quality, technique quality, injury, pain, muscular failure, load, set boundaries, editorial selection, or chronology claims. Camera-relative displacement is image evidence only. Machine candidates never populate segments or repetitions.

The Director-callable analyze() interface accepts providers and supplies prior normalized evidence as isolated context. Director blueprint files are absent from this repository snapshot; this phase documents the handoff rather than inventing them.

## Troubleshooting and verification

- unavailable: install the optional packages in the active Python environment.
- skipped: check package pin, local model path, and known duration.
- failed: inspect run.errors for model/task, decoder/timestamp, or CPU failure.
- partial: use observed coverage only; inspect warnings/errors and increase cadence if needed.
- ambiguous: visually choose the athlete; do not publish identity certainty from scores.
- undetected equipment: use visual review or a verified custom detector; never fabricate labels.
- accelerator failure: CPU retry is recorded; no CUDA installation is attempted.

Core tests use mocked worker/model output and deterministic multi-person fixtures; no ML stack or weights. Optional real smoke tests require separately provisioned weights and use explicitly selected setup acquisition, not runtime downloads. Real gym accuracy and crop usefulness require representative rights-cleared footage; fixture success alone cannot establish that.

The worker uses YOLO_OFFLINE=true, YOLO_AUTOINSTALL=false, isolated settings, sync/integrations disabled, no cloud credentials, and blocked outbound Python socket connections. No training/export/cloud callback is invoked. These controls are for trusted local dependencies, not a security sandbox for malicious checkpoints.
