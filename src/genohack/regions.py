"""Which region each isolate comes from, by BioProject (resources/regions.csv)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

REGIONS_CSV = Path(__file__).resolve().parents[2] / "resources" / "regions.csv"
# Isolates processed before metadata.json recorded their source row (early test runs).
FALLBACK_CSV = Path(__file__).resolve().parents[2] / "resources" / "sample_bioproject_fallback.csv"


def load_regions(path: str | Path = REGIONS_CSV) -> dict[str, dict[str, str]]:
    """BioProject -> {region, country, label}. `label` names the study for the dataset chip."""
    if not Path(path).exists():
        return {}
    with open(path) as fh:
        return {r["bioproject"]: r for r in csv.DictReader(fh)}


def sample_bioproject(results_dir: str | Path, sample: str) -> str:
    """BioProject of one isolate, from the source row that process_isolate.sh stored in metadata.json."""
    try:
        meta = json.load(open(Path(results_dir) / sample / "metadata.json"))
        found = str(meta.get("source", {}).get("bioproject", ""))
    except (OSError, ValueError):
        found = ""
    if found or not FALLBACK_CSV.exists():
        return found
    with open(FALLBACK_CSV) as fh:
        return next((r["bioproject"] for r in csv.DictReader(fh) if r["acc"] == sample), "")


def sample_region(results_dir: str | Path, sample: str, regions: dict[str, dict[str, str]] | None = None) -> str:
    regions = load_regions() if regions is None else regions
    return regions.get(sample_bioproject(results_dir, sample), {}).get("region", "unknown")


def describe(region_of: list[str], regions: dict[str, dict[str, str]] | None = None) -> tuple[str, str]:
    """(dataset name, plain list like 'Bandung, Tamil Nadu and Guangdong') for the regions present, in order of size."""
    regions = load_regions() if regions is None else regions
    names = [n for n, _ in sorted(((r, region_of.count(r)) for r in set(region_of)), key=lambda x: -x[1])]
    label = {v["region"]: v.get("label") or v["region"] for v in regions.values()}
    plain = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return " + ".join(label.get(n, n) for n in names), plain
