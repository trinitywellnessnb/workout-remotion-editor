# Third-Party Notices

Workout Remotion Editor's original material is licensed under MIT. **No third-party repository, package, model, or source code is vendored or copied in this repository.** The names below identify optional integrations or conceptual influences. External projects remain under their respective licenses and terms; users must review the license for the exact version, artifact, model, and intended use.

## PySceneDetect

Phase 1 calls the public Python API of optional PySceneDetect 0.7.1 to collect scene ranges and boundary candidates. The upstream software is BSD-3-Clause, copyright Brandon Castellano. See the [versioned license](https://github.com/Breakthrough/PySceneDetect/blob/v0.7.1/LICENSE) and [upstream third-party notices](https://github.com/Breakthrough/PySceneDetect/blob/v0.7.1/THIRD-PARTY.md). No PySceneDetect code or package is bundled or modified. Optional installation brings its own OpenCV/NumPy and other dependencies.

## PyAV

The optional scene installation uses PyAV 18.0.0, pinned for compatibility with PySceneDetect 0.7.1. PyAV source is BSD-3-Clause; see its [versioned license](https://github.com/PyAV-Org/PyAV/blob/v18.0.0/LICENSE.txt). PyAV wheels also include FFmpeg libraries with their own licensing/notices. No PyAV package, source, or binary is bundled in this repository or Skill ZIP.

## Auto-Editor

Phase 1 invokes optional Auto-Editor 31.6.0 through its documented levels and info CLI interfaces. It never invokes editing/rendering commands. Upstream repository source is public domain under the [Unlicense](https://github.com/WyattBlue/auto-editor/blob/31.6.0/LICENSE). Official release binaries include dependencies that can have different licenses; consult the exact binary and dependency notices before redistribution. No source or binary is bundled or modified here.

## FFmpeg / ffprobe

ffprobe is an optional metadata provider; ffmpeg generates synthetic media in separate integration tests. FFmpeg licensing depends on build configuration and enabled libraries; see [upstream legal information](https://ffmpeg.org/legal.html). No FFmpeg executable or source is distributed in the Skill.

## TensorFlow.js MoveNet and BlazePose

MoveNet and BlazePose are attributed as optional pose-estimation approaches for proposing landmarks and movement events. TensorFlow.js code, model files, BlazePose implementations, datasets, and related artifacts may carry separate notices or usage terms. None are included here. Review the applicable upstream TensorFlow/Google project and artifact terms.

## MediaPipe-style rep-state concepts

The rep workflow uses the general concept of converting observed landmark/movement phases into a guarded state machine (for example, ready/eccentric/bottom/concentric/complete), inspired by MediaPipe-style fitness examples and common pose-analysis practice. No MediaPipe repository source, model, graph, or sample is copied or distributed.

## librosa

librosa is referenced as an optional audio/music-analysis library for features such as onset, beat, and signal analysis. It is not included. Consult the [librosa project](https://librosa.org/) and exact-version license/notices before use or redistribution.

## Essentia

Essentia is referenced as an optional audio-analysis toolkit. It is not included. Essentia licensing and conditions may depend on the version and use; consult the [Essentia project](https://essentia.upf.edu/) before adoption.

## Remotion official agent skills

Remotion is the recommended video implementation/rendering layer, and users are directed to official Remotion agent skills and documentation for current implementation guidance. Those skills and Remotion packages are referenced rather than copied or redistributed. Consult the [Remotion project](https://www.remotion.dev/) and the licenses/terms of the exact packages and skills used.

## Ripple-inspired concepts

The project's auditable paper-edit and timeline-lint approach is conceptually inspired by Ripple-style paper editing/linting workflows. No Ripple repository source, documentation, or assets are vendored or copied. Consult the relevant upstream Ripple project and its license if you independently adopt its software.

## Downstream responsibility

Users must inventory and clear all dependencies and assets in their own editing/rendering project, including footage, likeness/permissions, music, fonts, logos, stock media, code, models, and datasets. Preserve required copyright notices, attribution, source offers, and license texts.

## Ultralytics YOLO — optional Phase 2 integration

The original adapter invokes the public Python API of separately installed Ultralytics 8.4.171. It uses detection checkpoints and supported tracking backends only. No Ultralytics source, YAML configuration, package, model weights, or binaries are copied, modified, or bundled.

Upstream code is [AGPL-3.0](https://github.com/ultralytics/ultralytics/blob/v8.4.171/LICENSE). Ultralytics states that default trained models are AGPL-3.0 as well; [Enterprise terms](https://www.ultralytics.com/license) provide an alternative. The project selected an Enterprise integration route: obtain terms covering the actual use/distribution before enabling this optional dependency. This notice does not establish an existing purchase or confer downstream license rights.

Original editor/adapter material remains MIT. Optional API/CLI/subprocess use does not automatically remove copyleft implications for a covered combined work. AGPL-compliant distribution can be possible, including commercial use, but requires review of corresponding-source, notices, and modified network-service obligations. Merely being MIT/open source is not sufficient to declare the combined integration compliant. Redistribution of weights/code or training custom weights requires artifact-specific licensing review.

Users provision trusted local weights separately. No models/dependencies are downloaded during analysis. No footage or telemetry is transmitted. Optional installation brings PyTorch, torchvision, NumPy, OpenCV, tracker requirements, PyAV/FFmpeg and other separately licensed dependencies; review their exact artifacts before redistribution. Existing PyAV and FFmpeg notices above apply. See the bundled references/object-tracking.md for supported classes and limitations.
