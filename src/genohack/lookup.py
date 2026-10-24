"""Chat lookup: which WHO catalogue targets exist for a drug, gene or variant, which have a design, and why the rest do not.

Everything it returns comes from the WHO table and the precomputed design library, so the assistant can quote it
without inventing numbers.
"""
from __future__ import annotations

import re

import pandas as pd

from .library import load_library
from .targets import MIN_RESISTANT, all_targets

PANEL_SIZE = 4  # two tubes of two assays on a 4-channel instrument (see multiplex.py)
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
    panel = designed[:PANEL_SIZE]
    in_scope = rows.groupby("variant")["present_R"].max().fillna(0).sum()
    # How much of the catalogue's resistance for this scope the panel's variants account for. Counts come from the
    # variant's own rows within the scope, so a variant shared by two drugs is not credited with the other drug's isolates.
    by_id = {t.id: t for t in all_targets()}  # several variants can share a position, so match the changed base too
    panel_n = sum(
        rows[(rows["pos"] == by_id[t["id"]].pos) & (rows["alt"] == by_id[t["id"]].alt)]["present_R"].fillna(0).max() for t in panel
    ) if panel else 0
    out = {
        "matched": scope, "who_variants": int(variants), "single_base_variants": int(n_pos),
        "designable_targets": len(mine), "designed": len(designed), "no_design": len(undesigned),
        "not_probeable": int(other), "explanation": explanation,
        # Set only when it is true, so the assistant never has to compare the counts itself.
        "limit_note": (f"Most of the WHO variants for {scope} cannot be one allele-specific probe, so an assay covers only a "
                       "small part of its resistance." if other > len(mine) else ""),
        "suggested_panel": [t["id"] for t in panel],
        "suggested_panel_names": [_name(t) for t in panel],
        "panel_share_of_who_resistance_percent": int(min(100, round(100 * panel_n / in_scope))) if in_scope and panel else 0,
        "weak_panel_note": ("Because this panel covers under half of the drug's resistance in the WHO catalogue, a negative result "
                            "tells little." if panel and in_scope and 100 * panel_n / in_scope < 50 else ""),
        "panel_note": ("The panel is the designed targets with the most resistant isolates in the WHO catalogue. The share adds up "
                       "isolates per variant, so an isolate with several variants counts more than once: a rough guide, not a "
                       "detection rate.") if panel else "",
        "targets": [
            {"id": t["id"], "name": _name(t), "drug": t["drug"], "resistant_isolates_in_who": t["resistant_isolates"],
             "overall_score": t["overall"], "exact_matches": f"{t['exact_matches']} of {t['isolates']} isolates"}
            for t in designed[:limit]
        ],
    }
    if undesigned:
        out["no_design_examples"] = [{"id": t["id"], "name": _name(t), "reason": t["reason"]} for t in undesigned[:3]]
    return out


def capabilities() -> dict:
    """What can be designed, from the library alone: designed variants per drug, and per region how many are seen there."""
    lib = load_library()
    designed = [t for t in lib["targets"] if t["status"] == "designed"]
    if not designed:
        return {"error": "the design library has not been built yet"}
    per_drug: dict[str, int] = {}
    for t in designed:
        for d in {x.strip() for x in t["drug"].split(",")}:
            per_drug[d] = per_drug.get(d, 0) + 1
    counted = any("mutation_by_region" in t for t in designed)  # libraries built before carrier counts lack it
    regions = {
        r: {"isolates": n, **({"designed_variants_seen_there": sum(1 for t in designed if t["mutation_by_region"].get(r, [0])[0] > 0)}
                              if counted else {})}
        for r, n in lib.get("regions", {}).items()
    }
    return {
        "designed_variants": len(designed), "drugs": dict(sorted(per_drug.items(), key=lambda kv: -kv[1])),
        "regions": regions, "isolates": lib.get("isolates"),
        "note": "Each variant is a single-base resistance change from the WHO catalogue seen in at least "
                f"{MIN_RESISTANT} resistant isolates. Drugs that are not listed have no such variant.",
    }


def _legacy_ids(rows: pd.DataFrame) -> set[str]:
    """The four hand-built targets use their own ids; match them by the catalogue variant they correspond to."""
    from .targets import default_targets

    keyed = {(r.pos, r.alt) for r in rows.itertuples() if pd.notna(r.pos)}
    return {t.id for t in default_targets() if (t.pos, t.alt) in keyed}


_REGIMENS = ("first-line", "first line", "second-line", "second line", "mdr", "xdr")


def names_a_target(text: str) -> bool:
    """True when the text names a drug, drug class, regimen or a gene from the WHO catalogue."""
    t = text.lower()
    words = set(re.findall(r"[a-z0-9\-]+", t))
    if any(w in words for w in DRUG_ALIASES if " " not in w) or any(r in t for r in _REGIMENS):
        return True
    if any(a in t for a in DRUG_ALIASES if " " in a):
        return True
    genes = {g.lower() for g in load_catalogue()["gene"].unique() if g != "gene"} | {"fabg1"}
    return bool(words & genes)
