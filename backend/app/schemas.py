"""Request and response bodies of the API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .registry import DEFAULT_MODEL_ID


class RentalFeatures(BaseModel):
    """Description of one rental listing, as entered by the user."""

    region: str
    state: str
    type: str
    sqfeet: float = Field(gt=0)
    beds: int = Field(ge=0, le=8)
    baths: float = Field(ge=0, le=8)
    laundry_options: str
    parking_options: str
    cats_allowed: bool = False
    dogs_allowed: bool = False
    smoking_allowed: bool = False
    wheelchair_access: bool = False
    electric_vehicle_charge: bool = False
    comes_furnished: bool = False

    # Optional: the typical coordinates of the region are used when omitted.
    lat: float | None = Field(default=None, ge=-90, le=90)
    long: float | None = Field(default=None, ge=-180, le=180)


class PredictRequest(BaseModel):
    features: RentalFeatures
    model: str = DEFAULT_MODEL_ID


class CompareRequest(BaseModel):
    features: RentalFeatures


class PredictResponse(BaseModel):
    model: str
    name: str
    price: float
    # Mean absolute error of the model on the test set, in dollars.
    test_mae: float | None


class ModelInfo(BaseModel):
    id: str
    name: str
    default: bool
    available: bool
    test_mae: float | None
    test_rmse: float | None
    test_r2: float | None
