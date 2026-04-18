"""Unit tests for the chord inference helpers in chords.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chords import infer_chord, infer_chords  # noqa: E402


def _notes(*pitches: str) -> list[dict]:
    return [
        {"pitch": p, "duration": "q", "start_beat": float(i + 1)}
        for i, p in enumerate(pitches)
    ]


# Diatonic triads in C major
@pytest.mark.parametrize(
    "root,expected",
    [
        ("C", "C"),    # I
        ("D", "Dm"),   # ii
        ("E", "Em"),   # iii
        ("F", "F"),    # IV
        ("G", "G"),    # V
        ("A", "Am"),   # vi
        ("B", "Bdim"), # vii°
    ],
)
def test_diatonic_triads_in_c_major(root, expected):
    assert infer_chord(_notes(f"{root}2"), "C major") == expected


# Diatonic triads in A minor
@pytest.mark.parametrize(
    "root,expected",
    [
        ("A", "Am"),   # i
        ("B", "Bdim"), # ii°
        ("C", "C"),    # III
        ("D", "Dm"),   # iv
        ("E", "Em"),   # v (natural minor)
        ("F", "F"),    # VI
        ("G", "G"),    # VII
    ],
)
def test_diatonic_triads_in_a_minor(root, expected):
    assert infer_chord(_notes(f"{root}2"), "A minor") == expected


def test_root_picked_by_frequency_not_position():
    # C is most common; D is on beat 1 but should not win.
    notes = _notes("D2", "C2", "C2", "C2")
    assert infer_chord(notes, "C major") == "C"


def test_tie_broken_by_first_beat_note():
    # Each pitch class appears once → tie, fall back to first note (G).
    notes = _notes("G2", "C2", "E2")
    assert infer_chord(notes, "C major") == "G"


def test_accidentals_are_recognized():
    # F# in G major → root scale degree 11 → vii° → F#dim.
    assert infer_chord(_notes("F#2"), "G major") == "F#dim"
    # Bb in F major → IV (b is at degree 5? actually Bb is 4 semitones above F: degree 5 → IV major)
    assert infer_chord(_notes("Bb3"), "F major") == "Bb"


def test_non_diatonic_root_falls_back_to_bare_letter():
    # F# in C major is non-diatonic → "F#"
    assert infer_chord(_notes("F#2"), "C major") == "F#"


def test_empty_measure_returns_none():
    assert infer_chord([], "C major") is None


def test_unknown_key_returns_none():
    assert infer_chord(_notes("C2"), "Wat dorian") is None


def test_infer_chords_walks_measures():
    measures = [
        {"notes": _notes("C2")},
        {"notes": _notes("F2")},
        {"notes": _notes("G2")},
        {"notes": []},
    ]
    assert infer_chords(measures, "C major") == ["C", "F", "G", None]
