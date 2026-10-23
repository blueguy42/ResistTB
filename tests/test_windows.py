import numpy as np

from genohack.genome import encode
from genohack.variants import RegionMatrix, position_table
from genohack.windows import rank_windows


def make_region(rows: list[str], ref: str):
    codes = np.stack([encode(r) for r in rows])
    rm = RegionMatrix("t", 1, len(ref), [f"s{i}" for i in range(len(rows))], codes, np.zeros(codes.shape, dtype=bool))
    ref_codes = encode(ref)
    return rm, ref_codes, position_table(rm, ref_codes)


REF = "ACGTTGCAAGCTTCGGATCCGATCGTACGATTGCAGCTAGCTTAGGC"


def test_variable_site_lowers_perfect_fraction():
    mutant = list(REF)
    mutant[20] = "A" if REF[20] != "A" else "C"
    rm, ref, table = make_region([REF] * 3 + ["".join(mutant)], REF)
    w = rank_windows(rm, table, ref, lengths=range(18, 19), gc_range=(0, 100), max_homopolymer=10)
    covering = w[(w.start <= 21) & (w.end >= 21)]
    assert (covering.perfect_isolates == 3).all()
    clean = w[(w.end < 21) | (w.start > 21)]
    assert (clean.perfect_isolates == 4).all()


def test_consensus_beats_reference():
    # Every isolate differs from the reference at one site: the site is conserved in the population.
    iso = list(REF)
    iso[20] = "A" if REF[20] != "A" else "C"
    rm, ref, table = make_region(["".join(iso)] * 4, REF)
    w = rank_windows(rm, table, ref, lengths=range(18, 19), gc_range=(0, 100), max_homopolymer=10)
    assert (w.perfect_frac == 1.0).all()
    assert (w[(w.start <= 21) & (w.end >= 21)].ref_diffs == 1).all()
    assert table.loc[20, "consensus"] == iso[20]


def test_missing_bases_count_against_a_window():
    gap = REF[:20] + "N" + REF[21:]
    rm, ref, table = make_region([REF, REF, gap], REF)
    w = rank_windows(rm, table, ref, lengths=range(18, 19), gc_range=(0, 100), max_homopolymer=10)
    assert (w[(w.start <= 21) & (w.end >= 21)].perfect_isolates == 2).all()


def test_exclude_drops_overlapping_windows():
    rm, ref, table = make_region([REF] * 2, REF)
    w = rank_windows(rm, table, ref, lengths=range(18, 19), gc_range=(0, 100), max_homopolymer=10, exclude=(21, 21))
    assert not ((w.start <= 21) & (w.end >= 21)).any()
