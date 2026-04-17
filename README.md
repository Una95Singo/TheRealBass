# TheRealBass

A fully local bass transcription web app. Upload an audio file; the app isolates
the bass stem, transcribes it to MIDI, and renders a Real Book-style bass-clef
lead sheet with key, BPM, and time signature.

Everything runs on `localhost` — no external APIs.

## Stack

- **Backend:** FastAPI, Demucs (bass isolation), Spotify Basic Pitch (MIDI
  transcription), music21 (quantization + key/tempo analysis)
- **Frontend:** React (Vite) + VexFlow (notation rendering)

## Folder structure

```
TheRealBass/
├── backend/
│   ├── main.py
│   ├── isolate.py
│   ├── transcribe.py
│   ├── analyze.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── UploadZone.jsx
│   │   │   ├── ProcessingView.jsx
│   │   │   ├── TranscriptionView.jsx
│   │   │   └── NotationRenderer.jsx
│   │   └── api.js
│   └── package.json
└── README.md
```

## First-run setup

### 1. Backend (Python venv)

The backend must be run inside a Python virtual environment. Python 3.10+ is
recommended.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

All dependency versions in `requirements.txt` are pinned exactly.

> **Note:** On the first transcription, Demucs downloads the `htdemucs` model
> weights (~1GB) into your Torch cache (`~/.cache/torch/hub/`). Subsequent runs
> use the cached weights. Basic Pitch bundles its own (much smaller) model.

Start the API:

```bash
# from backend/ with the venv active
python main.py
# → http://127.0.0.1:8000
```

### 2. Frontend (Vite)

```bash
cd frontend
npm install
npm run dev
# → http://127.0.0.1:5173
```

Open the Vite URL in your browser. The frontend only calls `http://127.0.0.1:8000`.

## API

### `POST /transcribe`

Multipart form upload with a single `file` field.

- **Max file size:** 50MB
- **Accepted MIME types:** `audio/mpeg`, `audio/wav`, `audio/x-wav`,
  `audio/mp4`, `audio/x-m4a` (mp3 / wav / m4a)
- **Invalid type:** returns `400`
- **Oversize:** returns `413`

Response shape:

```json
{
  "key": "G major",
  "bpm": 120,
  "time_signature": "4/4",
  "measures": [
    {
      "measure_number": 1,
      "notes": [
        { "pitch": "G2", "duration": "q", "start_beat": 1 },
        { "pitch": "D2", "duration": "q", "start_beat": 2 }
      ]
    }
  ],
  "bass_stem_path": "/tmp/therealbass/stems"
}
```

Duration codes follow VexFlow: `w`, `h`, `q`, `8`, `16`, `32`, with `d` suffix
for dotted values (e.g. `qd`).

## Security & dependencies

- Backend runs in a Python virtual environment.
- All dependency versions are pinned exactly — no `>=` or `~` ranges.
- Uploaded filenames are discarded; files are stored under a server-generated
  UUID plus the MIME-derived extension.
- A 50MB upload limit is enforced server-side (streaming check; rejects
  oversized uploads mid-stream with `413`).
- File type is validated server-side by MIME type. Only mp3, wav, and m4a are
  accepted; everything else returns `400`.
- All uploaded audio, isolated stems, and MIDI files are written under
  `/tmp/therealbass/` only. A path-traversal guard prevents writes outside it.
- The frontend only calls `http://127.0.0.1:8000` — no external network calls.
- CORS is restricted to the Vite dev server origin.
