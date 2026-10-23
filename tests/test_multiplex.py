from types import SimpleNamespace as NS

from genohack.multiplex import compatibility


def assay(tid, f, r, wt, mut, overall=80):
    return NS(target=NS(id=tid), pair=NS(left_seq=f, right_seq=r), probe=NS(wt_seq=wt, mut_seq=mut), scores={"overall": overall})


A = assay("a", "ACGTTGCAAGCTTCGGATCC", "TTGACCGATGACCCCGGTTC", "GCTAGCTAGGATCCGATCGT", "GCTAGCTCGGATCCGATCGT", 90)
B = assay("b", "CCGGATTAGCGCTAGCATGA", "GATCGTACGATTGCAGCTAG", "ATCGGCTAAGCTTGCAGGAC", "ATCGGCTCAGCTTGCAGGAC", 70)
C = assay("c", "AGCTTGGATCCAAGTCGTAC", "TCGAGATCCTAGGCTTAACG", "CTTAGGCCAATCGATTGGCA", "CTTAGGCGAATCGATTGGCA", 60)


def test_channel_limit_caps_assays_per_tube():
    m = compatibility([A, B, C], channels_per_tube=4, channels_per_assay=2)
    assert m["max_assays_per_tube"] == 2
    assert all(len(t) <= 2 for t in m["tubes"])
    assert sorted(x for t in m["tubes"] for x in t) == ["a", "b", "c"]


def test_every_pair_is_reported_once():
    m = compatibility([A, B, C])
    assert len(m["pairs"]) == 3
    assert {frozenset((p["a"], p["b"])) for p in m["pairs"]} == {frozenset("ab"), frozenset("ac"), frozenset("bc")}


def test_best_assay_is_placed_first():
    m = compatibility([C, B, A], channels_per_tube=2, channels_per_assay=2)  # one assay per tube
    assert [t[0] for t in m["tubes"]] == ["a", "b", "c"]
