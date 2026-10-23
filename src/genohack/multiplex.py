"""Can these assays share a tube? Cross-assay dimer screen plus a channel-limited tube grouping.

Dimer free energies come from Primer3's thermodynamic alignment (a screen, not a measurement). Two assays are
compatible when no oligo of one folds onto an oligo of the other more strongly than DG_CONFLICT; between DG_CAUTION
and DG_CONFLICT is flagged. The thresholds follow the usual multiplex design range and are settings, not facts
about any particular chemistry."""
from __future__ import annotations

from itertools import combinations

from .thermo import heterodimer_dg

DG_CAUTION = -7.0   # kcal/mol: weaker than this is fine
DG_CONFLICT = -9.0  # kcal/mol: stronger than this is a conflict


def _oligos(a) -> dict[str, str]:
    g = a.target.id
    return {f"{g}-F": a.pair.left_seq, f"{g}-R": a.pair.right_seq, f"{g}-WT": a.probe.wt_seq, f"{g}-MUT": a.probe.mut_seq}


def compatibility(assays: list, channels_per_tube: int = 4, channels_per_assay: int = 2) -> dict:
    """Pairwise compatibility and a greedy tube grouping.

    Each assay needs channels_per_assay fluorescence channels (one per allele probe), so a tube holds at most
    channels_per_tube // channels_per_assay assays no matter how well they get along."""
    pairs = []
    for a, b in combinations(assays, 2):
        oa, ob = _oligos(a), _oligos(b)
        worst = min(
            ((x, y, heterodimer_dg(sx, sy)) for x, sx in oa.items() for y, sy in ob.items()),
            key=lambda t: t[2],
        )
        status = "conflict" if worst[2] <= DG_CONFLICT else "caution" if worst[2] <= DG_CAUTION else "compatible"
        pairs.append({"a": a.target.id, "b": b.target.id, "worst_dg": round(worst[2], 2),
                      "worst_pair": f"{worst[0]} + {worst[1]}", "status": status})
    bad = {frozenset((p["a"], p["b"])) for p in pairs if p["status"] == "conflict"}
    cap = max(1, channels_per_tube // channels_per_assay)
    tubes: list[list[str]] = []
    for a in sorted(assays, key=lambda x: -x.scores["overall"]):  # best assays are placed first
        for tube in tubes:
            if len(tube) < cap and all(frozenset((a.target.id, t)) not in bad for t in tube):
                tube.append(a.target.id)
                break
        else:
            tubes.append([a.target.id])
    return {
        "channels_per_tube": channels_per_tube,
        "channels_per_assay": channels_per_assay,
        "max_assays_per_tube": cap,
        "thresholds": {"caution": DG_CAUTION, "conflict": DG_CONFLICT},
        "pairs": pairs,
        "tubes": tubes,
        "note": (f"Each assay uses {channels_per_assay} probe channels, so a {channels_per_tube}-channel instrument fits "
                 f"{cap} assays per tube. Grouping avoids pairs with a predicted dimer stronger than {DG_CONFLICT} kcal/mol."),
    }
