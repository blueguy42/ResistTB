"""Allele-discriminating probes: one wild-type and one mutant probe over a resistance SNP."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .targets import Target
from .thermo import duplex_tm, gc, homopolymer, revcomp, tm
from .variants import variable_sites


@dataclass
class ProbePair:
    start: int  # genome, 1-based inclusive
    end: int
    strand: str  # "+" probe equals the forward strand, "-" its reverse complement
    wt_seq: str
    mut_seq: str
    wt_tm: float
    mut_tm: float
    wt_gap: float  # Tm drop of the wild-type probe on the mutant target
    mut_gap: float  # Tm drop of the mutant probe on the wild-type target
    snp_offset: int  # 0-based position of the SNP within the probe sequence

    @property
    def gap(self) -> float:
        return min(self.wt_gap, self.mut_gap)


def design_probes(
    table: pd.DataFrame,
    target: Target,
    lengths: range = range(20, 31),
    tm_range: tuple[float, float] = (64.0, 74.0),
    gc_range: tuple[float, float] = (30.0, 75.0),
    max_maf: float = 0.02,
    min_minor: int = 2,
    min_flank: int = 4,
    allow_5prime_g: bool = False,
) -> list[ProbePair]:
    """All acceptable probe windows over the target SNP, best discrimination first.

    The wild-type probe is read from the population consensus and the mutant probe differs only at the
    SNP. Discrimination is the Tm drop when a probe meets the other allele, estimated with Primer3's
    thermodynamic alignment (a model, not a measurement). Windows are rejected if another variable site
    (see variable_sites) falls inside them, if the SNP is within `min_flank` bases of either end, or if the
    probe starts with G (which quenches the 5' fluorophore)."""
    t0 = int(table["pos"].iloc[0])
    cons = "".join(table["consensus"])
    variable = variable_sites(table, max_maf, min_minor)
    snp = target.pos - t0
    if cons[snp] != target.ref:
        return []  # population consensus is not the reference allele at the SNP; needs separate handling
    out: list[ProbePair] = []
    for length in lengths:
        for lo in range(snp - length + 1 + min_flank, snp - min_flank + 1):
            hi = lo + length
            if lo < 0 or hi > len(cons):
                continue
            others = [i for i in range(lo, hi) if i != snp and variable[i]]
            if others:
                continue
            wt_fwd = cons[lo:hi]
            mut_fwd = wt_fwd[: snp - lo] + target.alt + wt_fwd[snp - lo + 1 :]
            for strand in ("+", "-"):
                wt = wt_fwd if strand == "+" else revcomp(wt_fwd)
                mut = mut_fwd if strand == "+" else revcomp(mut_fwd)
                if (wt[0] == "G" and not allow_5prime_g) or (mut[0] == "G" and not allow_5prime_g):
                    continue
                if not gc_range[0] <= gc(wt) <= gc_range[1] or max(homopolymer(wt), homopolymer(mut)) > 4:
                    continue
                t_wt, t_mut = tm(wt), tm(mut)
                if not (tm_range[0] <= t_wt <= tm_range[1] and tm_range[0] <= t_mut <= tm_range[1]):
                    continue
                # A probe's partner is the reverse complement of the sequence it matches.
                wt_gap = t_wt - duplex_tm(wt, revcomp(mut))
                mut_gap = t_mut - duplex_tm(mut, revcomp(wt))
                offset = snp - lo if strand == "+" else hi - 1 - snp
                out.append(ProbePair(t0 + lo, t0 + hi - 1, strand, wt, mut, t_wt, t_mut, wt_gap, mut_gap, offset))
    return sorted(out, key=lambda p: (-p.gap, abs((p.wt_tm + p.mut_tm) / 2 - 69.0)))
