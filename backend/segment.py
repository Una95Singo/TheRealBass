"""Music structure analysis: assign rehearsal letters (A/B/C...) per measure.

Uses librosa's Laplacian-segmentation recipe (McFee & Ellis, 2014) on the
full mix, then votes labels onto measure windows using the known BPM grid.

Kept separate from analyze.py so the label-mapping helper can be unit-tested
without importing librosa or music21.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _cluster_ids_to_labels(
    ids: Sequence[int],
    min_section_measures: int = 2,
) -> list[str]:
    """Convert per-measure cluster ids into rehearsal letters.

    Runs shorter than `min_section_measures` are merged into their longer
    neighbour so we don't emit one-bar sections. Labels are assigned by
    first-occurrence order: the first cluster id seen becomes "A", the next
    new one "B", and so on. Repeated cluster ids reuse their letter.
    """
    if not ids:
        return []

    # 1. Find runs of equal cluster id.
    runs: list[list[int]] = []  # [start, end_exclusive, cluster_id]
    start = 0
    for i in range(1, len(ids)):
        if ids[i] != ids[i - 1]:
            runs.append([start, i, ids[i - 1]])
            start = i
    runs.append([start, len(ids), ids[-1]])

    # 2. Merge too-short runs into the longer adjacent neighbour.
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for i, run in enumerate(runs):
            length = run[1] - run[0]
            if length >= min_section_measures:
                continue
            left = runs[i - 1] if i > 0 else None
            right = runs[i + 1] if i + 1 < len(runs) else None
            if left is None and right is None:
                break
            if left is None:
                target = right
            elif right is None:
                target = left
            else:
                target = left if (left[1] - left[0]) >= (right[1] - right[0]) else right
            target_id = target[2]
            # Absorb this run into its neighbour.
            if target is left:
                left[1] = run[1]
            else:
                right[0] = run[0]
            runs.pop(i)
            # Re-merge adjacent runs that now share a cluster id.
            merged: list[list[int]] = []
            for r in runs:
                if merged and merged[-1][2] == r[2]:
                    merged[-1][1] = r[1]
                else:
                    merged.append(r)
            runs = merged
            changed = True
            break

    # 3. Build per-measure label list using first-occurrence letter mapping.
    cluster_to_letter: dict[int, str] = {}
    labels: list[str] = [""] * len(ids)
    for run_start, run_end, cluster_id in runs:
        if cluster_id not in cluster_to_letter:
            idx = len(cluster_to_letter)
            cluster_to_letter[cluster_id] = _ALPHABET[idx % len(_ALPHABET)]
        letter = cluster_to_letter[cluster_id]
        for j in range(run_start, run_end):
            labels[j] = letter
    return labels


def detect_sections(
    audio_path: Path,
    bpm: int,
    beats_per_measure: int,
    num_measures: int,
    *,
    min_measures: int = 8,
    max_labels: int = 6,
) -> list[str] | None:
    """Return one A/B/C... label per measure, or None if detection is skipped.

    Short clips (fewer than `min_measures` measures) are treated as a single
    section and return None so the caller can omit the field entirely.
    """
    if num_measures < min_measures or bpm <= 0 or beats_per_measure <= 0:
        return None

    # Heavy deps are imported lazily so unit tests for the label helper
    # don't pay the librosa startup cost.
    import librosa
    import numpy as np
    from scipy import sparse
    from sklearn.cluster import KMeans

    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    if y.size == 0:
        return None

    hop_length = 512
    # Beat grid driven by the BPM we already trust from analyze_midi rather
    # than re-estimating — keeps measure alignment consistent downstream.
    _tempo, beat_frames = librosa.beat.beat_track(
        y=y, sr=sr, bpm=float(bpm), hop_length=hop_length, trim=False
    )
    if beat_frames.size < beats_per_measure * 2:
        return None

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop_length, n_mfcc=13)

    chroma_sync = librosa.util.sync(chroma, beat_frames, aggregate=np.median)
    mfcc_sync = librosa.util.sync(mfcc, beat_frames, aggregate=np.mean)

    # Recurrence (chroma) + path sequence (MFCC) affinities, normalised and
    # combined exactly as in the librosa Laplacian-segmentation tutorial.
    rec = librosa.segment.recurrence_matrix(
        chroma_sync, width=3, mode="affinity", sym=True
    )
    df = librosa.segment.timelag_filter(lambda x: x, pad=False)
    rec = df(rec)

    path_distance = np.sum(np.diff(mfcc_sync, axis=1) ** 2, axis=0)
    sigma = np.median(path_distance) or 1.0
    path_sim = np.exp(-path_distance / sigma)
    n_frames = chroma_sync.shape[1]
    path = np.zeros((n_frames, n_frames), dtype=float)
    for i in range(n_frames - 1):
        path[i, i + 1] = path_sim[i]
        path[i + 1, i] = path_sim[i]

    mu = rec.mean() / (path.mean() + 1e-9) if path.mean() > 0 else 1.0
    affinity = rec + mu * path
    affinity = np.maximum(affinity, affinity.T)

    degree = affinity.sum(axis=1)
    d_inv_sqrt = 1.0 / np.sqrt(np.maximum(degree, 1e-9))
    laplacian = np.eye(n_frames) - (d_inv_sqrt[:, None] * affinity * d_inv_sqrt[None, :])
    laplacian = (laplacian + laplacian.T) / 2

    try:
        eigvals, eigvecs = sparse.linalg.eigsh(
            sparse.csr_matrix(laplacian),
            k=min(max_labels + 1, n_frames - 1),
            which="SM",
        )
    except Exception:
        eigvals, eigvecs = np.linalg.eigh(laplacian)
        eigvals = eigvals[: max_labels + 1]
        eigvecs = eigvecs[:, : max_labels + 1]

    order = np.argsort(eigvals)
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]

    # Pick k by the largest eigengap in [2, max_labels].
    upper = min(max_labels, len(eigvals) - 1)
    gaps = np.diff(eigvals[: upper + 1])
    k = 2 if gaps.size < 2 else int(np.argmax(gaps[1:]) + 2)
    k = max(2, min(k, max_labels))

    embedding = eigvecs[:, :k]
    norms = np.linalg.norm(embedding, axis=1, keepdims=True)
    embedding = embedding / np.maximum(norms, 1e-9)

    kmeans = KMeans(n_clusters=k, n_init=10, random_state=0)
    frame_labels = kmeans.fit_predict(embedding)

    # 4. Majority-vote beat-frame labels onto measure windows.
    measure_ids: list[int] = []
    for m_idx in range(num_measures):
        lo = m_idx * beats_per_measure
        hi = lo + beats_per_measure
        if lo >= frame_labels.size:
            measure_ids.append(int(measure_ids[-1]) if measure_ids else 0)
            continue
        window = frame_labels[lo : min(hi, frame_labels.size)]
        if window.size == 0:
            measure_ids.append(int(measure_ids[-1]) if measure_ids else 0)
            continue
        vals, counts = np.unique(window, return_counts=True)
        measure_ids.append(int(vals[int(np.argmax(counts))]))

    return _cluster_ids_to_labels(measure_ids)
