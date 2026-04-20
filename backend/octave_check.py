"""CREPE-based octave-correction QC pass for Basic Pitch note events.

Basic Pitch is trained on a multi-instrument corpus and occasionally
latches onto the second harmonic of a low bass note, reporting the note
one octave too high. CREPE is a deeper, monophonic-only pitch tracker
that wins raw-pitch benchmarks (~85% vs Basic Pitch's ~33% on the
lars76/pitch-benchmark suite) and very rarely makes the same mistake.

For each Basic Pitch note we run CREPE over the same audio slice and
ask: does CREPE think this note is one octave lower? If yes, transpose
Basic Pitch down. If CREPE strongly disagrees in some other way, drop
the note. If CREPE is unsure (low confidence) or roughly agrees, keep
Basic Pitch as-is.

This module exposes:
- ``decide_correction`` — pure, unit-testable decision function
- ``apply_octave_check`` — thin wrapper that calls CREPE per note and
  applies decisions to a list of pretty_midi notes in place

CREPE adds ~50 ms per note on CPU with ``model_capacity='tiny'``. For a
3-minute clip with ~300 notes that's ~15 s, acceptable for an offline
pipeline. ``apply_octave_check`` is therefore opt-in — call it after
``transcribe_to_midi`` when QC matters more than latency.
"""
from __future__ import annotations

import math
from enum import Enum


# Below this CREPE confidence we decline to override Basic Pitch — the
# audio slice is too noisy / short / silent to trust CREPE's verdict.
CREPE_MIN_CONFIDENCE = 0.30
# Above this CREPE confidence, a sustained disagreement of >1 semitone
# triggers DROP. Below this threshold we keep Basic Pitch even on
# disagreement, since CREPE itself isn't reliable on the slice.
CREPE_DROP_CONFIDENCE = 0.60
# Tolerance for "essentially the same pitch" — ±1 semitone covers slight
# mistuning, vibrato, and CREPE's median-rounding error without papering
# over genuine octave errors (which are exactly 12 semitones apart).
PITCH_TOLERANCE_SEMITONES = 1
# CREPE wants 16 kHz mono input.
CREPE_SAMPLE_RATE = 16000
# Notes shorter than this can't yield a stable CREPE estimate (CREPE's
# internal window is 1024 samples = 64 ms at 16 kHz, plus ~30 ms padding).
MIN_NOTE_DURATION_S = 0.10


class Decision(Enum):
    KEEP = "keep"
    TRANSPOSE_DOWN_OCTAVE = "transpose_down_octave"
    DROP = "drop"


def decide_correction(
    bp_pitch: int,
    crepe_pitch_midi: float | None,
    crepe_confidence: float,
) -> Decision:
    """Return what to do with a Basic Pitch note given CREPE's read.

    Pure function — all inputs are scalars, no audio touched. The wrapper
    ``apply_octave_check`` is responsible for actually running CREPE and
    feeding numbers into here.
    """
    if crepe_pitch_midi is None or not math.isfinite(crepe_pitch_midi):
        return Decision.KEEP
    if crepe_confidence < CREPE_MIN_CONFIDENCE:
        return Decision.KEEP

    delta = bp_pitch - crepe_pitch_midi  # positive => BP is HIGHER than CREPE

    # Within rounding/mistuning tolerance — keep Basic Pitch.
    if abs(delta) <= PITCH_TOLERANCE_SEMITONES:
        return Decision.KEEP

    # Classic Basic Pitch failure: latched onto the second harmonic, so
    # BP is exactly one octave above CREPE. Transpose BP down.
    if abs(delta - 12) <= PITCH_TOLERANCE_SEMITONES:
        return Decision.TRANSPOSE_DOWN_OCTAVE

    # Some other large disagreement. Only drop if CREPE is confident
    # enough to actually override — otherwise we'd be over-pruning on
    # transient/noisy slices.
    if crepe_confidence >= CREPE_DROP_CONFIDENCE:
        return Decision.DROP

    return Decision.KEEP


def _crepe_estimate_midi(
    audio_slice,
    sr: int,
) -> tuple[float | None, float]:
    """Run CREPE on a single slice; return (median_midi, mean_confidence).

    Returns ``(None, 0.0)`` when the slice is too short to score or CREPE
    raises. Lazy-imports numpy / crepe / librosa so this module is
    importable in test environments that don't have TF installed.
    """
    try:
        import numpy as np
    except Exception:
        return None, 0.0

    if audio_slice.size < int(MIN_NOTE_DURATION_S * sr):
        return None, 0.0

    try:
        import crepe  # heavy import; lazy
        import librosa
    except Exception:
        return None, 0.0

    if sr != CREPE_SAMPLE_RATE:
        audio_slice = librosa.resample(
            audio_slice.astype(np.float32), orig_sr=sr, target_sr=CREPE_SAMPLE_RATE
        )
        sr = CREPE_SAMPLE_RATE

    try:
        _, freqs, confs, _ = crepe.predict(
            audio_slice, sr, model_capacity="tiny", viterbi=True, verbose=0,
        )
    except Exception:
        return None, 0.0

    if freqs.size == 0:
        return None, 0.0

    mask = (confs > 0.1) & np.isfinite(freqs) & (freqs > 0)
    if not mask.any():
        return None, 0.0

    median_hz = float(np.median(freqs[mask]))
    if median_hz <= 0:
        return None, 0.0

    median_midi = float(librosa.hz_to_midi(median_hz))
    mean_conf = float(np.mean(confs[mask]))
    return median_midi, mean_conf


def apply_octave_check(
    notes: list,
    audio,
    sr: int,
) -> dict:
    """Apply CREPE octave-check QC to a list of pretty_midi notes in place.

    Walks each note, runs CREPE over the corresponding audio slice, and
    either transposes the note down an octave or drops it according to
    ``decide_correction``. Returns a small dict of counters useful for
    diagnostics: ``{"kept": N, "transposed": N, "dropped": N}``.

    ``notes`` is mutated in place: dropped notes are removed by rebuilding
    the list. Caller is responsible for re-syncing any parallel arrays
    (e.g. ``note_events`` in transcribe.py).
    """
    counters = {"kept": 0, "transposed": 0, "dropped": 0}
    survivors = []
    for note in notes:
        i0 = max(0, int(note.start * sr))
        i1 = min(len(audio), int(note.end * sr))
        if i1 <= i0:
            survivors.append(note)
            counters["kept"] += 1
            continue
        slice_ = audio[i0:i1]
        crepe_midi, crepe_conf = _crepe_estimate_midi(slice_, sr)
        decision = decide_correction(int(note.pitch), crepe_midi, crepe_conf)
        if decision is Decision.DROP:
            counters["dropped"] += 1
            continue
        if decision is Decision.TRANSPOSE_DOWN_OCTAVE:
            new_pitch = note.pitch - 12
            if 0 <= new_pitch <= 127:
                note.pitch = new_pitch
                counters["transposed"] += 1
            else:
                counters["kept"] += 1
        else:
            counters["kept"] += 1
        survivors.append(note)
    notes[:] = survivors
    return counters


__all__ = ["Decision", "decide_correction", "apply_octave_check"]
