"""Per-note confidence attachment from Basic Pitch note events.

Kept separate from analyze.py so tests can exercise the matching logic without
importing music21.
"""
from __future__ import annotations

from typing import Any, Iterable

_PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def pitch_str_to_midi(pitch: str) -> int | None:
    """Parse "F#2" / "Bb1" / "C3" into a MIDI note number."""
    if len(pitch) < 2:
        return None
    letter = pitch[0]
    if letter not in _PITCH_CLASS:
        return None
    semitone = _PITCH_CLASS[letter]
    rest = pitch[1:]
    if rest.startswith("##"):
        semitone += 2
        rest = rest[2:]
    elif rest.startswith("#"):
        semitone += 1
        rest = rest[1:]
    elif rest.startswith("bb"):
        semitone -= 2
        rest = rest[2:]
    elif rest.startswith("b") and len(rest) > 1:
        semitone -= 1
        rest = rest[1:]
    try:
        octave = int(rest)
    except ValueError:
        return None
    return (octave + 1) * 12 + semitone


def attach_confidence(
    measures: list[dict[str, Any]],
    note_events: Iterable[tuple[float, float, int, float, Any]] | None,
    bpm: int,
    beats_per_measure: int,
) -> None:
    """Annotate each note dict with "confidence" when a matching event exists.

    Matches by pitch and start-time within ±0.3s; seconds-per-beat is derived
    from the provided BPM. Mutates measures in place.
    """
    if not note_events:
        return
    events = sorted(
        (float(e[0]), int(e[2]), float(e[3])) for e in note_events
    )
    spb = 60.0 / max(1, bpm)
    for m_idx, measure in enumerate(measures):
        measure_start_s = m_idx * beats_per_measure * spb
        for note in measure["notes"]:
            note_midi = pitch_str_to_midi(note["pitch"])
            if note_midi is None:
                continue
            note_start_s = measure_start_s + (note["start_beat"] - 1.0) * spb
            best_dt: float | None = None
            best_conf: float | None = None
            for es, em, ea in events:
                if em != note_midi:
                    continue
                dt = abs(es - note_start_s)
                if dt > 0.3:
                    continue
                if best_dt is None or dt < best_dt:
                    best_dt = dt
                    best_conf = ea
            if best_conf is not None:
                note["confidence"] = round(best_conf, 3)
