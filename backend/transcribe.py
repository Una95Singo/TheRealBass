"""MIDI transcription of an isolated bass stem.

Pipeline: onset detection (``librosa.onset.onset_detect`` with backtracking
to the nearest energy minimum) segments the stem into note windows, then
``librosa.pyin`` extracts the fundamental frequency inside each window
and the median voiced pitch becomes the note. Finally we run beat
tracking on the same audio to stamp the MIDI with a real tempo and snap
each onset onto the nearest beat-grid subdivision — Basic Pitch's
default output was consistently mis-quantized because it wrote a fixed
120 BPM regardless of the song's real tempo, which wrecked downstream
music21 quantization.

Monophonic bass is pYIN's sweet spot, which is why this replaces the
earlier Basic Pitch run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import librosa
import numpy as np
import pretty_midi

from quantize_snap import snap_to_beat_grid


SAMPLE_RATE = 22050
PYIN_FMIN = 30.0   # ~B0; below the lowest practical 4-string bass (E1 ≈ 41 Hz)
PYIN_FMAX = 500.0  # ~B4; covers slap / upper-register fills
# After each onset we skip a short attack window before sampling pitch —
# plucks and slaps contain broadband transient energy that confuses pYIN's
# probabilistic voicing.
PITCH_SKIP_S = 0.02
# Keep the pitch window small so fast figures (16ths @ 120 BPM ≈ 125 ms)
# still resolve; pYIN's median is stable with ~100 ms of voiced signal.
PITCH_WIN_S = 0.10
# Voicing threshold for accepting a frame's f0. Looser than librosa's
# default (0.5) because the onset detector has already told us a note is
# present — we just need the cleanest f0 estimate, not a detection gate.
VOICED_THRESH = 0.3
MIN_PITCH_AUDIO_S = 0.03  # need at least ~30 ms to get a stable pYIN read
DEFAULT_VELOCITY = 90
# Cap the beat-grid snap well under mir_eval's 50 ms onset tolerance. Change
# 1 of the rhythm-fix plan makes this adaptive; for change 0 we only lift
# the literal into a constant so the debug artifact can record it.
SNAP_MAX_SHIFT_S = 0.03


def _pitch_for_window(
    y: np.ndarray, sr: int, t_start: float, t_end: float
) -> tuple[int, float] | None:
    """Run pYIN over [t_start, t_end] and return (midi_pitch, confidence).

    Confidence is the median voicing probability across frames that pYIN
    deemed voiced; returned in [0, 1] so it slots straight into the
    existing Basic-Pitch-shaped note_events confidence plumbing.
    """
    i0 = max(0, int(t_start * sr))
    i1 = min(len(y), int(t_end * sr))
    if i1 - i0 < int(MIN_PITCH_AUDIO_S * sr):
        return None
    segment = y[i0:i1]
    try:
        f0, _voiced_flag, voiced_prob = librosa.pyin(
            segment, fmin=PYIN_FMIN, fmax=PYIN_FMAX, sr=sr, fill_na=np.nan
        )
    except Exception:
        return None
    mask = np.isfinite(f0) & (voiced_prob >= VOICED_THRESH)
    if not np.any(mask):
        return None
    midi_pitch = int(round(float(librosa.hz_to_midi(float(np.median(f0[mask]))))))
    if not (0 <= midi_pitch <= 127):
        return None
    confidence = float(np.clip(np.median(voiced_prob[mask]), 0.0, 1.0))
    return midi_pitch, confidence


def _detect_onsets(y: np.ndarray, sr: int, duration: float) -> list[float]:
    """Return onset times in seconds, with t=0 prepended when needed.

    We prepend 0.0 if the first detected onset is more than 50 ms in —
    synthesised fixtures start exactly on the downbeat and the detector
    occasionally misses the very first transient, which silently drops
    the first note.
    """
    onset_frames = librosa.onset.onset_detect(
        y=y, sr=sr, backtrack=True, units="frames"
    )
    times = librosa.frames_to_time(onset_frames, sr=sr).tolist()
    if not times or times[0] > 0.05:
        times = [0.0] + times
    # Guard against the detector emitting an onset past the audio end.
    return [t for t in times if t < duration]


def _apply_beat_grid(
    midi_data: pretty_midi.PrettyMIDI,
    y: np.ndarray,
    sr: int,
) -> dict[str, Any]:
    """Overwrite the tempo map + snap onsets to the detected beat grid.

    Mutates ``midi_data`` in place. Silently leaves the MIDI unchanged if
    beat tracking fails or produces too few beats to be useful. Returns
    a dict describing what the snap did so callers can emit diagnostics;
    keys are absent when the corresponding step was skipped.
    """
    info: dict[str, Any] = {}
    try:
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    except Exception:
        return info

    if beat_frames.size < 4:
        return info

    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    tempo_bpm = float(np.atleast_1d(tempo).ravel()[0])
    if not np.isfinite(tempo_bpm) or tempo_bpm <= 0:
        return info

    # pretty_midi stores tempo changes internally; the supported way to
    # replace them is to clear the private buffers and re-initialise.
    midi_data._tick_scales = [(0, 60.0 / (tempo_bpm * midi_data.resolution))]
    midi_data._update_tick_to_time(0)

    info["tempo_bpm"] = tempo_bpm
    info["beat_times"] = beat_times
    info["snap_max_shift_s"] = SNAP_MAX_SHIFT_S

    for inst in midi_data.instruments:
        if inst.is_drum:
            continue
        starts = [note.start for note in inst.notes]
        # Cap corrections well under the mir_eval onset tolerance (50 ms).
        # At this size the snap only cleans up jitter — onsets that are
        # already close to truth stay put, and onsets far off the grid
        # (likely spurious) don't get yanked into a wrong slot.
        snapped = snap_to_beat_grid(starts, beat_times, max_shift_s=SNAP_MAX_SHIFT_S)
        for note, new_start in zip(inst.notes, snapped):
            duration = note.end - note.start
            note.start = new_start
            note.end = new_start + duration
    return info


def transcribe_to_midi(
    bass_audio: Path,
    output_dir: Path,
    *,
    return_debug: bool = False,
) -> (
    tuple[Path, list[tuple[float, float, int, float, Any]]]
    | tuple[Path, list[tuple[float, float, int, float, Any]], dict[str, Any]]
):
    """Transcribe an isolated bass stem to MIDI.

    Returns (midi_path, note_events). Each note_event is
    (start_time_s, end_time_s, pitch_midi, confidence, pitch_bends);
    confidence in [0, 1] is pYIN's median voicing probability for the
    note, kept in the same shape Basic Pitch used so the confidence
    plumbing downstream didn't have to change.

    If ``return_debug`` is True, returns an additional ``debug`` dict
    with pre-snap onset times, post-snap starts, placeholders for
    release times, and beat-track metadata. Used by main.py to write
    a per-upload JSON artifact for offline review.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    y, sr = librosa.load(str(bass_audio), sr=SAMPLE_RATE, mono=True)
    duration = len(y) / sr if sr else 0.0

    onset_times = _detect_onsets(y, sr, duration)

    midi_data = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=33)  # Electric Bass (finger)
    note_events: list[tuple[float, float, int, float, Any]] = []
    # Pre-snap onset time per accepted note (indices align with instrument.notes).
    kept_raw_onsets: list[float] = []

    for i, t_start in enumerate(onset_times):
        t_end = onset_times[i + 1] if i + 1 < len(onset_times) else duration
        if t_end <= t_start:
            continue
        win_start = t_start + PITCH_SKIP_S
        win_end = min(t_end, win_start + PITCH_WIN_S)
        result = _pitch_for_window(y, sr, win_start, win_end)
        if result is None:
            continue
        pitch, confidence = result
        instrument.notes.append(
            pretty_midi.Note(
                velocity=DEFAULT_VELOCITY,
                pitch=pitch,
                start=float(t_start),
                end=float(t_end),
            )
        )
        note_events.append((float(t_start), float(t_end), pitch, confidence, []))
        kept_raw_onsets.append(float(t_start))

    midi_data.instruments.append(instrument)
    snap_info = _apply_beat_grid(midi_data, y, sr)

    # Re-sync note_events onsets with the snapped MIDI onsets so the
    # downstream confidence matcher (±0.3 s tolerance) keeps lining up.
    snapped_notes = midi_data.instruments[0].notes if midi_data.instruments else []
    if len(snapped_notes) == len(note_events):
        note_events = [
            (n.start, n.end, n.pitch, ne[3], ne[4])
            for n, ne in zip(snapped_notes, note_events)
        ]

    midi_path = output_dir / f"{bass_audio.stem}.mid"
    midi_data.write(str(midi_path))

    if not return_debug:
        return midi_path, note_events

    debug: dict[str, Any] = {
        "sample_rate": int(sr) if sr else SAMPLE_RATE,
        "audio_duration_s": float(duration),
        "raw_onsets_all": [float(t) for t in onset_times],
        "raw_onsets_kept": list(kept_raw_onsets),
        "snapped_starts": [float(n.start) for n in snapped_notes],
        "note_ends": [float(n.end) for n in snapped_notes],
        "pitches": [int(n.pitch) for n in snapped_notes],
        # Release detection lands in change 4; leave an empty placeholder
        # so artifact consumers see the same schema across versions.
        "releases": [None] * len(snapped_notes),
        "confidences": [float(ne[3]) for ne in note_events],
        "tempo_bpm": snap_info.get("tempo_bpm"),
        "beat_times": snap_info.get("beat_times", []),
        "snap_max_shift_s": snap_info.get("snap_max_shift_s"),
    }
    return midi_path, note_events, debug
