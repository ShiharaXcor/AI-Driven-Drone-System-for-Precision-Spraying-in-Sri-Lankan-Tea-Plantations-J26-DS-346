"""Input preparation shared by train.py and predict.py."""
import pandas as pd

FEATURES = ["crosswind_ms", "height_m", "swath_m", "temp_c", "rh_pct", "droplet_code"]
TARGET = "drift_distance_m"
DROPLET_CODE = {"VF-F": 0, "F-M": 1, "M-C": 2, "C-VC": 3}

# ranges covered by the training data (predictions outside them are less reliable)
VALID_RANGES = {
    "crosswind_ms": (0.5, 6.7),
    "height_m": (2.0, 3.5),
    "swath_m": (4.8, 6.4),
    "temp_c": (7.7, 35.9),
    "rh_pct": (19.0, 100.0),
}


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Turn a table with droplet_class (text) into the 6 numeric model inputs."""
    out = df.copy()
    out["droplet_code"] = out["droplet_class"].map(DROPLET_CODE)
    if out["droplet_code"].isna().any():
        raise ValueError(f"droplet_class must be one of {list(DROPLET_CODE)}")
    return out[FEATURES]