"""A small precomputed copy of what the design reads from results/: the variant windows around each target.

The design only needs the sample list, each isolate's lineage and region, and a +/- flank base window per target:
a few hundred KB instead of the 500 MB of per-isolate files. This lets a small container run the design with no
results/ folder. Write one with: python -m genohack.cli snapshot --results results
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .genome import load_genes
from .isolates import finished_samples, read_resistance
from .regions import load_regions, sample_region
from .targets import all_targets
from .variants import RegionMatrix, build_region_matrices

DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[2] / "resources" / "snapshot_windows.npz"


@dataclass
class Snapshot:
    samples: list[str]
    lineage: list[str]  # TB-Profiler main lineage per isolate
    region: list[str]  # region name per isolate (resources/regions.csv)
    mats: dict[str, RegionMatrix]
    flank: int


def write_snapshot(results_dir: str | Path, out: str | Path = DEFAULT_SNAPSHOT, flank: int = 300) -> Path:
    samples = finished_samples(results_dir)
    targets = all_targets(load_genes())
    mats = build_region_matrices(results_dir, {t.id: (t.pos - flank, t.pos + flank) for t in targets}, samples)
    lineage = [str(read_resistance(results_dir, s).get("main_lineage") or "unknown") for s in samples]
    regions = load_regions()
    region = [sample_region(results_dir, s, regions) for s in samples]
    arrays: dict[str, np.ndarray] = {
        "samples": np.array(samples), "lineage": np.array(lineage), "region": np.array(region), "flank": np.array(flank),
        "targets": np.array([t.id for t in targets]),
    }
    for t in targets:
        rm = mats[t.id]
        arrays[f"codes__{t.id}"] = rm.codes
        arrays[f"indel__{t.id}"] = rm.indel
        arrays[f"range__{t.id}"] = np.array([rm.start, rm.end])
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, **arrays)
    return out


def load_snapshot(path: str | Path = DEFAULT_SNAPSHOT) -> Snapshot:
    z = np.load(path, allow_pickle=False)
    samples = [str(s) for s in z["samples"]]
    mats = {}
    for tid in (str(t) for t in z["targets"]):
        start, end = (int(v) for v in z[f"range__{tid}"])
        mats[tid] = RegionMatrix(tid, start, end, samples, z[f"codes__{tid}"], z[f"indel__{tid}"])
    # Snapshots written before regions existed hold one region, Bandung.
    region = [str(v) for v in z["region"]] if "region" in z.files else ["Bandung"] * len(samples)
    return Snapshot(samples, [str(v) for v in z["lineage"]], region, mats, int(z["flank"]))
