"""Variant table: for a genome region, what every finished isolate has at every position."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .genome import LETTERS, MISSING
from .isolates import finished_samples, read_aligned, read_vcf


@dataclass
class RegionMatrix:
    """Base codes for one region: rows are isolates, columns are positions start..end (1-based)."""

    name: str
    start: int
    end: int
    samples: list[str]
    codes: np.ndarray  # shape (n_samples, end - start + 1), uint8
    indel: np.ndarray  # shape (n_samples, end - start + 1), bool: an insertion/deletion/complex call overlaps


def build_region_matrices(
    results_dir: str | Path,
    regions: dict[str, tuple[int, int]],
    samples: list[str] | None = None,
) -> dict[str, RegionMatrix]:
    """Read every finished isolate once and cut out each region. Regions are (start, end), 1-based inclusive."""
    samples = samples or finished_samples(results_dir)
    out = {
        name: RegionMatrix(
            name, s, e, samples,
            np.empty((len(samples), e - s + 1), dtype=np.uint8),
            np.zeros((len(samples), e - s + 1), dtype=bool),
        )
        for name, (s, e) in regions.items()
    }
    for i, sample in enumerate(samples):
        aligned = read_aligned(results_dir, sample)
        vcf = read_vcf(results_dir, sample)
        indels = vcf[vcf["type"].isin(["ins", "del", "complex"])]
        for rm in out.values():
            rm.codes[i] = aligned[rm.start - 1 : rm.end]
            hit = indels[(indels["pos"] <= rm.end) & (indels["pos"] + indels["ref"].str.len() - 1 >= rm.start)]
            for pos, ref in zip(hit["pos"], hit["ref"]):
                lo = max(pos, rm.start) - rm.start
                hi = min(pos + len(ref) - 1, rm.end) - rm.start
                rm.indel[i, lo : hi + 1] = True
    return out


def position_table(rm: RegionMatrix, ref: np.ndarray, mask: np.ndarray | None = None) -> pd.DataFrame:
    """One row per position: base counts, missing, indel count, and variation measured two ways.

    alt_freq is against the H37Rv reference. maf is the minor-allele frequency against the population
    consensus (the most common base among covered isolates; the reference where nothing is covered).
    Conserved-window design uses the consensus, because a position that differs from H37Rv in every
    isolate is still perfectly conserved in the population."""
    n = len(rm.samples)
    ref_region = ref[rm.start - 1 : rm.end]
    counts = {b: (rm.codes == i).sum(axis=0) for i, b in enumerate(LETTERS)}
    count_matrix = np.stack([counts[b] for b in LETTERS])  # shape (4, L)
    missing = (rm.codes == MISSING).sum(axis=0)
    covered = n - missing
    ref_count = np.choose(ref_region, [counts[b] for b in LETTERS])
    alt = covered - ref_count
    consensus = np.where(covered > 0, count_matrix.argmax(axis=0), ref_region).astype(np.uint8)
    top = count_matrix.max(axis=0)
    table = pd.DataFrame(
        {
            "pos": np.arange(rm.start, rm.end + 1),
            "ref": [LETTERS[c] for c in ref_region],
            "n_isolates": n,
            "n_covered": covered,
            "n_missing": missing,
            "n_alt": alt,
            "alt_freq": np.where(covered > 0, alt / np.maximum(covered, 1), np.nan),
            "consensus": [LETTERS[c] for c in consensus],
            "maf": np.where(covered > 0, (covered - top) / np.maximum(covered, 1), np.nan),
            "n_minor": covered - top,
            "n_indel": rm.indel.sum(axis=0),
            **{f"n_{b}": counts[b] for b in LETTERS},
        }
    )
    table["masked"] = mask[rm.start - 1 : rm.end] if mask is not None else False
    return table


def variable_sites(table: pd.DataFrame, max_maf: float = 0.02, min_minor: int = 2) -> np.ndarray:
    """Boolean per position: varies enough to matter for oligo design.

    A site counts when its minor-allele frequency exceeds max_maf AND at least min_minor isolates carry
    the minor allele. The count floor stops a single isolate from blocking every window while the isolate
    set is small; the coverage numbers still count that isolate as a mismatch."""
    return ((table["maf"].fillna(1.0) > max_maf) & (table["n_minor"] >= min_minor)).to_numpy()
