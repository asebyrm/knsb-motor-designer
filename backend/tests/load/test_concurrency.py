"""Section 12.2 / acceptance 12: a running mission solve must not block normal sims.

The mission solver runs in a ProcessPoolExecutor and the request returns a job_id
immediately; forward simulations run in a thread pool. So while a mission job is in
flight, a burst of concurrent /simulate calls must all come back quickly.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pytest

pytestmark = pytest.mark.slow

_SIM_DESIGN = {
    "name": "load", "propellant": {"id": "knsb"},
    "grain": {"type": "bates", "outer_diameter": 0.045, "core_diameter": 0.018,
              "segment_length": 0.075, "segment_count": 3, "segment_spacing": 0.003},
    "nozzle": {"throat_diameter": 0.0115, "expansion_ratio": 5.0},
    "case": {"material_id": "pa12", "inner_diameter": 0.052, "wall_thickness": 0.005},
    "liner": {"material_id": "kraft_phenolic", "thickness": 0.003},
    "bulkhead": {"material_id": "pa12", "thickness": 0.010},
    "meop_bar": 45,
}


def test_missions_do_not_block_simulations(api_client):
    # kick off several mission jobs (heavy, ProcessPool)
    mission_ids = []
    for _ in range(5):
        r = api_client.post("/api/mission", json={
            "dry_mass": 6.0, "body_diameter": 0.10, "target_apogee": 800.0,
            "meop_bar": 45.0, "time_budget_s": 10.0})
        assert r.status_code == 200
        mission_ids.append(r.json()["job_id"])

    def one_sim(_i: int) -> float:
        start = time.perf_counter()
        resp = api_client.post("/api/simulate", json={"design": _SIM_DESIGN})
        assert resp.status_code == 200
        return time.perf_counter() - start

    with ThreadPoolExecutor(max_workers=16) as pool:
        durations = list(pool.map(one_sim, range(40)))

    # no single simulation request stalled behind the solver
    assert max(durations) < 5.0, f"slowest simulation took {max(durations):.2f}s"

    # the mission jobs still finish
    deadline = time.time() + 40
    while time.time() < deadline:
        states = [api_client.get(f"/api/jobs/{jid}").json()["status"] for jid in mission_ids]
        if all(s in ("done", "failed") for s in states):
            break
        time.sleep(0.5)
    assert all(s == "done" for s in states), states
