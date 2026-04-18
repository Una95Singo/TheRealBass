"""Per-measure chord inference from a bass line.

A bass line normally plays the root of the underlying chord, so for each
measure we pick the root pitch class from the bass notes (most common,
breaking ties by the first-beat note) and label it as the diatonic chord
implied by the analyzed key.

This is intentionally simple — it produces Real Book-style triad symbols
("C", "Am", "F", "G", "Bdim") that match the typical lead-sheet shorthand
for diatonic music. Non-diatonic roots fall back to a bare root letter.
"""
from __future__ import annotations

from collections import Counter

_LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_PC_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

# Mode → {scale-degree-in-semitones from tonic: triad quality}
_MAJOR_QUALITIES = {0: "", 2: "m", 4: "m", 5: "", 7: "", 9: "m", 11: "dim"}
_MINOR_QUALITIES = {0: "m", 2: "dim", 3: "", 5: "m", 7: "m", 8: "", 10: ""}


def _pitch_class(name: str) -> int | None:
    """Convert a pitch like 'G2' / 'F#2' / 'Bb3' to a pitch class 0-11."""
    if not name:
        return None
    letter = name[0].upper()
    if letter not in _LETTER_PC:
        return None
    accidental = name[1:-1]
    pc = _LETTER_PC[letter]
    if accidental == "#":
        pc += 1
    elif accidental == "##":
        pc += 2
    elif accidental == "b":
        pc -= 1
    elif accidental == "bb":
        pc -= 2
    return pc % 12


def _key_tonic_and_mode(key_str: str) -> tuple[int, str] | None:
    """Parse 'G major' / 'Eb minor' into (tonic_pc, mode)."""
    parts = key_str.strip().rsplit(" ", 1)
    if len(parts) != 2:
        return None
    tonic_name, mode = parts
    mode = mode.lower()
    if mode not in ("major", "minor"):
        return None
    pc = _pitch_class(tonic_name + "0")  # add octave so _pitch_class accepts it
    if pc is None:
        return None
    return pc, mode


def _measure_root_pc(notes: list[dict]) -> int | None:
    """Pick the root pitch class for a measure: most common, ties broken by first-beat note."""
    pcs = [_pitch_class(n["pitch"]) for n in notes if "pitch" in n]
    pcs = [p for p in pcs if p is not None]
    if not pcs:
        return None
    counts = Counter(pcs)
    top_count = counts.most_common(1)[0][1]
    candidates = {pc for pc, c in counts.items() if c == top_count}
    if len(candidates) == 1:
        return next(iter(candidates))
    # Tie — return the first note in the measure that's a candidate.
    for n in notes:
        pc = _pitch_class(n.get("pitch", ""))
        if pc in candidates:
            return pc
    return next(iter(candidates))


def _chord_symbol(root_pc: int, tonic_pc: int, mode: str) -> str:
    """Build a Real Book chord symbol from the root and the analyzed key."""
    degree = (root_pc - tonic_pc) % 12
    qualities = _MAJOR_QUALITIES if mode == "major" else _MINOR_QUALITIES
    quality = qualities.get(degree)
    root_name = _PC_NAMES[root_pc]
    if quality is None:
        # Non-diatonic root: bare letter is the safest Real Book fallback.
        return root_name
    return root_name + quality


def infer_chord(notes: list[dict], key_str: str) -> str | None:
    """Return a chord symbol for the measure, or None if it can't be inferred."""
    if not notes:
        return None
    parsed_key = _key_tonic_and_mode(key_str)
    root_pc = _measure_root_pc(notes)
    if parsed_key is None or root_pc is None:
        return None
    tonic_pc, mode = parsed_key
    return _chord_symbol(root_pc, tonic_pc, mode)


def infer_chords(measures: list[dict], key_str: str) -> list[str | None]:
    return [infer_chord(m.get("notes", []), key_str) for m in measures]
