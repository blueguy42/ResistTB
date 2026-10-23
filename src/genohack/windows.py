"""Rank candidate primer-binding windows by how conserved they are across isolates."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .genome import LETTERS, MISSING
from .variants import RegionMatrix

END_BASES = 5  # bases at each end of a window that count extra: a mismatch there hurts most
END_WEIGHT = 3.0


def _homopolymer(seq: str) -> int:
    return max((len(m.group(0)) for m in re.finditer(r"(.)\1*", seq)), default=0)


def rank_windows(
    rm: RegionMatrix,
    table: pd.DataFrame,
    ref: np.ndarray,
    lengths: range = range(18, 27),
    gc_range: tuple[float, float] = (40.0, 65.0),
    max_homopolymer: int = 4,
    allow_masked: bool = False,
    exclude: tuple[int, int] | None = None,
) -> pd.DataFrame:
    """Score every window of the given lengths in a region.

    Windows are read from the population consensus, not H37Rv. perfect_frac is the share of isolates whose
    sequence over the whole window equals that consensus with no missing base and no overlapping indel.
    burden adds up per-position variation (minor-allele frequency plus indel frequency plus missing
    fraction), counting the end bases END_WEIGHT times. A better window has higher perfect_frac, then
    lower burden. ref_diffs counts positions where the consensus differs from H37Rv. `exclude` drops windows overlapping a genome range
    (for example the mutation a probe will sit on)."""
    n = len(rm.samples)
    ref_region = ref[rm.start - 1 : rm.end]
    cons_region = np.array(["ACGT".index(b) for b in table["consensus"]], dtype=np.uint8)
    mismatch = (rm.codes != cons_region) | rm.indel  # MISSING != any base, so missing counts as a mismatch
    cs = np.concatenate([np.zeros((n, 1), dtype=np.int32), np.cumsum(mismatch, axis=1, dtype=np.int32)], axis=1)

    per_pos = (
        table["maf"].fillna(1.0).to_numpy()
        + table["n_indel"].to_numpy() / n
        + table["n_missing"].to_numpy() / n
    )
    masked = table["masked"].to_numpy()
    seq = "".join(table["consensus"])
    differs = (cons_region != ref_region).astype(int)

    rows = []
    for length in lengths:
        if length > len(seq):
            continue
        weights = np.ones(length)
        weights[:END_BASES] = END_WEIGHT
        weights[-END_BASES:] = END_WEIGHT
        starts = np.arange(0, len(seq) - length + 1)
        bad = (cs[:, starts + length] - cs[:, starts]) > 0
        perfect = n - bad.sum(axis=0)
        burden = np.array([float(per_pos[s : s + length] @ weights) for s in starts])
        for k, s in enumerate(starts):
            w = seq[s : s + length]
            gc = 100.0 * (w.count("G") + w.count("C")) / length
            g_start = rm.start + int(s)
            g_end = g_start + length - 1
            if "N" in w or not gc_range[0] <= gc <= gc_range[1] or _homopolymer(w) > max_homopolymer:
                continue
            if not allow_masked and masked[s : s + length].any():
                continue
            if exclude and g_start <= exclude[1] and g_end >= exclude[0]:
                continue
            rows.append(
                (g_start, g_end, length, w, round(gc, 1), int(perfect[k]), perfect[k] / n,
                 round(float(burden[k]), 4), float(per_pos[s : s + length].max()), int(differs[s : s + length].sum()))
            )
    out = pd.DataFrame(
        rows,
        columns=["start", "end", "length", "sequence", "gc", "perfect_isolates", "perfect_frac", "burden", "max_site_variation", "ref_diffs"],
    )
    out["region"] = rm.name
    return out.sort_values(["perfect_frac", "burden", "length"], ascending=[False, True, True]).reset_index(drop=True)
