"""A small precomputed copy of what the design reads from results/: the variant windows around each target.

The design only needs the sample list, each isolate's lineage and a +/- flank base window per target, a few
hundred KB instead of the 500 MB of per-isolate files. This lets a small container run the design with no
results/ folder. Write one with: python -m genohack.cli snapshot --results results
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .genome import load_genes
from .isolates import finished_samples, read_resistance
from .targets import default_targets
from .variants import RegionMatrix, build_region_matrices

DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[2] / "resources" / "snapshot_windows.npz"


def write_snapshot(results_dir: str | Path, out: str | Path = DEFAULT_SNAPSHOT, flank: int = 300) -> Path:
    samples = finished_samples(results_dir)
    targets = default_targets(load_genes())
    mats = build_region_matrices(results_dir, {t.id: (t.pos - flank, t.pos + flank) for t in targets}, samples)
    lineage = [str(read_resistance(results_dir, s).get("main_lineage") or "unknown") for s in samples]
    arrays: dict[str, np.ndarray] = {
        "samples": np.array(samples), "lineage": np.array(lineage), "flank": np.array(flank),
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


def load_snapshot(path: str | Path = DEFAULT_SNAPSHOT) -> tuple[list[str], list[str], dict[str, RegionMatrix], int]:
    """Return (samples, lineage per sample, region matrices by target id, flank)."""
    z = np.load(path, allow_pickle=False)
    samples = [str(s) for s in z["samples"]]
    mats = {}
    for tid in (str(t) for t in z["targets"]):
        start, end = (int(v) for v in z[f"range__{tid}"])
        mats[tid] = RegionMatrix(tid, start, end, samples, z[f"codes__{tid}"], z[f"indel__{tid}"])
    return samples, [str(v) for v in z["lineage"]], mats, int(z["flank"])
