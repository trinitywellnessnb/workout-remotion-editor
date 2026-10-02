# Pose evidence (Phase 3)

Rep analysis has a separate dense-sampling gate (about 6 usable samples/s minimum; median interval ≤0.167 s), so ordinary 2 Hz evidence is ineligible. See [repetition-evidence.md](repetition-evidence.md).


## Role and boundary

MMPose is an optional evidence provider in the existing analyzer pipeline. It estimates 2D image landmarks; it is not the Workout Remotion Editor and does not identify exercises, assess technique or safety, diagnose injury or pain, infer load/effort/failure, or emit repetitions. The normalized collections are `pose_samples`, `derived_joint_metrics`, `movement_signals`, and advisory `pose_crop_constraints`. Provider, model, local asset identity, and runtime belong in analyzer provenance rather than collection names.

## Model and acquisition

The CPU/basic target is an RTMPose small-class, approximately 256×192, COCO-17 model. Balanced and high-accuracy modes are explicit choices; whole-body and accelerators are never silently selected. The adapter requires local config and checkpoint files and lazy-loads MMPose only with `--pose`. It does not require MMDetection: existing YOLO person detections are passed to `inference_topdown` as ROIs. Without YOLO, a full-frame, scene-local pose-only candidate is allowed with weaker association confidence.

Upstream access was unavailable during implementation (the documentation endpoint returned HTTP 401). Consequently, no exact dependency compatibility claim is made. Before production installation, verify the current MMPose `init_model` and `inference_topdown` signatures, RTMPose config/checkpoint naming, and the MMPose/MMEngine/MMCV/PyTorch/torchvision compatibility matrix against official OpenMMLab documentation. The version-sensitive calls are isolated in `MMPoseProvider`.

## Vocabulary, coordinates, confidence, and missing data

The initial layout is `coco_17`: nose, eyes, ears, shoulders, elbows, wrists, hips, knees, and ankles with preserved left/right names. Layout identity is stored separately. Neck, pelvis, heels, toes, hands, z, and occlusion are not fabricated. Coordinates refer to displayed-source x/y normalized to `[0,1]`; source dimensions are retained. Out-of-frame estimates remain out-of-frame rather than being clipped to visible. Missing and low-confidence joints remain valid partial skeleton evidence. Scores are upstream model scores, not calibrated probabilities.

## Identity and multi-person behavior

A YOLO ROI attaches pose to the same cross-run `entity_id` and originating detection using `association_method: supplied_roi`. Cross-run references are preserved verbatim and validated for source, person category, scene, timestamp, and supplying-run status. Ambiguous skeletons remain unassociated, no tracked entity receives two forced identities, scene changes reset processing state, and evidence is not extrapolated through long occlusion. Pose-only candidates never claim tracked-YOLO identity strength.

## Derived evidence

Raw measurements are immutable. A conservative timestamp-aware One Euro variant produces separately identified smoothed samples, with filter state separated by source scene, entity, joint, and axis and reset after excessive gaps. Raw pose is never interpolated. Future derived interpolation is limited to one interior sample and `min(0.25s, 1.5 × nominal interval)`, must reduce quality, and may not cross scenes or identities.

Joint metrics are 2D displayed-image-plane shoulder/elbow/wrist, hip/knee/ankle, shoulder/hip/knee, and elbow/shoulder/hip angles in 0–180 degrees. Every metric references its supporting pose and contributing landmarks, and is omitted when inputs lack confidence. Movement signals use real timestamp deltas and torso image length; units explicitly remain image-space. Direction-change candidates require excursion plus velocity hysteresis and are not repetitions. Anatomy groups (`upper_limb`, `lower_limb`, `trunk`, and future side/bilateral candidates) describe motion only.

COCO-17 crop advice may report ankle, wrist, or head edge risk and a working-anatomy union. It cannot report precise heel/toe risk. All constraints are advisory; the Workout Editor remains final authority.

## CLI, performance, and fallback

```bash
python workout-remotion-editor/scripts/analyze_video.py input.mp4 --object-tracking \
  --yolo-model /models/yolo.pt --pose --pose-config /models/rtmpose.py \
  --pose-checkpoint /models/rtmpose.pth --pose-device cpu --pose-sample-rate 2
```

`cpu_basic` targets about 2 Hz. `balanced` conceptually targets about 4 Hz on an explicitly supported device; `high_accuracy` is opt-in. YOLO timestamps/ROIs are reused when present. Requested and decoded timing drift is recorded; caches are bounded to the current frame. Missing package/assets produce `unavailable`, model or inference/decode errors produce `failed`, valid empty execution produces `no_results`, and prior scene/motion/object evidence survives.

## Installation, acquisition, licensing, and limitations

Install `scripts/requirements-pose.txt` only in a dedicated optional environment after verifying the upstream matrix. Do not silently download; acquire a compatible config and checkpoint separately and review each source, checkpoint/model-card, training dataset, and fixture license. The repository redistributes no OpenMMLab source, config, binary, or weights.

MMPose source, MMEngine, and MMCV are commonly distributed under Apache-2.0 releases, while PyTorch uses its own BSD-style terms; these statements do not cover checkpoints, configs, datasets, CUDA/native runtimes, or transitive binaries. Verify the exact selected artifacts. 2D pixels are not true 3D biomechanics, physical distance, physical speed, load, pain, form quality, correctness, or completed movement.
