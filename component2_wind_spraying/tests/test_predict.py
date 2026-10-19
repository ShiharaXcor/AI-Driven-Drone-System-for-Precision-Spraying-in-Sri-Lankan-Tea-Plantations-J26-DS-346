"""Automatic checks for predict_drift(). Run from the repo root:
    python -m pytest component2_wind_spraying/tests -v
"""
import pytest

from component2_wind_spraying.drift_model.predict import predict_drift

# typical conditions used in the tests
BASE = dict(crosswind_ms=2.0, height_m=2.75, swath_m=5.6, temp_c=25, rh_pct=70)


def test_returns_a_positive_number():
    drift = predict_drift(**BASE, droplet_class="F-M")
    assert isinstance(drift, float) and drift > 0


def test_finer_droplets_drift_further():
    drifts = [predict_drift(**BASE, droplet_class=c) for c in ["VF-F", "F-M", "M-C", "C-VC"]]
    assert drifts == sorted(drifts, reverse=True)


def test_more_wind_gives_more_drift():
    low = predict_drift(**{**BASE, "crosswind_ms": 1.0}, droplet_class="F-M")
    high = predict_drift(**{**BASE, "crosswind_ms": 3.0}, droplet_class="F-M")
    assert high > low


def test_unknown_droplet_class_gives_error():
    with pytest.raises(ValueError):
        predict_drift(**BASE, droplet_class="XYZ")


def test_out_of_range_input_gives_warning():
    with pytest.warns(UserWarning):
        predict_drift(**{**BASE, "crosswind_ms": 9.0}, droplet_class="F-M")