"""Snap note onsets to the nearest subdivision of a beat grid.

Kept separate from transcribe.py so the arithmetic can be unit-tested
without pulling in basic_pitch or librosa.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import Sequence

# Resolution: start of beat, 8th, 8th-triplet (2/3), 8th-swung (1/3), dotted
# 8th (3/4). Covers straight, swing, and dotted feels without going finer
# than music21's quantizer can handle downstream.
DEFAULT_SUBDIVISIONS: tuple[float, ...] = (
    0.0, 1.0 / 3.0, 0.5, 2.0 / 3.0, 3.0 / 4.0,
)


def _grid_positions(
    beat_times: Sequence[float],
    subdivisions: Sequence[float],
) -> list[float]:
    """Expand a beat-times list into a dense grid of subdivision positions."""
    if len(beat_times) < 2:
        return list(beat_times)
    grid: list[float] = []
    for i in range(len(beat_times) - 1):
        beat_start = beat_times[i]
        beat_len = beat_times[i + 1] - beat_times[i]
        for frac in subdivisions:
            grid.append(beat_start + frac * beat_len)
    # Plus the final beat itself so onsets near the end still have a target.
    grid.append(beat_times[-1])
    grid.sort()
    return grid


def snap_to_beat_grid(
    onsets_s: Sequence[float],
    beat_times_s: Sequence[float],
    subdivisions: Sequence[float] = DEFAULT_SUBDIVISIONS,
    max_shift_s: float | None = None,
) -> list[float]:
    """Snap each onset to the nearest grid position.

    If ``max_shift_s`` is set, onsets farther than that from any grid
    position are left at their original time (assumed spurious — let the
    downstream quantizer drop them if it wants).

    Onsets outside the [first beat, last beat] range pass through
    unchanged; extrapolating the grid beyond the tracked beats is
    unreliable.
    """
    if not onsets_s or len(beat_times_s) < 2:
        return list(onsets_s)

    grid = _grid_positions(beat_times_s, subdivisions)
    first_beat = beat_times_s[0]
    last_beat = beat_times_s[-1]

    out: list[float] = []
    for onset in onsets_s:
        if onset < first_beat or onset > last_beat:
            out.append(onset)
            continue
        # Binary search + check both neighbours.
        idx = bisect_left(grid, onset)
        candidates: list[float] = []
        if idx < len(grid):
            candidates.append(grid[idx])
        if idx > 0:
            candidates.append(grid[idx - 1])
        if not candidates:
            out.append(onset)
            continue
        best = min(candidates, key=lambda g: abs(g - onset))
        if max_shift_s is not None and abs(best - onset) > max_shift_s:
            out.append(onset)
        else:
            out.append(best)
    return out


def clamp_to_beat_window(
    t: float, beat_times_s: Sequence[float]
) -> float:
    """Convenience: clamp a time into the tracked beat range, for tests."""
    if not beat_times_s:
        return t
    lo, hi = beat_times_s[0], beat_times_s[-1]
    return max(lo, min(hi, t))


__all__ = [
    "DEFAULT_SUBDIVISIONS",
    "snap_to_beat_grid",
    "clamp_to_beat_window",
]


# Expose a utility used by the tests without making them reach into private
# names across the public API surface.
def _grid_positions_for_tests(
    beat_times_s: Sequence[float], subdivisions: Sequence[float]
) -> list[float]:
    return _grid_positions(beat_times_s, subdivisions)
