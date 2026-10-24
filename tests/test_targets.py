"""Targets generated from the WHO table, the chat lookup, and the design library they feed."""
import json

import pytest

from genohack.genome import DEFAULT_REF, decode, load_reference
from genohack.library import LIBRARY
from genohack.lookup import find_targets
from genohack.targets import MIN_RESISTANT, all_targets, default_targets, who_targets


def test_main_four_keep_their_ids_and_are_not_duplicated():
    ids = [t.id for t in all_targets()]
    assert ids[:4] == [t.id for t in default_targets()]
    assert len(ids) == len(set(ids))
    positions = [(t.pos, t.alt) for t in all_targets()]
    assert len(positions) == len(set(positions))  # the same change is never two targets


def test_generic_loss_of_function_labels_are_not_targets():
    # pncA_LoF stands for many mutations; the catalogue gives it a position but it is not one single-base change.
    assert not any("LoF" in t.id for t in all_targets())
    assert all(t.n_resistant >= MIN_RESISTANT for t in who_targets())


@pytest.mark.skipif(not DEFAULT_REF.exists(), reason="needs ref/NC_000962.3.fasta")
def test_every_target_reference_base_matches_h37rv():
    ref = decode(load_reference())
    assert [t.id for t in all_targets() if ref[t.pos - 1] != t.ref] == []


@pytest.mark.skipif(not LIBRARY.exists(), reason="needs the design library")
def test_lookup_explains_what_can_and_cannot_be_designed():
    emb = find_targets("ethambutol")
    assert emb["matched"] == "Ethambutol" and emb["targets"] and emb["targets"][0]["id"].startswith("embB_")
    bdq = find_targets("bedaquiline")  # mostly loss-of-function: few probe-able variants out of many
    assert bdq["not_probeable"] > bdq["designable_targets"]
    assert "cannot cover" in bdq["explanation"]
    unknown = find_targets("aspirin")
    assert unknown["matched"] is None and unknown["drugs_covered"]
    assert find_targets("fluoroquinolones")["targets"][0]["id"] == "gyrA_D94G"


@pytest.mark.skipif(not LIBRARY.exists(), reason="needs the design library")
def test_library_keeps_the_main_four_designs_and_designs_rrs_1401():
    rows = {r["id"]: r for r in json.load(open(LIBRARY))["targets"]}
    assert rows["inhA_c-15"]["overall"] == 94
    assert rows["rpoB_S450L"]["status"] == "designed"  # its score moves with the pooled consensus
    assert rows["rrs_n.1401A>G"]["status"] == "designed"  # needs the probe-room fallback
