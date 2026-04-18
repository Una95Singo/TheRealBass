"""Quantization and key/tempo analysis with music21."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from music21 import converter, meter, tempo

from chords import infer_chord


_DURATION_MAP = {
    4.0: "w",
    3.0: "hd",
    2.0: "h",
    1.5: "qd",
    1.0: "q",
    0.75: "8d",
    0.5: "8",
    0.25: "16",
    0.125: "32",
}


def _duration_code(quarter_length: float) -> str:
    """Map a music21 quarter-length to a VexFlow-style duration code."""
    if quarter_length <= 0:
        return "16"
    best = min(_DURATION_MAP, key=lambda q: abs(q - quarter_length))
    return _DURATION_MAP[best]


def analyze_midi(midi_path: Path) -> dict[str, Any]:
    """Parse the MIDI file and return structured notation data."""
    score = converter.parse(str(midi_path))
    quantized = score.quantize(quarterLengthDivisors=(4, 3), inPlace=False)

    key_obj = quantized.analyze("key")
    key_name = f"{key_obj.tonic.name} {key_obj.mode}"

    tempos = quantized.recurse().getElementsByClass(tempo.MetronomeMark)
    bpm = int(round(tempos[0].number)) if len(tempos) else 120

    time_sigs = quantized.recurse().getElementsByClass(meter.TimeSignature)
    time_sig = time_sigs[0].ratioString if len(time_sigs) else "4/4"
    beats_per_measure = time_sigs[0].numerator if len(time_sigs) else 4

    part = quantized.parts[0] if quantized.parts else quantized
    measures: list[dict[str, Any]] = []

    for i, m in enumerate(part.getElementsByClass("Measure"), start=1):
        notes: list[dict[str, Any]] = []
        for n in m.notes:
            if not n.isNote:
                continue
            notes.append(
                {
                    "pitch": f"{n.pitch.name.replace('-', 'b')}{n.pitch.octave}",
                    "duration": _duration_code(float(n.duration.quarterLength)),
                    "start_beat": float(n.offset) + 1.0,
                }
            )
        measures.append({"measure_number": i, "notes": notes})

    if not measures:
        flat_notes: list[dict[str, Any]] = []
        for n in part.recurse().notes:
            if not n.isNote:
                continue
            flat_notes.append(
                {
                    "pitch": f"{n.pitch.name.replace('-', 'b')}{n.pitch.octave}",
                    "duration": _duration_code(float(n.duration.quarterLength)),
                    "offset": float(n.offset),
                }
            )
        grouped: dict[int, list[dict[str, Any]]] = {}
        for n in flat_notes:
            m_idx = int(n["offset"] // beats_per_measure) + 1
            grouped.setdefault(m_idx, []).append(
                {
                    "pitch": n["pitch"],
                    "duration": n["duration"],
                    "start_beat": (n["offset"] % beats_per_measure) + 1.0,
                }
            )
        measures = [
            {"measure_number": i, "notes": grouped.get(i, [])}
            for i in sorted(grouped)
        ]

    return {
        "key": key_name,
        "bpm": bpm,
        "time_signature": time_sig,
        "measures": [
            {**m, "chord": infer_chord(m["notes"], key_name)} for m in measures
        ],
    }
