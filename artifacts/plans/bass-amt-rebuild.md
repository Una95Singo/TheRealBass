# Bass AMT Rebuild — Plan

Date: 2026-04-20
Branch: `claude/general-session-SsMKd`
Status: awaiting your approval — no code changes yet.

---

## What the rhythm-logs actually showed

Two real clips you uploaded (`artifacts/rhythm-logs/`):

- `4Una_Sticky Vicky` (92 BPM, 221 s) — note idx 64 sustains **12.65 s**.
  Cause: `note.end = next_onset` with no release detection.
- `4Una_Sexter` (123 BPM, 187 s) — **162 of 234 notes are MIDI 28 (E1)**.
  Cause: pYIN returns `fmin` (~30 Hz → E1) on noisy/silent windows.

Synthetic eval reports F1=0.95. That number is lying because the synth corpus
is sine waves with no decay and no silence — neither failure mode appears.

So: the engine choice is wrong, AND the eval is blind to the real failures.
Both have to change.

---

## Verified open-source landscape (what's actually used for bass)

| Tool | Bass-specific? | Note events? | Pip? | Verdict |
|---|---|---|---|---|
| **Spotify Basic Pitch** | bass in training set (Slakh, MedleyDB) | yes (MIDI out) | yes | Default engine. Has confidence knobs. |
| **CREPE** | no, but best raw-pitch tracker (85% vs Basic Pitch 33% in benchmarks) | no — F0 only | yes | Use as octave-check QC pass. |
| pYIN (current) | no | no — F0 only | librosa | Drop. fmin floor pile-up is not fixable. |
| MR-MT3 (gudgud96) | explicitly fixes MT3 bass octave errors | yes | no — JAX/T5X, GPU | Too heavy for this app. Bookmark. |
| bassunet (jakobabesser) | yes | CSV only | TF1.15, Py3.6 | Research artifact, not integrable. |
| Omnizart | no bass mode | yes | yes | No advantage over Basic Pitch. |
| ByteDance models | piano only, archived | n/a | n/a | Not relevant. |
| **songscribe** (gabe-serna) | yes — Demucs → Basic Pitch with bass preset | yes | repo | **Reference implementation** of the pattern we want. |

**Conclusion:** the proven pattern is **Demucs → bass stem → Basic Pitch**
(which we already have the first half of). songscribe ships exactly this.
We use it as the spine, then add a CREPE octave-correction QC pass that
nobody else has bothered with.

---

## The plan — five phases, land in order

### Phase 1 — Real-bass corpus (BLOCKS everything else)

The synthetic corpus is the reason we shipped a broken pipeline with 0.95 F1.
Fix the eval input first, otherwise we re-ship the same bug.

1. Add `backend/eval/corpus/real/` directory (gitignored — clips are large).
2. Curate **6–10 real clips**, ~10–15 s each, MP3 or WAV:
   - 2 isolated electric bass (DI, no effects)
   - 2 fingerstyle bass with light overdrive
   - 2 bass-in-mix that demucs has to separate first
   - 1 pick-style 16ths
   - 1 with explicit rests on beats 2 & 4 (the dropout fixture)
   - 1 walking bass
   - 1 your own song that currently sounds bad
3. **Source options** (all license-clean, verified):
   - IDMT-SMT-Bass dataset (research, free for non-commercial)
   - MedleyDB bass stems (research, free with form)
   - freesound.org isolated bass tags (CC0/CC-BY)
   - Your own studio recordings
4. Hand-label ground-truth MIDI for each clip in MuseScore (~30 min total).
   Commit only the `.mid` files to the repo — keep the audio external.
5. **Ground-truth metadata file**: `corpus/real/manifest.json` listing
   `{audio_path, midi_path, bpm, time_sig, source, license, notes}`.

**Why this first:** every later phase is calibrated against this. If we
swap engines but only test on synth, we won't know if anything improved.

### Phase 2 — Replace pYIN with Basic Pitch

Touch only `backend/transcribe.py`. The endpoint contract stays identical.

```python
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH

_, midi_data, note_events = predict(
    str(audio_path),
    model_or_model_path=ICASSP_2022_MODEL_PATH,
    onset_threshold=0.5,        # tunable per phase 5 calibration
    frame_threshold=0.3,
    minimum_note_length=80,     # ms; bass eighth at 187 BPM = 80 ms
    minimum_frequency=30.0,     # B0 = 30.87 Hz, covers 5-string
    maximum_frequency=500.0,    # cap harmonics; bass G3 = 196 Hz
    melodia_trick=True,
)
```

Drop: `_detect_onsets`, `_estimate_pitch_pyin`, the entire main note loop.
Keep: `_apply_beat_grid` (Basic Pitch onsets benefit from snap too), the
`return_debug` plumbing (logs become more useful, not less).

`note_events` shape from Basic Pitch is `[(start, end, pitch, amplitude,
pitch_bends)]` — adapt the existing 5-tuple consumer in `confidence.py`.

### Phase 3 — Mobile-reviewable eval harness

Replace `eval/run_eval.py`'s "print three numbers" output with a per-clip
artifact bundle. Result: every eval run produces something you can swipe
through on your phone in the GitHub mobile app.

**Output layout per run:**

```
artifacts/eval/2026-04-20T12-34-56/
  index.md                    ← markdown table, renders inline on mobile
  summary.json                ← machine-readable for CI
  quarters_80bpm/
    roll.png                  ← CQT spectrogram + GT-vs-EST diff piano roll
    ab.wav                    ← stereo: stem L, MIDI synth R
    ab.mp4                    ← muxed with roll.png for PR-comment upload
    metrics.json
  ... (one folder per clip)
```

