# Phase 13 soundtrack intelligence

Phase 13 adds optional, inspectable soundtrack evidence after the authoritative
Phase 12 timeline. Music may adjust edit timing; it cannot rewrite workout
truth. With no soundtrack, failed/unavailable analysis, or an `off` intent, the
visual timeline is unchanged. Camera/workout audio stays **muted by default**.

## Input and rights policy

`soundtrack_input()` records a soundtrack ID, local path, SHA-256 cache key,
rights/source note, optional source trim, desired composition start, normalized
volume, fades, and an explicitly requested loop flag. Do not commit private or
commercial music. Local WAV/MP3/video media are ignored; deterministic synthetic
PCM WAV is generated during tests and never checked in. No personal information
is required.

A long soundtrack is deterministically trimmed to the composition. A short one
ends in silence unless looping is explicitly requested. Phase 13 does not alter
soundtrack speed, perform loudness mastering, or automatically mix source audio.
The normalized audio slot leaves room for future voice, selected gym sound,
impact sound design, and coaching, but these are out of scope.

## Analysis and provider boundary

`PcmWavProvider` is the built-in CPU-only provider. It uses only Python's
standard library to decode PCM WAV once, derive a normalized RMS energy curve,
find envelope transients, and estimate a regular beat grid/BPM when sufficient
evidence exists. Each beat/onset/accent is in source soundtrack seconds and has
strength and provenance. Provider states are `success`, `partial`, `no_results`,
`unavailable`, `failed`, and `skipped`.

The interface is provider-neutral. Optional librosa/aubio/Essentia dependencies
were deliberately not added: their install/native weight and CI variation are
not justified for the conservative baseline. Other providers may return richer
sections or downbeats through the same contract. The baseline does **not** infer
bars/downbeats or musical sections; it reports them unavailable rather than
inventing structure. Energy is an editorial pacing hint, never a physiology,
emotion, lyrical-meaning, or musical-intent claim. Normalized analysis can be
cached by SHA-256 so unchanged audio need not be decoded repeatedly.

Validation rejects non-monotonic or out-of-range event times, non-finite BPM or
strength, invalid sections/bar grouping, missing provenance, and inconsistent
provider status. Malformed audio and optional-provider failure are isolated from
ordinary editing.

## Locked and flexible timing

The Composer now emits `boundary_lock`, `safe_trim_margin_before`,
`safe_trim_margin_after`, `transition_safe_boundary`, and `timing_priority` on
the existing rhythmic-cut contract. Boundaries involving reviewed reps, counter
events, hook identity/replay, identity-critical footage, or user-required
moments are locked. Optional detail/context/setup footage may expose conservative
flex margins. A beat outside the declared window is logged and ignored.

Accepted visual shifts reflow composition ranges, overlap transitions,
source-to-composition origins, and counter event mappings. Validation rechecks
chronology, ranges, transitions, counters, duration, trim, offset, and locked
boundaries. Adjustments carry reason codes such as
`snapped_to_nearby_beat`, `aligned_exercise_transition_to_accent`,
`preserved_locked_rep_boundary`, and `beat_outside_safe_margin`.

## Intent, style, and priority

Natural language resolves to `off`, `subtle`, `moderate`, or `strong`. Negations
such as “ignore the beat” win. “Don't sync every cut” reduces sync strength and
density rather than forcing either all-beat cutting or a full disable. Even
strong mode samples opportunities rather than cutting on every beat.

Truthfulness, explicit instructions, reviewed rep structure, chronology, and
locked events outrank style; style outranks section/energy alignment, beat snap,
and decorative timing. Viral, fast montage, and gritty profiles allow stronger
transient alignment. Cinematic emphasizes sparse accents; smooth and clean
coaching remain restrained. Hybrid style uses a bounded middle behavior.
Transition **type** remains style-owned while music may influence **when** a safe
transition happens.

For “make the final rep hit on the drop,” the synchronizer first tries a bounded,
deterministically recorded soundtrack start offset. It preserves the rep source
range and completion/counter event. Future providers can expose defensible
section peaks and safe remap assistance; Phase 13 never fabricates a drop or
exceeds source-FPS slowdown safety.

## CLI and renderer

```bash
python workout-remotion-editor/scripts/soundtrack_analysis.py soundtrack.wav --output analysis.json
python workout-remotion-editor/scripts/music_sync.py timeline.json analysis.json \
  --soundtrack soundtrack.json --prompt "Cut it to the beat" --output synced.json
```

The second output contains the compiled timeline, soundtrack trim/offset/fades,
adjustment report, and validation. `music_summary()` produces an operator-facing
summary. Remotion receives final frame values for soundtrack source, offset,
trim, volume, fades, looping policy, and already synchronized clips. It plays
and fades audio; it must not detect beats or move edits.

## Limitations

The standard provider accepts PCM WAV, uses envelope heuristics, supports stable
click/percussive material best, and makes no calibrated-confidence claim.
Changing tempo, polyphonic music, section labels, downbeats, and loudness
measurement need a separately evaluated optional provider. There is no default
loop, time stretch, source-audio restoration, DAW mixing, or commercial fixture.
