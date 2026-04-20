"""Per-clip eval artifacts: piano-roll PNG + stereo A/B WAV + metrics JSON.

The point of this module is mobile review. After every eval run the user
gets a folder of PNGs that render inline in the GitHub mobile app and
WAVs that play in any phone's audio app — no laptop, no special tools,
no spinning up the dev server. Three artifacts per clip:

- ``roll.png`` — CQT spectrogram of the input audio with a GT-vs-EST
  difference piano roll stacked underneath. Blue cells are notes the
  ground truth has but the pipeline missed; red cells are notes the
  pipeline emitted that the ground truth doesn't have. A clean run is
  mostly transparent.
- ``ab.wav`` — stereo mix. Left channel is the input audio (or the GT
  rendered to audio if the input is the synth corpus); right channel is
  the predicted MIDI rendered through the same envelope synth used for
  the corpus. Plug in earbuds, listen for ~5 seconds — any timing slip
  or octave error is immediately audible.
- ``metrics.json`` — the three mir_eval F1 numbers, machine-readable for
  CI gating.

Pure-function module; the eval harness wires it into ``run_eval.py``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pretty_midi  # noqa: E402
import soundfile as sf  # noqa: E402

import librosa  # noqa: E402
import librosa.display  # noqa: E402

from eval.synth import _synthesize_with_envelope  # noqa: E402

PIANO_ROLL_LO = 24  # C1 — well below 4-string bass low E (28)
PIANO_ROLL_HI = 72  # C5 — well above any reasonable bass note
HOP_LENGTH = 512


def _piano_roll(midi_path: Path, fs_pr: float, total_frames: int) -> np.ndarray:
    """Get a (pitch x frames) binary piano roll trimmed to bass register."""
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    pr = midi.get_piano_roll(fs=fs_pr)  # (128, frames)
    if pr.shape[1] < total_frames:
        pr = np.pad(pr, ((0, 0), (0, total_frames - pr.shape[1])))
    else:
        pr = pr[:, :total_frames]
    return (pr[PIANO_ROLL_LO:PIANO_ROLL_HI] > 0).astype(np.int8)


def write_clip_artifacts(
    *,
    clip_name: str,
    audio_path: Path,
    gt_midi: Path,
    est_midi: Path,
    metrics: dict[str, Any],
    out_dir: Path,
    sr: int = 22050,
) -> dict[str, Path]:
    """Write roll.png + ab.wav + metrics.json for one clip. Returns the paths."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Audio I/O ---
    y, sr = librosa.load(str(audio_path), sr=sr, mono=True)
    duration_s = len(y) / sr
    fs_pr = sr / HOP_LENGTH
    total_frames = int(np.ceil(duration_s * fs_pr))

    # --- Piano roll diff (GT vs EST) ---
    pr_gt = _piano_roll(gt_midi, fs_pr, total_frames)
    pr_est = _piano_roll(est_midi, fs_pr, total_frames)
    diff = pr_est - pr_gt  # +1 = false positive, -1 = miss, 0 = agree

    # --- CQT for the spectrogram panel ---
    n_bins = (PIANO_ROLL_HI - PIANO_ROLL_LO) * 2  # 2 bins/semitone for resolution
    fmin = librosa.note_to_hz(pretty_midi.note_number_to_name(PIANO_ROLL_LO))
    cqt = np.abs(
        librosa.cqt(
            y, sr=sr, hop_length=HOP_LENGTH, fmin=fmin,
            n_bins=n_bins, bins_per_octave=24,
        )
    )
    cqt_db = librosa.amplitude_to_db(cqt, ref=np.max)

    # --- Render PNG ---
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    librosa.display.specshow(
        cqt_db, sr=sr, hop_length=HOP_LENGTH, x_axis="time",
        y_axis="cqt_note", fmin=fmin, bins_per_octave=24, ax=axes[0],
    )
    axes[0].set_title(f"{clip_name} — CQT (input audio)")

    # Trim diff to the displayed time range
    diff_trim = diff[:, : cqt.shape[1]]
    axes[1].imshow(
        diff_trim, aspect="auto", origin="lower", cmap="coolwarm",
        vmin=-1, vmax=1,
        extent=[0, cqt.shape[1] * HOP_LENGTH / sr, PIANO_ROLL_LO, PIANO_ROLL_HI],
        interpolation="nearest",
    )
    axes[1].set_title(
        f"GT vs EST diff — blue = miss, red = false positive   |   "
        f"onset F1 {metrics.get('onset_f1', 0):.3f}, "
        f"+pitch {metrics.get('onset_pitch_f1', 0):.3f}, "
        f"+offset {metrics.get('onset_pitch_offset_f1', 0):.3f}   |   "
        f"GT {metrics.get('n_gt', 0)}, EST {metrics.get('n_est', 0)}"
    )
    axes[1].set_ylabel("MIDI pitch")
    axes[1].set_xlabel("time (s)")
    fig.tight_layout()

    png_path = out_dir / "roll.png"
    fig.savefig(png_path, dpi=120, bbox_inches="tight")
    plt.close(fig)

    # --- Stereo A/B WAV ---
    est_audio = _synthesize_with_envelope(pretty_midi.PrettyMIDI(str(est_midi)), sr)
    n = min(len(y), len(est_audio))
    left = y[:n].astype(np.float64)
    right = est_audio[:n].astype(np.float64)
    # Independent normalisation so neither channel dominates.
    for ch in (left, right):
        peak = float(np.max(np.abs(ch))) if ch.size else 1.0
        if peak > 0:
            ch *= 0.9 / peak
    stereo = np.stack([left, right], axis=1).astype(np.float32)
    wav_path = out_dir / "ab.wav"
    sf.write(str(wav_path), stereo, sr, subtype="PCM_16")

    # --- Metrics JSON ---
    metrics_path = out_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))

    return {"png": png_path, "wav": wav_path, "metrics": metrics_path}


def write_run_index(
    *,
    run_dir: Path,
    rows: list[tuple[str, dict[str, Any]]],
    means: dict[str, float],
) -> Path:
    """Write index.md and summary.json at the run root."""
    summary = {
        "n_clips": len(rows),
        "means": means,
        "clips": {name: m for name, m in rows},
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    lines = [
        f"# Eval run — {run_dir.name}",
        "",
        "Mobile review checklist:",
        "- [ ] mean onset F1 ≥ baseline (see prior run for the number)",
        "- [ ] no clip regresses by > 0.05 F1",
        "- [ ] tap two worst clips, scan their `roll.png` (blue = miss, red = false positive)",
        "- [ ] download one `ab.wav`, listen on earbuds (L = input audio, R = predicted MIDI)",
        "",
        f"**Mean across {len(rows)} clips:** "
        f"onset {means.get('onset_f1', 0):.3f}  |  "
        f"+pitch {means.get('onset_pitch_f1', 0):.3f}  |  "
        f"+offset {means.get('onset_pitch_offset_f1', 0):.3f}",
        "",
        "| clip | onset F1 | +pitch F1 | +offset F1 | n_gt | n_est | review |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for name, m in rows:
        lines.append(
            f"| {name} | {m.get('onset_f1', 0):.3f} | "
            f"{m.get('onset_pitch_f1', 0):.3f} | "
            f"{m.get('onset_pitch_offset_f1', 0):.3f} | "
            f"{m.get('n_gt', 0)} | {m.get('n_est', 0)} | "
            f"![]({name}/roll.png) [audio]({name}/ab.wav) |"
        )
    lines.append("")
    index_path = run_dir / "index.md"
    index_path.write_text("\n".join(lines))
    return index_path


__all__ = ["write_clip_artifacts", "write_run_index"]
