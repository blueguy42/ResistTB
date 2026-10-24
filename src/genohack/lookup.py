"""Chat lookup: which WHO catalogue targets exist for a drug, gene or variant, which have a design, and why the rest do not.

Everything it returns comes from the WHO table and the precomputed design library, so the assistant can quote it
without inventing numbers.
"""
from __future__ import annotations

import re

import pandas as pd

from .library import load_library
from .targets import MIN_RESISTANT
from .who import load_catalogue

# What people type, mapped to the catalogue's drug names.
DRUG_ALIASES: dict[str, list[str]] = {
    "rifampicin": ["Rifampicin"], "rifampin": ["Rifampicin"], "rif": ["Rifampicin"], "rr-tb": ["Rifampicin"],
    "isoniazid": ["Isoniazid"], "inh": ["Isoniazid"],
    "ethambutol": ["Ethambutol"], "emb": ["Ethambutol"],
    "pyrazinamide": ["Pyrazinamide"], "pza": ["Pyrazinamide"],
    "streptomycin": ["Streptomycin"], "sm": ["Streptomycin"],
    "kanamycin": ["Kanamycin"], "amikacin": ["Amikacin"], "capreomycin": ["Capreomycin"],
    "levofloxacin": ["Levofloxacin"], "moxifloxacin": ["Moxifloxacin"],
    "fluoroquinolone": ["Levofloxacin", "Moxifloxacin"], "fluoroquinolones": ["Levofloxacin", "Moxifloxacin"],
    "fq": ["Levofloxacin", "Moxifloxacin"],
    "second-line injectables": ["Kanamycin", "Amikacin", "Capreomycin"], "injectables": ["Kanamycin", "Amikacin", "Capreomycin"],
    "aminoglycosides": ["Kanamycin", "Amikacin", "Streptomycin"],
    "bedaquiline": ["Bedaquiline"], "bdq": ["Bedaquiline"],
    "linezolid": ["Linezolid"], "lzd": ["Linezolid"],
    "clofazimine": ["Clofazimine"], "cfz": ["Clofazimine"],
    "delamanid": ["Delamanid"], "dlm": ["Delamanid"],
    "ethionamide": ["Ethionamide"], "eto": ["Ethionamide"], "prothionamide": ["Ethionamide"],
}


def _norm(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())


def _name(r) -> str:
    return f"{r['gene']} {r['mutation']}"


def find_targets(query: str, limit: int = 8) -> dict:
    """Targets for a drug (or class), a gene, or a variant name. Returns the best designed ones plus an explanation."""
    q = _norm(query)
    cat = load_catalogue()
    cat = cat[cat["gene"] != "gene"]
    lib = load_library()["targets"]
    if not lib:
        return {"error": "the design library has not been built yet"}

    drugs = DRUG_ALIASES.get(q)
    gene = next((g for g in cat["gene"].unique() if g.lower() == q), None)
    if q in ("inha", "fabg1"):
        gene = "inhA"
    variant = [v for v in cat["variant"].unique() if q and q in v.lower()] if not drugs and not gene else []

    if drugs:
        rows = cat[cat["drug"].isin(drugs)]
        scope = " and ".join(drugs)
    elif gene:
        rows = cat[cat["gene"] == gene]
        scope = f"{gene} (gene)"
    elif variant:
        rows = cat[cat["variant"].isin(variant)]
        scope = f"variants matching '{query}'"
    else:
        return {
            "matched": None,
            "message": f"'{query}' is not a drug, gene or variant in the WHO catalogue list used here.",
            "drugs_covered": sorted(cat["drug"].unique()), "genes_covered": sorted(cat["gene"].unique()),
        }

    variants = rows["variant"].nunique()
    with_pos = rows[rows["pos"].notna() & (rows["ref"].str.len() == 1) & (rows["alt"].str.len() == 1)]
    n_pos = with_pos["variant"].nunique()
    ids = set(rows["variant"])
    mine = [t for t in lib if t["id"] in ids or t["id"] in _legacy_ids(rows)]
    designed = sorted((t for t in mine if t["status"] == "designed"), key=lambda t: -t["resistant_isolates"])
    undesigned = [t for t in mine if t["status"] != "designed"]
    other = variants - len(mine)
    explanation = (
        f"The WHO catalogue lists {variants} resistance variants for {scope}. {len(mine)} of them are single-base changes "
        f"seen in at least {MIN_RESISTANT} resistant isolates, so each can be one allele-specific probe; {len(designed)} have "
        f"a working design here"
        + (f" and {len(undesigned)} have none because no primer pair with a probe between its primers passed the checks"
           if undesigned else "")
        + (f". The other {other} are loss-of-function mutations, insertions or deletions, changes with no single position, "
           f"or changes seen in fewer than {MIN_RESISTANT} resistant isolates, so one probe cannot cover them." if other > 0 else ".")
        if len(mine) else
        f"The WHO catalogue lists {variants} resistance variants for {scope}, but none is a single-base change seen in at "
        f"least {MIN_RESISTANT} resistant isolates, so none can be one allele-specific probe (they are mostly "
        "loss-of-function mutations or indels spread across the gene)."
    )
    out = {
        "matched": scope, "who_variants": int(variants), "single_base_variants": int(n_pos),
        "designable_targets": len(mine), "designed": len(designed), "no_design": len(undesigned),
        "not_probeable": int(other), "explanation": explanation,
        # Set only when it is true, so the assistant never has to compare the counts itself.
        "limit_note": (f"Most of the WHO variants for {scope} cannot be one allele-specific probe, so an assay covers only a "
                       "small part of its resistance." if other > len(mine) else ""),
        "targets": [
            {"id": t["id"], "name": _name(t), "drug": t["drug"], "resistant_isolates_in_who": t["resistant_isolates"],
             "overall_score": t["overall"], "exact_matches": f"{t['exact_matches']} of {t['isolates']} isolates"}
            for t in designed[:limit]
        ],
    }
    if undesigned:
        out["no_design_examples"] = [{"id": t["id"], "name": _name(t), "reason": t["reason"]} for t in undesigned[:3]]
    return out


def _legacy_ids(rows: pd.DataFrame) -> set[str]:
    """The four hand-built targets use their own ids; match them by the catalogue variant they correspond to."""
    from .targets import default_targets

    keyed = {(r.pos, r.alt) for r in rows.itertuples() if pd.notna(r.pos)}
    return {t.id for t in default_targets() if (t.pos, t.alt) in keyed}
