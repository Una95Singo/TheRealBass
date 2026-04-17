"""MIDI transcription of an isolated bass stem using Spotify Basic Pitch."""
from __future__ import annotations

from pathlib import Path

from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict_and_save


def transcribe_to_midi(bass_audio: Path, output_dir: Path) -> Path:
    """Run Basic Pitch on the bass stem. Returns the generated .mid path."""
    output_dir.mkdir(parents=True, exist_ok=True)

    predict_and_save(
        audio_path_list=[str(bass_audio)],
        output_directory=str(output_dir),
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False,
        model_or_model_path=ICASSP_2022_MODEL_PATH,
    )

    midi_path = output_dir / f"{bass_audio.stem}_basic_pitch.mid"
    if not midi_path.exists():
        raise FileNotFoundError(f"Basic Pitch did not produce MIDI at {midi_path}")
    return midi_path
