"""Unit tests for the CREPE octave-correction decision logic.

Tests target the pure-function ``decide_correction`` — running CREPE
itself requires TF and isn't unit-testable. The integration is covered
by exercising ``apply_octave_check`` with a fake CREPE call patched in.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from octave_check import (  # noqa: E402
    CREPE_DROP_CONFIDENCE,
    CREPE_MIN_CONFIDENCE,
    Decision,
    apply_octave_check,
    decide_correction,
)


# ------------------------- decide_correction --------------------------

def test_keeps_when_crepe_confidence_too_low():
    # Even though CREPE thinks the pitch is wildly different, low conf -> keep.
    assert decide_correction(40, 28.0, CREPE_MIN_CONFIDENCE - 0.01) is Decision.KEEP


def test_keeps_when_crepe_returns_no_pitch():
    assert decide_correction(40, None, 0.9) is Decision.KEEP


def test_keeps_when_pitch_agrees_within_tolerance():
    # CREPE off by 0.4 semitones (mild mistuning) — keep.
    assert decide_correction(40, 39.6, 0.8) is Decision.KEEP
    assert decide_correction(40, 40.6, 0.8) is Decision.KEEP


def test_transposes_down_when_basic_pitch_an_octave_high():
    # Classic harmonic-latch failure: BP says E2 (40), CREPE says E1 (28).
    assert decide_correction(40, 28.0, 0.7) is Decision.TRANSPOSE_DOWN_OCTAVE


def test_transposes_down_with_slight_mistuning_inside_octave_window():
    # CREPE 28.4 still rounds to "an octave below 40" — still transpose.
    assert decide_correction(40, 28.4, 0.7) is Decision.TRANSPOSE_DOWN_OCTAVE


def test_drops_when_strongly_disagrees_and_crepe_confident():
    # 5-semitone disagreement at 0.8 conf: DROP.
    assert decide_correction(40, 35.0, 0.8) is Decision.DROP


def test_keeps_on_disagreement_when_crepe_only_marginally_confident():
    # 5-semitone disagreement but conf below DROP threshold: KEEP.
    assert decide_correction(40, 35.0, CREPE_DROP_CONFIDENCE - 0.05) is Decision.KEEP


def test_does_not_transpose_when_crepe_is_one_octave_high():
    # Inverse case (BP low, CREPE high) — we don't transpose UP, just drop or keep.
    # 12 semitones BELOW BP shouldn't trigger TRANSPOSE_DOWN.
    assert (
        decide_correction(40, 52.0, 0.8)
        in {Decision.DROP, Decision.KEEP}
    )


# ------------------------- apply_octave_check -------------------------

class _FakeNote:
    def __init__(self, pitch: int, start: float, end: float):
        self.pitch = pitch
        self.start = start
        self.end = end


def _patch_crepe(monkeypatch, sequence):
    """Patch _crepe_estimate_midi to yield (midi, conf) from sequence."""
    import octave_check
    iterator = iter(sequence)

    def fake(audio_slice, sr):
        try:
            return next(iterator)
        except StopIteration:
            return None, 0.0

    monkeypatch.setattr(octave_check, "_crepe_estimate_midi", fake)


class _FakeAudio:
    """Minimal stand-in for an ndarray: supports len() and [start:end]."""
    def __init__(self, n: int):
        self.n = n

    def __len__(self):
        return self.n

    def __getitem__(self, key):
        if isinstance(key, slice):
            return _FakeAudio(max(0, (key.stop or self.n) - (key.start or 0)))
        raise TypeError(key)


def test_apply_octave_check_transposes_and_drops_in_place(monkeypatch):
    notes = [
        _FakeNote(pitch=40, start=0.0, end=0.5),  # CREPE says E1 -> transpose down
        _FakeNote(pitch=45, start=0.5, end=1.0),  # CREPE agrees -> keep
        _FakeNote(pitch=33, start=1.0, end=1.5),  # CREPE strongly disagrees -> drop
    ]
    audio = _FakeAudio(int(1.5 * 22050))
    _patch_crepe(monkeypatch, [
        (28.0, 0.7),   # one octave below 40
        (45.2, 0.8),   # ~agrees with 45
        (45.0, 0.9),   # 12 semitones above 33 -> not the down-transpose case, drops
    ])
    counters = apply_octave_check(notes, audio, sr=22050)
    pitches = [n.pitch for n in notes]
    assert pitches == [28, 45]  # third note dropped
    assert counters == {"kept": 1, "transposed": 1, "dropped": 1}


def test_apply_octave_check_handles_empty_audio_window():
    note = _FakeNote(pitch=40, start=0.5, end=0.4)  # end < start
    counters = apply_octave_check([note], _FakeAudio(100), sr=22050)
    # Note kept untouched, counted under kept.
    assert counters == {"kept": 1, "transposed": 0, "dropped": 0}
