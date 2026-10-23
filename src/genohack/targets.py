"""Resistance targets for the prototype, located from gene annotation instead of typed-in coordinates."""
from __future__ import annotations

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
