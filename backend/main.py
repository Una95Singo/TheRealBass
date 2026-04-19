"""FastAPI entry point for TheRealBass."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from analyze import analyze_midi
from isolate import isolate_bass
from segment import detect_sections
from transcribe import transcribe_to_midi

MAX_FILE_BYTES = 250 * 1024 * 1024  # 250MB
STORAGE_ROOT = Path("/tmp/therealbass").resolve()
UPLOAD_DIR = STORAGE_ROOT / "uploads"
STEMS_DIR = STORAGE_ROOT / "stems"
MIDI_DIR = STORAGE_ROOT / "midi"

ALLOWED_MIME_TYPES = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
}

for d in (UPLOAD_DIR, STEMS_DIR, MIDI_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="TheRealBass")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _safe_child(parent: Path, child: Path) -> Path:
    """Guarantee child resolves inside parent; prevents path traversal."""
    resolved = child.resolve()
    if parent not in resolved.parents and resolved != parent:
        raise HTTPException(status_code=400, detail="Invalid path.")
    return resolved


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)) -> dict:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: mp3, wav, m4a.",
        )

    extension = ALLOWED_MIME_TYPES[file.content_type]
    file_id = uuid.uuid4().hex
    safe_name = f"{file_id}{extension}"
    upload_path = _safe_child(UPLOAD_DIR, UPLOAD_DIR / safe_name)

    bytes_written = 0
    try:
        with upload_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > MAX_FILE_BYTES:
                    out.close()
                    upload_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds 250MB limit.",
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")

    midi_subdir = _safe_child(MIDI_DIR, MIDI_DIR / file_id)
    midi_subdir.mkdir(parents=True, exist_ok=True)
    try:
        bass_stem = isolate_bass(upload_path, STEMS_DIR)
        midi_path, note_events = transcribe_to_midi(bass_stem, midi_subdir)
        # Normalize Basic Pitch's bass_basic_pitch.mid → bass.mid for a clean URL.
        canonical_midi = midi_subdir / "bass.mid"
        if midi_path != canonical_midi:
            midi_path.replace(canonical_midi)
            midi_path = canonical_midi
        result = analyze_midi(midi_path, note_events=note_events)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")

    # Section analysis is best-effort: a failure here (missing librosa,
    # decode error, very short clip) must not kill the transcription.
    try:
        sections = detect_sections(
            upload_path,
            bpm=int(result["bpm"]),
            beats_per_measure=int(result["time_signature"].split("/")[0]),
            num_measures=len(result["measures"]),
        )
    except Exception:
        sections = None
    if sections and len(sections) == len(result["measures"]):
        for measure, label in zip(result["measures"], sections):
            measure["section"] = label

    result["bass_stem_path"] = str(bass_stem)
    result["file_id"] = file_id
    result["bass_audio_url"] = f"/stems/{file_id}/bass.wav"
    result["midi_url"] = f"/midi/{file_id}/bass.mid"
    return result


_UUID_HEX_RE = re.compile(r"^[0-9a-f]{32}$")


@app.get("/stems/{file_id}/bass.wav")
def get_bass_stem(file_id: str) -> FileResponse:
    if not _UUID_HEX_RE.match(file_id):
        raise HTTPException(status_code=400, detail="Invalid file id.")

    bass_path = _safe_child(STEMS_DIR, STEMS_DIR / "htdemucs" / file_id / "bass.wav")
    if not bass_path.is_file():
        raise HTTPException(status_code=404, detail="Bass stem not found.")
    return FileResponse(str(bass_path), media_type="audio/wav")


@app.get("/midi/{file_id}/bass.mid")
def get_bass_midi(file_id: str) -> FileResponse:
    if not _UUID_HEX_RE.match(file_id):
        raise HTTPException(status_code=400, detail="Invalid file id.")

    midi_path = _safe_child(MIDI_DIR, MIDI_DIR / file_id / "bass.mid")
    if not midi_path.is_file():
        raise HTTPException(status_code=404, detail="MIDI not found.")
    return FileResponse(str(midi_path), media_type="audio/midi")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
