# Phase 2 object detection and tracking

## Role and pipeline

The optional `YoloObjectTracking` provider extends the existing path rather than creating a second analysis system:

`video → media probe → scenes → motion/activity → object tracking → normalized evidence → Editor → Director → Remotion → QA`

YOLO supplies observations only. It does **not** recognize exercises, count reps, infer movement phases or joints, assess biomechanics or failure, or make crop/editorial decisions. Phase 3 pose/action work must enrich the same `tracked_entities` by `entity_id`; it must not replace this identity layer.

## Install and run

Core analysis has no YOLO dependency. For the optional provider:

```bash
python -m pip install -r workout-remotion-editor/scripts/requirements-object-tracking.txt
python workout-remotion-editor/scripts/analyze_video.py input.mp4 --object-tracking \
  --yolo-model /models/yolo11n.pt --yolo-device cpu --yolo-sample-rate 2 \
  --yolo-tracker bytetrack.yaml -o analysis.json
```

The CPU-first default is the nano `yolo11n.pt` model name, CPU device, ByteTrack, 2 samples/second, and 0.25 detection confidence. CUDA device indexes and `mps` may be selected when supported by the installed PyTorch/Ultralytics build. A local model path is required by default. Passing `--allow-model-download` explicitly permits Ultralytics to resolve/download a named model and therefore may access the network. User video is decoded and inferred locally; this repository adds no upload or telemetry path.

The analyzer samples active motion at the configured rate and long regions classified inactive at no more than 0.5 samples/second. Source-relative timestamps use decoder presentation time where available, with frame index/probed FPS only as a monotonic fallback. Scene boundaries reset the scene-local identity namespace; equal tracker numbers in two scenes are different entities. ByteTrack receives sequential sampled frames and can preserve IDs through short losses, but an absent/reassigned upstream ID is never fabricated as continuous identity.

## Evidence contract

`object_detections` records category, source-relative timestamp, confidence, optional track/entity reference, provider/model, source dimensions, sample index, and `bounding_box`. Boxes use normalized `[x_min, y_min, x_max, y_max]` coordinates in the displayed source plane, each value in `[0,1]`. `tracked_entities` groups scene-local trajectories and leaves room for later landmark/action evidence to reference the same entity. `entity_roles` contains advisory `primary_athlete_candidate` evidence.

Candidate scoring combines temporal persistence, continuity, movement, observed duration, prominence, and proximity to model-supported equipment. No one factor decides identity. A brief large foreground crossing is duration-limited. Close candidates are marked `ambiguous` with the alternative in supporting reasons. Identity is reset at Phase 1 scene boundaries; mirrors remain a known ambiguity rather than an invented certainty.

`visual_regions` and `crop_constraints` are advisory evidence only. They report the athlete envelope and risks such as source-edge contact, temporary loss, or excessive motion. Without joint landmarks they cannot guarantee working-anatomy, foot, implement-path, or biomechanical visibility; the Editor retains the priority order and final framing authority.

## Equipment limitations

Stock COCO detection models do not reliably provide dumbbell, barbell, kettlebell, plate, cable-handle, or gym-machine classes. The adapter preserves only category names actually returned by the selected model and never relabels a generic object as gym equipment. Some stock classes such as `sports ball`, `baseball bat`, or `tennis racket` may act as weak proximity evidence but are not generalized into a fabricated weight label. Future custom models can emit their actual taxonomy; generic downstream roles should use `equipment`, `unknown_equipment`, or `custom_object` when certainty is unavailable.

## Failure behavior and metadata

Missing Ultralytics, missing local weights, model-load errors, decode/inference errors, timeouts, and zero detections produce an isolated analyzer status. Prior scene/motion evidence and the full editing workflow continue. Successful runs record model, tracker, device, analyzed samples, skipped frames, source duration, effective sample rate, and wall-clock analysis duration. No large model is downloaded in normal tests; an explicit-download real-model smoke test is intentionally optional.
