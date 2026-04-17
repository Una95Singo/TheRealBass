"""Smoke test for analyze.py using a hand-crafted MIDI fixture.

Does not require Demucs or Basic Pitch — only music21 + pretty_midi. Useful
for verifying the quantization / key / time-signature / measure-grouping
pipeline in environments where Demucs model weights cannot be downloaded.

Run from the backend/ directory with the .venv active:

    cd backend
    source .venv/bin/activate
    python scripts/smoke_analyze.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pretty_midi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analyze import analyze_midi  # noqa: E402


def build_fixture(path: Path) -> None:
    pm = pretty_midi.PrettyMIDI(initial_tempo=120.0)
    bass = pretty_midi.Instrument(program=33)  # Electric Bass (finger)
    # Two bars of quarter notes at 120 BPM, 4/4: C2, D2, E2, G2 repeated.
    seconds_per_beat = 60.0 / 120.0
    pattern = ["C2", "D2", "E2", "G2"]
    for bar in range(2):
        for i, name in enumerate(pattern):
            start = (bar * 4 + i) * seconds_per_beat
            end = start + seconds_per_beat
            bass.notes.append(
                pretty_midi.Note(
                    velocity=100,
                    pitch=pretty_midi.note_name_to_number(name),
                    start=start,
                    end=end,
                )
            )
    pm.instruments.append(bass)
    pm.write(str(path))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        fixture = Path(tmp) / "fixture.mid"
        build_fixture(fixture)
        result = analyze_midi(fixture)

    assert "key" in result, "missing key"
    assert "bpm" in result, "missing bpm"
    assert "time_signature" in result, "missing time_signature"
    assert result["measures"], "measures should be non-empty"

    first = result["measures"][0]
    assert first["notes"], "first measure should have notes"
    note = first["notes"][0]
    for field in ("pitch", "duration", "start_beat"):
        assert field in note, f"note missing {field}"

    print(json.dumps(result, indent=2))
    print("\nsmoke_analyze: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
