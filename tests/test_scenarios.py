"""Free-text questions about patients: what the lookup supplies, and what the model is shown."""
import pytest

from genohack.assay import build_report
from genohack.library import LIBRARY
from genohack.lookup import PANEL_SIZE, find_targets, names_a_target
from genohack.snapshot import DEFAULT_SNAPSHOT

needs_library = pytest.mark.skipif(not LIBRARY.exists(), reason="needs the design library")


@pytest.mark.parametrize("text,expected", [
    ("Patients treated with ethambutol in Bandung did not improve", True),
    ("Patients in Bandung did not improve on the first-line regimen", True),
    ("What about embB?", True),
    ("Patients on RIF did not improve", True),
    ("Which assay for fluoroquinolones", True),
    ("A few patients in Bandung are not improving on treatment", False),
    ("The other person has also been treated with [drug]", False),
    ("people in Bandung got worse after a month", False),
])
def test_names_a_target(text, expected):
    assert names_a_target(text) is expected


@needs_library
def test_panel_is_the_best_designed_targets_with_a_share_that_is_not_double_counted():
    rif = find_targets("rifampicin")
    assert len(rif["suggested_panel"]) == PANEL_SIZE == len(rif["suggested_panel_names"])
    assert rif["suggested_panel"][0] == "rpoB_S450L"  # most resistant isolates in the catalogue
    # S450L and S450W share a genome position; each must be credited with its own count, so the share stays below 100
    assert 0 < rif["panel_share_of_who_resistance_percent"] < 100


@needs_library
def test_warnings_are_set_by_the_lookup_not_judged_by_the_model():
    assert find_targets("pyrazinamide")["weak_panel_note"]  # scattered loss-of-function: panel covers a small part
    assert not find_targets("ethambutol")["weak_panel_note"]
    assert find_targets("bedaquiline")["limit_note"] and not find_targets("kanamycin")["limit_note"]


@pytest.mark.skipif(not DEFAULT_SNAPSHOT.exists(), reason="needs the snapshot")
def test_the_model_is_shown_the_sequences_and_a_region_sentence_that_names_the_region():
    import genohack.agent as agent

    report = build_report(target_ids=["embB_p.Met306Val"], snapshot=DEFAULT_SNAPSHOT)
    compact = agent._compact(report)["assays"][0]
    real = {o["role"]: o["sequence"] for o in report["candidates"][0]["oligos"]}
    assert compact["sequences"] == real and set(real) == {"forward", "reverse", "probe_wt", "probe_mut"}
    for sentence in compact.get("region_matches", {}).values():
        assert sentence.startswith("In ")
