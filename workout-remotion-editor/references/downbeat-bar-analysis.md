# Phase 15 downbeat, bar, and long-track analysis

## Research and adoption decision

Research was refreshed on 2026-10-05 against upstream project documentation.
Phase 15 does **not** enable a production downbeat backend. It adds the normalized
adapter seam and deterministic fake-provider tests, but fails closed when
`downbeat` is explicitly selected. This is deliberate, not a placeholder that
guesses bar structure.

| Candidate | License / reuse | Compatibility and weight | Evidence and long-track behavior | Decision |
|---|---|---|---|---|
| Essentia | AGPL-3.0 source or proprietary commercial license; exact binaries/models need review | C++/native stack; Linux/macOS/Windows builds; CPU; no GPU required for classic algorithms | Strong beat tooling, but `RhythmExtractor2013` does not establish downbeats, bar positions, or meter; streaming APIs exist | Rejected: licensing burden and the evaluated algorithm does not satisfy the downbeat gate |
| madmom | BSD source; bundled neural model/data files are CC BY-NC-SA 4.0 | Last PyPI release is old; Cython/native scientific stack has modern-Python friction; CPU | Established joint beat/downbeat DBN and meter choices; whole-track processing; confidence semantics require adapter care | Rejected: non-commercial model terms conflict with unrestricted reuse and CI is impractical |
| BeatNet | MIT code; pretrained-model provenance/terms are not sufficiently explicit for redistribution | PyTorch/librosa/madmom/PyAudio stack; CPU works, optional GPU; sizeable models are bundled upstream | Joint online/offline beat, downbeat, tempo, and meter; online mode is promising for long audio | Adapter candidate only: model-license and dependency review must be resolved before enablement |
| librosa | ISC source; established Phase 14 optional stack | Current Python, cross-platform scientific stack; CPU | Beat/onset and block streaming, but no defensible native downbeat/bar/meter result | Retained for Phase 14 evidence, never promoted into downbeats |

No dependency, binary, model, or network download was added. A future adapter
must take a local, explicitly configured model, record its name/version/hash and
license, report missing assets as `unavailable`, and operate offline. It must
have CPU support; GPU may only be opt-in.

## Provider and normalized contract

The registry exposes `baseline`, `advanced`, `downbeat`, and `auto`. `auto`
chooses the richest **installed and safe** provider, currently librosa then PCM.
It does not select the unavailable downbeat adapter. Consumers query declared
capabilities, not names: tempo, beat grid/support, onset/accent, downbeats,
bar positions, meter, sections/energy/loudness, streaming decode, and chunked
analysis.

Contract 3 downbeats contain source-relative `timestamp`, optional zero-based
`bar_index`, `support`, `support_kind`, and `provider`. Support kinds preserve
semantics: `calibrated_probability`, `provider_score`,
`normalized_support_score`, or `heuristic_strength`. A score is never renamed a
probability. Beats may carry `beat_within_bar` only when supplied. Meter is a
nullable provider result such as `3/4`, `4/4`, or `6/8`; 4/4 is never assumed.
Meter support is absent unless the provider supplies it. Variable meter can be
added later as evidence regions only if a backend supports changes.

Validation requires monotonic, in-bounds downbeats; monotonic bar indices;
valid provider/support semantics; capability consistency; and beat positions
within a known numerator. Actual event timestamps are retained under variable
tempo. Downbeats do not resolve Phase 14 half/double-time ambiguity unless a
future provider explicitly supplies that evidence. Old Phase 13/14 documents
remain valid under their earlier contract.

Provider grids are never averaged. A future orchestrator must designate one
authoritative rhythm provider, retain disagreement diagnostically, and record
selection reason, capabilities used, and fallback path.

## Streaming and memory policy

PCM WAV tracks at least 600 seconds long use bounded chunks by default; operators
may configure the threshold, chunk duration (default 120 seconds), and overlap
(default 2 seconds). The minimum chunk is 30 seconds. Each secure temporary WAV
contains only the current chunk plus controlled overlap and is removed in a
`finally` path. Source timestamps are restored during stitching. Events within
30 ms (energy within 80 ms) are deterministically deduplicated, keeping the
stronger event. Failures yield partial results when other chunks survive.

PCM accumulation is bounded to roughly `(chunk + 2*overlap) * sample_rate *
channels`; the quality report records this estimate, chunks processed, partial
failures, boundary duplicates, and processing time. Stitched beat timestamps
drive tempo regions—future beats are never generated from one summary BPM.
Integrated loudness, semantic section interpretation, and other whole-track
features remain global Phase 14 operations rather than being falsely described
as perfectly streamable.

The source SHA-256 is checked before and after analysis. Cache keys include the
source hash, provider/version, model identity when present, sample/hop settings,
and chunk/overlap configuration. Incompatible configurations cannot share a
cache. No source is modified and no normal analysis requires a network.

## Synchronization and limitations

For major boundaries the priority is section change, strong supported downbeat,
accent, then beat. Downbeats are capability- and quality-gated: high/moderate
evidence may guide major events; low/insufficient evidence is ignored in favor
of Phase 14 behavior. Fine cuts may still use ordinary beats. Cinematic edits
can request sparse grouped-bar buildup, viral edits can use occasional bursts,
smooth edits remain restrained, and coaching remains minimally musical. Density
caps prevent “every bar forever.” Locked reps, counters, chronology, safe trim
margins, and user-required content always win.

Natural requests such as “new bar,” “two bars,” “song phrasing,” “next phrase,”
and “few beats” enable conservative bar awareness only when the capability is
present. Bars do not prove semantic musical phrases, so “phrase” means grouped
bar timing unless an actual section provider supplies stronger structure.

Final-rep alignment retains the hierarchy section peak/change, strong downbeat,
accent, beat, and adjusts soundtrack offset before any flexible visual boundary
or safe time-remap. The protected rep is unchanged. Without a downbeat backend
the system falls back Phase 15 → Phase 14 librosa → Phase 13 PCM → no soundtrack.

Remaining limitations: no production downbeat model is enabled; chunked PCM
analysis is baseline-quality and not equivalent to a context-aware neural
stream; integrated loudness and advanced sections can still require whole-track
work; variable meter is not represented until a defensible provider supplies it.
