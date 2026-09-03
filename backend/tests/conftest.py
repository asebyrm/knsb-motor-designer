"""Shared fixtures."""

from __future__ import annotations

import logging
import os

import pytest

# API tests run against an in-memory SQLite DB and an ephemeral secret.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("COOKIE_SECURE", "false")
# login limiting is still exercised (test_login_rate_limited); relax the heavy buckets
# so the concurrency load test can send its burst.
os.environ.setdefault("RATE_LIMIT_SIM_PER_MIN", "2000")
os.environ.setdefault("RATE_LIMIT_MISSION_PER_MIN", "500")
logging.disable(logging.CRITICAL)  # silence per-request structlog output in tests


@pytest.fixture(scope="session")
def knsb():
    from core.propellant import load_propellant

    return load_propellant("knsb")


@pytest.fixture
def api_client():
    """A TestClient with a fresh schema; lifespan creates tables for the in-memory DB."""
    from fastapi.testclient import TestClient

    from api.main import create_app
    from models.base import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(create_app()) as client:
        yield client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_design() -> dict:
    return {
        "name": "sample", "prefix": "PARS", "designer": "test",
        "propellant": {"id": "knsb"},
        "grain": {"type": "bates", "outer_diameter": 0.045, "core_diameter": 0.018,
                  "segment_length": 0.075, "segment_count": 3, "segment_spacing": 0.003},
        "nozzle": {"throat_diameter": 0.0115, "expansion_ratio": 5.0, "throat_length": 0.006},
        "case": {"material_id": "pa12", "inner_diameter": 0.052, "wall_thickness": 0.005,
                 "print_method": "sls"},
        "liner": {"material_id": "kraft_phenolic", "thickness": 0.003},
        "bulkhead": {"material_id": "pa12", "thickness": 0.010},
        "meop_bar": 45,
    }
