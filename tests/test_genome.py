from genohack.genome import Gene, LETTERS, load_genes, load_reference
from genohack.targets import default_targets


def test_plus_strand_coordinates():
    g = Gene("x", "Rv0000", 100, 199, "+")
    assert g.coding_pos(1) == 100
    assert g.codon_pos(2, 3) == 105  # coding base 6 -> 100 + 6 - 1
    assert g.upstream_pos(15) == 85


def test_minus_strand_coordinates():
    g = Gene("x", "Rv0000c", 100, 199, "-")
    assert g.coding_pos(1) == 199
    assert g.codon_pos(2, 3) == 194  # coding base 6 -> 199 - 6 + 1
    assert g.upstream_pos(15) == 214


def test_targets_sit_on_the_expected_reference_base():
    # Guards the strand logic: every target base must match the reference genome.
    ref = load_reference()
    for t in default_targets(load_genes()):
        assert LETTERS[ref[t.pos - 1]] == t.ref, t.id


def test_known_positions():
    pos = {t.id: t.pos for t in default_targets(load_genes())}
    assert pos["rpoB_S450L"] == 761155
    assert pos["katG_S315T"] == 2155168
    assert pos["inhA_c-15"] == 1673425
