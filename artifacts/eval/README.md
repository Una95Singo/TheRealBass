# Eval runs — mobile review index

Latest runs, both against the synthetic corpus (real corpus is empty
until the user drops clips into `backend/eval/corpus/real/audio/`).

## Synthetic corpus baseline (Basic Pitch only, no QC)

→ [run-baseline-no-octave-check/index.md](run-baseline-no-octave-check/index.md)

| metric | value |
|---|---:|
| mean onset F1 | **0.588** |
| mean +pitch F1 | **0.577** |
| mean +offset F1 | **0.349** |

## Synthetic corpus with CREPE octave-check QC

→ [run-with-octave-check/index.md](run-with-octave-check/index.md)

| metric | value | vs baseline |
|---|---:|---:|
| mean onset F1 | **0.621** | +0.033 |
| mean +pitch F1 | **0.607** | +0.030 |
| mean +offset F1 | **0.366** | +0.017 |

CREPE pruned ~30% of false-positive notes on `eighths_120bpm` and
`shuffle_110bpm` without losing any true-positives — exactly the
expected signature of fixing harmonic-latch over-emission.

## How to read the per-clip artifacts

Each run folder contains one subfolder per clip with three files:

- **roll.png** — top: CQT spectrogram of the input audio. bottom: GT-vs-EST
  diff. **Blue = the pipeline missed a note. Red = the pipeline emitted
  a note that wasn't in the ground truth.** A clean run is mostly grey.
- **ab.wav** — stereo. Left ear = input audio, right ear = predicted MIDI
  rendered through the same envelope synth. Plug in earbuds to A/B them.
- **metrics.json** — the three F1 numbers, machine-readable.

## Caveats — why these numbers are LOWER than the previous 0.95

The old 0.95 mean was lying. The previous synth corpus was bit-perfect
sine waves with no decay, so a pipeline that set `note.end = next_onset`
got full +offset credit even though that's the bug that produced 12-second
sustained notes on real audio.

The new synth corpus has:
- ADSR envelope (5 ms attack, exp decay τ=0.45 s, 20 ms release)
- -60 dB noise floor
- A `dotted8_rests_100bpm` fixture with explicit silence on beats 2 and 4

So the new numbers are *honest* baselines for the new pipeline. The next
gate is real-bass clips dropped into `backend/eval/corpus/real/audio/` —
those are what the +offset F1 actually needs to be calibrated against.
