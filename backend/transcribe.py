"""MIDI transcription of an isolated bass stem.

Pipeline: Spotify Basic Pitch (CRNN, ICASSP 2022) emits note events
directly from the audio. We constrain the frequency range to the bass
register so the model can't hallucinate guitar-range notes, then run
librosa beat tracking on the same audio to overwrite Basic Pitch's
default 120 BPM tempo and snap each onset onto the detected beat grid
— Basic Pitch's onsets are accurate to ~25 ms but the resulting MIDI
still benefits from tempo-locked quantization for downstream music21.

Replaces an earlier librosa+pYIN per-window pipeline. pYIN was returning
its ``fmin`` floor (~30 Hz → E1) on noisy or quiet windows, producing
real-audio runs where 69% of notes were stuck on E1. Basic Pitch is
trained on Slakh + MedleyDB which contain bass stems, has explicit
``onset_threshold`` / ``frame_threshold`` confidence knobs, and doesn't
have the floor-pile-up failure mode.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import librosa
import numpy as np
import pretty_midi

from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import Model, predict

from octave_check import apply_octave_check
from quantize_snap import snap_to_beat_grid


SAMPLE_RATE = 22050
# Bass-register clamp. B0=30.87 Hz covers a 5-string low-B; G3=196 Hz
# covers slap and upper-register fills. Basic Pitch can hallucinate
# midrange notes when given a clean bass stem, so the cap matters.
BP_MIN_FREQ_HZ = 30.0
BP_MAX_FREQ_HZ = 500.0
# Confidence thresholds. Defaults are basic-pitch's own (0.5 / 0.3) and
# work well on isolated bass; phase 5 of the rebuild plan calibrates
# these against the real-bass corpus.
BP_ONSET_THRESHOLD = 0.5
BP_FRAME_THRESHOLD = 0.3
# Minimum note length in milliseconds. 80 ms is a 16th note at 187 BPM,
# which is faster than any bass line we expect to transcribe.
BP_MIN_NOTE_LEN_MS = 80.0
# Cap the beat-grid snap well under mir_eval's 50 ms onset tolerance.
SNAP_MAX_SHIFT_S = 0.03

# Module-level cache so a long-running uvicorn process pays the TF
# initialisation cost once, not on every request.
_MODEL_CACHE: Model | None = None


def _get_model() -> Model:
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        _MODEL_CACHE = Model(ICASSP_2022_MODEL_PATH)
    return _MODEL_CACHE


def _apply_beat_grid(
    midi_data: pretty_midi.PrettyMIDI,
    y: np.ndarray,
    sr: int,
) -> dict[str, Any]:
    """Overwrite the tempo map + snap onsets to the detected beat grid.

    Mutates ``midi_data`` in place. Silently leaves the MIDI unchanged if
    beat tracking fails or produces too few beats to be useful. Returns
    a dict describing what the snap did so callers can emit diagnostics.
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

    midi_data._tick_scales = [(0, 60.0 / (tempo_bpm * midi_data.resolution))]
    midi_data._update_tick_to_time(0)

    info["tempo_bpm"] = tempo_bpm
    info["beat_times"] = beat_times
    info["snap_max_shift_s"] = SNAP_MAX_SHIFT_S

    for inst in midi_data.instruments:
        if inst.is_drum:
            continue
        starts = [note.start for note in inst.notes]
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
    octave_check: bool = False,
) -> (
    tuple[Path, list[tuple[float, float, int, float, Any]]]
    | tuple[Path, list[tuple[float, float, int, float, Any]], dict[str, Any]]
):
    """Transcribe an isolated bass stem to MIDI via Basic Pitch.

    Returns (midi_path, note_events). Each note_event is
    (start_time_s, end_time_s, pitch_midi, amplitude, pitch_bends);
    amplitude in [0, 1] is Basic Pitch's per-note activation strength
    and slots into the same confidence plumbing the previous pipeline used.

    If ``return_debug`` is True, returns an additional ``debug`` dict
    with the raw and snapped note arrays plus beat-track metadata. Used
    by main.py to write a per-upload JSON artifact for offline review.

    If ``octave_check`` is True, runs CREPE on each note's audio slice
    and either transposes Basic Pitch down an octave when CREPE catches
    a harmonic-latch error or drops the note when CREPE strongly
    disagrees. Adds ~50 ms per note on CPU; opt-in.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    model = _get_model()
    _, midi_data, note_events = predict(
        str(bass_audio),
        model_or_model_path=model,
        onset_threshold=BP_ONSET_THRESHOLD,
        frame_threshold=BP_FRAME_THRESHOLD,
        minimum_note_length=BP_MIN_NOTE_LEN_MS,
        minimum_frequency=BP_MIN_FREQ_HZ,
        maximum_frequency=BP_MAX_FREQ_HZ,
        melodia_trick=True,
    )

    # Capture raw onset times before the beat snap mutates them.
    raw_starts = [
        float(n.start)
        for inst in midi_data.instruments
        if not inst.is_drum
        for n in inst.notes
    ]

    # Re-load audio at our sample rate for beat tracking. Basic Pitch
    # ran at its own internal rate; librosa beat-track wants its own.
    y, sr = librosa.load(str(bass_audio), sr=SAMPLE_RATE, mono=True)
    duration = len(y) / sr if sr else 0.0

    octave_check_counters: dict[str, int] = {}
    if octave_check:
        # Snapshot per-note amplitudes by start time so we can preserve
        # them when octave_check drops/transposes notes (start times are
        # untouched by apply_octave_check; the beat snap below is what
        # would change them, and runs after this).
        amp_by_start = {float(ne[0]): float(ne[3]) for ne in note_events}
        for inst in midi_data.instruments:
            if inst.is_drum:
                continue
            counters = apply_octave_check(inst.notes, y, sr)
            for k, v in counters.items():
                octave_check_counters[k] = octave_check_counters.get(k, 0) + v
        note_events = [
            (
                float(n.start), float(n.end), int(n.pitch),
                amp_by_start.get(float(n.start), 1.0),
                [],
            )
            for inst in midi_data.instruments
            if not inst.is_drum
            for n in inst.notes
        ]

    snap_info = _apply_beat_grid(midi_data, y, sr)

    snapped_notes = (
        midi_data.instruments[0].notes if midi_data.instruments else []
    )
    # Re-sync note_events onsets/ends with the snapped MIDI so the
    # downstream confidence matcher (±0.3 s tolerance) keeps lining up.
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
        "engine": "basic_pitch",
        "bp_onset_threshold": BP_ONSET_THRESHOLD,
        "bp_frame_threshold": BP_FRAME_THRESHOLD,
        "bp_min_freq_hz": BP_MIN_FREQ_HZ,
        "bp_max_freq_hz": BP_MAX_FREQ_HZ,
        "raw_onsets_all": raw_starts,
        "raw_onsets_kept": raw_starts,
        "snapped_starts": [float(n.start) for n in snapped_notes],
        "note_ends": [float(n.end) for n in snapped_notes],
        "pitches": [int(n.pitch) for n in snapped_notes],
        # Basic Pitch sets its own note ends from frame activations;
        # no separate release-detector pass yet (phase 4 adds CREPE QC).
        "releases": [None] * len(snapped_notes),
        "confidences": [float(ne[3]) for ne in note_events],
        "tempo_bpm": snap_info.get("tempo_bpm"),
        "beat_times": snap_info.get("beat_times", []),
        "snap_max_shift_s": snap_info.get("snap_max_shift_s"),
        "octave_check": octave_check_counters or None,
    }
    return midi_path, note_events, debug
