"""Train and save the tuned Ridge Regression rental-price model.

Run from the repository root:

    python -m models.linear_ridge.train_model
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .linear_ridge import (
    DEFAULT_ARTIFACT_PATH,
    MODEL_PARAMETERS,
    REQUIRED_FEATURES,
    LinearRidgeRentalPriceModel,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAIN_PATH = PROJECT_ROOT / "data" / "raw_train.csv"
DEFAULT_TEST_PATH = PROJECT_ROOT / "data" / "raw_test.csv"


def load_modeling_data(path: str | Path) -> tuple[pd.DataFrame, pd.Series]:
    """Load an authoritative cleaned split and separate predictors/target."""

    data = pd.read_csv(path)
    if "price" not in data.columns:
        raise ValueError(f"Missing target column 'price' in {path}")

    missing_features = [c for c in REQUIRED_FEATURES if c not in data.columns]
    if missing_features:
        raise ValueError(
            f"Missing required features in {path}: " + ", ".join(missing_features)
        )

    return data.loc[:, REQUIRED_FEATURES].copy(), data["price"].copy()


def train_and_save(
    train_path: str | Path = DEFAULT_TRAIN_PATH,
    artifact_path: str | Path = DEFAULT_ARTIFACT_PATH,
) -> LinearRidgeRentalPriceModel:
    """Fit only on ``raw_train.csv`` and save all inference components."""

    X_train, y_train = load_modeling_data(train_path)
    print(f"Training data: {len(X_train):,} rows x {X_train.shape[1]} features")
    print("Ridge parameters:", MODEL_PARAMETERS)
    print("Target transformation: log1p")

    predictor = LinearRidgeRentalPriceModel().fit(X_train, y_train)
    saved_path = predictor.save(artifact_path)

    print(f"Artifact saved: {saved_path}")
    return predictor


def evaluate_untouched_test(
    predictor: LinearRidgeRentalPriceModel,
    test_path: str | Path = DEFAULT_TEST_PATH,
) -> None:
    """Evaluate without fitting any component on the test set."""

    X_test, y_test = load_modeling_data(test_path)
    predictions = predictor.predict(X_test)

    print("Untouched test-set verification")
    print(f"MAE:  {mean_absolute_error(y_test, predictions):.2f}")
    print(f"RMSE: {np.sqrt(mean_squared_error(y_test, predictions)):.2f}")
    print(f"R²:   {r2_score(y_test, predictions):.4f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the reusable tuned Ridge Regression model."
    )
    parser.add_argument("--train-data", type=Path, default=DEFAULT_TRAIN_PATH)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT_PATH)
    parser.add_argument(
        "--evaluate-test",
        action="store_true",
        help="Evaluate the saved methodology on raw_test.csv without fitting it.",
    )
    parser.add_argument("--test-data", type=Path, default=DEFAULT_TEST_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    predictor = train_and_save(args.train_data, args.artifact)
    if args.evaluate_test:
        evaluate_untouched_test(predictor, args.test_data)


if __name__ == "__main__":
    main()
