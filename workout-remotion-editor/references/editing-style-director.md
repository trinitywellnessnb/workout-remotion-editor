# Natural-language Editing Style Director (Phase 10)

`scripts/style_director.py` sits between a user's brief and the Phase 9 paper
edit. It returns structured decisions only; it does not expose private reasoning,
inspect pixels, or render React.

```text
ordinary request -> resolve_style -> style contract -> Phase 9 selection
                 -> apply_style -> normalized edit plan -> Remotion
```

## Language and internal families

Users say “social media ready”, “TikTok-ish but cleaner”, “let the final reps
breathe”, or “viral hook, cinematic body”. They do not need profile names.
The maintainable internal library contains `viral_shortform`,
`fast_fitness_montage`, `cinematic_trailer`, `epic_dramatic`,
`gritty_aggressive`, `smooth_sweeping`, `clean_coaching`, `raw_documentary`,
`polished_commercial`, and `rhythmic_music_montage`.

Resolution combines phrase evidence, contextual phrases, intensity modifiers,
negations, and explicit overrides. Matching concepts receive normalized weights;
their numeric intent, duration-band, role, and transition distributions blend.
“Social media ready” deliberately blends viral and athletic montage behavior
rather than defaulting to maximum-speed editing. “TikTok hook but cinematic
after that” creates explicit phase ranges.

## Contract

The output exposes detected concepts and weights; energy, pace, breathing room,
polish, authenticity, rhythm, and cinematic weight; platform bias; pacing curve;
phases; weighted clip-duration bands; shot-role targets; transition palette and
frequency; time-remapping rules; hook/setup/ending policies; explicit overrides;
and concise decision reasons. The original request and deterministic seed are
recorded.

### Duration and rhythm

Durations are distributions over micro, short, medium, anchor, long, and hero
bands, never one average. `duration_sequence()` hashes the recorded seed, index,
role, and available bands. It bounds explicit minimum/maximum values and prevents
more than three identical band choices in succession. Roles can force an anchor
or hero band where available. Identical inputs reproduce identical output.

### Pacing and roles

Profiles carry whole-video curves such as viral spike/rapid/breath/finish,
trailer tease/build/pause/escalation/climax/hero, and smooth establish/steady/
build/peak/finish. Evidence-backed roles include hook, primary movement, complete
rep anchor, micro detail, setup, breather, environment, close detail, hero, and
replay. A role is used only when source/editorial evidence supplies it.

Setup may include approaching equipment, loading weight, grip/stance placement,
bench or seat adjustment, pin changes, and recovery posture. Style controls its
target and 0.3–1.0 second range; a 25% ceiling prevents setup from dominating.

### Hooks, endings, and replay safety

Profiles choose different hook intent: immediate high motion, dramatic teaser,
impact detail, hero/build, or clear movement preview. Candidates remain limited
to user-selected or reviewed descriptions such as late-set or high-effort-looking.
The Director never diagnoses failure. A hook replay retains the same editorial
rep identity and suppresses its counter; its chronological primary occurrence is
not duplicated. Ending policies range from action cut through natural completion
to deliberate hero/fade.

### Transitions

The vocabulary is semantic: hard cut for immediacy/rhythm; motion match for
aligned movement; sparse whip for aggressive changes; the existing vertical-strip
glitch only when allowed; dissolve/fade for smooth passage; dip to black for
punctuation; sparse push/impact emphasis; or no effect. Frequency is separate
from palette. Cinematic profiles remain cut-dominant. `no glitch`, `not too
flashy`, explicit preferred transitions, and forbidden transitions win.

### Time remapping

`speed_curve()` emits renderer-neutral rate keyframes. The dramatic curve eases
from normal to slower shoulders, reaches its minimum at a reviewed landmark (or
the clip center when the profile alone requests it), and returns to normal. It
does not mutate Phase 9's primary `playback_rate`; the renderer consumes the
curve while rebuilding source-to-composition mapping. Below 50 fps—or when FPS
is unknown—the minimum is conservatively limited to 0.7x. Optical flow is false.
`no slow motion` disables ramps. Slow motion never asserts load, pain, failure,
or technique quality.

### Truth, determinism, and overrides

The enforced priority is source chronology, explicit instructions, reviewed
movement, meaningful movement visibility, target duration, style, then effects.
Style attachment deep-copies the Phase 9 plan and preserves identities,
chronology, hook counter suppression, and 1.0x active-movement defaults. Raw
machine `rep_candidates` are not an input. Explicit min/max, transition allow/
deny lists, maximum slowdown, and setup/hook preferences are optional—not a
questionnaire.

Source audio remains muted unless the user explicitly requests otherwise. Rhythm
metadata is future-ready but does not require or assume copyrighted music.


## Phase 11 shot-role integration

The style contract describes pacing and preferences; it does not identify source
semantics. Pass it to `semantic_shot_director.py`, which combines profile weights
with evidence-backed roles and general usability. Explicit role requests override
profile tendencies, and chronology/editorial repetition truth override style.
Candidate duration and FPS constraints bound Phase 10 duration/time-remap choices.
See [semantic-shot-director.md](semantic-shot-director.md).
