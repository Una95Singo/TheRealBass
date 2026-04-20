"""AMT quality-benchmark CLI.

For each ground-truth MIDI in eval/corpus/, synthesize to WAV, run the
current pipeline's transcribe_to_midi on it, and score the output against
the ground truth using mir_eval.transcription.precision_recall_f1_overlap
(the MIREX onset/pitch/offset scoring routine).

Prints a per-clip + mean F1 table, and (when ``--artifacts-out`` is
given, default ``<repo>/artifacts/eval/<timestamp>``) writes per-clip
PNG diff rolls + stereo A/B WAVs + a markdown index for mobile review.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np  # noqa: E402
import pretty_midi  # noqa: E402
from mir_eval import transcription  # noqa: E402

from eval.artifacts import write_clip_artifacts, write_run_index  # noqa: E402
from eval.synth import synthesize_midi_to_wav  # noqa: E402
from transcribe import transcribe_to_midi  # noqa: E402

CORPUS_DIR = HERE / "corpus"
DEFAULT_ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "eval"


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


def run_pipeline(wav_path: Path, out_dir: Path, *, octave_check: bool = False) -> Path:
    """Run the pipeline-under-test on a WAV, return path to produced MIDI."""
    midi_path, _ = transcribe_to_midi(wav_path, out_dir, octave_check=octave_check)
    return midi_path


def _load_manifest(corpus_dir: Path) -> list[tuple[Path, Path, dict]] | None:
    """Return [(audio_path, gt_midi_path, entry_dict), ...] from manifest.json
    if present. None means "no manifest, use synth-from-MIDI fallback"."""
    manifest_path = corpus_dir / "manifest.json"
    if not manifest_path.is_file():
        return None
    data = json.loads(manifest_path.read_text())
    out: list[tuple[Path, Path, dict]] = []
    for entry in data.get("clips", []):
        audio = corpus_dir / entry["audio"]
        midi = corpus_dir / entry["midi"]
        if not audio.is_file():
            print(f"  [skip] {entry['slug']}: audio missing ({audio})",
                  file=sys.stderr)
            continue
        if not midi.is_file():
            print(f"  [skip] {entry['slug']}: midi missing ({midi})",
                  file=sys.stderr)
            continue
        out.append((audio, midi, entry))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=CORPUS_DIR)
    parser.add_argument("--only", type=str, default=None,
                        help="Substring match on clip name to evaluate just one.")
    parser.add_argument("--artifacts-out", type=Path, default=None,
                        help=("Root directory for per-clip eval artifacts. "
                              f"Default: {DEFAULT_ARTIFACTS_ROOT}/<timestamp>"))
    parser.add_argument("--no-artifacts", action="store_true",
                        help="Skip writing the PNG/WAV/markdown artifact bundle.")
    parser.add_argument("--octave-check", action="store_true",
                        help="Run CREPE octave-check QC on Basic Pitch output. "
                             "Adds ~50 ms per note; off by default.")
    args = parser.parse_args()

    # Real-corpus mode: corpus dir contains manifest.json and we eval
    # against the listed real audio. Synth mode: glob *.mid and synthesise.
    manifest_clips = _load_manifest(args.corpus)
    if manifest_clips is not None:
        if args.only:
            manifest_clips = [
                t for t in manifest_clips if args.only in t[2].get("slug", "")
            ]
        if not manifest_clips:
            print(f"no clips matched in {args.corpus}/manifest.json",
                  file=sys.stderr)
            return 1
    else:
        clips = sorted(p for p in args.corpus.glob("*.mid"))
        if args.only:
            clips = [p for p in clips if args.only in p.stem]
        if not clips:
            print(f"no MIDI files under {args.corpus}", file=sys.stderr)
            return 1

    header = f"{'clip':<24}  {'onset':>7}  {'+pitch':>7}  {'+offset':>7}  {'n_gt':>5}  {'n_est':>5}"
    print(header)
    print("-" * len(header))

    if args.no_artifacts:
        artifact_root = None
    else:
        run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        artifact_root = (args.artifacts_out or DEFAULT_ARTIFACTS_ROOT) / run_id
        artifact_root.mkdir(parents=True, exist_ok=True)

    rows: list[tuple[str, dict[str, float]]] = []
    with tempfile.TemporaryDirectory(prefix="therealbass-eval-") as tmpdir:
        tmp = Path(tmpdir)
        if manifest_clips is not None:
            jobs = [(audio, gt, entry["slug"]) for audio, gt, entry in manifest_clips]
        else:
            jobs = []
            for gt in clips:
                wav = synthesize_midi_to_wav(gt, tmp / f"{gt.stem}.wav")
                jobs.append((wav, gt, gt.stem))

        for wav, gt, name in jobs:
            est_dir = tmp / f"{name}_out"
            est_dir.mkdir(exist_ok=True)
            try:
                est_midi = run_pipeline(wav, est_dir, octave_check=args.octave_check)
            except Exception as exc:
                print(f"{name:<24}  FAILED: {exc}")
                continue
            metrics = score_one(gt, est_midi)
            rows.append((name, metrics))
            print(
                f"{name:<24}  {metrics['onset_f1']:>7.3f}  "
                f"{metrics['onset_pitch_f1']:>7.3f}  "
                f"{metrics['onset_pitch_offset_f1']:>7.3f}  "
                f"{metrics['n_gt']:>5}  {metrics['n_est']:>5}"
            )
            if artifact_root is not None:
                try:
                    write_clip_artifacts(
                        clip_name=name,
                        audio_path=wav,
                        gt_midi=gt,
                        est_midi=est_midi,
                        metrics=metrics,
                        out_dir=artifact_root / name,
                    )
                except Exception as exc:  # artifacts are best-effort
                    print(f"  [artifacts] {name}: {exc}", file=sys.stderr)

    means: dict[str, float] = {}
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

    if artifact_root is not None and rows:
        index_path = write_run_index(run_dir=artifact_root, rows=rows, means=means)
        print(f"\nartifacts: {index_path.parent}")
        print(f"open on mobile: {index_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
