"""Primer design on a window so fragmented that Primer3 would refuse it."""
import numpy as np
import pandas as pd

from genohack.primers import design_primer_pairs
from genohack.variants import RegionMatrix


def _window(n: int, variable: np.ndarray) -> tuple[RegionMatrix, pd.DataFrame]:
    rng = np.random.default_rng(1)
    start = 1000
    table = pd.DataFrame({
        "pos": np.arange(start, start + n), "consensus": rng.choice(list("ACGT"), n),
        "maf": np.where(variable, 0.5, 0.0), "n_minor": np.where(variable, 100, 0),
        "n_indel": 0, "n_missing": 0, "masked": False,
    })
    rm = RegionMatrix("t", start, start + n - 1, [f"s{i}" for i in range(200)], np.zeros((200, n), dtype=np.uint8), np.zeros((200, n), dtype=bool))
    return rm, table


def test_a_window_with_over_200_separate_variable_sites_gives_no_primers_instead_of_crashing():
    n = 1000
    rm, table = _window(n, (np.arange(n) % 2 == 0))  # 500 variable positions, none adjacent
    assert design_primer_pairs(rm, table, 1500) == []


def test_adjacent_variable_sites_are_merged_into_one_excluded_run():
    n = 601
    variable = np.zeros(n, dtype=bool)
    variable[100:260] = True  # 160 adjacent positions: one run, so well under Primer3's limit of 200
    rm, table = _window(n, variable)
    design_primer_pairs(rm, table, 1000 + 300)  # must not raise
