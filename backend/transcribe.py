"""MIDI transcription of an isolated bass stem using Spotify Basic Pitch.

After Basic Pitch returns its raw MIDI, we (a) run librosa beat tracking
on the same audio to get a real tempo + beat grid — Basic Pitch otherwise
stamps a default 120 BPM on every output, which wrecks downstream
quantization — and (b) snap each note's onset to the nearest subdivision
of that grid before writing the MIDI. This is what makes the transcribed
MIDI actually line up with the audio on playback.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import librosa
import numpy as np
import pretty_midi
from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict

from quantize_snap import snap_to_beat_grid


def _apply_beat_grid(
    midi_data: pretty_midi.PrettyMIDI,
    audio_path: Path,
) -> None:
    """Overwrite the tempo map + snap onsets to the detected beat grid.

    Mutates ``midi_data`` in place. Silently leaves the MIDI unchanged if
    beat tracking fails or produces too few beats to be useful.
    """
    try:
        y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    except Exception:
        return

    if beat_frames.size < 4:
        return

    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    tempo_bpm = float(np.atleast_1d(tempo).ravel()[0])
    if not np.isfinite(tempo_bpm) or tempo_bpm <= 0:
        return

    # pretty_midi stores tempo changes internally; the supported way to
    # replace them is to clear the private buffers and re-initialise.
    midi_data._tick_scales = [(0, 60.0 / (tempo_bpm * midi_data.resolution))]
    midi_data._update_tick_to_time(0)

    # Snap every note's start onto the grid; preserve duration to keep
    # offsets consistent with onsets.
    for inst in midi_data.instruments:
        if inst.is_drum:
            continue
        starts = [note.start for note in inst.notes]
        # Allow up to a quarter beat of correction; farther than that the
        # onset is either (a) genuinely far from the grid and probably
        # spurious, or (b) close to a grid position that happens to lie on
        # the far side of another — snapping either way hurts more than it
        # helps.
        max_shift = 0.25 * (60.0 / tempo_bpm)
        snapped = snap_to_beat_grid(starts, beat_times, max_shift_s=max_shift)
        for note, new_start in zip(inst.notes, snapped):
            duration = note.end - note.start
            note.start = new_start
            note.end = new_start + duration


def transcribe_to_midi(
    bass_audio: Path, output_dir: Path
) -> tuple[Path, list[tuple[float, float, int, float, Any]]]:
    """Run Basic Pitch on the bass stem.

    Returns (midi_path, note_events). Each note_event is
    (start_time_s, end_time_s, pitch_midi, amplitude, pitch_bends);
    amplitude in [0, 1] is Basic Pitch's per-note confidence.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    _model_output, midi_data, note_events = predict(
        str(bass_audio),
        model_or_model_path=ICASSP_2022_MODEL_PATH,
    )

    _apply_beat_grid(midi_data, bass_audio)

    midi_path = output_dir / f"{bass_audio.stem}_basic_pitch.mid"
    midi_data.write(str(midi_path))
    return midi_path, note_events
