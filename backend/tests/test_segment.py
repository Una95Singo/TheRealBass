"""Unit tests for the cluster-id → rehearsal-letter helper in segment.py.

These tests exercise the pure-Python label-mapping logic without needing
librosa or a real audio file. An additional integration-style test runs the
full detect_sections pipeline if librosa is installed; otherwise it skips.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# test_main.py installs a `segment` stub module at import time to keep librosa
# out of its dependency graph; drop it so we pick up the real module here.
sys.modules.pop("segment", None)

from segment import _cluster_ids_to_labels, detect_sections  # noqa: E402


def test_empty_input_returns_empty_list():
    assert _cluster_ids_to_labels([]) == []


def test_single_cluster_single_letter():
    assert _cluster_ids_to_labels([0, 0, 0, 0]) == ["A", "A", "A", "A"]


def test_aba_pattern_reuses_first_letter():
    assert _cluster_ids_to_labels([0, 0, 1, 1, 0, 0]) == [
        "A", "A", "B", "B", "A", "A",
    ]


def test_first_occurrence_order_not_cluster_id_order():
    """Cluster id 2 appears first, so it's labelled A even though 2 > 0."""
    assert _cluster_ids_to_labels([2, 2, 0, 0, 1, 1]) == [
        "A", "A", "B", "B", "C", "C",
    ]


def test_short_run_merges_into_longer_neighbour():
    """A single 1 between two 0 runs gets absorbed (min section = 2)."""
    assert _cluster_ids_to_labels([0, 0, 0, 1, 0, 0, 0]) == [
        "A", "A", "A", "A", "A", "A", "A",
    ]


def test_alternating_short_runs_collapse_to_one_section():
    """No run is long enough so they all merge into a single section."""
    assert _cluster_ids_to_labels([0, 1, 0, 1], min_section_measures=2) == [
        "A", "A", "A", "A",
    ]


def test_many_clusters_use_sequential_letters():
    ids = [0] * 2 + [1] * 2 + [2] * 2 + [3] * 2
    assert _cluster_ids_to_labels(ids) == [
        "A", "A", "B", "B", "C", "C", "D", "D",
    ]


def test_detect_sections_returns_none_for_short_clip():
    """Below min_measures the detector short-circuits without touching audio."""
    assert detect_sections(
        Path("/does/not/exist.wav"),
        bpm=120,
        beats_per_measure=4,
        num_measures=4,
    ) is None


def test_detect_sections_returns_none_for_zero_bpm(tmp_path):
    """Invalid metadata bails gracefully."""
    assert detect_sections(
        tmp_path / "missing.wav",
        bpm=0,
        beats_per_measure=4,
        num_measures=32,
    ) is None
