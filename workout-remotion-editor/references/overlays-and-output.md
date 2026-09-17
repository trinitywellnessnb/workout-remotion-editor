# Overlays and output

## Overlay system

Use a restrained, consistent hierarchy: title, context label, captions, counter/timer, coaching cue, and end card. Every overlay has a stable ID, start/end frame or seconds, content, placement, style, entrance/exit behavior, and evidence/brief source. Keep one primary idea on screen. Do not cover faces, joints relevant to instruction, equipment contact points, or burned-in platform controls.

Use high contrast, readable type, adequate size, and non-color-only meaning. Keep essential text within conservative title-safe margins (at least 5% horizontal and vertical; increase for platform UI). Provide captions when speech matters; preserve meaning and speaker attribution and check line breaks manually.

### Rep counters

Bind displayed values to verified rep events rather than animation time guesses. Do not advance on incomplete/uncertain reps. If the opening is reordered, ensure the counter cannot imply a false set count. Label partial excerpts such as “rep 6” only when the preceding source context establishes it.

### Coaching overlays

Use short, actionable, neutral cues. Point lines/arrows only at visible evidence and account for reframing. Avoid medical certainty and guarantees. Freeze frames/replays must be labeled when ambiguity is possible.

## Remotion implementation

Remotion is recommended because frame-based React compositions make edits reviewable and repeatable. Keep source timing, EDL, and overlays as data. Set explicit composition width, height, fps, and duration; convert seconds once; sequence clips and audio deterministically; preload assets; use static/random seeds where needed; and avoid network-dependent render-time behavior. Follow the applicable official Remotion agent skills/documentation rather than copying them into this package.

Other capable video-editing agents or plugins may work experimentally if they support accurate source trims, frame timing, transforms, text, audio mixing, deterministic export, and full-output review.

## Audio

Avoid clipping, abrupt room-tone changes, and speech/music masking. Use licensed or user-supplied music only. Duck music beneath speech; add short fades at cuts; retain meaningful exertion sounds unless privacy/tone requires otherwise. Measure peaks/loudness with an appropriate tool and listen for sync/artifacts.

## Deliverables

Default when unspecified: 1080x1920, 30 fps, H.264 video plus AAC audio in MP4. Do not upscale claims of quality. Name deliverables predictably and include analysis JSON, EDL/overlay plan, render settings, attribution/license notes, and QA report when requested. Verify the final file with a media probe and real playback.
