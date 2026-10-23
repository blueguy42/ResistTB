"""In-silico checks on a set of oligos: self and cross interactions, and near-matches elsewhere in H37Rv.

Specificity here covers H37Rv only. Human and non-tuberculous mycobacteria need a BLAST database and are
reported as not checked until that has been run."""
from __future__ import annotations

from itertools import combinations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from .genome import encode
from .thermo import revcomp, heterodimer_dg, hairpin_dg, homodimer_dg


def interactions(oligos: dict[str, str]) -> dict:
    """Worst-case folding and dimer free energies (kcal/mol, more negative is worse) for named oligos."""
    hairpins = {n: hairpin_dg(s) for n, s in oligos.items()}
    selfdim = {n: homodimer_dg(s) for n, s in oligos.items()}
    cross = {f"{a}|{b}": heterodimer_dg(oligos[a], oligos[b]) for a, b in combinations(oligos, 2)}
    worst = min(cross.items(), key=lambda kv: kv[1]) if cross else ("", 0.0)
    return {"hairpin": hairpins, "self_dimer": selfdim, "cross_dimer": cross, "worst_cross": worst}


_CACHE: dict[tuple, tuple[int, ...]] = {}


def _hit_starts(seq: str, ref: np.ndarray, max_mismatch: int, clamp: int) -> tuple[int, ...]:
    """1-based start of every near-match on either strand. Cached: the same primer appears in many pairs."""
    key = (seq, id(ref), max_mismatch, clamp)
    if key in _CACHE:
        return _CACHE[key]
    n = len(seq)
    starts: list[int] = []
    for strand, query in (("+", encode(seq)), ("-", encode(revcomp(seq)))):
        view = sliding_window_view(ref, n)
        ok = (view != query).sum(axis=1) <= max_mismatch
        if clamp:
            tail = slice(n - clamp, n) if strand == "+" else slice(0, clamp)  # 3' end of the oligo on this strand
            ok &= (view[:, tail] == query[tail]).all(axis=1)
        starts += [int(i) + 1 for i in np.flatnonzero(ok)]
    _CACHE[key] = tuple(starts)
    return _CACHE[key]


def genome_hits(
    seq: str,
    ref: np.ndarray,
    intended: tuple[int, int],
    max_mismatch: int = 2,
    clamp: int = 0,
) -> int:
    """Near-matches of `seq` (either strand) elsewhere in the reference genome.

    A hit has at most `max_mismatch` mismatches over the whole oligo. For a primer, set `clamp` to the number
    of 3' bases that must match exactly (a primer extends only from a matched 3' end); 0 disables the rule.
    `intended` is the oligo's own (start, end) 1-based site, which is not counted."""
    n = len(seq)
    return sum(1 for st in _hit_starts(seq, ref, max_mismatch, clamp) if not (st <= intended[1] and st + n - 1 >= intended[0]))
