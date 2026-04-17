"""Bass stem isolation using Demucs."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def isolate_bass(input_audio: Path, output_dir: Path) -> Path:
    """Run Demucs on input_audio and return the path to the isolated bass stem.

    Demucs downloads model weights (~1GB) on first run into the user's torch cache.
    Output layout: {output_dir}/htdemucs/{stem_name}/bass.wav
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "demucs.separate",
        "-n",
        "htdemucs",
        "--two-stems",
        "bass",
        "-o",
        str(output_dir),
        str(input_audio),
    ]
    subprocess.run(cmd, check=True)

    stem_folder = output_dir / "htdemucs" / input_audio.stem
    bass_path = stem_folder / "bass.wav"
    if not bass_path.exists():
        raise FileNotFoundError(f"Demucs did not produce bass stem at {bass_path}")
    return bass_path
