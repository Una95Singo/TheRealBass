"""Unit tests for confidence.attach_confidence."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from confidence import attach_confidence, pitch_str_to_midi  # noqa: E402


def test_pitch_str_to_midi_naturals():
    assert pitch_str_to_midi("C4") == 60
    assert pitch_str_to_midi("A4") == 69
    assert pitch_str_to_midi("E1") == 28
    assert pitch_str_to_midi("G2") == 43


def test_pitch_str_to_midi_accidentals():
    assert pitch_str_to_midi("F#2") == 42
    assert pitch_str_to_midi("Bb3") == 58
    assert pitch_str_to_midi("C#4") == 61
    assert pitch_str_to_midi("Gb2") == 42  # enharmonic with F#2


def test_pitch_str_to_midi_rejects_garbage():
    assert pitch_str_to_midi("") is None
    assert pitch_str_to_midi("X2") is None
    assert pitch_str_to_midi("C") is None


def test_attach_confidence_no_events_is_noop():
    measures = [{"notes": [{"pitch": "G2", "start_beat": 1.0}]}]
    attach_confidence(measures, None, 120, 4)
    assert "confidence" not in measures[0]["notes"][0]
    attach_confidence(measures, [], 120, 4)
    assert "confidence" not in measures[0]["notes"][0]


def test_attach_confidence_matches_pitch_and_time():
    # At 120 BPM, one beat = 0.5s. Measure 1 starts at 0s; measure 2 at 2s.
    measures = [
        {
            "notes": [
                {"pitch": "G2", "start_beat": 1.0},   # t = 0.0s
                {"pitch": "D2", "start_beat": 3.0},   # t = 1.0s
            ],
        },
        {
            "notes": [
                {"pitch": "E2", "start_beat": 1.0},   # t = 2.0s
            ],
        },
    ]
    events = [
        (0.02, 0.4, 43, 0.91, []),   # G2 at ~0.02s, confidence 0.91
        (0.98, 1.4, 38, 0.42, []),   # D2 at ~0.98s, confidence 0.42
        (2.05, 2.4, 40, 0.77, []),   # E2 at ~2.05s, confidence 0.77
    ]
    attach_confidence(measures, events, 120, 4)
    assert measures[0]["notes"][0]["confidence"] == 0.91
    assert measures[0]["notes"][1]["confidence"] == 0.42
    assert measures[1]["notes"][0]["confidence"] == 0.77


def test_attach_confidence_skips_when_pitch_mismatches():
    measures = [{"notes": [{"pitch": "G2", "start_beat": 1.0}]}]
    # Event at the right time but wrong pitch (D2 instead of G2).
    events = [(0.0, 0.5, 38, 0.9, [])]
    attach_confidence(measures, events, 120, 4)
    assert "confidence" not in measures[0]["notes"][0]


def test_attach_confidence_skips_when_time_too_far():
    measures = [{"notes": [{"pitch": "G2", "start_beat": 1.0}]}]
    # Right pitch but 1s off — outside the 0.3s window.
    events = [(1.5, 2.0, 43, 0.9, [])]
    attach_confidence(measures, events, 120, 4)
    assert "confidence" not in measures[0]["notes"][0]


def test_attach_confidence_picks_closest_event():
    measures = [{"notes": [{"pitch": "G2", "start_beat": 1.0}]}]
    events = [
        (0.25, 0.5, 43, 0.3, []),   # 0.25s off, low confidence
        (0.05, 0.5, 43, 0.8, []),   # 0.05s off, high confidence — should win
    ]
    attach_confidence(measures, events, 120, 4)
    assert measures[0]["notes"][0]["confidence"] == 0.8
