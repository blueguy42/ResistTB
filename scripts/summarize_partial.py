#!/usr/bin/env python3
"""Summarise whatever isolates have finished so far. Safe to run at any point, repeatedly.

Reads results/<sample>/ (pull from the bucket first with scripts/sync_results.sh) and writes
tables to results/summary/. Only per-isolate outputs are used, so the summary stays valid if the
downstream design changes.

Usage: python scripts/summarize_partial.py [results_dir] [total_isolates_planned]
Durations come from each isolate's metadata.json; pass the planned total to get a time projection.
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
            # TB-Profiler 6.x lists drugs inside each variant's annotation records.
            "drugs": ";".join(sorted({a["drug"] for a in v.get("annotation", []) if a.get("drug")})),
        })

iso = pd.DataFrame(isolates)

# Per-isolate durations and metadata written by process_isolate.sh.
meta_rows = []
for d in done:
    m = d / "metadata.json"
    if m.exists():
        j = json.load(open(m))
        row = {"sample": j["sample"], "bioproject": j.get("source", {}).get("bioproject")}
        row.update({f"sec_{k}": v for k, v in j.get("duration_seconds", {}).items()})
        row["machine_type"] = j.get("run", {}).get("machine_type")
        row["raw_fastq_mb"] = round(j.get("input_bytes", {}).get("raw_fastq", j.get("input_bytes", {}).get("raw_fastq_gz", 0)) / 1e6)
        meta_rows.append(row)
if meta_rows:
    iso = iso.merge(pd.DataFrame(meta_rows), on="sample", how="left")
iso.to_csv(out / "isolates.csv", index=False)

if "sec_total" in iso.columns and iso["sec_total"].notna().any():
    t = iso["sec_total"].dropna()
    total_isolates = int(sys.argv[2]) if len(sys.argv) > 2 else None
    print(f"\nduration per isolate: mean {t.mean() / 60:.1f} min, median {t.median() / 60:.1f} min, "
          f"max {t.max() / 60:.1f} min; total compute so far {t.sum() / 3600:.1f} h")
    step_cols = [c for c in iso.columns if c.startswith("sec_") and c != "sec_total"]
    print("mean minutes per step:\n", (iso[step_cols].mean() / 60).round(1).to_string())
    if total_isolates:
        left = total_isolates - len(iso)
        print(f"projected time for the remaining {left}: {left * t.mean() / 3600:.1f} h (one at a time)")
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
