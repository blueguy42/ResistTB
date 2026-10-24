"""Resistance targets for the prototype, located from gene annotation instead of typed-in coordinates."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .genome import Gene, load_genes


@dataclass(frozen=True)
class Target:
    id: str
    gene: str
    drug: str
    mutation: str  # protein or promoter change
    pos: int  # genome position of the changed base on NC_000962.3
    ref: str  # reference base on the forward strand
    alt: str  # resistance allele on the forward strand
    n_resistant: int = 0  # resistant isolates the WHO catalogue lists with this variant (0 for the hand-built targets)


def default_targets(genes: dict[str, Gene] | None = None) -> list[Target]:
    g = genes or load_genes()
    rc = {"A": "T", "C": "G", "G": "C", "T": "A"}

    def coding(gene: str, ref: str, alt: str) -> tuple[str, str]:
        """Convert coding-strand bases to forward-strand bases."""
        return (ref, alt) if g[gene].strand == "+" else (rc[ref], rc[alt])

    rpob_ref, rpob_alt = coding("rpoB", "C", "T")  # TCG -> TTG, Ser450Leu
    katg_ref, katg_alt = coding("katG", "G", "C")  # AGC -> ACC, Ser315Thr
    gyra_ref, gyra_alt = coding("gyrA", "A", "G")  # GAC -> GGC, Asp94Gly
    inha_ref, inha_alt = coding("fabG1", "C", "T")  # c.-15C>T, upstream of fabG1/inhA
    return [
        Target("rpoB_S450L", "rpoB", "Rifampicin", "p.Ser450Leu", g["rpoB"].codon_pos(450, 2), rpob_ref, rpob_alt),
        Target("katG_S315T", "katG", "Isoniazid", "p.Ser315Thr", g["katG"].codon_pos(315, 2), katg_ref, katg_alt),
        Target("inhA_c-15", "fabG1", "Isoniazid, ethionamide", "c.-15C>T", g["fabG1"].upstream_pos(15), inha_ref, inha_alt),
        Target("gyrA_D94G", "gyrA", "Fluoroquinolones", "p.Asp94Gly", g["gyrA"].codon_pos(94, 2), gyra_ref, gyra_alt),
    ]


MIN_RESISTANT = 10  # WHO catalogue variants seen in at least this many resistant isolates become targets

# A specific single-base change by name: amino acid (p.Met306Val), stop gained (p.Gln125*), start lost (p.Met1?),
# promoter (c.-14C>T) or rRNA (n.1401A>G). Names such as pncA_LoF stand for many mutations and are not one change,
# even though the catalogue gives them a representative position.
_SPECIFIC = re.compile(r"^[A-Za-z0-9]+_(p\.[A-Z][a-z]{2}\d+([A-Z][a-z]{2}|\*|\?)|c\.-?\d+[ACGT]>[ACGT]|n\.\d+[ACGT]>[ACGT])$")


def who_targets(min_resistant: int = MIN_RESISTANT) -> list[Target]:
    """One target per WHO catalogue variant that is a single-base change with a genome position.

    The catalogue already gives the position and the forward-strand bases, so no codon arithmetic is needed (all of
    them match H37Rv; tests/test_targets.py checks). The id is the catalogue's own variant name, for example
    embB_p.Met306Val. Variants without a position (loss-of-function, indels) cannot be one allele-specific probe."""
    from .who import load_catalogue

    cat = load_catalogue()
    cat = cat[cat["pos"].notna() & (cat["ref"].str.len() == 1) & (cat["alt"].str.len() == 1)]
    cat = cat[cat["variant"].map(lambda v: bool(_SPECIFIC.match(v)))]
    out = []
    for variant, rows in cat.groupby("variant", sort=False):
        counts = rows["present_R"].fillna(0)  # the catalogue leaves the count blank for some variants: not enough to rank
        n = int(counts.max())
        if n < min_resistant:
            continue
        first = rows.loc[counts.idxmax()]
        gene, _, mutation = variant.partition("_")
        out.append(Target(variant, gene, ", ".join(sorted(set(rows["drug"]))), mutation, int(first["pos"]),
                          first["ref"], first["alt"], n))
    return sorted(out, key=lambda t: -t.n_resistant)


def all_targets(genes: dict[str, Gene] | None = None, min_resistant: int = MIN_RESISTANT) -> list[Target]:
    """The four hand-built targets (kept with their ids) plus every WHO target not already among them."""
    from dataclasses import replace

    who = who_targets(0)
    count = {(t.pos, t.alt): t.n_resistant for t in who}
    base = [replace(t, n_resistant=count.get((t.pos, t.alt), 0)) for t in default_targets(genes)]
    seen = {(t.pos, t.alt) for t in base}
    return base + [t for t in who if t.n_resistant >= min_resistant and (t.pos, t.alt) not in seen]
