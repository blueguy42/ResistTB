"""The design from a snapshot must equal the design from the per-isolate results."""
from pathlib import Path

import pytest

from genohack.assay import build_report
from genohack.snapshot import DEFAULT_SNAPSHOT, load_snapshot

RESULTS = Path(__file__).resolve().parents[1] / "results"


def _strip(report: dict) -> dict:
    report = {k: v for k, v in report.items() if k not in ("generated_at", "steps")}
    return report


@pytest.mark.skipif(not RESULTS.exists() or not DEFAULT_SNAPSHOT.exists(), reason="needs results/ and the snapshot")
def test_snapshot_report_matches_results():
    ids = ["inhA_c-15", "gyrA_D94G"]
    from_results = build_report(RESULTS, target_ids=ids)
    from_snapshot = build_report(RESULTS, target_ids=ids, snapshot=DEFAULT_SNAPSHOT)
    assert _strip(from_results) == _strip(from_snapshot)


@pytest.mark.skipif(not DEFAULT_SNAPSHOT.exists(), reason="needs the snapshot")
def test_snapshot_shape():
    samples, lineage, mats, flank = load_snapshot(DEFAULT_SNAPSHOT)
    assert len(samples) == len(lineage) > 0
    for rm in mats.values():
        assert rm.codes.shape == (len(samples), rm.end - rm.start + 1) == rm.indel.shape
        assert rm.end - rm.start == 2 * flank
