"""Unit tests for the rhythm-log JSON writer."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

sys.modules.pop("rhythm_log", None)

from rhythm_log import build_payload, write_artifact  # noqa: E402


def _sample_debug() -> dict:
    return {
        "sample_rate": 22050,
        "audio_duration_s": 2.4,
        "raw_onsets_all": [0.0, 0.6, 1.2, 1.8],
        "raw_onsets_kept": [0.0, 0.6, 1.2, 1.8],
        "snapped_starts": [0.0, 0.6, 1.2, 1.8],
        "note_ends": [0.5, 1.1, 1.7, 2.3],
        "pitches": [40, 43, 45, 47],
        "releases": [None, 1.05, None, None],
        "confidences": [0.9, 0.8, 0.85, 0.7],
        "tempo_bpm": 100.0,
        "beat_times": [0.0, 0.6, 1.2, 1.8, 2.4],
        "snap_max_shift_s": 0.03,
    }


def test_build_payload_shape_and_counts():
    payload = build_payload(_sample_debug(), {"file_id": "abc123", "original_filename": "song.mp3"})
    assert payload["schema_version"] == 1
    assert payload["file_id"] == "abc123"
    assert payload["original_filename"] == "song.mp3"
    assert payload["tempo_bpm"] == 100.0
    assert payload["n_raw_onsets"] == 4
    assert payload["n_notes_final"] == 4
    assert len(payload["notes"]) == 4


def test_build_payload_note_fields():
    payload = build_payload(_sample_debug(), {"file_id": "abc123"})
    n0 = payload["notes"][0]
    assert n0["idx"] == 0
    assert n0["raw_onset_s"] == 0.0
    assert n0["snapped_start_s"] == 0.0
    assert n0["release_s"] is None
    assert n0["final_end_s"] == 0.5
    assert n0["duration_ms"] == 500
    assert n0["pitch_midi"] == 40
    assert n0["pitch_name"] == "E2"
    assert n0["confidence"] == 0.9

    # Release should survive into the payload when present.
    assert payload["notes"][1]["release_s"] == 1.05


def test_build_payload_handles_empty_debug():
    payload = build_payload({}, {"file_id": "x"})
    assert payload["notes"] == []
    assert payload["n_notes_final"] == 0
    assert payload["beat_times_s"] == []
    assert payload["tempo_bpm"] is None


def test_write_artifact_round_trip(tmp_path: Path):
    out = write_artifact(
        _sample_debug(),
        {"file_id": "deadbeef00", "original_filename": "clip.wav"},
        tmp_path,
    )
    assert out.exists()
    assert out.parent == tmp_path
    # Filename must be path-safe and contain the file id prefix.
    assert "deadbeef00" in out.name
    assert out.name.endswith(".json")

    data = json.loads(out.read_text())
    assert data["file_id"] == "deadbeef00"
    assert data["notes"][0]["pitch_name"] == "E2"


def test_write_artifact_sanitises_file_id(tmp_path: Path):
    # File ids shouldn't be able to inject path separators.
    out = write_artifact(
        _sample_debug(),
        {"file_id": "../../etc/passwd"},
        tmp_path,
    )
    # Everything non-alphanumeric gets stripped, so no traversal reaches disk.
    assert out.parent == tmp_path
    assert ".." not in out.name
    assert "/" not in out.name
