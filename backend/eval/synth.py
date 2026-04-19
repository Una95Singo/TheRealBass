"""MIDI -> WAV synthesizer for the AMT harness.

Uses pretty_midi's built-in sine-wave synthesizer so there's no SoundFont
dependency. The resulting audio isn't realistic bass timbre, but that's
fine — we're measuring whether the pipeline finds the right notes at the
right times, not whether it likes the sound.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pretty_midi
import soundfile as sf


def synthesize_midi_to_wav(midi_path: Path, wav_path: Path, fs: int = 22050) -> Path:
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    audio = midi.synthesize(fs=fs)
    # Normalize to -1..1 so the AMT model has headroom.
    peak = float(np.max(np.abs(audio))) if audio.size else 1.0
    if peak > 0:
        audio = audio / peak * 0.9
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(wav_path), audio, fs, subtype="PCM_16")
    return wav_path
