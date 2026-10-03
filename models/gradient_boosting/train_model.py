"""Train/evaluate a chosen Gradient Boosting configuration.

Run from the repository root after selecting parameters in the experiment
notebook:

    python -m models.gradient_boosting.train_model --evaluate-test
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .gradient_boosting import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_MODEL_PARAMETERS,
    REQUIRED_FEATURES,
    GradientBoostingRentalPriceModel,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAIN_PATH = PROJECT_ROOT / "data" / "raw_train.csv"
DEFAULT_TEST_PATH = PROJECT_ROOT / "data" / "raw_test.csv"


def load_modeling_data(path: str | Path) -> tuple[pd.DataFrame, pd.Series]:
    data = pd.read_csv(path)
    if "price" not in data.columns:
        raise ValueError(f"Missing target column 'price' in {path}")
    missing = [column for column in REQUIRED_FEATURES if column not in data.columns]
    if missing:
        raise ValueError(f"Missing required features in {path}: " + ", ".join(missing))
    return data.loc[:, REQUIRED_FEATURES].copy(), data["price"].copy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the selected Gradient Boosting rental-price model."
    )
    parser.add_argument("--train-data", type=Path, default=DEFAULT_TRAIN_PATH)
    parser.add_argument("--test-data", type=Path, default=DEFAULT_TEST_PATH)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT_PATH)
    parser.add_argument(
        "--parameters-json",
        type=Path,
        help="Optional JSON object containing the notebook-selected parameters.",
    )
    parser.add_argument("--engineered-features", action="store_true")
    parser.add_argument("--evaluate-test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    parameters = DEFAULT_MODEL_PARAMETERS.copy()
    use_engineered_features = args.engineered_features
    if args.parameters_json:
        saved_choice = json.loads(args.parameters_json.read_text(encoding="utf-8"))
        # Accept either a plain parameter dictionary or the richer
        # selection_record.json exported by the experiment notebook.
        if "parameters" in saved_choice:
            parameters.update(saved_choice["parameters"])
            use_engineered_features = bool(
                saved_choice.get("use_engineered_features", use_engineered_features)
            )
        else:
            parameters.update(saved_choice)

    X_train, y_train = load_modeling_data(args.train_data)
    predictor = GradientBoostingRentalPriceModel(
        model_parameters=parameters,
        use_engineered_features=use_engineered_features,
    ).fit(X_train, y_train)
    saved_path = predictor.save(args.artifact)
    print("Parameters:", parameters)
    print("Engineered features:", use_engineered_features)
    print(f"Artifact saved: {saved_path}")

    if args.evaluate_test:
        X_test, y_test = load_modeling_data(args.test_data)
        predictions = predictor.predict(X_test)
        print("Untouched test-set performance")
        print(f"MAE:  {mean_absolute_error(y_test, predictions):.2f}")
        print(f"RMSE: {np.sqrt(mean_squared_error(y_test, predictions)):.2f}")
        print(f"R²:   {r2_score(y_test, predictions):.4f}")


if __name__ == "__main__":
    main()
