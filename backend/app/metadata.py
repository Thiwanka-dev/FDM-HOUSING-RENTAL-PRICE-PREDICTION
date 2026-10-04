"""Reference data: the values a user can choose from and region coordinates.

``metadata.json`` is created by ``backend.scripts.build_metadata``.
"""

from __future__ import annotations

import json
from pathlib import Path


METADATA_PATH = Path(__file__).resolve().parent / "metadata.json"
OPTION_FEATURES = ["type", "laundry_options", "parking_options"]

METADATA = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

# (state, region) -> coordinates of the region in that state.
REGION_COORDINATES = {
    (state["code"], region["name"]): {"lat": region["lat"], "long": region["long"]}
    for state in METADATA["states"]
    for region in state["regions"]
}
