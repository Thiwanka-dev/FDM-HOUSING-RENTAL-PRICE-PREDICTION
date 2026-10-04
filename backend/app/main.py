"""API of the rental-price estimation system.

Run from the repository root:

    uvicorn backend.app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from models.neural_network.neural_network import BINARY_FEATURES, COORDINATE_FEATURES

from .metadata import METADATA, OPTION_FEATURES, REGION_COORDINATES
from .registry import DEFAULT_MODEL_ID, REGISTRY, ModelEntry
from .schemas import (
    CompareRequest,
    ModelInfo,
    PredictRequest,
    PredictResponse,
    RentalFeatures,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The default model is loaded at start-up; the others on their first use.
    REGISTRY[DEFAULT_MODEL_ID].model
    yield


app = FastAPI(title="U.S. Rental Price Estimation API", lifespan=lifespan)


def prepare_features(features: RentalFeatures) -> dict[str, Any]:
    """Convert a validated request into the raw record expected by the models."""

    record = features.model_dump()

    unknown = [
        f"{column}='{record[column]}'"
        for column in OPTION_FEATURES
        if record[column] not in METADATA[column]
    ]
    coordinates = REGION_COORDINATES.get((record["state"], record["region"]))
    if coordinates is None:
        unknown.append(f"region='{record['region']}' in state='{record['state']}'")
    if unknown:
        raise HTTPException(status_code=422, detail="Unknown values: " + ", ".join(unknown))

    # The user selects a region, not coordinates. The median coordinates of
    # the region in the training data stand in for the exact location.
    for column in COORDINATE_FEATURES:
        if record[column] is None:
            record[column] = coordinates[column]

    for column in BINARY_FEATURES:
        record[column] = int(record[column])
    return record


def get_entry(model_id: str) -> ModelEntry:
    entry = REGISTRY.get(model_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown model: '{model_id}'")
    if not entry.available:
        raise HTTPException(
            status_code=503,
            detail=f"The {entry.name} model file is missing. "
            "Run: python -m models.setup_models",
        )
    return entry


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    # The API has no home page; show the interactive documentation instead.
    return RedirectResponse("/docs")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/metadata")
def metadata() -> dict[str, Any]:
    """Values the input form offers: states, regions, options and ranges."""

    return METADATA


@app.get("/api/models")
def list_models() -> list[ModelInfo]:
    return [
        ModelInfo(
            id=entry.id,
            name=entry.name,
            default=entry.id == DEFAULT_MODEL_ID,
            available=entry.available,
            test_mae=(entry.metrics or {}).get("MAE"),
            test_rmse=(entry.metrics or {}).get("RMSE"),
            test_r2=(entry.metrics or {}).get("R2"),
        )
        for entry in REGISTRY.values()
    ]


def _prediction(entry: ModelEntry, record: dict[str, Any]) -> PredictResponse:
    return PredictResponse(
        model=entry.id,
        name=entry.name,
        price=round(entry.model.predict_one(record), 2),
        test_mae=(entry.metrics or {}).get("MAE"),
    )


@app.post("/api/predict")
def predict(request: PredictRequest) -> PredictResponse:
    entry = get_entry(request.model)
    return _prediction(entry, prepare_features(request.features))


@app.post("/api/predict/compare")
def compare(request: CompareRequest) -> list[PredictResponse]:
    """Predict the same listing with every model whose file is available."""

    record = prepare_features(request.features)
    return [_prediction(entry, record) for entry in REGISTRY.values() if entry.available]
