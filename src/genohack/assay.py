"""Assemble primer pairs and probes into scored assays and a report the interface can render."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .checks import genome_hits, interactions
from .genome import MISSING, load_genes, load_mask, load_reference
from .isolates import finished_samples
from . import specificity
from .primers import PrimerPair, design_primer_pairs
from .probes import ProbePair, design_probes
from .targets import Target, default_targets
from .thermo import hairpin_dg, homodimer_dg
from .variants import RegionMatrix, build_region_matrices, position_table
from .who import evidence_for, evidence_score

WEIGHTS = {"conservation": 0.30, "thermodynamics": 0.30, "specificity": 0.20, "resistance_evidence": 0.20}


@dataclass
class Assay:
    target: Target
    pair: PrimerPair
    probe: ProbePair
    coverage: dict
    scores: dict
    interactions: dict
    hits: dict
    evidence: pd.DataFrame
    off_target: dict | None = None  # predicted off-target products per group, when the database is available
    tolerance: float = 0.02  # variable sites above this frequency were avoided; larger means the design had to relax


def _clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


def coverage_for(rm: RegionMatrix, table: pd.DataFrame, target: Target, pair: PrimerPair, probe: ProbePair) -> dict:
    """Per-isolate match to the oligos. The SNP position is excluded from the mismatch count because the
    wild-type and mutant probe cover both alleles; an isolate still needs a called base there."""
    cons = np.array(["ACGT".index(b) for b in table["consensus"]], dtype=np.uint8)
    pos, critical = [], []
    for s, e, tail in ((pair.left_start, pair.left_end, "end"), (pair.right_start, pair.right_end, "start"), (probe.start, probe.end, None)):
        for p in range(s, e + 1):
            if p == target.pos:
                continue
            pos.append(p)
            critical.append((tail == "end" and p > e - 3) or (tail == "start" and p < s + 3))
    idx = np.array(pos) - rm.start
    crit = np.array(critical)
    mism = (rm.codes[:, idx] != cons[idx]) | rm.indel[:, idx]
    called = rm.codes[:, target.pos - rm.start] != MISSING
    n_mm = mism.sum(axis=1) + (~called)
    critical_hit = mism[:, crit].any(axis=1) | (~called)
    perfect = n_mm == 0
    one = (n_mm == 1) & ~critical_hit
    return {
        "isolates_total": len(rm.samples),
        "perfect_match": int(perfect.sum()),
        "one_mismatch": int(one.sum()),
        "failing": int((~(perfect | one)).sum()),
    }


def score_assay(cov: dict, pair: PrimerPair, probe: ProbePair, inter: dict, hits_total: int, evidence: int | None) -> dict:
    n = cov["isolates_total"]
    conservation = 100 * cov["perfect_match"] / n
    probe_tm = min(probe.wt_tm, probe.mut_tm)
    mean_primer = (pair.left_tm + pair.right_tm) / 2
    offset = probe_tm - mean_primer
    offset_score = 1.0 if 6 <= offset <= 12 else _clip01(1 - 0.15 * (6 - offset if offset < 6 else offset - 12))
    worst_dimer = inter["worst_cross"][1]
    worst_hairpin = min(inter["hairpin"].values())
    parts = [
        _clip01(probe.gap / 8.0),                              # probe discrimination, 8 C or more is full marks
        1 - _clip01(abs(pair.left_tm - pair.right_tm) / 3.0),   # primer Tm balance
        offset_score,                                           # probe Tm sits above the primers
        _clip01((worst_dimer + 10) / 4.0),                      # cross dimers: -6 kcal/mol or better is full
        _clip01((worst_hairpin + 4) / 2.0),                     # hairpins: -2 kcal/mol or better is full
    ]
    thermo = 100 * float(np.mean(parts))
    specificity = max(0.0, 100.0 - 25.0 * hits_total)
    comp = {"conservation": conservation, "thermodynamics": thermo, "specificity": specificity}
    if evidence is not None:
        comp["resistance_evidence"] = float(evidence)
    wsum = sum(WEIGHTS[k] for k in comp)
    overall = sum(WEIGHTS[k] * v for k, v in comp.items()) / wsum
    out = {k: int(round(v)) for k, v in comp.items()}
    out["resistance_evidence"] = out.get("resistance_evidence")
    out["overall"] = int(round(overall))
    return out


TOLERANCE_LADDER = (0.02, 0.05, 0.10, 0.20)


def build_assay(rm, table, ref, target: Target, n_pairs: int = 20) -> Assay | None:
    """Design at the strictest variable-site tolerance that yields both primers and a probe; relax only if needed."""
    for tol in TOLERANCE_LADDER:
        pairs = design_primer_pairs(rm, table, target.pos, n=n_pairs, max_maf=tol)
        probes = design_probes(table, target, max_maf=tol)
        if pairs and probes:
            break
    else:
        return None
    ev_rows = evidence_for(target)
    ev = evidence_score(ev_rows)
    best: Assay | None = None
    for pair in pairs:
        inside = [p for p in probes if p.start > pair.left_end + 1 and p.end < pair.right_start - 1]
        if not inside:
            continue
        mean_primer = (pair.left_tm + pair.right_tm) / 2
        # Prefer discrimination, then a probe Tm 6-12 C above the primers.
        probe = sorted(inside, key=lambda p: (-(min(p.wt_tm, p.mut_tm) - mean_primer >= 6), -p.gap))[0]
        oligos = {"F": pair.left_seq, "R": pair.right_seq, "WT": probe.wt_seq, "MUT": probe.mut_seq}
        inter = interactions(oligos)
        hits = {
            "F": genome_hits(pair.left_seq, ref, (pair.left_start, pair.left_end), max_mismatch=3, clamp=6),
            "R": genome_hits(pair.right_seq, ref, (pair.right_start, pair.right_end), max_mismatch=3, clamp=6),
            "probe": genome_hits(probe.wt_seq, ref, (probe.start, probe.end), max_mismatch=2),
        }
        cov = coverage_for(rm, table, target, pair, probe)
        scores = score_assay(cov, pair, probe, inter, sum(hits.values()), ev)
        cand = Assay(target, pair, probe, cov, scores, inter, hits, ev_rows, tolerance=tol)
        if best is None or cand.scores["overall"] > best.scores["overall"]:
            best = cand
    return best


def annotate_off_target(a: Assay) -> None:
    """Predict off-target products (BLAST) for the primer pair, then rescore with them included."""
    a.off_target = specificity.predict_products({"F": a.pair.left_seq, "R": a.pair.right_seq})
    total = sum(a.hits.values()) + sum(a.off_target.values())
    a.scores = score_assay(a.coverage, a.pair, a.probe, a.interactions, total, evidence_score(a.evidence))


def _oligo_rows(a: Assay) -> list[dict]:
    g, p, pr = a.target.gene, a.pair, a.probe
    inter = a.interactions
    rows = [
        ("forward", f"{g}-F", p.left_seq, p.left_start, p.left_end, "+", p.left_tm, None),
        ("reverse", f"{g}-R", p.right_seq, p.right_start, p.right_end, "-", p.right_tm, None),
        ("probe_wt", f"{g}-WT probe", pr.wt_seq, pr.start, pr.end, pr.strand, pr.wt_tm, pr.wt_gap),
        ("probe_mut", f"{g}-{a.target.mutation} probe", pr.mut_seq, pr.start, pr.end, pr.strand, pr.mut_tm, pr.mut_gap),
    ]
    keys = {"forward": "F", "reverse": "R", "probe_wt": "WT", "probe_mut": "MUT"}
    out = []
    for role, name, seq, s, e, strand, tm_, gap in rows:
        k = keys[role]
        out.append({
            "name": name, "role": role, "sequence": seq, "start": s, "end": e, "strand": strand,
            "tm": round(tm_, 1), "hairpin_dg": round(inter["hairpin"][k], 2),
            "self_dimer_dg": round(inter["self_dimer"][k], 2),
            **({"mismatch_dtm": round(gap, 1)} if gap is not None else {}),
        })
    return out


def _who_text(rows: pd.DataFrame) -> tuple[str, list[str]]:
    if rows.empty:
        return "Not in the WHO catalogue slice", []
    best = rows.sort_values("ppv", ascending=False).iloc[0]
    lines = [
        f"{r.drug}: grade {r.grade.split(')')[0]}, resistant in {int(r.present_R):,} and susceptible in {int(r.present_S):,} "
        f"isolates (positive predictive value {r.ppv:.2f})"
        for r in rows.itertuples()
    ]
    return best["grade"].split(") ", 1)[1], lines


def _specificity(a: Assay) -> dict:
    self_hits = sum(a.hits.values())
    if a.off_target is None:
        return {"human_hits": None, "ntm_hits": None,
                "note": f"{self_hits} near-matches elsewhere in H37Rv. Human and non-tuberculous genomes were not checked."}
    o = a.off_target
    return {"human_hits": o["human"], "ntm_hits": o["ntm"],
            "note": f"Predicted off-target products: human {o['human']}, non-tuberculous mycobacteria {o['ntm']}, "
                    f"respiratory bacteria {o['flora']}; {self_hits} near-matches elsewhere in H37Rv. "
                    "BLAST screen: a product needs both primers to bind within 3 kb, matching at the 3' end."}


def to_candidate(a: Assay, rank: int) -> dict:
    t, c, s = a.target, a.coverage, a.scores
    tier, who_lines = _who_text(a.evidence)
    drug = ", ".join(sorted(set(a.evidence["drug"]))) if not a.evidence.empty else t.drug
    n = c["isolates_total"]
    reasons = [
        f"WHO catalogue: {tier}. " + "; ".join(who_lines) + "." if who_lines else "Not found in the WHO catalogue slice.",
        f"{c['perfect_match']} of {n} isolates match every oligo exactly ({100 * c['perfect_match'] / n:.0f}%).",
        f"Probes separate the two alleles by an estimated {a.probe.wt_gap:.1f} C (wild-type) and {a.probe.mut_gap:.1f} C (mutant).",
    ]
    caveats = [
        "Computed from the finished isolates only; coverage will change as more are processed." if n < 222 else
        "Coverage is measured on the Bandung isolates only, not all of Indonesia.",
        ("Specificity was screened against H37Rv, human, seven non-tuberculous mycobacteria and six respiratory bacteria; "
         "a screen is not proof of no cross-reaction." if a.off_target is not None else
         "Specificity covers the H37Rv genome only; human and non-tuberculous genomes have not been checked."),
        f"Probe discrimination is a thermodynamic estimate ({a.probe.gap:.1f} C at worst), not a measurement.",
    ]
    if c["failing"]:
        caveats.append(f"{c['failing']} isolates carry a variant likely to break the assay.")
    if a.tolerance > 0.02:
        caveats.append(f"No design avoided every variable site, so oligos were allowed over sites varying in up to "
                       f"{100 * a.tolerance:.0f}% of isolates; isolates carrying them count as mismatches in the coverage.")
    return {
        "id": t.id, "rank": rank, "gene": t.gene if t.gene != "fabG1" else "inhA promoter", "drug": drug,
        "mutation": t.mutation, "genome_pos": t.pos, "who_tier": tier,
        "amplicon_start": a.pair.left_start, "amplicon_end": a.pair.right_end,
        "oligos": _oligo_rows(a),
        "scores": s,
        "coverage": c,
        "specificity": _specificity(a),
        "reasons": reasons, "caveats": caveats, "validation": "in_silico",
    }


def build_report(results_dir: str | Path = "results", request: str = "", target_ids: list[str] | None = None, flank: int = 300) -> dict:
    steps, t_all = [], time.perf_counter()

    def step(tool: str, label: str, detail: str, t0: float) -> None:
        steps.append({"id": f"s{len(steps) + 1}", "tool": tool, "label": label, "detail": detail,
                      "status": "done", "seconds": round(time.perf_counter() - t0, 1)})

    t0 = time.perf_counter()
    ref, mask, genes = load_reference(), load_mask(), load_genes()
    samples = finished_samples(results_dir)
    targets = [t for t in default_targets(genes) if not target_ids or t.id in target_ids]
    mats = build_region_matrices(results_dir, {t.id: (t.pos - flank, t.pos + flank) for t in targets}, samples)
    step("get_variants", "Load variant tables around each target", f"{len(samples)} isolates, {len(targets)} targets", t0)

    t0 = time.perf_counter()
    assays = []
    for t in targets:
        rm = mats[t.id]
        a = build_assay(rm, position_table(rm, ref, mask), ref, t)
        if a:
            assays.append(a)
    step("design_assays", "Design primers and probes, check specificity and coverage",
         "Primer3, thermodynamic alignment, H37Rv near-match scan", t0)

    if specificity.available():
        t0 = time.perf_counter()
        for a in assays:
            annotate_off_target(a)
        step("check_specificity", "Screen oligos against human, non-tuberculous and respiratory genomes", "BLAST", t0)
    assays.sort(key=lambda a: -a.scores["overall"])
    cands = [to_candidate(a, i + 1) for i, a in enumerate(assays)]
    best = cands[0] if cands else None
    summary = (
        f"I designed {len(cands)} candidate assays on {len(samples)} Bandung isolates. "
        + (f"The top-ranked is {best['gene']} {best['mutation']} (overall {best['scores']['overall']}), "
           f"matching {best['coverage']['perfect_match']} of {best['coverage']['isolates_total']} isolates exactly. " if best else "")
        + "Results are in silico only."
        + ("" if specificity.available() else " Specificity against human and non-tuberculous genomes was not checked.")
    )
    return {
        "mock": False,
        "request": request or "Design qPCR assays for the main rifampicin, isoniazid and fluoroquinolone resistance mutations.",
        "summary": summary,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": {"name": "Bandung active case finding", "bioproject": "PRJNA1433044", "isolates": len(samples), "reference": "NC_000962.3 (H37Rv)"},
        "steps": steps,
        "candidates": cands,
    }
