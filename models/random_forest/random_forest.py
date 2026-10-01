"""Reusable Random Forest training components and prediction interface.

The implementation mirrors ``03_RandomForest_Thiwanka.ipynb``. Region target
encoding is fitted from training targets only, and the fitted mapping is stored
with the other artifacts for target-free inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


NUMERICAL_FEATURES = ["sqfeet", "beds", "baths", "lat", "long"]
ONEHOT_FEATURES = [
    "type",
    "laundry_options",
    "parking_options",
    "state",
]
BINARY_FEATURES = [
    "cats_allowed",
    "dogs_allowed",
    "smoking_allowed",
    "wheelchair_access",
    "electric_vehicle_charge",
    "comes_furnished",
]
REGION_FEATURE = "region"
REGION_ENCODED_FEATURE = "region_encoded"

REQUIRED_FEATURES = [
    *NUMERICAL_FEATURES,
    REGION_FEATURE,
    *ONEHOT_FEATURES,
    *BINARY_FEATURES,
]

DEFAULT_ARTIFACT_PATH = (
    Path(__file__).resolve().parent / "artifacts" / "random_forest.joblib"
)

MODEL_PARAMETERS = {
    "n_estimators": 200,
    "max_depth": 25,
    "min_samples_leaf": 2,
    "max_features": 0.7,
    "random_state": 42,
    "n_jobs": 2,
}


@dataclass
class SmoothedRegionTargetEncoder:
    """Notebook-equivalent smoothed target encoder for ``region``.

    The mapping is learned only from the supplied training target. As in the
    notebook, training rows are encoded with the full training mapping rather
    than an internal out-of-fold mapping. Unknown or missing regions use the
    stored global training-target mean.
    """

    smoothing: float = 10.0
    column: str = REGION_FEATURE
    global_mean_: float | None = None
    mapping_: dict[Any, float] | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "SmoothedRegionTargetEncoder":
        self._validate_column(X)

        target = pd.Series(y).reset_index(drop=True)
        regions = X[self.column].reset_index(drop=True)
        self.global_mean_ = float(target.mean())

        stats = (
            pd.DataFrame({self.column: regions, "target": target})
            .groupby(self.column, dropna=True)["target"]
            .agg(["mean", "count"])
        )
        stats["encoded"] = (
            stats["count"] * stats["mean"]
            + self.smoothing * self.global_mean_
        ) / (stats["count"] + self.smoothing)

        self.mapping_ = stats["encoded"].to_dict()
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        self._validate_fitted()
        self._validate_column(X)

        transformed = X.copy()
        transformed[REGION_ENCODED_FEATURE] = (
            transformed[self.column]
            .map(self.mapping_)
            .fillna(self.global_mean_)
            .astype(float)
        )
        return transformed.drop(columns=[self.column])

    def fit_transform(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        return self.fit(X, y).transform(X)

    def _validate_column(self, X: pd.DataFrame) -> None:
        if self.column not in X.columns:
            raise ValueError(f"Missing target-encoded feature: {self.column}")

    def _validate_fitted(self) -> None:
        if self.global_mean_ is None or self.mapping_ is None:
            raise RuntimeError("The region target encoder has not been fitted.")


def build_preprocessor() -> ColumnTransformer:
    """Create the notebook-equivalent, unscaled feature preprocessor."""

    numerical_pipeline = Pipeline(
        [("imputer", SimpleImputer(strategy="median"))]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )

    return ColumnTransformer(
        [
            (
                "numerical",
                numerical_pipeline,
                [*NUMERICAL_FEATURES, REGION_ENCODED_FEATURE],
            ),
            ("categorical", categorical_pipeline, ONEHOT_FEATURES),
            ("binary", "passthrough", BINARY_FEATURES),
        ]
    )


def build_random_forest() -> RandomForestRegressor:
    """Create the selected Tuned_3 Random Forest configuration."""

    return RandomForestRegressor(**MODEL_PARAMETERS)


def validate_input_columns(data: pd.DataFrame) -> None:
    """Raise a clear error if any required predictor column is absent."""

    missing = [column for column in REQUIRED_FEATURES if column not in data.columns]
    if missing:
        raise ValueError(
            "Missing required input columns: " + ", ".join(missing)
        )


def _to_dataframe(
    input_data: pd.DataFrame | pd.Series | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    if isinstance(input_data, pd.DataFrame):
        frame = input_data.copy()
    elif isinstance(input_data, pd.Series):
        frame = input_data.to_frame().T
    elif isinstance(input_data, Mapping):
        frame = pd.DataFrame([input_data])
    else:
        frame = pd.DataFrame(list(input_data))

    validate_input_columns(frame)
    return frame.loc[:, REQUIRED_FEATURES].copy()


class RandomForestRentalPriceModel:
    """Fitted preprocessing and Random Forest model used by the backend."""

    def __init__(
        self,
        *,
        region_encoder: SmoothedRegionTargetEncoder | None = None,
        preprocessor: ColumnTransformer | None = None,
        model: RandomForestRegressor | None = None,
    ) -> None:
        self.region_encoder = region_encoder or SmoothedRegionTargetEncoder()
        self.preprocessor = preprocessor or build_preprocessor()
        self.model = model or build_random_forest()
        self.is_fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RandomForestRentalPriceModel":
        """Fit all components using training data only.

        The target is log-transformed because the notebook trains the forest on
        ``log1p(price)``. Prediction applies ``expm1`` to return dollar-scale
        rental prices.
        """

        validate_input_columns(X)
        training_features = X.loc[:, REQUIRED_FEATURES].copy()
        training_target = pd.Series(y).reset_index(drop=True)

        if len(training_features) != len(training_target):
            raise ValueError("Training features and target must have equal lengths.")
        if training_target.isna().any():
            raise ValueError("Training target contains missing values.")
        if (training_target < 0).any():
            raise ValueError("Training target must be non-negative for log1p.")

        encoded = self.region_encoder.fit_transform(
            training_features.reset_index(drop=True), training_target
        )
        processed = self.preprocessor.fit_transform(encoded)
        self.model.fit(processed, np.log1p(training_target.to_numpy()))
        self.is_fitted = True
        return self

    def predict(
        self,
        input_data: pd.DataFrame
        | pd.Series
        | Mapping[str, Any]
        | Sequence[Mapping[str, Any]],
    ) -> np.ndarray:
        """Predict rental prices on the original dollar scale without a target."""

        self._validate_fitted()
        features = _to_dataframe(input_data)
        encoded = self.region_encoder.transform(features)
        processed = self.preprocessor.transform(encoded)
        prediction_log = self.model.predict(processed)
        return np.expm1(prediction_log)

    def predict_one(self, input_data: Mapping[str, Any] | pd.Series) -> float:
        """Return one backend-friendly rental-price prediction."""

        predictions = self.predict(input_data)
        if len(predictions) != 1:
            raise ValueError("predict_one expects exactly one input record.")
        return float(predictions[0])

    def save(self, artifact_path: str | Path = DEFAULT_ARTIFACT_PATH) -> Path:
        """Save the model, fitted preprocessing, encoder mapping, and metadata."""

        self._validate_fitted()
        destination = Path(artifact_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "artifact_version": 1,
                "model_type": "RandomForestRegressor",
                "model_parameters": MODEL_PARAMETERS.copy(),
                "required_features": REQUIRED_FEATURES.copy(),
                "target_transformation": "log1p/expm1",
                "region_smoothing": self.region_encoder.smoothing,
                "region_encoder": self.region_encoder,
                "preprocessor": self.preprocessor,
                "model": self.model,
            },
            destination,
            compress=3,
        )
        return destination

    @classmethod
    def load(
        cls, artifact_path: str | Path = DEFAULT_ARTIFACT_PATH
    ) -> "RandomForestRentalPriceModel":
        """Load a saved artifact without retraining."""

        source = Path(artifact_path)
        if not source.exists():
            raise FileNotFoundError(
                f"Random Forest artifact not found: {source}. "
                "Run the training script first."
            )

        artifact = joblib.load(source)
        if artifact.get("artifact_version") != 1:
            raise ValueError("Unsupported Random Forest artifact version.")
        if artifact.get("required_features") != REQUIRED_FEATURES:
            raise ValueError("Artifact feature schema does not match this code version.")

        instance = cls(
            region_encoder=artifact["region_encoder"],
            preprocessor=artifact["preprocessor"],
            model=artifact["model"],
        )
        instance.is_fitted = True
        return instance

    def _validate_fitted(self) -> None:
        if not self.is_fitted:
            raise RuntimeError("The Random Forest rental-price model is not fitted.")


def predict_price(
    input_data: pd.DataFrame
    | pd.Series
    | Mapping[str, Any]
    | Sequence[Mapping[str, Any]],
    artifact_path: str | Path = DEFAULT_ARTIFACT_PATH,
) -> float | np.ndarray:
    """Load the artifact and predict prices for backend integration.

    A single mapping/Series returns one ``float``. Batch inputs return a NumPy
    array. No ``price`` target is required or read during inference.
    """

    predictor = RandomForestRentalPriceModel.load(artifact_path)
    if isinstance(input_data, (Mapping, pd.Series)):
        return predictor.predict_one(input_data)
    return predictor.predict(input_data)
