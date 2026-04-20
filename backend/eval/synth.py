"""MIDI -> WAV synthesizer for the AMT harness.

Renders each note with an explicit ADSR envelope and a small bass-shaped
harmonic stack instead of pretty_midi's flat sine. Two changes from the
v1 (sine-only) synth, both motivated by failures the rhythm-logs surfaced
on real audio that the v1 corpus could not reproduce:

1. **Decay envelope.** v1 played a flat sine for the full note duration,
   so the pipeline could set ``note.end = next_onset`` and the eval
   wouldn't notice. Real bass decays; the v2 envelope (5 ms attack,
   exp decay tau=0.45 s, 20 ms release) means a note that overruns into
   the next onset's silence is now audibly wrong, and the +offset F1
   reflects it.
2. **Noise floor.** v1 was bit-perfect silence between notes, so pYIN-
   style detectors never tripped on quiet frames. Real recordings have a
   noise floor that triggered the E1 pile-up in production logs. v2 adds
   ~-60 dB noise so quiet-window failures show up in eval.

A small harmonic stack (1.0 fundamental + 0.4 octave + 0.2 fifth) gives
the synth a vaguely bass-like timbre. Still not real bass — but real bass
in the eval corpus is gated on the user dropping clips into
``corpus/real/audio/``. This is the synthetic fast-loop fixture that runs
on every commit.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pretty_midi
import soundfile as sf

# ADSR knobs, chosen to roughly match a finger-played electric bass note.
ATTACK_S = 0.005
DECAY_TAU_S = 0.45
SUSTAIN_LEVEL = 0.55
RELEASE_S = 0.020
# -60 dB white noise — quiet enough not to mask the fundamentals, loud
# enough to make a pitch-on-silence detector twitch.
NOISE_AMPLITUDE = 1e-3


def _render_note(
    pitch: int, duration_s: float, fs: int
) -> np.ndarray:
    """Render a single note as fundamental + 2 harmonics with ADSR."""
    f0 = pretty_midi.note_number_to_hz(pitch)
    n_total = max(1, int(round(duration_s * fs)))
    n_release = int(round(RELEASE_S * fs))
    t = np.arange(n_total + n_release) / fs

    tone = (
        1.00 * np.sin(2 * np.pi * f0 * t)
        + 0.40 * np.sin(2 * np.pi * 2 * f0 * t)
        + 0.20 * np.sin(2 * np.pi * 3 * f0 * t)
    )

    env = np.zeros_like(t)
    n_attack = max(1, int(round(ATTACK_S * fs)))
    n_attack = min(n_attack, n_total)
    env[:n_attack] = np.linspace(0.0, 1.0, n_attack)
    n_decay = n_total - n_attack
    if n_decay > 0:
        decay_t = np.arange(n_decay) / fs
        env[n_attack:n_total] = SUSTAIN_LEVEL + (1.0 - SUSTAIN_LEVEL) * np.exp(
            -decay_t / DECAY_TAU_S
        )
    if n_release > 0:
        last_level = env[n_total - 1]
        env[n_total:] = np.linspace(last_level, 0.0, n_release)

    return tone * env


def _synthesize_with_envelope(midi: pretty_midi.PrettyMIDI, fs: int) -> np.ndarray:
    end_time = midi.get_end_time() + RELEASE_S + 0.1
    audio = np.zeros(int(round(end_time * fs)) + 1, dtype=np.float64)
    for inst in midi.instruments:
        if inst.is_drum:
            continue
        for note in inst.notes:
            tone = _render_note(note.pitch, note.end - note.start, fs)
            gain = note.velocity / 127.0
            start_idx = int(round(note.start * fs))
            end_idx = start_idx + len(tone)
            if end_idx > len(audio):
                audio = np.concatenate(
                    [audio, np.zeros(end_idx - len(audio) + 1, dtype=np.float64)]
                )
            audio[start_idx:end_idx] += tone * gain
    return audio


def synthesize_midi_to_wav(midi_path: Path, wav_path: Path, fs: int = 22050) -> Path:
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    audio = _synthesize_with_envelope(midi, fs)
    # Deterministic noise so eval runs are reproducible.
    rng = np.random.default_rng(seed=0xBA55)
    audio = audio + rng.standard_normal(len(audio)) * NOISE_AMPLITUDE
    peak = float(np.max(np.abs(audio))) if audio.size else 1.0
    if peak > 0:
        audio = audio / peak * 0.9
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(wav_path), audio.astype(np.float32), fs, subtype="PCM_16")
    return wav_path
