"""Write a per-upload JSON artifact capturing what transcribe_to_midi did.

Pure-function module — no librosa / pretty_midi import — so the JSON shape
can be unit-tested in isolation. Consumed by main.py on every /transcribe
call, and manually reviewed by committing the output file under
artifacts/rhythm-logs/ so rhythm problems on real audio can be diagnosed
without re-running the pipeline.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_PITCH_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def _pitch_name(midi_pitch: int) -> str:
    return f"{_PITCH_NAMES[midi_pitch % 12]}{midi_pitch // 12 - 1}"


def _safe_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def build_payload(debug: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Assemble the JSON-serialisable payload from a transcribe debug dict."""
    snapped = debug.get("snapped_starts", [])
    ends = debug.get("note_ends", [])
    pitches = debug.get("pitches", [])
    releases = debug.get("releases", [])
    confidences = debug.get("confidences", [])
    raw_kept = debug.get("raw_onsets_kept", [])

    n = len(snapped)
    notes: list[dict[str, Any]] = []
    for i in range(n):
        start = float(snapped[i])
        end = float(ends[i]) if i < len(ends) else start
        pitch = int(pitches[i]) if i < len(pitches) else 0
        notes.append({
            "idx": i,
            "raw_onset_s": float(raw_kept[i]) if i < len(raw_kept) else None,
            "snapped_start_s": start,
            "release_s": _safe_float(releases[i]) if i < len(releases) else None,
            "final_end_s": end,
            "duration_ms": int(round((end - start) * 1000)),
            "pitch_midi": pitch,
            "pitch_name": _pitch_name(pitch),
            "confidence": _safe_float(confidences[i]) if i < len(confidences) else None,
        })

    return {
        "schema_version": 1,
        "file_id": metadata.get("file_id"),
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "original_filename": metadata.get("original_filename"),
        "audio_duration_s": _safe_float(debug.get("audio_duration_s")),
        "sample_rate": debug.get("sample_rate"),
        "tempo_bpm": _safe_float(debug.get("tempo_bpm")),
        "beat_times_s": [float(t) for t in debug.get("beat_times", [])],
        "snap_max_shift_s": _safe_float(debug.get("snap_max_shift_s")),
        "n_raw_onsets": len(debug.get("raw_onsets_all", [])),
        "n_notes_final": n,
        "notes": notes,
    }


_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _artifact_filename(metadata: dict[str, Any]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_id = str(metadata.get("file_id") or "unknown")
    short = _SAFE_ID_RE.sub("", raw_id)[:12] or "unknown"
    return f"{stamp}_{short}.json"


def write_artifact(
    debug: dict[str, Any],
    metadata: dict[str, Any],
    out_dir: Path,
) -> Path:
    """Serialise the debug payload to JSON under ``out_dir`` and return the path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build_payload(debug, metadata)
    path = out_dir / _artifact_filename(metadata)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False))
    return path


__all__ = ["build_payload", "write_artifact"]
