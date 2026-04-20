"""Generate the ground-truth MIDI fixtures for the AMT harness.

Run once (`python eval/corpus/build_corpus.py`) to (re)write the five .mid
files next to this script. They're committed to the repo so the harness
itself doesn't need to re-generate them on every invocation.

All lines are monophonic, live in the bass register (E1–G3), and are built
out of plain 16th-note arithmetic — no subtlety, the goal is to exercise
specific pipeline failure modes, not to sound musical.
"""
from __future__ import annotations

from pathlib import Path

import pretty_midi

BASS_PROGRAM = pretty_midi.instrument_name_to_program("Electric Bass (finger)")
HERE = Path(__file__).resolve().parent


def _write(clip_name: str, bpm: float, events: list[tuple[float, float, int]]) -> None:
    """events: list of (start_beat, duration_beats, pitch_midi)."""
    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    bass = pretty_midi.Instrument(program=BASS_PROGRAM, is_drum=False, name="Bass")
    spb = 60.0 / bpm
    for start_beat, dur_beats, pitch in events:
        start_s = start_beat * spb
        end_s = start_s + dur_beats * spb
        bass.notes.append(
            pretty_midi.Note(velocity=96, pitch=pitch, start=start_s, end=end_s)
        )
    midi.instruments.append(bass)
    out = HERE / f"{clip_name}.mid"
    midi.write(str(out))
    print(f"wrote {out.name}: {len(events)} notes @ {bpm} bpm")


def quarters_80bpm() -> None:
    # 8 bars, one quarter per beat, I–IV–V–I walking in A (pitches E1=28, A1=33, D2=38, E2=40).
    pattern = [33, 33, 33, 33, 38, 38, 38, 38, 40, 40, 40, 40, 33, 33, 33, 33]
    events = []
    for bar in range(2):
        for i, p in enumerate(pattern):
            events.append((bar * 16 + i, 1.0, p))
    _write("quarters_80bpm", 80.0, events)


def eighths_120bpm() -> None:
    # 8 bars of straight 8ths on a 4-note root-fifth-octave-fifth figure.
    figure = [28, 35, 40, 35]  # E1, B1, E2, B1
    events = []
    for beat in range(32):  # 8 bars * 4 beats
        base_beat = beat
        for sub in range(2):
            start = base_beat + sub * 0.5
            p = figure[(beat * 2 + sub) % len(figure)]
            events.append((start, 0.5, p))
    _write("eighths_120bpm", 120.0, events)


def sixteenths_100bpm() -> None:
    # 4 bars of 16ths, busy funk-style line cycling E1–G1–A1–E1.
    pitches = [28, 31, 33, 28]
    events = []
    for beat in range(16):  # 4 bars * 4 beats
        for sub in range(4):
            start = beat + sub * 0.25
            p = pitches[sub % len(pitches)]
            events.append((start, 0.25, p))
    _write("sixteenths_100bpm", 100.0, events)


def shuffle_110bpm() -> None:
    # 8 bars of a triplet-shuffle feel: long-short long-short per beat.
    # In triplet terms that's a dotted-8th + 16th-triplet, rendered here as
    # start-of-beat + 2/3-through-beat.
    pitches = [33, 40, 33, 40]
    events = []
    for beat in range(32):
        p1 = pitches[beat % len(pitches)]
        events.append((beat, 2.0 / 3.0, p1))
        events.append((beat + 2.0 / 3.0, 1.0 / 3.0, p1 + 7))
    _write("shuffle_110bpm", 110.0, events)


def walkup_95bpm() -> None:
    # 4 bars, one quarter note per beat, chromatic climb across the full
    # bass register E1 (28) -> G3 (55).
    events = []
    for beat in range(16):
        pitch = 28 + beat  # stops well below G3 but covers ~an octave+fourth
        events.append((beat, 1.0, pitch))
    _write("walkup_95bpm", 95.0, events)


def dotted8_rests_100bpm() -> None:
    # 4 bars at 100 BPM. Notes only on beats 1 and 3, each a dotted-8th
    # (0.75 beats), beats 2 and 4 fully silent. Forces the pipeline to
    # cut notes short where the next onset is far away — exposes the
    # "note.end = next_onset" sustain bug that the rhythm-logs caught
    # on real audio.
    events = []
    pitches = [33, 38, 33, 38, 33, 38, 33, 38]  # A1, D2 alternating
    for bar in range(4):
        events.append((bar * 4 + 0, 0.75, pitches[bar * 2]))
        events.append((bar * 4 + 2, 0.75, pitches[bar * 2 + 1]))
    _write("dotted8_rests_100bpm", 100.0, events)


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    quarters_80bpm()
    eighths_120bpm()
    sixteenths_100bpm()
    shuffle_110bpm()
    walkup_95bpm()
    dotted8_rests_100bpm()


if __name__ == "__main__":
    main()
