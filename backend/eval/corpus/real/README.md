# Real-bass eval corpus

Drop a clip in here and the eval harness will score the pipeline against
it on every run.

## Layout

```
real/
  manifest.json     ← metadata for every clip; commit this
  audio/            ← gitignored; large bass recordings live here
    <slug>.wav
    <slug>.mp3
  midi/             ← committed; ground-truth MIDI per clip
    <slug>.mid
```

## Adding a clip

1. Drop the audio under `real/audio/<slug>.<ext>`.
2. Hand-label the ground-truth MIDI in MuseScore / Logic / wherever and
   export to `real/midi/<slug>.mid`. Keep the line monophonic.
3. Run `python eval/corpus/real/add_clip.py <slug> --bpm <N> --time-sig 4/4`
   to register it in `manifest.json`.
4. Commit `manifest.json` + the new `.mid` file. The audio stays local
   (gitignored) — for the eval to run on someone else's machine they
   either drop in the same audio or re-record their own using the
   labelled MIDI as a guide.

## Running the eval against the real corpus

```bash
cd backend
source .venv/bin/activate
python eval/run_eval.py --corpus eval/corpus/real
```

The harness picks up every `.mid` under the corpus directory; it pairs
each one with the audio path the manifest lists.

## License hygiene

`manifest.json` records the source + license per clip so we don't ship
anything we shouldn't. Allowed buckets:

- `cc0` / `cc-by` / `cc-by-sa` — freesound, MedleyDB
- `research-only` — IDMT-SMT-Bass and similar academic datasets
- `original` — recordings made by the project owner

Anything else (commercial samples, copyrighted recordings) stays out
of the manifest entirely.
