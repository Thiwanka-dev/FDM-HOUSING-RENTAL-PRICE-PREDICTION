"""Reusable Gradient Boosting model for U.S. rental-price prediction.

The module is deliberately separate from the Random Forest implementation so
that each group member's work remains isolated.  It expects the cleaned raw
train/test splits produced by ``02_Preprocessing.ipynb`` and learns every
target-dependent or data-dependent transformation from training data only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


NUMERICAL_FEATURES = ["sqfeet", "beds", "baths", "lat", "long"]
ONEHOT_FEATURES = ["type", "laundry_options", "parking_options", "state"]
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
ENGINEERED_FEATURES = ["total_rooms", "sqfeet_per_room"]

REQUIRED_FEATURES = [
    *NUMERICAL_FEATURES,
    REGION_FEATURE,
    *ONEHOT_FEATURES,
    *BINARY_FEATURES,
]

DEFAULT_ARTIFACT_PATH = (
    Path(__file__).resolve().parent / "artifacts" / "gradient_boosting.joblib"
)

# This is a sensible starting configuration.  The experiment notebook selects
# the final configuration from cross-validation evidence rather than assuming
# that this configuration must win.
DEFAULT_MODEL_PARAMETERS = {
    "n_estimators": 200,
    "learning_rate": 0.05,
    "max_depth": 3,
    "min_samples_leaf": 5,
    "subsample": 0.8,
    "loss": "squared_error",
    "random_state": 42,
}


@dataclass
class SmoothedRegionTargetEncoder:
    """Encode ``region`` using smoothed training-target means."""

    smoothing: float = 10.0
    column: str = REGION_FEATURE
    global_mean_: float | None = None
    mapping_: dict[Any, float] | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "SmoothedRegionTargetEncoder":
        if self.column not in X.columns:
            raise ValueError(f"Missing target-encoded feature: {self.column}")

        regions = X[self.column].reset_index(drop=True)
        target = pd.Series(y).reset_index(drop=True)
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
        if self.global_mean_ is None or self.mapping_ is None:
            raise RuntimeError("The region target encoder has not been fitted.")
        if self.column not in X.columns:
            raise ValueError(f"Missing target-encoded feature: {self.column}")

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


def add_engineered_features(X: pd.DataFrame) -> pd.DataFrame:
    """Add two safe size/room features without division by zero."""

    transformed = X.copy()
    room_count = transformed["beds"].fillna(0) + transformed["baths"].fillna(0)
    safe_room_count = room_count.clip(lower=1)
    transformed["total_rooms"] = room_count
    transformed["sqfeet_per_room"] = transformed["sqfeet"] / safe_room_count
    return transformed


def build_preprocessor(*, use_engineered_features: bool) -> ColumnTransformer:
    """Create the unscaled preprocessing used by the tree-based model."""

    numeric_columns = [*NUMERICAL_FEATURES, REGION_ENCODED_FEATURE]
    if use_engineered_features:
        numeric_columns.extend(ENGINEERED_FEATURES)

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
            ("numerical", numerical_pipeline, numeric_columns),
            ("categorical", categorical_pipeline, ONEHOT_FEATURES),
            ("binary", "passthrough", BINARY_FEATURES),
        ]
    )


def validate_input_columns(data: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_FEATURES if column not in data.columns]
    if missing:
        raise ValueError("Missing required input columns: " + ", ".join(missing))


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


class GradientBoostingRentalPriceModel:
    """Training, preprocessing, persistence, and inference in one object."""

    def __init__(
        self,
        *,
        model_parameters: Mapping[str, Any] | None = None,
        use_engineered_features: bool = False,
        region_smoothing: float = 10.0,
        region_encoder: SmoothedRegionTargetEncoder | None = None,
        preprocessor: ColumnTransformer | None = None,
        model: GradientBoostingRegressor | None = None,
    ) -> None:
        self.model_parameters = dict(
            model_parameters or DEFAULT_MODEL_PARAMETERS
        )
        self.use_engineered_features = use_engineered_features
        self.region_encoder = region_encoder or SmoothedRegionTargetEncoder(
            smoothing=region_smoothing
        )
        self.preprocessor = preprocessor or build_preprocessor(
            use_engineered_features=use_engineered_features
        )
        self.model = model or GradientBoostingRegressor(**self.model_parameters)
        self.is_fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "GradientBoostingRentalPriceModel":
        validate_input_columns(X)
        features = X.loc[:, REQUIRED_FEATURES].reset_index(drop=True)
        target = pd.Series(y).reset_index(drop=True)
        if len(features) != len(target):
            raise ValueError("Training features and target must have equal lengths.")
        if target.isna().any() or (target < 0).any():
            raise ValueError("Training target must be complete and non-negative.")

        if len(features) < 5:
            raise ValueError("At least five training rows are required for region encoding.")

        # Training rows receive out-of-fold values.  The final mapping, learned
        # from all training rows, is retained only for unseen-row inference.
        encoded_values = np.empty(len(features), dtype=float)
        inner_folds = KFold(n_splits=5, shuffle=True, random_state=42)
        for fit_index, holdout_index in inner_folds.split(features):
            fold_encoder = SmoothedRegionTargetEncoder(
                smoothing=self.region_encoder.smoothing
            ).fit(features.iloc[fit_index], target.iloc[fit_index])
            encoded_values[holdout_index] = fold_encoder.transform(
                features.iloc[holdout_index]
            )[REGION_ENCODED_FEATURE].to_numpy()

        self.region_encoder.fit(features, target)
        encoded = features.copy()
        encoded[REGION_ENCODED_FEATURE] = encoded_values
        encoded = encoded.drop(columns=[REGION_FEATURE])
        if self.use_engineered_features:
            encoded = add_engineered_features(encoded)
        processed = self.preprocessor.fit_transform(encoded)
        self.model.fit(processed, np.log1p(target.to_numpy()))
        self.is_fitted = True
        return self

    def predict(
        self,
        input_data: pd.DataFrame
        | pd.Series
        | Mapping[str, Any]
        | Sequence[Mapping[str, Any]],
    ) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("The Gradient Boosting model is not fitted.")
        features = _to_dataframe(input_data)
        encoded = self.region_encoder.transform(features)
        if self.use_engineered_features:
            encoded = add_engineered_features(encoded)
        processed = self.preprocessor.transform(encoded)
        return np.maximum(0.0, np.expm1(self.model.predict(processed)))

    def predict_one(self, input_data: Mapping[str, Any] | pd.Series) -> float:
        predictions = self.predict(input_data)
        if len(predictions) != 1:
            raise ValueError("predict_one expects exactly one input record.")
        return float(predictions[0])

    def save(self, artifact_path: str | Path = DEFAULT_ARTIFACT_PATH) -> Path:
        if not self.is_fitted:
            raise RuntimeError("The Gradient Boosting model is not fitted.")
        destination = Path(artifact_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "artifact_version": 1,
                "model_type": "GradientBoostingRegressor",
                "model_parameters": self.model_parameters,
                "use_engineered_features": self.use_engineered_features,
                "required_features": REQUIRED_FEATURES.copy(),
                "target_transformation": "log1p/expm1",
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
    ) -> "GradientBoostingRentalPriceModel":
        source = Path(artifact_path)
        if not source.exists():
            raise FileNotFoundError(
                f"Gradient Boosting artifact not found: {source}. Train it first."
            )
        artifact = joblib.load(source)
        if artifact.get("artifact_version") != 1:
            raise ValueError("Unsupported Gradient Boosting artifact version.")
        if artifact.get("required_features") != REQUIRED_FEATURES:
            raise ValueError("Artifact feature schema does not match this code version.")
        instance = cls(
            model_parameters=artifact["model_parameters"],
            use_engineered_features=artifact["use_engineered_features"],
            region_encoder=artifact["region_encoder"],
            preprocessor=artifact["preprocessor"],
            model=artifact["model"],
        )
        instance.is_fitted = True
        return instance


def predict_price(
    input_data: pd.DataFrame
    | pd.Series
    | Mapping[str, Any]
    | Sequence[Mapping[str, Any]],
    artifact_path: str | Path = DEFAULT_ARTIFACT_PATH,
) -> float | np.ndarray:
    predictor = GradientBoostingRentalPriceModel.load(artifact_path)
    if isinstance(input_data, (Mapping, pd.Series)):
        return predictor.predict_one(input_data)
    return predictor.predict(input_data)