**`index.md` is the killer artifact.** Renders inline in GitHub mobile.
Each row links to its `roll.png` (which also renders inline on tap) and
shows the F1 numbers. You scroll through, tap any row that looks bad,
see the diff piano roll — entire review takes ~2 min on a phone.

**The stereo A/B WAV is the second killer.** Plug in earbuds: left ear
is the original bass, right ear is what the pipeline heard. Wrong notes
and timing drift are instantly audible — no need to read MIDI.

**Implementation:**

- New file `backend/eval/artifacts.py` — pure-function module that takes
  `(stem_wav, gt_midi, est_midi, out_dir)` and writes the four files.
- Extend `run_eval.py` to call it per clip and emit `index.md`.
- The PNG recipe (CQT + diff roll) is the canonical librosa+pretty_midi
  one — research agent already verified it works.
- The A/B WAV is `np.stack([stem_norm, synth_norm], axis=1)` then
  `soundfile.write`. ~10 lines.
- The MP4 is `ffmpeg -loop 1 -i roll.png -i ab.wav ...` — optional, only
  needed when you want to drag it into a PR comment for inline playback.

**Mobile review checklist** (lives at top of `index.md`):
- [ ] Mean onset F1 ≥ baseline
- [ ] No clip regresses by >0.05 F1
- [ ] Spot-check 2 worst clips: piano-roll diff looks plausible
- [ ] Listen to 1 A/B WAV on earbuds: timing locked, no octave errors

### Phase 4 — CREPE octave-check QC pass

This is the "adversarial QC" you asked about, with verified prior art.

After Basic Pitch produces note events, for each note:

1. Slice the bass stem from `note.start` to `note.end`.
2. Run `crepe.predict(slice, sr, viterbi=True, model_capacity='tiny')`.
3. Median CREPE F0 → MIDI pitch. Confidence = mean of CREPE confidence column.
4. Decision tree:
   - CREPE confidence < 0.3 → keep Basic Pitch as-is (stem too noisy to trust).
   - CREPE pitch within ±50 cents of Basic Pitch → keep Basic Pitch.
   - CREPE pitch is one octave below Basic Pitch → **transpose down**
     (this is the documented MT3/Basic-Pitch failure mode).
   - CREPE pitch otherwise disagrees by >1 semitone → **drop the note**
     (Basic Pitch hallucinated it).

CREPE is `pip install crepe`, CPU-fine with `model_capacity='tiny'`,
adds ~50 ms per note. For a 200-note clip that's 10 s — acceptable for
an offline pipeline; we can profile and demote to opt-in if too slow.

New file: `backend/octave_check.py` (~80 lines, pure function, easily
unit-tested with synthetic CREPE outputs). New tests:
`backend/tests/test_octave_check.py`.

### Phase 5 — Calibrate, commit, gate

1. Run new eval against the real corpus (Phase 1) — capture baseline.
2. Tune Basic Pitch `onset_threshold` and `frame_threshold` against the
   real clips, not synth. Sweep [0.3, 0.4, 0.5, 0.6, 0.7] for each, pick
   the pair that maxes mean `+pitch` F1.
3. Commit the artifact bundle for the chosen settings under
   `artifacts/eval/<run_id>/` so you can review on mobile.
4. Add a CI gate (`pytest backend/tests/`) that asserts each real clip
   stays above its committed-baseline F1 minus 0.05.

**Acceptance** (against the real corpus, not synth):

- mean `onset` F1 ≥ 0.85 (real bass is harder than sine waves; 0.85 is realistic)
- mean `+pitch` F1 ≥ 0.80
- mean `+offset` F1 ≥ 0.65
- **zero clips with >50% notes on a single MIDI pitch** (the E1 pile-up gate)
- **zero notes with duration > 4 s** unless ground truth says so (the sustain gate)

The last two are the regression gates derived directly from your two
broken logs. They catch the actual failure modes, not the synthetic ones.

---

## Order of work + estimated time

| Phase | Time | Blocks | Reviewable on mobile? |
|---|---|---|---|
| 1. Real corpus | 1 hr (you label) + 30 min (me wire it up) | everything | manifest.json |
| 2. Basic Pitch swap | 1 hr | phase 5 | code review only |
| 3. Eval artifacts | 2 hr | phase 5 | **YES — index.md + roll.png** |
| 4. CREPE QC | 2 hr | phase 5 | code review + before/after rolls |
| 5. Calibrate + gate | 1 hr | done | **YES — final eval run** |

I can do phases 2, 3, 4 while you sleep. Phase 1 needs you to provide
or approve the real-bass clips — I can't curate audio for you. Without
phase 1 the calibration in phase 5 is meaningless.

---

## What I'm explicitly NOT doing

- **Fine-tuning Basic Pitch.** Real prior art is sparse, requires GPU + a
  labelled corpus, weeks of work. We can revisit if QC alone falls short.
- **Adding MT3 / MR-MT3.** JAX dependency, polyphonic transformer is
  overkill for monophonic bass.
- **Building a webapp for eval review.** The GitHub mobile app + committed
  PNG/MP4 artifacts gets you 95% of the value at 0% of the cost.
- **Touching the frontend.** This is purely a backend pipeline + eval change.
- **Removing the synthetic eval.** Keeping it as a fast smoke test, but
  the real corpus becomes the gate.

---

## Open question for you (only one)

Do you have ~6–10 isolated bass clips you can drop into
`backend/eval/corpus/real/audio/` (gitignored), or should I pull from
freesound.org / IDMT-SMT-Bass and you approve the selection?

If you reply by morning with either the clips or "use freesound", I can
have phases 2–3 done before you wake up and phase 5 calibrated by lunch.
