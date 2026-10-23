#!/usr/bin/env python3
"""Summarise whatever isolates have finished so far. Safe to run at any point, repeatedly.

Reads results/<sample>/ (pull from the bucket first with scripts/sync_results.sh) and writes
tables to results/summary/. Only per-isolate outputs are used, so the summary stays valid if the
downstream design changes.

Usage: python scripts/summarize_partial.py [results_dir]
"""
import json
import sys
from pathlib import Path

import pandas as pd

results = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
out = results / "summary"
out.mkdir(parents=True, exist_ok=True)

done = sorted(p.parent for p in results.glob("*/DONE"))
print(f"{len(done)} isolates finished")
if not done:
    sys.exit(0)

isolates, variants = [], []
for d in done:
    sample = d.name
    f = d / f"{sample}.results.json"
    if not f.exists():
        continue
    r = json.load(open(f))
    # Field names follow TB-Profiler 6.x JSON; .get() keeps this tolerant of version differences.
    isolates.append({
        "sample": sample,
        "main_lineage": r.get("main_lineage"),
        "sub_lineage": r.get("sub_lineage"),
        "drtype": r.get("drtype"),
    })
    for v in r.get("dr_variants", []):
        variants.append({
            "sample": sample,
            "gene": v.get("gene_name"),
            "change": v.get("change") or v.get("nucleotide_change"),
            "freq": v.get("freq"),
            "drugs": ";".join(x.get("drug", "") for x in v.get("drugs", [])),
        })

iso = pd.DataFrame(isolates)
iso.to_csv(out / "isolates.csv", index=False)
print("\nlineage:\n", iso["main_lineage"].value_counts(dropna=False).to_string())
print("\ndrug-resistance class:\n", iso["drtype"].value_counts(dropna=False).to_string())

if variants:
    var = pd.DataFrame(variants)
    var.to_csv(out / "dr_variants_per_isolate.csv", index=False)
    freq = (
        var.groupby(["gene", "change", "drugs"])["sample"].nunique().rename("n_isolates").reset_index()
    )
    freq["fraction_of_done"] = (freq["n_isolates"] / len(iso)).round(3)
    freq = freq.sort_values("n_isolates", ascending=False)
    freq.to_csv(out / "dr_variant_frequency.csv", index=False)
    print("\ntop resistance variants:\n", freq.head(15).to_string(index=False))

print(f"\ntables written to {out}/ (based on {len(iso)} isolates)")
