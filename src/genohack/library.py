"""A precomputed design for every WHO target, so a lookup is instant and says honestly which targets can be designed.

Build with: python -m genohack.cli library --snapshot resources/snapshot_windows.npz
The chat tool design_assays still designs live for the targets it is asked about (a few seconds each); this library
is what the lookup tool reads to rank targets and to explain why one has no design.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from .assay import annotate_off_target, build_assay, mutation_counts, to_candidate
from .genome import load_genes, load_mask, load_reference
from .snapshot import DEFAULT_SNAPSHOT, load_snapshot
from .targets import Target, all_targets
from .variants import position_table
from .who import evidence_for

LIBRARY = Path(__file__).resolve().parents[2] / "resources" / "design_library.json"


def _why_not(target: Target, table, ref_base: str) -> str:
    """The most useful single reason a target has no design."""
    row = table.loc[table["pos"] == target.pos].iloc[0]
    if row["consensus"] != target.ref:
        return ("The isolates' consensus base here differs from the reference, so a wild-type probe built on the "
                "reference would not match most isolates.")
    if row["n_covered"] < 0.9 * row["n_isolates"]:
        return "Fewer than 90% of isolates have a called base at this position."
    return ("No primer pair with a probe between its primers passed the checks, even with positions that vary in up to 20% of "
            "isolates allowed and the primers kept away from the SNP to leave room for the probe.")


def design_one(target: Target, snap, ref, mask) -> dict:
    rm = snap.mats[target.id]
    table = position_table(rm, ref, mask)
    ev = evidence_for(target)
    row = {
        "id": target.id, "gene": target.gene, "mutation": target.mutation,
        # The catalogue's own drug names (the four hand-built targets word theirs differently).
        "drug": ", ".join(sorted(set(ev["drug"]))) if not ev.empty else target.drug,
        "genome_pos": target.pos, "resistant_isolates": target.n_resistant,
        "who_ppv": None if ev.empty else round(float(ev["ppv"].max()), 2),
    }
    # Prevalence of the resistance allele needs no design, so every target gets it.
    row["mutation_by_region"] = mutation_counts(rm, target, snap.region)
    assay = build_assay(rm, table, ref, target, lineages=snap.lineage, regions=snap.region)
    if assay is None:
        return {**row, "status": "no_design", "reason": _why_not(target, table, str(ref[target.pos - 1]))}
    annotate_off_target(assay)
    c = to_candidate(assay, 0)
    cov = c["coverage"]
    return {
        **row, "status": "designed", "overall": c["scores"]["overall"], "scores": c["scores"],
        "exact_matches": cov["perfect_match"], "isolates": cov["isolates_total"], "likely_fail": cov["failing"],
        "by_region": {r: [v["perfect_match"], v["isolates"]] for r, v in cov.get("by_region", {}).items()},
        "amplicon": [c["amplicon_start"], c["amplicon_end"]], "tolerance": assay.tolerance, "probe_room_fallback": bool(assay.target_margin),
        "specificity_checked": c["specificity"]["human_hits"] is not None,
    }


def build_library(snapshot: str | Path = DEFAULT_SNAPSHOT, out: str | Path = LIBRARY, log=print) -> dict:
    snap = load_snapshot(snapshot)
    ref, mask, genes = load_reference(), load_mask(), load_genes()
    targets = [t for t in all_targets(genes) if t.id in snap.mats]
    rows, t0 = [], time.perf_counter()
    for i, t in enumerate(targets, 1):
        try:
            rows.append(design_one(t, snap, ref, mask))
        except Exception as exc:  # one odd target must not lose the other 200; it is listed as having no design
            rows.append({"id": t.id, "gene": t.gene, "mutation": t.mutation, "drug": t.drug, "genome_pos": t.pos,
                         "resistant_isolates": t.n_resistant, "who_ppv": None, "status": "no_design",
                         "reason": f"The design failed with an error ({type(exc).__name__}); this is a bug to look at."})
            log(f"{t.id}: {type(exc).__name__}: {exc}")
        if i % 25 == 0 or i == len(targets):
            log(f"{i}/{len(targets)} targets, {time.perf_counter() - t0:.0f} s")
    lib = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "isolates": len(snap.samples), "regions": {r: snap.region.count(r) for r in sorted(set(snap.region))},
        "targets": rows,
    }
    Path(out).write_text(json.dumps(lib, indent=1))
    return lib


@lru_cache(maxsize=1)
def load_library(path: str | Path = LIBRARY) -> dict:
    if not Path(path).exists():
        return {"targets": []}
    return json.loads(Path(path).read_text())
