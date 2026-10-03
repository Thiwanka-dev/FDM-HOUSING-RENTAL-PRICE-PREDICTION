"""Linear Ridge Regression rental-price model package."""

from .linear_ridge import (
    REQUIRED_FEATURES,
    LinearRidgeRentalPriceModel,
    predict_price,
)

__all__ = [
    "REQUIRED_FEATURES",
    "LinearRidgeRentalPriceModel",
    "predict_price",
]
