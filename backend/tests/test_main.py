"""Validation and security tests for TheRealBass FastAPI backend.

The heavy ML dependencies (music21, demucs, basic_pitch) are stubbed out with
fake modules before importing main.py so we can exercise the HTTP layer
without pulling in torch or running real inference.
"""
from __future__ import annotations

import io
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _install_stub_modules() -> None:
    """Replace the ML-backed modules with lightweight stubs before main import."""
    # Stub analyze
    analyze_stub = types.ModuleType("analyze")
    analyze_stub.analyze_midi = lambda midi_path: {
        "key": "G major",
        "bpm": 120,
        "time_signature": "4/4",
        "measures": [],
    }
    sys.modules["analyze"] = analyze_stub

    # Stub isolate
    isolate_stub = types.ModuleType("isolate")
    isolate_stub.isolate_bass = lambda audio, out_dir: Path(out_dir) / "bass.wav"
    sys.modules["isolate"] = isolate_stub

    # Stub transcribe
    transcribe_stub = types.ModuleType("transcribe")
    transcribe_stub.transcribe_to_midi = lambda stem, out_dir: Path(out_dir) / "out.mid"
    sys.modules["transcribe"] = transcribe_stub


_install_stub_modules()

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with isolated upload/stems/midi dirs per test."""
    upload_dir = tmp_path / "uploads"
    stems_dir = tmp_path / "stems"
    midi_dir = tmp_path / "midi"
    for d in (upload_dir, stems_dir, midi_dir):
        d.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(main, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(main, "STEMS_DIR", stems_dir)
    monkeypatch.setattr(main, "MIDI_DIR", midi_dir)
    monkeypatch.setattr(main, "STORAGE_ROOT", tmp_path)

    with TestClient(main.app) as c:
        c.upload_dir = upload_dir  # type: ignore[attr-defined]
        c.stems_dir = stems_dir  # type: ignore[attr-defined]
        c.midi_dir = midi_dir  # type: ignore[attr-defined]
        yield c


CANNED_RESULT = {
    "key": "E minor",
    "bpm": 128,
    "time_signature": "4/4",
    "measures": [
        {
            "measure_number": 1,
            "notes": [{"pitch": "E2", "duration": "q", "start_beat": 1.0}],
        }
    ],
}


def _patched_pipeline():
    """Return a context manager that patches isolate/transcribe/analyze on main.

    transcribe_to_midi writes a tiny fake MIDI file so main.py's rename-to-
    canonical step has something real to move.
    """
    def fake_transcribe(stem, out):
        out_path = Path(out) / "bass_basic_pitch.mid"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"MThd")
        return out_path, []

    return patch.multiple(
        "main",
        isolate_bass=lambda audio, out: Path(out) / "bass.wav",
        transcribe_to_midi=fake_transcribe,
        analyze_midi=lambda midi, note_events=None: dict(CANNED_RESULT),
    )


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------
def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Valid uploads
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename,mime,extension",
    [
        ("song.mp3", "audio/mpeg", ".mp3"),
        ("song.mp3", "audio/mp3", ".mp3"),
        ("song.wav", "audio/wav", ".wav"),
        ("song.wav", "audio/x-wav", ".wav"),
        ("song.wav", "audio/wave", ".wav"),
        ("song.m4a", "audio/mp4", ".m4a"),
        ("song.m4a", "audio/x-m4a", ".m4a"),
    ],
)
def test_valid_upload_returns_canned_json(client, filename, mime, extension):
    payload = b"\x00\x01\x02fake-audio-bytes"
    with _patched_pipeline():
        resp = client.post(
            "/transcribe",
            files={"file": (filename, payload, mime)},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["key"] == CANNED_RESULT["key"]
    assert body["bpm"] == CANNED_RESULT["bpm"]
    assert body["time_signature"] == CANNED_RESULT["time_signature"]
    assert body["measures"] == CANNED_RESULT["measures"]
    assert "bass_stem_path" in body
    assert body["bass_stem_path"].endswith("bass.wav")
    assert len(body["file_id"]) == 32
    int(body["file_id"], 16)
    assert body["bass_audio_url"] == f"/stems/{body['file_id']}/bass.wav"
    assert body["midi_url"] == f"/midi/{body['file_id']}/bass.mid"

    # Stored file should have the right extension and a UUID-hex stem.
    stored = list(client.upload_dir.iterdir())
    assert len(stored) == 1
    assert stored[0].suffix == extension
    assert len(stored[0].stem) == 32
    int(stored[0].stem, 16)  # must be valid hex


# ---------------------------------------------------------------------------
# Wrong MIME types -> 400
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "mime",
    ["application/pdf", "audio/ogg", "image/png", "text/plain", "application/octet-stream"],
)
def test_disallowed_mime_returns_400(client, mime):
    with _patched_pipeline():
        resp = client.post(
            "/transcribe",
            files={"file": ("payload.bin", b"irrelevant", mime)},
        )
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]
    # Nothing should have been written.
    assert list(client.upload_dir.iterdir()) == []


# ---------------------------------------------------------------------------
# Oversize -> 413, and no leftover file on disk
# ---------------------------------------------------------------------------
class _ZeroStream(io.RawIOBase):
    """A streaming source of zero bytes of a given length (never materialized)."""

    def __init__(self, total: int) -> None:
        self._remaining = total

    def readable(self) -> bool:
        return True

    def readinto(self, buf) -> int:  # type: ignore[override]
        if self._remaining <= 0:
            return 0
        n = min(len(buf), self._remaining, 64 * 1024)
        buf[:n] = b"\x00" * n
        self._remaining -= n
        return n


def test_oversize_upload_returns_413_and_cleans_up(client):
    total = 251 * 1024 * 1024  # 251 MB
    stream = io.BufferedReader(_ZeroStream(total))  # type: ignore[arg-type]
    with _patched_pipeline():
        resp = client.post(
            "/transcribe",
            files={"file": ("huge.mp3", stream, "audio/mpeg")},
        )
    assert resp.status_code == 413, resp.text
    assert "250MB" in resp.json()["detail"]
    # Temp file must NOT persist after rejection.
    assert list(client.upload_dir.iterdir()) == []


# ---------------------------------------------------------------------------
# Filenames are rewritten to UUID hex (malicious filename dropped)
# ---------------------------------------------------------------------------
def test_uploaded_filename_is_uuid_not_original(client):
    malicious = "malicious; name.mp3"
    with _patched_pipeline():
        resp = client.post(
            "/transcribe",
            files={"file": (malicious, b"abcdef", "audio/mpeg")},
        )
    assert resp.status_code == 200, resp.text
    stored = list(client.upload_dir.iterdir())
    assert len(stored) == 1
    name = stored[0].name
    assert "malicious" not in name
    assert ";" not in name
    assert " " not in name
    assert stored[0].suffix == ".mp3"
    assert len(stored[0].stem) == 32
    int(stored[0].stem, 16)


# ---------------------------------------------------------------------------
# CORS: allowed origin gets header; disallowed origin does not.
# ---------------------------------------------------------------------------
def test_cors_preflight_allows_localhost_5173(client):
    resp = client.options(
        "/transcribe",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "POST" in resp.headers.get("access-control-allow-methods", "")


def test_cors_preflight_allows_127_0_0_1_5173(client):
    resp = client.options(
        "/transcribe",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


# ---------------------------------------------------------------------------
# /stems/{file_id}/bass.wav
# ---------------------------------------------------------------------------
def _write_fake_bass(stems_dir: Path, file_id: str, content: bytes = b"RIFFFAKE") -> Path:
    target_dir = stems_dir / "htdemucs" / file_id
    target_dir.mkdir(parents=True, exist_ok=True)
    bass = target_dir / "bass.wav"
    bass.write_bytes(content)
    return bass


def test_get_bass_stem_returns_file(client):
    file_id = "a" * 32
    _write_fake_bass(client.stems_dir, file_id, b"RIFFFAKEWAVE")
    resp = client.get(f"/stems/{file_id}/bass.wav")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    assert resp.content == b"RIFFFAKEWAVE"


def test_get_bass_stem_missing_returns_404(client):
    file_id = "b" * 32
    resp = client.get(f"/stems/{file_id}/bass.wav")
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "bad_id",
    [
        "../../etc/passwd",
        "not-a-hex-id",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",  # uppercase — regex requires lowercase
        "a" * 31,  # too short
        "a" * 33,  # too long
    ],
)
def test_get_bass_stem_rejects_bad_file_id(client, bad_id):
    resp = client.get(f"/stems/{bad_id}/bass.wav")
    # FastAPI may 404 on path-mismatch (e.g. slashes); 400 on regex reject.
    assert resp.status_code in (400, 404)
    if resp.status_code == 400:
        assert "Invalid file id" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# /midi/{file_id}/bass.mid
# ---------------------------------------------------------------------------
def _write_fake_midi(midi_dir: Path, file_id: str, content: bytes = b"MThd") -> Path:
    target_dir = midi_dir / file_id
    target_dir.mkdir(parents=True, exist_ok=True)
    midi = target_dir / "bass.mid"
    midi.write_bytes(content)
    return midi


def test_get_bass_midi_returns_file(client):
    file_id = "c" * 32
    _write_fake_midi(client.midi_dir, file_id, b"MThdFAKEMIDI")
    resp = client.get(f"/midi/{file_id}/bass.mid")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/midi"
    assert resp.content == b"MThdFAKEMIDI"


def test_get_bass_midi_missing_returns_404(client):
    file_id = "d" * 32
    resp = client.get(f"/midi/{file_id}/bass.mid")
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "bad_id",
    [
        "../../etc/passwd",
        "not-a-hex-id",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "a" * 31,
        "a" * 33,
    ],
)
def test_get_bass_midi_rejects_bad_file_id(client, bad_id):
    resp = client.get(f"/midi/{bad_id}/bass.mid")
    assert resp.status_code in (400, 404)
    if resp.status_code == 400:
        assert "Invalid file id" in resp.json()["detail"]


def test_cors_disallowed_origin_has_no_allow_origin_header(client):
    resp = client.options(
        "/transcribe",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    # Starlette's CORSMiddleware rejects the preflight; the critical assertion
    # is that the allow-origin header is not granted to the foreign origin.
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example.com"
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers.keys()}
