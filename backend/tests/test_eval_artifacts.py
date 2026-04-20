"""Smoke tests for the per-clip eval artifact writer.

Skipped when the heavy audio stack (numpy / librosa / matplotlib /
pretty_midi / soundfile) isn't installed in the active venv — these
tests run from ``backend/.venv`` (the same env the eval CLI runs in),
not from the lighter ``backend/.venv-test``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pretty_midi = pytest.importorskip("pretty_midi")
sf = pytest.importorskip("soundfile")
pytest.importorskip("librosa")
pytest.importorskip("matplotlib")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from eval.artifacts import write_clip_artifacts, write_run_index  # noqa: E402


def _toy_midi(path: Path, pitches: list[int]) -> Path:
    midi = pretty_midi.PrettyMIDI(initial_tempo=120.0)
    inst = pretty_midi.Instrument(program=33)
    for i, p in enumerate(pitches):
        inst.notes.append(
            pretty_midi.Note(velocity=90, pitch=p, start=i * 0.5, end=i * 0.5 + 0.4)
        )
    midi.instruments.append(inst)
    midi.write(str(path))
    return path


def _toy_wav(path: Path, sr: int = 22050, duration_s: float = 2.5) -> Path:
    n = int(sr * duration_s)
    y = 0.3 * np.sin(2 * np.pi * 110 * np.arange(n) / sr)
    sf.write(str(path), y.astype(np.float32), sr)
    return path


def test_write_clip_artifacts_emits_three_files(tmp_path: Path):
    gt = _toy_midi(tmp_path / "gt.mid", [40, 43, 45, 47])
    est = _toy_midi(tmp_path / "est.mid", [40, 43, 45, 48])  # one wrong note
    wav = _toy_wav(tmp_path / "in.wav")

    metrics = {
        "onset_f1": 0.9, "onset_pitch_f1": 0.75,
        "onset_pitch_offset_f1": 0.6, "n_gt": 4, "n_est": 4,
    }
    out_dir = tmp_path / "bundle"
    paths = write_clip_artifacts(
        clip_name="toy", audio_path=wav, gt_midi=gt, est_midi=est,
        metrics=metrics, out_dir=out_dir,
    )

    assert paths["png"].exists() and paths["png"].stat().st_size > 1000
    assert paths["wav"].exists()
    # Stereo, two channels.
    audio, sr = sf.read(str(paths["wav"]))
    assert audio.ndim == 2 and audio.shape[1] == 2
    assert sr == 22050
    # Both channels should carry signal.
    assert np.max(np.abs(audio[:, 0])) > 0.1
    assert np.max(np.abs(audio[:, 1])) > 0.0  # synth may be quiet but non-zero
    # Metrics round-trip.
    loaded = json.loads(paths["metrics"].read_text())
    assert loaded["onset_f1"] == 0.9


def test_write_run_index_lists_every_clip(tmp_path: Path):
    rows = [
        ("alpha", {"onset_f1": 0.8, "onset_pitch_f1": 0.7,
                   "onset_pitch_offset_f1": 0.5, "n_gt": 10, "n_est": 12}),
        ("beta", {"onset_f1": 0.6, "onset_pitch_f1": 0.5,
                  "onset_pitch_offset_f1": 0.3, "n_gt": 20, "n_est": 18}),
    ]
    means = {"onset_f1": 0.7, "onset_pitch_f1": 0.6, "onset_pitch_offset_f1": 0.4}
    index = write_run_index(run_dir=tmp_path, rows=rows, means=means)

    text = index.read_text()
    assert "alpha" in text and "beta" in text
    assert "alpha/roll.png" in text  # mobile-renderable inline image link
    assert "alpha/ab.wav" in text
    assert "Mean across 2 clips" in text

    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["n_clips"] == 2
    assert "alpha" in summary["clips"]
