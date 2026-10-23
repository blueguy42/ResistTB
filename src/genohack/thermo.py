"""Thermodynamic helpers. One set of salt and concentration settings is used everywhere so Tm values
for primers and probes are comparable (typical qPCR conditions)."""
from __future__ import annotations

import primer3

SALT = dict(mv_conc=50.0, dv_conc=3.0, dntp_conc=0.8, dna_conc=250.0)
_COMP = str.maketrans("ACGTN", "TGCAN")


def revcomp(seq: str) -> str:
    return seq.upper().translate(_COMP)[::-1]


def gc(seq: str) -> float:
    return 100.0 * sum(b in "GC" for b in seq.upper()) / len(seq)


def tm(seq: str) -> float:
    return primer3.calc_tm(seq, **SALT)


def duplex_tm(probe: str, partner: str) -> float:
    """Melting temperature of `probe` annealed to `partner` (both 5'->3'). The alignment may include
    mismatches, so a mismatched partner gives a lower Tm than the perfect partner."""
    return primer3.calc_heterodimer(probe, partner, **SALT).tm


def hairpin_dg(seq: str) -> float:
    return primer3.calc_hairpin(seq, **SALT).dg / 1000.0  # kcal/mol


def homodimer_dg(seq: str) -> float:
    return primer3.calc_homodimer(seq, **SALT).dg / 1000.0


def heterodimer_dg(a: str, b: str) -> float:
    return primer3.calc_heterodimer(a, b, **SALT).dg / 1000.0


def homopolymer(seq: str) -> int:
    best = run = 1
    for a, b in zip(seq, seq[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    return best
