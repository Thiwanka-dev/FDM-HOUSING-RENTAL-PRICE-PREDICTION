"""Reusable neural-network training components and prediction interface.

The implementation mirrors ``04_NeuralNetwork_Savindu.ipynb``. Every learned
preprocessing value is fitted from training rows only and is stored with the
network weights, so inference needs neither the training data nor a target.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from torch import nn


NUMERICAL_FEATURES = ["sqfeet", "beds", "baths", "lat", "long"]
COORDINATE_FEATURES = ["lat", "long"]
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
GEO_MISSING_FEATURE = "geo_missing"

REQUIRED_FEATURES = [
    *NUMERICAL_FEATURES,
    *CATEGORICAL_FEATURES,
    *BINARY_FEATURES,
]

# Order of the continuous inputs of the network.
CONTINUOUS_FEATURES = [
    *NUMERICAL_FEATURES,
    GEO_MISSING_FEATURE,
    *BINARY_FEATURES,
]

DEFAULT_ARTIFACT_PATH = (
    Path(__file__).resolve().parent / "artifacts" / "neural_network.pt"
)

# Percentiles of the training data used as clipping limits.
CLIP_QUANTILES = {
    "sqfeet": (0.005, 0.995),
    "lat": (0.001, 0.999),
    "long": (0.001, 0.999),
}

# Index reserved for categories that were not seen during training.
UNKNOWN_INDEX = 0

# Selected Tuned_5 configuration.
MODEL_PARAMETERS = {
    "hidden_sizes": (1024, 512, 256),
    "dropout": 0.3,
    "n_frequencies": 32,
    "sigma": 30.0,
}

TRAINING_PARAMETERS = {
    "learning_rate": 1e-3,
    "weight_decay": 1e-4,
    "batch_size": 512,
    "max_epochs": 100,
    "patience": 10,
    "huber_delta": 1.0,
    "validation_size": 0.15,
    "random_state": 42,
}


@dataclass
class RentalPreprocessor:
    """Notebook-equivalent feature and target preprocessing.

    All learned values are plain Python types, so they can be stored next to
    the network weights and loaded without unpickling arbitrary objects.
    """

    region_medians_: dict[str, dict[str, float]] | None = None
    numerical_medians_: dict[str, float] | None = None
    clip_bounds_: dict[str, list[float]] | None = None
    scaler_mean_: list[float] | None = None
    scaler_scale_: list[float] | None = None
    category_maps_: dict[str, dict[str, int]] | None = None
    target_mean_: float | None = None
    target_std_: float | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RentalPreprocessor":
        medians = X.groupby("region")[COORDINATE_FEATURES].median()
        self.region_medians_ = {
            column: medians[column].dropna().to_dict()
            for column in COORDINATE_FEATURES
        }
        self.numerical_medians_ = {
            column: float(X[column].median()) for column in NUMERICAL_FEATURES
        }
        self.clip_bounds_ = {
            column: [float(X[column].quantile(lower)), float(X[column].quantile(upper))]
            for column, (lower, upper) in CLIP_QUANTILES.items()
        }

        prepared = self._prepare_numerical(X)[NUMERICAL_FEATURES].to_numpy(dtype="float64")
        self.scaler_mean_ = prepared.mean(axis=0).tolist()
        self.scaler_scale_ = prepared.std(axis=0).tolist()

        self.category_maps_ = {
            column: {
                category: index
                for index, category in enumerate(
                    sorted(X[column].dropna().unique()), start=1
                )
            }
            for column in CATEGORICAL_FEATURES
        }

        target_log = np.log1p(pd.Series(y).astype("float64"))
        self.target_mean_ = float(target_log.mean())
        self.target_std_ = float(target_log.std())
        return self

    @property
    def category_sizes(self) -> list[int]:
        """Rows of each embedding table: training categories plus unknown."""

        self._validate_fitted()
        return [len(self.category_maps_[column]) + 1 for column in CATEGORICAL_FEATURES]

    def transform_features(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        self._validate_fitted()

        prepared = self._prepare_numerical(X)
        numerical = prepared[NUMERICAL_FEATURES].to_numpy(dtype="float64")
        prepared[NUMERICAL_FEATURES] = (
            numerical - np.asarray(self.scaler_mean_)
        ) / np.asarray(self.scaler_scale_)

        continuous = prepared[CONTINUOUS_FEATURES].to_numpy(dtype="float32")
        categorical = np.column_stack(
            [
                X[column]
                .map(self.category_maps_[column])
                .fillna(UNKNOWN_INDEX)
                .astype("int64")
                for column in CATEGORICAL_FEATURES
            ]
        )
        return continuous, categorical

    def transform_target(self, y: pd.Series | np.ndarray) -> np.ndarray:
        self._validate_fitted()
        target_log = np.log1p(np.asarray(y, dtype="float64"))
        return ((target_log - self.target_mean_) / self.target_std_).astype("float32")

    def inverse_transform_target(self, y_scaled: np.ndarray) -> np.ndarray:
        self._validate_fitted()
        target_log = np.asarray(y_scaled, dtype="float64") * self.target_std_ + self.target_mean_
        return np.expm1(target_log)

    def state_dict(self) -> dict[str, Any]:
        self._validate_fitted()
        return copy.deepcopy(self.__dict__)

    @classmethod
    def from_state_dict(cls, state: Mapping[str, Any]) -> "RentalPreprocessor":
        return cls(**copy.deepcopy(dict(state)))

    def _prepare_numerical(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()

        # The indicator must be created before the coordinates are filled.
        X[GEO_MISSING_FEATURE] = X[COORDINATE_FEATURES].isna().any(axis=1).astype(int)

        for column in COORDINATE_FEATURES:
            X[column] = X[column].fillna(X["region"].map(self.region_medians_[column]))

        # The notebook data has no other missing numerical values. The training
        # medians keep inference usable if a backend request omits one.
        for column in NUMERICAL_FEATURES:
            X[column] = X[column].astype("float64").fillna(self.numerical_medians_[column])

        for column, (lower, upper) in self.clip_bounds_.items():
            X[column] = X[column].clip(lower=lower, upper=upper)

        X["sqfeet"] = np.log1p(X["sqfeet"])
        return X

    def _validate_fitted(self) -> None:
        if self.target_mean_ is None or self.category_maps_ is None:
            raise RuntimeError("The rental preprocessor has not been fitted.")


def embedding_size(n_categories: int) -> int:
    """Rule of thumb used in the notebook for the length of an embedding."""

    return min(50, round(1.6 * n_categories**0.56))


class PeriodicFeatures(nn.Module):
    """Learnable sine and cosine features for selected continuous columns."""

    def __init__(self, columns: Sequence[int], n_frequencies: int, sigma: float) -> None:
        super().__init__()
        self.columns = list(columns)
        self.frequencies = nn.Parameter(
            torch.randn(len(self.columns), n_frequencies) * sigma
        )

    def forward(self, continuous: torch.Tensor) -> torch.Tensor:
        x = continuous[:, self.columns].unsqueeze(-1)
        angles = 2 * torch.pi * self.frequencies * x
        return torch.cat([torch.sin(angles), torch.cos(angles)], dim=-1).flatten(1)


class RentalPriceNet(nn.Module):
    """Feed-forward network with embeddings and periodic coordinate features."""

    def __init__(
        self,
        category_sizes: Sequence[int],
        *,
        hidden_sizes: Sequence[int] = MODEL_PARAMETERS["hidden_sizes"],
        dropout: float = MODEL_PARAMETERS["dropout"],
        n_frequencies: int = MODEL_PARAMETERS["n_frequencies"],
        sigma: float = MODEL_PARAMETERS["sigma"],
    ) -> None:
        super().__init__()

        periodic_columns = [
            CONTINUOUS_FEATURES.index(column) for column in COORDINATE_FEATURES
        ]
        n_periodic = 2 * len(periodic_columns) * n_frequencies

        self.embeddings = nn.ModuleList(
            [nn.Embedding(n, embedding_size(n)) for n in category_sizes]
        )
        n_inputs = (
            sum(embedding.embedding_dim for embedding in self.embeddings)
            + len(CONTINUOUS_FEATURES)
            + n_periodic
        )

        layers: list[nn.Module] = []
        for n_hidden in hidden_sizes:
            layers += [
                nn.Linear(n_inputs, n_hidden),
                nn.BatchNorm1d(n_hidden),
                nn.ReLU(),
                nn.Dropout(dropout),
            ]
            n_inputs = n_hidden
        layers.append(nn.Linear(n_inputs, 1))
        self.layers = nn.Sequential(*layers)

        # Created last so that the weights are initialised in the notebook order.
        self.periodic = PeriodicFeatures(periodic_columns, n_frequencies, sigma)

    def forward(self, continuous: torch.Tensor, categorical: torch.Tensor) -> torch.Tensor:
        embedded = [
            embedding(categorical[:, index])
            for index, embedding in enumerate(self.embeddings)
        ]
        inputs = torch.cat([*embedded, continuous, self.periodic(continuous)], dim=1)
        return self.layers(inputs)


def build_network(category_sizes: Sequence[int]) -> RentalPriceNet:
    """Create the selected Tuned_5 network configuration."""

    return RentalPriceNet(category_sizes, **MODEL_PARAMETERS)


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
    for column in [*NUMERICAL_FEATURES, *BINARY_FEATURES]:
        frame[column] = pd.to_numeric(frame[column])
    return frame


def _iterate_batches(n_rows: int, batch_size: int, shuffle: bool, device: torch.device):
    if shuffle:
        indices = torch.randperm(n_rows, device=device)
    else:
        indices = torch.arange(n_rows, device=device)

    for start in range(0, n_rows, batch_size):
        yield indices[start : start + batch_size]


class NeuralNetworkRentalPriceModel:
    """Fitted preprocessing and neural network used by the backend."""

    def __init__(
        self,
        *,
        preprocessor: RentalPreprocessor | None = None,
        network: RentalPriceNet | None = None,
        device: str | torch.device | None = None,
    ) -> None:
        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.preprocessor = preprocessor or RentalPreprocessor()
        self.network = network
        self.history_: list[dict[str, float]] = []
        self.is_fitted = False

    def fit(
        self, X: pd.DataFrame, y: pd.Series, *, verbose: bool = True
    ) -> "NeuralNetworkRentalPriceModel":
        """Fit all components using training data only.

        Part of the supplied data is held out as a validation set for early
        stopping, as in the notebook. The preprocessing is fitted on the
        remaining rows. The network is trained on the standardised
        ``log1p(price)``; prediction returns dollar-scale rental prices.
        """

        validate_input_columns(X)
        features = X.loc[:, REQUIRED_FEATURES].reset_index(drop=True)
        target = pd.Series(y).reset_index(drop=True)

        if len(features) != len(target):
            raise ValueError("Training features and target must have equal lengths.")
        if target.isna().any():
            raise ValueError("Training target contains missing values.")
        if (target < 0).any():
            raise ValueError("Training target must be non-negative for log1p.")

        X_train, X_valid, y_train, y_valid = train_test_split(
            features,
            target,
            test_size=TRAINING_PARAMETERS["validation_size"],
            random_state=TRAINING_PARAMETERS["random_state"],
        )

        self.preprocessor = RentalPreprocessor().fit(X_train, y_train)
        train_data = self._to_tensors(X_train, y_train)
        valid_data = self._to_tensors(X_valid, y_valid)

        torch.manual_seed(TRAINING_PARAMETERS["random_state"])
        self.network = build_network(self.preprocessor.category_sizes).to(self.device)
        self._train(train_data, valid_data, verbose)

        self.is_fitted = True
        return self

    def predict(
        self,
        input_data: pd.DataFrame
        | pd.Series
        | Mapping[str, Any]
        | Sequence[Mapping[str, Any]],
        *,
        batch_size: int = 4096,
    ) -> np.ndarray:
        """Predict rental prices on the original dollar scale without a target."""

        self._validate_fitted()
        features = _to_dataframe(input_data)
        continuous, categorical = self._to_tensors(features)

        self.network.eval()
        outputs = []
        with torch.no_grad():
            for batch in _iterate_batches(len(features), batch_size, False, self.device):
                outputs.append(self.network(continuous[batch], categorical[batch]))

        scaled = torch.cat(outputs).squeeze(1).cpu().numpy()
        return self.preprocessor.inverse_transform_target(scaled)

    def predict_one(self, input_data: Mapping[str, Any] | pd.Series) -> float:
        """Return one backend-friendly rental-price prediction."""

        predictions = self.predict(input_data)
        if len(predictions) != 1:
            raise ValueError("predict_one expects exactly one input record.")
        return float(predictions[0])

    def save(self, artifact_path: str | Path = DEFAULT_ARTIFACT_PATH) -> Path:
        """Save the network weights, fitted preprocessing, and metadata."""

        self._validate_fitted()
        destination = Path(artifact_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "artifact_version": 1,
                "model_type": "RentalPriceNet",
                "model_parameters": {
                    **MODEL_PARAMETERS,
                    "hidden_sizes": list(MODEL_PARAMETERS["hidden_sizes"]),
                },
                "training_parameters": TRAINING_PARAMETERS.copy(),
                "required_features": REQUIRED_FEATURES.copy(),
                "target_transformation": "standardised log1p/expm1",
                "category_sizes": self.preprocessor.category_sizes,
                "preprocessor": self.preprocessor.state_dict(),
                "network_state": {
                    name: tensor.cpu()
                    for name, tensor in self.network.state_dict().items()
                },
            },
            destination,
        )
        return destination

    @classmethod
    def load(
        cls,
        artifact_path: str | Path = DEFAULT_ARTIFACT_PATH,
        *,
        device: str | torch.device | None = None,
    ) -> "NeuralNetworkRentalPriceModel":
        """Load a saved artifact without retraining."""

        source = Path(artifact_path)
        if not source.exists():
            raise FileNotFoundError(
                f"Neural network artifact not found: {source}. "
                "Run the training script first."
            )

        artifact = torch.load(source, map_location="cpu", weights_only=True)
        if artifact.get("artifact_version") != 1:
            raise ValueError("Unsupported neural network artifact version.")
        if artifact.get("required_features") != REQUIRED_FEATURES:
            raise ValueError("Artifact feature schema does not match this code version.")

        instance = cls(
            preprocessor=RentalPreprocessor.from_state_dict(artifact["preprocessor"]),
            device=device,
        )
        instance.network = RentalPriceNet(
            artifact["category_sizes"], **artifact["model_parameters"]
        )
        instance.network.load_state_dict(artifact["network_state"])
        instance.network.to(instance.device).eval()
        instance.is_fitted = True
        return instance

    def _to_tensors(
        self, X: pd.DataFrame, y: pd.Series | None = None
    ) -> tuple[torch.Tensor, ...]:
        continuous, categorical = self.preprocessor.transform_features(X)
        tensors = [
            torch.from_numpy(continuous).to(self.device),
            torch.from_numpy(categorical).to(self.device),
        ]
        if y is not None:
            target = self.preprocessor.transform_target(y)
            tensors.append(torch.from_numpy(target).unsqueeze(1).to(self.device))
        return tuple(tensors)

    def _evaluate_loss(
        self, data: tuple[torch.Tensor, ...], loss_function: nn.Module, batch_size: int = 4096
    ) -> float:
        continuous, categorical, target = data

        self.network.eval()
        total_loss = 0.0
        with torch.no_grad():
            for batch in _iterate_batches(len(target), batch_size, False, self.device):
                prediction = self.network(continuous[batch], categorical[batch])
                total_loss += loss_function(prediction, target[batch]).item() * len(batch)
        return total_loss / len(target)

    def _train(
        self,
        train_data: tuple[torch.Tensor, ...],
        valid_data: tuple[torch.Tensor, ...],
        verbose: bool,
    ) -> None:
        """Mini-batch training with a learning rate schedule and early stopping."""

        parameters = TRAINING_PARAMETERS
        loss_function = nn.HuberLoss(delta=parameters["huber_delta"])
        optimizer = torch.optim.AdamW(
            self.network.parameters(),
            lr=parameters["learning_rate"],
            weight_decay=parameters["weight_decay"],
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=3
        )

        continuous, categorical, target = train_data
        best_valid_loss = float("inf")
        best_weights = None
        epochs_without_improvement = 0
        self.history_ = []

        for epoch in range(1, parameters["max_epochs"] + 1):
            self.network.train()
            total_loss = 0.0

            for batch in _iterate_batches(
                len(target), parameters["batch_size"], True, self.device
            ):
                optimizer.zero_grad()
                prediction = self.network(continuous[batch], categorical[batch])
                loss = loss_function(prediction, target[batch])
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * len(batch)

            train_loss = total_loss / len(target)
            valid_loss = self._evaluate_loss(valid_data, loss_function)
            scheduler.step(valid_loss)

            self.history_.append(
                {"epoch": epoch, "train_loss": train_loss, "valid_loss": valid_loss}
            )
            if verbose and (epoch == 1 or epoch % 5 == 0):
                print(
                    f"Epoch {epoch:3d} | train loss {train_loss:.4f} | "
                    f"valid loss {valid_loss:.4f}"
                )

            if valid_loss < best_valid_loss:
                best_valid_loss = valid_loss
                best_weights = copy.deepcopy(self.network.state_dict())
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1
                if epochs_without_improvement >= parameters["patience"]:
                    break

        # Restore the weights of the best epoch.
        self.network.load_state_dict(best_weights)
        if verbose:
            print(
                f"Stopped after {len(self.history_)} epochs. "
                f"Best validation loss: {best_valid_loss:.4f}"
            )

    def _validate_fitted(self) -> None:
        if not self.is_fitted or self.network is None:
            raise RuntimeError("The neural network rental-price model is not fitted.")


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

    predictor = NeuralNetworkRentalPriceModel.load(artifact_path)
    if isinstance(input_data, (Mapping, pd.Series)):
        return predictor.predict_one(input_data)
    return predictor.predict(input_data)
