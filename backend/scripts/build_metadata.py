"""Create the reference data used by the API and the input form.

The file lists the values a user can choose from and the typical coordinates
of every region. It is stored in git, so the backend runs without the data.

Run from the repository root after 02_Preprocessing.ipynb:

    python -m backend.scripts.build_metadata
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_PATH = PROJECT_ROOT / "data" / "raw_train.csv"
METADATA_PATH = PROJECT_ROOT / "backend" / "app" / "metadata.json"

OPTION_FEATURES = ["type", "laundry_options", "parking_options"]
COORDINATE_FEATURES = ["lat", "long"]

# Percentiles of the training data that the models clip square footage to.
SQFEET_QUANTILES = (0.005, 0.995)

STATE_NAMES = {
    "ak": "Alaska", "al": "Alabama", "ar": "Arkansas", "az": "Arizona",
    "ca": "California", "co": "Colorado", "ct": "Connecticut",
    "dc": "District of Columbia", "de": "Delaware", "fl": "Florida",
    "ga": "Georgia", "hi": "Hawaii", "ia": "Iowa", "id": "Idaho",
    "il": "Illinois", "in": "Indiana", "ks": "Kansas", "ky": "Kentucky",
    "la": "Louisiana", "ma": "Massachusetts", "md": "Maryland", "me": "Maine",
    "mi": "Michigan", "mn": "Minnesota", "mo": "Missouri", "ms": "Mississippi",
    "mt": "Montana", "nc": "North Carolina", "nd": "North Dakota",
    "ne": "Nebraska", "nh": "New Hampshire", "nj": "New Jersey",
    "nm": "New Mexico", "nv": "Nevada", "ny": "New York", "oh": "Ohio",
    "ok": "Oklahoma", "or": "Oregon", "pa": "Pennsylvania",
    "ri": "Rhode Island", "sc": "South Carolina", "sd": "South Dakota",
    "tn": "Tennessee", "tx": "Texas", "ut": "Utah", "va": "Virginia",
    "vt": "Vermont", "wa": "Washington", "wi": "Wisconsin",
    "wv": "West Virginia", "wy": "Wyoming",
}


def build_states(data: pd.DataFrame) -> list[dict]:
    """States with their regions and the median coordinates of each region.

    The coordinates are calculated for every state and region pair, because
    one region name can be two different places, such as Albany in Georgia
    and Albany in New York.
    """

    pair_medians = data.groupby(["state", "region"])[COORDINATE_FEATURES].median()
    # Used when no listing of a pair has coordinates.
    region_medians = data.groupby("region")[COORDINATE_FEATURES].median()

    states = []
    for code in sorted(data["state"].unique(), key=STATE_NAMES.__getitem__):
        regions = []
        for region, medians in pair_medians.loc[code].iterrows():
            medians = medians.fillna(region_medians.loc[region])
            regions.append({
                "name": region,
                "lat": round(float(medians["lat"]), 4),
                "long": round(float(medians["long"]), 4),
            })
        states.append({"code": code, "name": STATE_NAMES[code], "regions": regions})
    return states


def build_metadata(data: pd.DataFrame) -> dict:
    lower, upper = (float(data["sqfeet"].quantile(q)) for q in SQFEET_QUANTILES)

    return {
        "states": build_states(data),
        # Most common value first.
        **{
            column: data[column].value_counts().index.tolist()
            for column in OPTION_FEATURES
        },
        "numeric": {
            "sqfeet": {
                "min": lower,
                "max": upper,
                "default": float(data["sqfeet"].median()),
            },
            "beds": {
                "min": int(data["beds"].min()),
                "max": int(data["beds"].max()),
                "default": int(data["beds"].median()),
            },
            "baths": {
                "min": float(data["baths"].min()),
                "max": float(data["baths"].max()),
                "default": float(data["baths"].median()),
            },
        },
    }


def main() -> None:
    if not TRAIN_PATH.exists():
        raise FileNotFoundError(
            f"Missing data file: {TRAIN_PATH.relative_to(PROJECT_ROOT)}. "
            "Run notebooks/02_Preprocessing.ipynb first."
        )

    metadata = build_metadata(pd.read_csv(TRAIN_PATH))
    METADATA_PATH.write_text(json.dumps(metadata, indent=1) + "\n", encoding="utf-8")

    n_regions = sum(len(state["regions"]) for state in metadata["states"])
    print(f"States: {len(metadata['states'])}, state and region pairs: {n_regions}")
    print(f"Metadata saved: {METADATA_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
