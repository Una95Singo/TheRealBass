"""Register a real-bass clip in the corpus manifest.

Usage:
    python eval/corpus/real/add_clip.py <slug> [--audio audio/<slug>.wav]
        [--midi midi/<slug>.mid] [--bpm 95] [--time-sig 4/4]
        [--source freesound:12345] [--license cc0]
        [--notes "isolated DI bass, fingerstyle"]

Validates that the audio + MIDI files exist on disk before writing the
entry. Idempotent: re-running with the same slug updates the existing
entry instead of duplicating it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.json"
ALLOWED_LICENSES = {"cc0", "cc-by", "cc-by-sa", "research-only", "original"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="Short identifier, also the file basename.")
    parser.add_argument("--audio", default=None,
                        help="Audio path relative to corpus/real/. "
                             "Defaults to audio/<slug>.wav.")
    parser.add_argument("--midi", default=None,
                        help="Ground-truth MIDI path relative to corpus/real/. "
                             "Defaults to midi/<slug>.mid.")
    parser.add_argument("--bpm", type=float, required=True)
    parser.add_argument("--time-sig", default="4/4")
    parser.add_argument("--source", default="unknown",
                        help="Where the audio came from, e.g. freesound:12345.")
    parser.add_argument("--license", required=True, choices=sorted(ALLOWED_LICENSES))
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    audio_rel = args.audio or f"audio/{args.slug}.wav"
    midi_rel = args.midi or f"midi/{args.slug}.mid"
    audio_path = HERE / audio_rel
    midi_path = HERE / midi_rel

    if not audio_path.is_file():
        print(f"audio not found: {audio_path}", file=sys.stderr)
        return 1
    if not midi_path.is_file():
        print(f"midi not found: {midi_path}", file=sys.stderr)
        return 1

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {
        "schema_version": 1, "clips": [],
    }
    entry = {
        "slug": args.slug,
        "audio": audio_rel,
        "midi": midi_rel,
        "bpm": args.bpm,
        "time_sig": args.time_sig,
        "source": args.source,
        "license": args.license,
        "notes": args.notes,
    }
    clips = [c for c in manifest.get("clips", []) if c.get("slug") != args.slug]
    clips.append(entry)
    clips.sort(key=lambda c: c["slug"])
    manifest["clips"] = clips
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"registered {args.slug} ({len(clips)} total clips)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
