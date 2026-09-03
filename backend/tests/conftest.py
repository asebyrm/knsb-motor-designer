"""Shared fixtures."""

from __future__ import annotations

import pytest

from core.propellant import load_propellant


@pytest.fixture(scope="session")
def knsb():
    return load_propellant("knsb")
