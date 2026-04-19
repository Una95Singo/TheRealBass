"""Unit tests for the beat-grid snap helper."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

sys.modules.pop("quantize_snap", None)

from quantize_snap import (  # noqa: E402
    DEFAULT_SUBDIVISIONS,
    _grid_positions_for_tests,
    snap_to_beat_grid,
)


# 100 BPM = 0.6 s/beat. Beat grid covers 4 beats (2.4 s total).
BEATS_100BPM = [0.0, 0.6, 1.2, 1.8, 2.4]


def test_empty_onsets_returns_empty():
    assert snap_to_beat_grid([], BEATS_100BPM) == []


def test_empty_beat_grid_passes_through():
    assert snap_to_beat_grid([0.1, 0.5], []) == [0.1, 0.5]


def test_exact_beat_onsets_unchanged():
    assert snap_to_beat_grid(BEATS_100BPM, BEATS_100BPM) == BEATS_100BPM


def test_slight_jitter_snaps_to_nearest_beat():
    # 10 ms early / late should pull onto the beat at 0.6 s.
    assert snap_to_beat_grid([0.59, 0.61], BEATS_100BPM) == [0.6, 0.6]


def test_eighth_note_position_snaps_to_half_beat():
    # At 100 BPM a straight 8th sits at beat + 0.3 s. Nearest grid = 0.3 s.
    snapped = snap_to_beat_grid([0.305], BEATS_100BPM)
    assert abs(snapped[0] - 0.3) < 1e-9


def test_triplet_position_snaps_to_third():
    # 1/3 through beat 1 = 0.2 s. Put the onset at 0.21 (just past).
    snapped = snap_to_beat_grid([0.21], BEATS_100BPM)
    assert abs(snapped[0] - 0.2) < 1e-9


def test_onset_before_first_beat_passes_through():
    # Grid starts at 0.0, so anything negative just stays put.
    assert snap_to_beat_grid([-0.05], BEATS_100BPM) == [-0.05]


def test_onset_after_last_beat_passes_through():
    # Past the last tracked beat we don't extrapolate.
    assert snap_to_beat_grid([3.0], BEATS_100BPM) == [3.0]


def test_max_shift_leaves_far_onset_alone():
    # Put an onset 100 ms off any grid position and cap the shift at 30 ms.
    # At 100 BPM beat 2 = 1.2 s, closest grid pos to 1.25 is 1.2 (50 ms away).
    snapped = snap_to_beat_grid([1.25], BEATS_100BPM, max_shift_s=0.03)
    assert snapped == [1.25]


def test_max_shift_allows_close_onset():
    snapped = snap_to_beat_grid([1.21], BEATS_100BPM, max_shift_s=0.03)
    assert abs(snapped[0] - 1.2) < 1e-9


def test_grid_contains_default_subdivisions_of_every_beat():
    grid = _grid_positions_for_tests(BEATS_100BPM, DEFAULT_SUBDIVISIONS)
    # Beat 0 subdivisions: 0, 0.2, 0.3, 0.4, 0.45.
    for expected in (0.0, 0.2, 0.3, 0.4, 0.45):
        assert any(abs(g - expected) < 1e-9 for g in grid), f"missing {expected}"


def test_monotonic_input_stays_monotonic():
    # Snapping shouldn't reorder onsets that were in the right order.
    onsets = [0.1, 0.35, 0.62, 1.01]
    snapped = snap_to_beat_grid(onsets, BEATS_100BPM)
    assert snapped == sorted(snapped)
