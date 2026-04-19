"""AMT quality-benchmark CLI.

For each ground-truth MIDI in eval/corpus/, synthesize to WAV, run the
current pipeline's transcribe_to_midi on it, and score the output against
the ground truth using mir_eval.transcription.precision_recall_f1_overlap
(the MIREX onset/pitch/offset scoring routine).

Prints a per-clip + mean F1 table.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np  # noqa: E402
import pretty_midi  # noqa: E402
from mir_eval import transcription  # noqa: E402

from eval.synth import synthesize_midi_to_wav  # noqa: E402
from transcribe import transcribe_to_midi  # noqa: E402

CORPUS_DIR = HERE / "corpus"


def midi_to_mir_eval_arrays(midi_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Extract (intervals, pitches_hz) from a MIDI file for mir_eval."""
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    intervals: list[tuple[float, float]] = []
    pitches: list[float] = []
    for inst in midi.instruments:
        if inst.is_drum:
            continue
        for note in inst.notes:
            if note.end <= note.start:
                continue
            intervals.append((note.start, note.end))
            pitches.append(pretty_midi.note_number_to_hz(note.pitch))
    if not intervals:
        return np.zeros((0, 2)), np.zeros(0)
    return np.array(intervals), np.array(pitches)


def score_one(gt_midi: Path, est_midi: Path) -> dict[str, float]:
    gt_intervals, gt_pitches = midi_to_mir_eval_arrays(gt_midi)
    est_intervals, est_pitches = midi_to_mir_eval_arrays(est_midi)

    # Onset-only (pitch ignored — set tolerance very wide so pitch doesn't gate).
    onset_p, onset_r, onset_f, _ = transcription.precision_recall_f1_overlap(
        gt_intervals, gt_pitches, est_intervals, est_pitches,
        onset_tolerance=0.05, pitch_tolerance=1e9, offset_ratio=None,
    )
    # Onset + pitch (±50 cents).
    op_p, op_r, op_f, _ = transcription.precision_recall_f1_overlap(
        gt_intervals, gt_pitches, est_intervals, est_pitches,
        onset_tolerance=0.05, pitch_tolerance=50.0, offset_ratio=None,
    )
    # Onset + pitch + offset.
    opo_p, opo_r, opo_f, _ = transcription.precision_recall_f1_overlap(
        gt_intervals, gt_pitches, est_intervals, est_pitches,
        onset_tolerance=0.05, pitch_tolerance=50.0, offset_ratio=0.2,
    )
    return {
        "onset_f1": float(onset_f),
        "onset_pitch_f1": float(op_f),
        "onset_pitch_offset_f1": float(opo_f),
        "n_gt": int(len(gt_intervals)),
        "n_est": int(len(est_intervals)),
    }


def run_pipeline(wav_path: Path, out_dir: Path) -> Path:
    """Run the pipeline-under-test on a WAV, return path to produced MIDI."""
    midi_path, _ = transcribe_to_midi(wav_path, out_dir)
    return midi_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=CORPUS_DIR)
    parser.add_argument("--only", type=str, default=None,
                        help="Substring match on clip name to evaluate just one.")
    args = parser.parse_args()

    clips = sorted(p for p in args.corpus.glob("*.mid"))
    if args.only:
        clips = [p for p in clips if args.only in p.stem]
    if not clips:
        print(f"no MIDI files under {args.corpus}", file=sys.stderr)
        return 1

    header = f"{'clip':<24}  {'onset':>7}  {'+pitch':>7}  {'+offset':>7}  {'n_gt':>5}  {'n_est':>5}"
    print(header)
    print("-" * len(header))

    rows: list[tuple[str, dict[str, float]]] = []
    with tempfile.TemporaryDirectory(prefix="therealbass-eval-") as tmpdir:
        tmp = Path(tmpdir)
        for gt in clips:
            wav = synthesize_midi_to_wav(gt, tmp / f"{gt.stem}.wav")
            est_dir = tmp / f"{gt.stem}_out"
            est_dir.mkdir()
            try:
                est_midi = run_pipeline(wav, est_dir)
            except Exception as exc:
                print(f"{gt.stem:<24}  FAILED: {exc}")
                continue
            metrics = score_one(gt, est_midi)
            rows.append((gt.stem, metrics))
            print(
                f"{gt.stem:<24}  {metrics['onset_f1']:>7.3f}  "
                f"{metrics['onset_pitch_f1']:>7.3f}  "
                f"{metrics['onset_pitch_offset_f1']:>7.3f}  "
                f"{metrics['n_gt']:>5}  {metrics['n_est']:>5}"
            )

    if rows:
        means = {
            key: sum(m[key] for _, m in rows) / len(rows)
            for key in ("onset_f1", "onset_pitch_f1", "onset_pitch_offset_f1")
        }
        print("-" * len(header))
        print(
            f"{'MEAN':<24}  {means['onset_f1']:>7.3f}  "
            f"{means['onset_pitch_f1']:>7.3f}  "
            f"{means['onset_pitch_offset_f1']:>7.3f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
