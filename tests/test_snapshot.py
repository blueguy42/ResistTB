"""The design from a snapshot must equal the design from the per-isolate results."""
from pathlib import Path

import pytest

from genohack.assay import build_report
from genohack.regions import describe, load_regions
from genohack.snapshot import DEFAULT_SNAPSHOT, load_snapshot

RESULTS = Path(__file__).resolve().parents[1] / "results"


def _strip(report: dict) -> dict:
    return {k: v for k, v in report.items() if k not in ("generated_at", "steps")}


def _snapshot_matches_results() -> bool:
    """Only comparable when the snapshot was made from the isolates now in results/ (it goes stale while a run syncs)."""
    if not RESULTS.exists() or not DEFAULT_SNAPSHOT.exists():
        return False
    from genohack.isolates import finished_samples

    return load_snapshot(DEFAULT_SNAPSHOT).samples == finished_samples(RESULTS)


@pytest.mark.skipif(not _snapshot_matches_results(), reason="needs a snapshot made from the isolates now in results/")
def test_snapshot_report_matches_results():
    ids = ["inhA_c-15", "gyrA_D94G"]
    from_results = build_report(RESULTS, target_ids=ids)
    from_snapshot = build_report(RESULTS, target_ids=ids, snapshot=DEFAULT_SNAPSHOT)
    assert _strip(from_results) == _strip(from_snapshot)


@pytest.mark.skipif(not DEFAULT_SNAPSHOT.exists(), reason="needs the snapshot")
def test_snapshot_shape():
    snap = load_snapshot(DEFAULT_SNAPSHOT)
    assert len(snap.samples) == len(snap.lineage) == len(snap.region) > 0
    for rm in snap.mats.values():
        assert rm.codes.shape == (len(snap.samples), rm.end - rm.start + 1) == rm.indel.shape
        assert rm.end - rm.start == 2 * snap.flank


def test_region_names_and_dataset_label():
    regions = load_regions()
    assert regions["PRJNA1433044"]["region"] == "Bandung"
    name, plain = describe(["Bandung"] * 3 + ["Tamil Nadu"] * 2 + ["Guangdong"], regions)
    assert plain == "Bandung, Tamil Nadu and Guangdong"
    assert name.startswith("Bandung active case finding + ")
    assert describe(["Bandung"], regions)[1] == "Bandung"
