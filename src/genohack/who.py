"""Resistance evidence from the WHO 2023 mutation catalogue (grades 1 and 2 only; see resources/README.md)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from .targets import Target

CATALOGUE = Path(__file__).resolve().parents[2] / "resources" / "who_catalogue_2023_assoc_with_R.csv"


@lru_cache(maxsize=1)
def load_catalogue() -> pd.DataFrame:
    return pd.read_csv(CATALOGUE)


def evidence_for(target: Target) -> pd.DataFrame:
    """Catalogue rows for the exact nucleotide change at the target position (one row per drug)."""
    cat = load_catalogue()
    return cat[(cat["pos"] == target.pos) & (cat["ref"] == target.ref) & (cat["alt"] == target.alt)].reset_index(drop=True)


def evidence_score(rows: pd.DataFrame) -> int | None:
    """0-100: the best positive predictive value among the matching drugs (None when not in the catalogue)."""
    if rows.empty:
        return None
    return int(round(100 * float(rows["ppv"].max())))
