"""The design endpoint behind the target library panel, and the rate limiter."""
import pytest

from genohack.api import RateLimit, app
from genohack.snapshot import DEFAULT_SNAPSHOT

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402


def test_rate_limit_counts_per_caller_and_per_day():
    lim = RateLimit(per_ip_hour=2, per_day=3)
    assert lim.allow("a") and lim.allow("a")
    assert not lim.allow("a")  # third for the same caller in the hour
    assert lim.allow("b")
    assert not lim.allow("c")  # fourth overall: the daily ceiling
    off = RateLimit(per_ip_hour=0, per_day=0)
    assert all(off.allow("x") for _ in range(50))  # 0 turns a limit off


def test_design_endpoint_rejects_unknown_targets():
    r = TestClient(app).post("/api/design", json={"targets": ["not_a_target"]})
    assert r.status_code == 400 and "error" in r.json()


@pytest.mark.skipif(not DEFAULT_SNAPSHOT.exists(), reason="needs the snapshot")
def test_design_endpoint_returns_the_picked_targets_in_a_report(monkeypatch):
    import genohack.agent as agent

    monkeypatch.setattr(agent, "SNAPSHOT", str(DEFAULT_SNAPSHOT))  # design from the snapshot, not results/
    r = TestClient(app).post("/api/design", json={"targets": ["embB_p.Met306Val", "rpsL_p.Lys43Arg", "embB_p.Met306Val"]})
    assert r.status_code == 200
    body = r.json()
    assert {c["id"] for c in body["candidates"]} == {"embB_p.Met306Val", "rpsL_p.Lys43Arg"}
    assert body["request"].startswith("Target library: ")
    assert all(c["coverage"]["by_region"] for c in body["candidates"])
