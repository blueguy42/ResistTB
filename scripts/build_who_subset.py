#!/usr/bin/env python3
"""Build resources/who_catalogue_2023_assoc_with_R.csv from the WHO 2023 mutation catalogue files.

Source: https://github.com/GTB-tbsequencing/mutation-catalogue-2023 ("Final Result Files"), MIT licence.
Keeps variants graded "1) Assoc w R" or "2) Assoc w R - Interim", with their evidence counts and the
genome coordinates of the single-nucleotide form of each variant.

Usage: python scripts/build_who_subset.py "<path to Final Result Files>"
"""
import sys
from pathlib import Path

import pandas as pd

src = Path(sys.argv[1])
master = pd.read_csv(
    next(src.glob("*catalogue_master_file.txt")),
    sep="\t",
    low_memory=False,
    usecols=["drug", "gene", "variant", "tier", "FINAL CONFIDENCE GRADING", "Present_R_DATASET ALL",
             "Present_S_DATASET ALL", "Sens_DATASET ALL", "PPV_DATASET ALL"],
)
master = master.rename(columns={
    "FINAL CONFIDENCE GRADING": "grade", "Present_R_DATASET ALL": "present_R", "Present_S_DATASET ALL": "present_S",
    "Sens_DATASET ALL": "sensitivity", "PPV_DATASET ALL": "ppv",
})
master = master[master["grade"].str.startswith(("1)", "2)"))]

coords = pd.read_csv(next(src.glob("*genomic_coordinates.txt")), sep="\t")
snv = coords[(coords["reference_nucleotide"].str.len() == 1) & (coords["alternative_nucleotide"].str.len() == 1)]
snv = snv.rename(columns={"position": "pos", "reference_nucleotide": "ref", "alternative_nucleotide": "alt"})
snv = snv[["variant", "pos", "ref", "alt"]].drop_duplicates("variant")

out = master.merge(snv, on="variant", how="left").sort_values(["gene", "variant", "drug"])
dest = Path(__file__).resolve().parents[1] / "resources" / "who_catalogue_2023_assoc_with_R.csv"
out.to_csv(dest, index=False)
print(f"{len(out)} rows, {out['variant'].nunique()} variants, {out['pos'].notna().sum()} with SNV coordinates -> {dest}")
