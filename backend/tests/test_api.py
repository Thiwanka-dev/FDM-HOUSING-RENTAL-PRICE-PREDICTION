"""Tests of the API endpoints.

Run from the repository root:

    python -m pytest backend
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from backend.app.metadata import REGION_COORDINATES
from backend.app.registry import DEFAULT_MODEL_ID, REGISTRY
from models.setup_models import TEST_PATH


N_PARITY_ROWS = 20


def predict(client, features: dict, **body):
    return client.post("/api/predict", json={"features": features, **body})


# ---------------------------------------------------------------- information


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_models_lists_the_four_models(client):
    models = client.get("/api/models").json()

    assert [model["id"] for model in models] == list(REGISTRY)
    assert [model["id"] for model in models if model["default"]] == [DEFAULT_MODEL_ID]
    for model in models:
        assert model["test_mae"] > 0
        assert 0 < model["test_r2"] < 1


def test_metadata_has_the_form_options(client):
    metadata = client.get("/api/metadata").json()

    assert len(metadata["states"]) == 51
    for state in metadata["states"]:
        assert state["regions"], f"{state['name']} has no regions"
    for column in ["type", "laundry_options", "parking_options"]:
        assert metadata[column]
    for column in ["sqfeet", "beds", "baths"]:
        limits = metadata["numeric"][column]
        assert limits["min"] <= limits["default"] <= limits["max"]


# ----------------------------------------------------------------- prediction


def test_predict_uses_the_neural_network_by_default(client, listing):
    response = predict(client, listing)

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == DEFAULT_MODEL_ID
    assert body["price"] > 0
    assert body["test_mae"] > 0


def test_missing_coordinates_are_filled_from_the_region(client, listing):
    coordinates = REGION_COORDINATES[(listing["state"], listing["region"])]

    without = predict(client, listing).json()["price"]
    explicit = predict(client, {**listing, **coordinates}).json()["price"]
    assert without == explicit


def test_regions_with_the_same_name_are_different_places(client, listing):
    georgia = predict(client, {**listing, "region": "albany", "state": "ga"}).json()
    new_york = predict(client, {**listing, "region": "albany", "state": "ny"}).json()

    assert georgia["price"] != new_york["price"]


@pytest.mark.parametrize("model_id", list(REGISTRY))
def test_api_matches_the_model_called_directly(client, model_id):
    entry = REGISTRY[model_id]
    if not entry.available:
        pytest.skip(f"{entry.name} model file is missing; run models.setup_models")
    if not TEST_PATH.exists():
        pytest.skip("data/raw_test.csv is missing; run 02_Preprocessing.ipynb")

    test = pd.read_csv(TEST_PATH).dropna()
    # The API only accepts state and region pairs seen in the training data.
    known = [pair in REGION_COORDINATES for pair in zip(test["state"], test["region"])]
    rows = test[known].sample(N_PARITY_ROWS, random_state=0).drop(columns=["price"])

    expected = entry.model.predict(rows)
    for features, price in zip(json.loads(rows.to_json(orient="records")), expected):
        response = predict(client, features, model=model_id)
        assert response.status_code == 200
        assert response.json()["price"] == pytest.approx(price, abs=0.02)


# ------------------------------------------------------------------ bad input


@pytest.mark.parametrize(
    "change",
    [
        {"type": "castle"},
        {"laundry_options": "robot"},
        {"parking_options": "helipad"},
        {"region": "colombo"},
        {"state": "fl"},  # seattle-tacoma is not in Florida
        {"sqfeet": 0},
        {"sqfeet": -100},
        {"beds": -1},
        {"beds": 9},
        {"baths": 9},
        {"lat": 120},
        {"sqfeet": "large"},
    ],
)
def test_invalid_values_are_rejected(client, listing, change):
    assert predict(client, {**listing, **change}).status_code == 422


@pytest.mark.parametrize("field", ["region", "state", "type", "sqfeet", "beds", "baths"])
def test_missing_fields_are_rejected(client, listing, field):
    del listing[field]
    assert predict(client, listing).status_code == 422


def test_unknown_model_is_not_found(client, listing):
    assert predict(client, listing, model="xgboost").status_code == 404


def test_model_without_a_saved_file_is_unavailable(client, listing, monkeypatch):
    entry = REGISTRY["random_forest"]
    monkeypatch.setattr(entry, "artifact_path", Path("missing.joblib"))

    models = {model["id"]: model for model in client.get("/api/models").json()}
    assert models["random_forest"]["available"] is False
    assert predict(client, listing, model="random_forest").status_code == 503
