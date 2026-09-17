# Workout analysis

## Complete-pass method

1. Probe containers and streams; note rotation and variable frame rate.
2. Make a coarse full-duration pass to map activity, shots, audio, and defects.
3. Make a focused pass around candidate sets and story moments.
4. Mark exercise/setup/work/rest/transition intervals with confidence.
5. When requested, propose rep events and verify each against visible evidence.
6. Save structured JSON and validate it before editing.

## Rep counting

Define the movement cycle before counting. Use observable phases such as `ready -> eccentric -> bottom -> concentric -> lockout`, tailored to the exercise and camera view. A repetition counts only after the defined completion state is reached in order. Add hysteresis and a minimum state duration to prevent jitter; never count solely from one noisy threshold. Track `start`, `peak_or_bottom`, `end`, `complete`, `confidence`, and an optional exclusion reason. Manual verification controls the published count.

Pose tools such as TensorFlow.js MoveNet or BlazePose can estimate landmarks. MediaPipe-style rep-state concepts can help implement phase transitions. These are optional inspirations/dependencies, not bundled components, and their outputs can fail with occlusion, unusual bodies/equipment, fast motion, or poor angles.

## Struggle and effort

Possible signals include slowed concentric velocity, pauses, repeated setup, changed range, visible shaking, audible exertion, spotting, or abandonment. Describe only what is visible/audible. Label interpretations (“high-effort moment”) and confidence. Never infer pain, injury, emotional state, or medical risk from appearance alone.

## Coaching observations

Tie each note to a time range and observable relationship: joint/implement path in the image plane, stance, tempo, range, bracing setup, or loss of repeatability. State camera limitations. Prefer “the knee appears to move inward from this angle” over diagnostic or absolute language. Include positive execution where supported.

## Shot and audio aids

PySceneDetect can propose scene boundaries. librosa and Essentia can propose onsets, tempo, beats, loudness, and audio events. Verify all candidates manually; cuts need not land on detected beats. Record tool/version/configuration when automated analysis materially affects the edit.

## Analysis artifact

Use seconds as non-negative numbers. End times must exceed start times and fit known source duration. IDs must be unique. Segments need `id`, `source_id`, `start`, `end`, `type`, and `confidence`. Repetitions need `id`, `source_id`, `start`, `end`, `complete`, and `confidence`; `segment_id` is recommended. Preserve uncertainty in `notes` or `issues` rather than fabricating precision.
