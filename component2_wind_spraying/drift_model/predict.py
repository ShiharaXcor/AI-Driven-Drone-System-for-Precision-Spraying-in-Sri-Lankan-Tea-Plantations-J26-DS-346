"""Predict spray drift distance. This is the function other components import.

Example:
    from component2_wind_spraying.drift_model.predict import predict_drift
    predict_drift(crosswind_ms=2.5, height_m=3.0, swath_m=5.5, temp_c=28, rh_pct=60, droplet_class="F-M")
"""
import warnings
from functools import lru_cache
from pathlib import Path

import pandas as pd
from xgboost import XGBRegressor

from .features import DROPLET_CODE, VALID_RANGES, prepare_features

MODEL_PATH = Path(__file__).resolve().parent / "saved" / "drift_xgb.json"


@lru_cache(maxsize=1)
def _load_model() -> XGBRegressor:
    """Load the saved model once and reuse it (faster for repeated calls)."""
    model = XGBRegressor()
    model.load_model(str(MODEL_PATH))
    return model


def predict_drift(crosswind_ms, height_m, swath_m, temp_c, rh_pct, droplet_class):
    """Return predicted drift distance in metres.

    Inputs: crosswind_ms (m/s), height_m (m), swath_m (m), temp_c (°C), rh_pct (%),
    droplet_class: one of "VF-F", "F-M", "M-C", "C-VC".
    """
    if droplet_class not in DROPLET_CODE:
        raise ValueError(f"droplet_class must be one of {list(DROPLET_CODE)}")

    values = {"crosswind_ms": crosswind_ms, "height_m": height_m, "swath_m": swath_m,
              "temp_c": temp_c, "rh_pct": rh_pct}
    for name, (low, high) in VALID_RANGES.items():
        if not low <= values[name] <= high:
            warnings.warn(f"{name}={values[name]} is outside the training range {low}-{high}; prediction is less reliable")

    row = pd.DataFrame([{**values, "droplet_class": droplet_class}])
    return float(_load_model().predict(prepare_features(row))[0])


if __name__ == "__main__":
    print(predict_drift(2.5, 3.0, 5.5, 28, 60, "VF-F"), "m")