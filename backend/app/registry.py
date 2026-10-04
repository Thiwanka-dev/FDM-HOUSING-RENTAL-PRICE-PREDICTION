"""Registry of the saved rental-price models served by the API.

The artifact paths and loaders are taken from ``models.setup_models`` so that
the backend and the setup script always describe the same four models.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Callable

from models.setup_models import METRICS_PATH, MODELS


DEFAULT_MODEL_ID = "neural_network"

# API identifier -> model name used in models.setup_models and the notebooks.
MODEL_NAMES = {
    "neural_network": "Neural Network",
    "random_forest": "Random Forest",
    "gradient_boosting": "Gradient Boosting",
    "linear_ridge": "Ridge Regression",
}


@dataclass
class ModelEntry:
    """One saved model, loaded from disk the first time it is used."""

    id: str
    name: str
    artifact_path: Path
    loader: Callable[[], Any]
    metrics: dict[str, float] | None = None
    _model: Any = field(default=None, repr=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def available(self) -> bool:
        """Whether the saved model file exists on this computer."""

        return self.artifact_path.exists()

    @property
    def model(self) -> Any:
        # The lock stops two simultaneous requests from loading the file twice.
        with self._lock:
            if self._model is None:
                self._model = self.loader()
            return self._model


def _load_metrics() -> dict[str, dict[str, float]]:
    if not METRICS_PATH.exists():
        return {}
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def _build_registry() -> dict[str, ModelEntry]:
    metrics = _load_metrics()
    registry = {}
    for model_id, name in MODEL_NAMES.items():
        artifact_path, _, loader = MODELS[name]
        registry[model_id] = ModelEntry(
            id=model_id,
            name=name,
            artifact_path=artifact_path,
            loader=loader,
            metrics=metrics.get(name),
        )
    return registry


REGISTRY = _build_registry()
