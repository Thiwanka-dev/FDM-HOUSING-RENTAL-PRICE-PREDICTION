"""Create the saved model files that are missing after cloning the project.

The Neural Network, Gradient Boosting and Ridge Regression files are stored in
git. The Random Forest file (about 270 MB) is too large for GitHub, so it is
trained here instead (about 1 minute).

Run from the repository root:

    python -m models.setup_models                  # build missing files only
    python -m models.setup_models --evaluate-test  # and check them on raw_test.csv
    python -m models.setup_models --force          # rebuild every file
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = PROJECT_ROOT / "data" / "raw_train.csv"
TEST_PATH = PROJECT_ROOT / "data" / "raw_test.csv"
METRICS_PATH = PROJECT_ROOT / "models" / "test_metrics.json"

# Configuration selected by cross-validation in 04_GradientBoosting_Janeesha.ipynb.
# The package default differs, so it is passed explicitly.
GRADIENT_BOOSTING_PARAMETERS = {
    "n_estimators": 150,
    "learning_rate": 0.05,
    "max_depth": 4,
    "min_samples_leaf": 10,
    "subsample": 0.8,
    "random_state": 42,
}


def _train_random_forest() -> None:
    from .random_forest.train_model import train_and_save

    train_and_save(TRAIN_PATH)


def _train_gradient_boosting() -> None:
    from .gradient_boosting.gradient_boosting import (
        REQUIRED_FEATURES,
        GradientBoostingRentalPriceModel,
    )

    data = pd.read_csv(TRAIN_PATH)
    predictor = GradientBoostingRentalPriceModel(
        model_parameters=GRADIENT_BOOSTING_PARAMETERS,
        use_engineered_features=False,
    ).fit(data.loc[:, REQUIRED_FEATURES], data["price"])
    print(f"Artifact saved: {predictor.save()}")


def _train_neural_network() -> None:
    from .neural_network.train_model import train_and_save

    train_and_save(TRAIN_PATH)


def _train_linear_ridge() -> None:
    from .linear_ridge.train_model import train_and_save

    train_and_save(TRAIN_PATH)


def _load_random_forest():
    from .random_forest import RandomForestRentalPriceModel

    return RandomForestRentalPriceModel.load()


def _load_gradient_boosting():
    from .gradient_boosting import GradientBoostingRentalPriceModel

    return GradientBoostingRentalPriceModel.load()


def _load_neural_network():
    from .neural_network import NeuralNetworkRentalPriceModel

    return NeuralNetworkRentalPriceModel.load()


def _load_linear_ridge():
    from .linear_ridge import LinearRidgeRentalPriceModel

    return LinearRidgeRentalPriceModel.load()


MODELS = {
    "Random Forest": (
        PROJECT_ROOT / "models" / "random_forest" / "artifacts" / "random_forest.joblib",
        _train_random_forest,
        _load_random_forest,
    ),
    "Gradient Boosting": (
        PROJECT_ROOT / "models" / "gradient_boosting" / "artifacts" / "gradient_boosting.joblib",
        _train_gradient_boosting,
        _load_gradient_boosting,
    ),
    "Neural Network": (
        PROJECT_ROOT / "models" / "neural_network" / "artifacts" / "neural_network.pt",
        _train_neural_network,
        _load_neural_network,
    ),
    "Ridge Regression": (
        PROJECT_ROOT / "models" / "linear_ridge" / "artifacts" / "linear_ridge.joblib",
        _train_linear_ridge,
        _load_linear_ridge,
    ),
}


def build_models(force: bool = False) -> None:
    """Train every model whose saved file is missing (or all with ``force``)."""

    for name, (artifact, train, _) in MODELS.items():
        if artifact.exists() and not force:
            print(f"{name}: found {artifact.relative_to(PROJECT_ROOT)}")
            continue

        print(f"\n{name}: training...")
        train()


def evaluate_models() -> None:
    """Score every saved model on the untouched test set.

    The results are also written to ``test_metrics.json`` for the backend.
    """

    test = pd.read_csv(TEST_PATH)
    X_test, y_test = test.drop(columns=["price"]), test["price"]

    rows = []
    for name, (_, _, load) in MODELS.items():
        predictions = load().predict(X_test)
        rows.append({
            "Model": name,
            "MAE": float(mean_absolute_error(y_test, predictions)),
            "RMSE": float(np.sqrt(mean_squared_error(y_test, predictions))),
            "R2": float(r2_score(y_test, predictions)),
        })

    results = pd.DataFrame(rows).set_index("Model").round(4)
    print("\nTest-set performance of the saved models")
    print(results.to_string())

    METRICS_PATH.write_text(
        json.dumps(results.to_dict(orient="index"), indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nMetrics saved: {METRICS_PATH.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the saved model files needed by the project."
    )
    parser.add_argument("--force", action="store_true", help="Rebuild every model file.")
    parser.add_argument(
        "--evaluate-test",
        action="store_true",
        help="Score every saved model on raw_test.csv afterwards.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    missing = [path for path in (TRAIN_PATH, TEST_PATH) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing data files: "
            + ", ".join(str(path.relative_to(PROJECT_ROOT)) for path in missing)
            + ". Run notebooks/02_Preprocessing.ipynb first."
        )

    build_models(force=args.force)
    if args.evaluate_test:
        evaluate_models()


if __name__ == "__main__":
    main()
