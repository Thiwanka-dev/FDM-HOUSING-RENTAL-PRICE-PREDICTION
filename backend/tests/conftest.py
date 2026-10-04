"""Shared fixtures of the backend tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="session")
def client():
    # The context manager runs the start-up code that loads the default model.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def listing() -> dict:
    """A valid request without coordinates, as the input form sends it."""

    return {
        "region": "seattle-tacoma",
        "state": "wa",
        "type": "apartment",
        "sqfeet": 850,
        "beds": 2,
        "baths": 1,
        "laundry_options": "w/d in unit",
        "parking_options": "off-street parking",
    }
