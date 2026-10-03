"""Reusable tuned Ridge Regression model and prediction interface.

The implementation mirrors ``03_Linear_Ridge_Models.ipynb``: the raw features
are prepared in a preprocessing pipeline fitted on training data only, and the
model is trained on ``log1p(price)``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


NUMERICAL_FEATURES = ["beds", "baths", "lat", "long"]
CATEGORICAL_FEATURES = [
    "region",
    "type",
    "state",
    "laundry_options",
    "parking_options",
]
BINARY_FEATURES = [
    "cats_allowed",
    "dogs_allowed",
    "smoking_allowed",
    "wheelchair_access",
    "electric_vehicle_charge",
    "comes_furnished",
]

REQUIRED_FEATURES = [
    "sqfeet",
    *NUMERICAL_FEATURES,
    *CATEGORICAL_FEATURES,
    *BINARY_FEATURES,
]

DEFAULT_ARTIFACT_PATH = (
    Path(__file__).resolve().parent / "artifacts" / "linear_ridge.joblib"
)

# alpha selected by 5-fold cross-validation in the notebook.
MODEL_PARAMETERS = {"alpha": 10.0}


class SqfeetClipLog(BaseEstimator, TransformerMixin):
    """Clip square footage to training percentiles, then apply ``log1p``."""

    def __init__(self, lower_quantile: float = 0.005, upper_quantile: float = 0.995):
        self.lower_quantile = lower_quantile
        self.upper_quantile = upper_quantile

    def fit(self, X, y=None) -> "SqfeetClipLog":
        values = np.asarray(X, dtype="float64")
        self.lower_ = float(np.nanquantile(values, self.lower_quantile))
        self.upper_ = float(np.nanquantile(values, self.upper_quantile))
        return self

    def transform(self, X) -> np.ndarray:
        values = np.asarray(X, dtype="float64")
        return np.log1p(np.clip(values, self.lower_, self.upper_))


def build_pipeline(alpha: float = MODEL_PARAMETERS["alpha"]) -> Pipeline:
    """Create the notebook-equivalent preprocessing and Ridge model."""

    preprocessor = ColumnTransformer(
        [
            (
                "sqfeet",
                Pipeline(
                    [("clip_log", SqfeetClipLog()), ("scaler", StandardScaler())]
                ),
                ["sqfeet"],
            ),
            (
                "numerical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                NUMERICAL_FEATURES,
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
            ("binary", "passthrough", BINARY_FEATURES),
        ]
    )
    return Pipeline([("preprocessor", preprocessor), ("model", Ridge(alpha=alpha))])


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
    frame = frame.loc[:, REQUIRED_FEATURES].copy()

    # A single record arrives with object columns; restore numeric types.
    for column in ["sqfeet", *NUMERICAL_FEATURES, *BINARY_FEATURES]:
        frame[column] = pd.to_numeric(frame[column])
    return frame


class LinearRidgeRentalPriceModel:
    """Fitted preprocessing and Ridge Regression model used by the backend."""

    def __init__(self, *, pipeline: Pipeline | None = None) -> None:
        self.pipeline = pipeline or build_pipeline()
        self.is_fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LinearRidgeRentalPriceModel":
        """Fit the preprocessing and the model using training data only."""

        validate_input_columns(X)
        features = X.loc[:, REQUIRED_FEATURES].copy()
        target = pd.Series(y)

        if len(features) != len(target):
            raise ValueError("Training features and target must have equal lengths.")
        if target.isna().any() or (target < 0).any():
            raise ValueError("Training target must be complete and non-negative.")

        self.pipeline.fit(features, np.log1p(target.to_numpy()))
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
        return np.expm1(self.pipeline.predict(_to_dataframe(input_data)))

    def predict_one(self, input_data: Mapping[str, Any] | pd.Series) -> float:
        """Return one backend-friendly rental-price prediction."""

        predictions = self.predict(input_data)
        if len(predictions) != 1:
            raise ValueError("predict_one expects exactly one input record.")
        return float(predictions[0])

    def save(self, artifact_path: str | Path = DEFAULT_ARTIFACT_PATH) -> Path:
        """Save the fitted pipeline and metadata."""

        self._validate_fitted()
        destination = Path(artifact_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "artifact_version": 1,
                "model_type": "Ridge",
                "model_parameters": MODEL_PARAMETERS.copy(),
                "required_features": REQUIRED_FEATURES.copy(),
                "target_transformation": "log1p/expm1",
                "pipeline": self.pipeline,
            },
            destination,
            compress=3,
        )
        return destination

    @classmethod
    def load(
        cls, artifact_path: str | Path = DEFAULT_ARTIFACT_PATH
    ) -> "LinearRidgeRentalPriceModel":
        """Load a saved artifact without retraining."""

        source = Path(artifact_path)
        if not source.exists():
            raise FileNotFoundError(
                f"Linear Ridge artifact not found: {source}. "
                "Run the training script first."
            )

        artifact = joblib.load(source)
        if artifact.get("artifact_version") != 1:
            raise ValueError("Unsupported Linear Ridge artifact version.")
        if artifact.get("required_features") != REQUIRED_FEATURES:
            raise ValueError("Artifact feature schema does not match this code version.")

        instance = cls(pipeline=artifact["pipeline"])
        instance.is_fitted = True
        return instance

    def _validate_fitted(self) -> None:
        if not self.is_fitted:
            raise RuntimeError("The Linear Ridge rental-price model is not fitted.")


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

    predictor = LinearRidgeRentalPriceModel.load(artifact_path)
    if isinstance(input_data, (Mapping, pd.Series)):
        return predictor.predict_one(input_data)
    return predictor.predict(input_data)
