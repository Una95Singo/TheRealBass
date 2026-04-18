"""MIDI transcription of an isolated bass stem using Spotify Basic Pitch."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict


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

    midi_path = output_dir / f"{bass_audio.stem}_basic_pitch.mid"
    midi_data.write(str(midi_path))
    return midi_path, note_events
