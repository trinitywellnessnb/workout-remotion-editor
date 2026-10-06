# Phase 16 production rhythm provider and compressed streaming decision

Research was refreshed on 2026-10-06 from upstream source, license, model, and
runtime documentation. Library and checkpoint terms were evaluated separately.
No production downbeat backend passed every adoption gate, so Phase 15's
fail-closed `downbeat` slot remains the production behavior.

| Candidate | Code / model licensing | Runtime and maintenance | Rhythm evidence | Phase 16 decision |
|---|---|---|---|---|
| BeatNet | MIT source; the repository bundles pretrained CRNN files, but a sufficiently explicit separate redistribution/commercial-use grant for those weight artifacts was not established | PyTorch, librosa, madmom/PyAudio/native dependencies; CPU and online/offline modes; active research implementation but heavy normal-CI footprint | Joint beats, downbeats, tempo, meter and online operation; output score calibration still requires adapter study | Deferred: bundled weights fail the separate model-license gate |
| madmom | BSD source; model/data files are explicitly CC BY-NC-SA 4.0 and therefore not cleared for unrestricted commercial use | Cython/scientific native stack, old PyPI release and modern-Python friction; CPU/offline | Established RNN/DBN beats and downbeats with meter-state choices | Rejected for production: model terms are non-commercial; forks that download the same weights do not change those terms |
| Essentia | AGPL-3.0 source or proprietary license; MTG ML models are CC BY-NC-SA 4.0 unless separately licensed | Large C++/native stack; CPU streaming algorithms; Python/platform packaging cost | Classic beat/tempo tools do not alone prove bar phase/meter; relevant learned artifacts retain separate terms | Deferred: licensing/deployment burden and no evaluated clear downbeat artifact |
| aubio | GPL source (commercial alternative available from author); no required neural weights | Small native C library, causal and CPU-friendly, but mature rather than rapidly evolving | Beats/onsets/tempo, not defensible downbeat, bar-position, or meter evidence | Not adopted: capability gate fails |
| librosa | ISC source, no downbeat checkpoint | Maintained Python scientific stack, CPU; Phase 14 optional dependency | Beat/onset/energy evidence but no native defensible bar phase/meter | Retained as advanced provider, never relabeled as downbeat evidence |
| newer research systems | Licenses and checkpoint/data-derived terms vary; many download weights from model hubs | Often PyTorch-heavy and checkpoint/network oriented | Potentially stronger joint tracking, but deployment provenance and score semantics need individual verification | Deferred until a stable release and explicit commercial checkpoint grant exist |

This is an engineering compatibility decision, not legal advice. The repository
bundles no rhythm weights, adds no downbeat dependency, performs no download, and
makes no hidden network call. A later model adapter must require an explicit local
path, verify an operator-supplied expected SHA-256, record provider/model/license
identity and inference mode, and return `unavailable` for a missing or mismatched
asset. It may label a native number `provider_score` or documented model posterior,
but never `probability` without calibration documentation.

## Compressed streaming architecture

For `.mp3`, `.aac`, `.m4a`, and `.flac`, baseline analysis selects the optional
FFmpeg PCM stream decoder when FFmpeg exists:

```
read-only source -> argv-only FFmpeg process -> mono 22,050 Hz s16le stdout
                 -> one synchronous bounded PCM chunk (+ overlap tail)
                 -> existing PCM analyzer -> globally stitched contract
```

No shell is used, filenames occupy one argument, stdin is disabled, video/data
streams are excluded, and no full decoded WAV or whole-track waveform is created.
Synchronous reads provide backpressure. Chunk offsets are integer sample counts,
then converted to seconds, avoiding cumulative timestamp drift. Overlap events are
sorted and deduplicated; beats are globally re-indexed. The bound is reported as
`(chunk_frames + overlap_frames) * channels * 2` bytes.

The session records source SHA-256 before/after, FFmpeg version, PCM format/rate/
channels, chunk configuration, decoded duration, successful/failed chunks,
coverage, failed tail when known, and bounded stderr diagnostics. Cache identity
includes source hash, provider/version (therefore FFmpeg version), decode backend,
rate/channels, timeout, chunk/overlap, and model identity. Configuration changes
cannot reuse stale evidence.

Timeout uses a readiness wait rather than a blocking whole-stream read. Timeout,
decode error, or analyzer exception terminates then kills/waits if necessary, so
children are reaped. A decoder error after useful chunks returns those events as
`partial`, caps coverage below 100%, marks quality low, and describes the unknown
remaining source span. Source bytes are never opened for writing.

## Evidence and limitations

Compressed baseline output has beats/onsets/accents/energy only. It advertises no
downbeat, bar, meter, variable-meter, section, calibrated-confidence, or semantic
structure capability. FFmpeg is a decoder, not a rhythm authority. Phase 15
validation and sync priority remain unchanged: supported sections, strong verified
downbeats, accents, then ordinary beats. Provider grids are not averaged; any
future comparison must retain an authoritative provider plus explicit disagreement.

The advanced librosa provider still has a whole-waveform limitation. Phase 16 does
not pretend independent local energy changes are global song sections, does not
stretch soundtrack audio, and does not guess variable meter or bar continuity.
EBU R128 measurement already runs directly against the source through FFmpeg, but
is measurement-only. A single streaming baseline decode supplies beat, onset,
accent, and energy evidence; isolated optional providers may decode separately.
