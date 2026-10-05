# Phase 14 advanced music analysis

## Decision and research

Phase 14 selects **librosa as an optional provider**, with the Phase 13 PCM-WAV
envelope provider retained as the zero-dependency baseline. The evaluation was
made in October 2026 from official project documentation and should be revisited
before changing pins.

| Option | Strengths | Costs / decision |
|---|---|---|
| librosa | ISC license; maintained Python API; onset, dynamic-programming beat tracking, local pulse/tempo, RMS and temporal segmentation; Linux/macOS/Windows wheels through its scientific-Python dependencies; deterministic when configuration is fixed | Scientific-Python install is larger than baseline and decoding support varies by SoundFile build. **Selected** because it is the smallest well-supported Python MIR layer that materially improves timing and structure without models. |
| Essentia | Broad MIR including rhythm, loudness, and advanced structural models; some downbeat options | Larger native package and licensing/deployment review is more involved (AGPL/proprietary options); some richer algorithms/models increase CI and artifact burden. Rejected for this optional, dependency-light phase. |
| aubio | Lightweight C library, onset and tempo tracking, broad OS support | Current stable documentation/release line is old, native build burden remains, and it does not supply the structural/loudness breadth needed here. Rejected. |
| FFmpeg | Mature compressed decoding; broad MP3, AAC/M4A, FLAC and WAV support; EBU R128/loudnorm measurement; process isolation | Not a capable musical beat/section tracker. Selected only as an optional, detected decoding and read-only measurement backend. License depends on the exact build. |

No package, binary, model, or weight is downloaded automatically. Install with
`python -m pip install -r workout-remotion-editor/scripts/requirements-audio-advanced.txt`.
FFmpeg is independently optional and discovered on `PATH`.

## Registry, capabilities, and selection

`provider_registry()` declares `baseline`, `advanced`, and `auto`. `baseline`
uses PCM WAV only. `advanced` explicitly requests librosa and returns
`unavailable` if it cannot import. `auto` prefers librosa, but falls back to the
baseline after absence or isolated failure where PCM WAV is supported. A
compressed file without a usable advanced decoder returns an honest unavailable
or failed state. The providers declare capabilities; consumers must not infer
unlisted features.

One selected provider owns overlapping evidence for a run. Results are never
silently averaged. The normalized document preserves Phase 13 fields and adds
optional provider configuration/capabilities, source SHA-256, contract version,
decode backend, processing duration, quality, tempo curve/regions, labeled beat
support, alternate half/double tempo candidate, sections, energy detail, and
loudness measurements. Old documents remain readable.

## Evidence semantics

- `estimated_bpm` is only the global summary. `tempo_curve` and merged
  `tempo_regions` retain actual local beat intervals and drive variable-tempo
  synchronization; displayed values are rounded to avoid false precision.
- `alternate_tempo_bpm` and `tempo_ambiguity` preserve half/double-time
  ambiguity. They are candidates, not certainty.
- `beat_confidence_kind=normalized_support_score` labels a deterministic
  regularity/strength support score. It is **not** a probability and not claimed
  to be provider-calibrated confidence.
- librosa does not defensibly provide downbeats, bar positions, or meter in this
  architecture, so `downbeats`/`bars` stay empty, `meter` stays null, and no
  every-fourth-beat guess is made.
- Sections are neutral `section_N` coarse energy phases (`low`, `rising`,
  `steady`, `high`, `falling`), emitted only when a track is long enough and has
  more than one stable phase. They are not verse/chorus/bridge or emotion labels.
- Energy points combine normalized local RMS and transient density. These are
  editorial intensity signals, not mood inference.
- When FFmpeg is available, its `loudnorm` analysis reports integrated LUFS,
  loudness range, and true peak. Peak and loudness are measurements only;
  soundtrack `volume` is never changed.

`analysis_quality` is a small evidence-availability rubric: high requires a
sustained, well-supported beat grid; moderate requires usable support; low means
onsets but weak beats; insufficient means no useful evidence. Low quality
reduces synchronization to subtle; insufficient evidence preserves the Phase 12
timeline. Existing Phase 13 documents without quality retain Phase 13 behavior.

## Decode, safety, cache, and performance

WAV and FLAC are loaded through librosa/SoundFile where supported. For MP3 and
M4A/AAC, detected FFmpeg decodes once into a temporary mono analysis WAV; the
original is opened read-only and the temporary file is deleted. Failures are
isolated. FFmpeg version/build remains an operator provenance concern and its
license depends on enabled codecs.

`--cache-dir` stores normalized JSON under a key derived from source SHA-256,
provider name/version, and analysis configuration. A run performs one decode and
shares onset/RMS features. Analysis is single-process, has a five-minute external
process timeout, and reports approximate processing time. The current librosa
path loads one downmixed track into memory, so very long recordings should be
trimmed by the operator before analysis.

## Synchronization and limits

The synchronizer ranks section boundaries, defensible downbeats (from future
capable providers), strong accents, then ordinary beats. Natural language can
request song sections, big hits, downbeats, loose synchronization, buildup, or a
final-rep drop without technical configuration. Density caps remain style-aware.
Only Phase 12 flexible, safe boundaries may move; locked reps, hook replays,
counter events, chronology, and source ranges remain authoritative. Final-rep
alignment prefers soundtrack offset rather than mutating the rep.

This provider performs no lyric/vocal analysis, mood diagnosis, automatic
mastering, or codec implementation. It does not claim downbeats, meter, or
semantic song form. Remotion remains renderer-only and receives the already
synchronized timeline plus source, trim, offset, fades, and user volume.
