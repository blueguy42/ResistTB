"""Primer pairs from Primer3, restricted to conserved sequence."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import primer3

from .thermo import SALT
from .variants import RegionMatrix, variable_sites


@dataclass
class PrimerPair:
    left_seq: str
    left_start: int  # genome, 1-based inclusive
    left_end: int
    left_tm: float
    left_gc: float
    right_seq: str  # 5'->3' on the reverse strand
    right_start: int
    right_end: int
    right_tm: float
    right_gc: float
    product_size: int
    penalty: float

    @property
    def amplicon(self) -> tuple[int, int]:
        return self.left_start, self.right_end


def isolate_perfect(rm: RegionMatrix, table: pd.DataFrame, ranges: list[tuple[int, int]]) -> np.ndarray:
    """Boolean per isolate: matches the population consensus with no missing base and no indel over
    every (start, end) genome range given."""
    cons = np.array(["ACGT".index(b) for b in table["consensus"]], dtype=np.uint8)
    ok = np.ones(len(rm.samples), dtype=bool)
    for s, e in ranges:
        lo, hi = s - rm.start, e - rm.start + 1
        ok &= ~((rm.codes[:, lo:hi] != cons[lo:hi]) | rm.indel[:, lo:hi]).any(axis=1)
    return ok


def design_primer_pairs(
    rm: RegionMatrix,
    table: pd.DataFrame,
    target_pos: int,
    n: int = 20,
    product: tuple[int, int] = (70, 160),
    tm_range: tuple[float, float] = (58.0, 64.0),
    max_maf: float = 0.02,
    min_minor: int = 2,
) -> list[PrimerPair]:
    """Pairs whose amplicon includes `target_pos`, with primers kept off any position that varies by more
    than `max_maf` (see variable_sites), is masked, has an indel, or is poorly covered. Sequence comes
    from the consensus."""
    n_iso = len(rm.samples)
    bad = (
        variable_sites(table, max_maf, min_minor)
        | table["masked"].to_numpy()
        | ((table["n_indel"] >= min_minor) & (table["n_indel"] / n_iso > max_maf)).to_numpy()
        | ((table["n_missing"] >= min_minor) & (table["n_missing"] / n_iso > max_maf)).to_numpy()
    )
    excluded = [[int(i), 1] for i in np.flatnonzero(bad)]
    args = {
        "SEQUENCE_ID": rm.name,
        "SEQUENCE_TEMPLATE": "".join(table["consensus"]),
        "SEQUENCE_TARGET": [target_pos - rm.start, 1],
        "SEQUENCE_EXCLUDED_REGION": excluded,
    }
    glob = {
        "PRIMER_OPT_SIZE": 20, "PRIMER_MIN_SIZE": 18, "PRIMER_MAX_SIZE": 25,
        "PRIMER_OPT_TM": sum(tm_range) / 2, "PRIMER_MIN_TM": tm_range[0], "PRIMER_MAX_TM": tm_range[1],
        "PRIMER_MIN_GC": 40.0, "PRIMER_MAX_GC": 65.0, "PRIMER_MAX_POLY_X": 4,
        "PRIMER_PRODUCT_SIZE_RANGE": [list(product)], "PRIMER_NUM_RETURN": n,
        "PRIMER_SALT_MONOVALENT": SALT["mv_conc"], "PRIMER_SALT_DIVALENT": SALT["dv_conc"],
        "PRIMER_DNTP_CONC": SALT["dntp_conc"], "PRIMER_DNA_CONC": SALT["dna_conc"],
    }
    res = primer3.bindings.design_primers(args, glob)
    pairs = []
    for i in range(res["PRIMER_PAIR_NUM_RETURNED"]):
        ls, ll = res[f"PRIMER_LEFT_{i}"]
        r5, rl = res[f"PRIMER_RIGHT_{i}"]  # r5 is the index of the reverse primer's 5' end
        pairs.append(
            PrimerPair(
                res[f"PRIMER_LEFT_{i}_SEQUENCE"], rm.start + ls, rm.start + ls + ll - 1,
                res[f"PRIMER_LEFT_{i}_TM"], res[f"PRIMER_LEFT_{i}_GC_PERCENT"],
                res[f"PRIMER_RIGHT_{i}_SEQUENCE"], rm.start + r5 - rl + 1, rm.start + r5,
                res[f"PRIMER_RIGHT_{i}_TM"], res[f"PRIMER_RIGHT_{i}_GC_PERCENT"],
                res[f"PRIMER_PAIR_{i}_PRODUCT_SIZE"], res[f"PRIMER_PAIR_{i}_PENALTY"],
            )
        )
    return pairs
