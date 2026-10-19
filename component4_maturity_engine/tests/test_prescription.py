"""Tests for Function 2: spray decisions, safety fallbacks and baseline comparison."""

import json

import pytest

from src.prescription.engine import (SprayConfig, build_prescription, decide,
                                     save_prescription)
from src.prescription.evaluate import compare


@pytest.fixture
def cfg():
    return SprayConfig.from_yaml()   # the real configs/spray_mapping.yaml


# ------------------------------------------------------------ happy path
@pytest.mark.parametrize("maturity,level", [("young", "low"), ("medium", "normal"),
                                            ("mature", "high")])
def test_confident_predictions_follow_mapping(cfg, maturity, level):
    d = decide(maturity, 0.95, cfg)
    assert d["spray_level"] == level
    assert not d["needs_review"]


def test_prescription_summary(cfg):
    preds = [{"region_id": 1, "maturity": "young", "confidence": 0.9, "lat": 6.9, "lon": 80.7},
             {"region_id": 2, "maturity": "mature", "confidence": 0.9},
             {"region_id": 3, "maturity": "medium", "confidence": 0.3}]
    p = build_prescription(preds, cfg, "F001")
    assert p["summary"]["by_level"] == {"low": 1, "normal": 1, "high": 1}
    assert p["summary"]["needs_review"] == 1
    assert p["regions"][0]["lat"] == 6.9          # location passed through for C3
    assert p["regions"][1]["lat"] is None


# ---------------------------------------------------------- failure paths
def test_low_confidence_falls_back_to_safe_level(cfg):
    d = decide("mature", 0.41, cfg)
    assert d["spray_level"] == cfg.low_confidence_level
    assert d["needs_review"]


def test_threshold_boundary_is_trusted(cfg):
    assert not decide("young", cfg.confidence_threshold, cfg)["needs_review"]


def test_unknown_maturity_does_not_crash(cfg):
    d = decide("unknown_class", 0.99, cfg)
    assert d["spray_level"] == cfg.low_confidence_level
    assert d["needs_review"]


def test_bad_config_is_rejected():
    with pytest.raises(ValueError):
        SprayConfig(mapping={"young": "extreme"})
    with pytest.raises(ValueError):
        SprayConfig(confidence_threshold=1.5)
    with pytest.raises(ValueError):
        SprayConfig(rate_multiplier={"low": 0.5, "normal": 1.0})


def test_empty_flight(cfg):
    p = build_prescription([], cfg)
    assert p["summary"]["regions"] == 0
    with pytest.raises(ValueError):
        compare([], cfg)


# --------------------------------------------------- baseline comparison
def test_comparison_counts_over_and_under_spray(cfg):
    rows = [  # true, predicted, confidence
        {"image": "a", "true_label": "young", "predicted": "young", "confidence": 0.9},
        {"image": "b", "true_label": "mature", "predicted": "mature", "confidence": 0.9},
        {"image": "c", "true_label": "medium", "predicted": "medium", "confidence": 0.9},
        {"image": "d", "true_label": "young", "predicted": "mature", "confidence": 0.9},
    ]
    result, _ = compare(rows, cfg)
    fixed, adaptive = result["fixed_rate_baseline"], result["adaptive_engine"]
    # fixed-rate sprays "normal" everywhere: young over-sprayed, mature under-sprayed
    assert (fixed["correct"], fixed["over_spray"], fixed["under_spray"]) == (1, 2, 1)
    # adaptive gets 3 right, over-sprays the misclassified young one
    assert (adaptive["correct"], adaptive["over_spray"], adaptive["under_spray"]) == (3, 1, 0)
    assert fixed["relative_chemical_use"] == 1.0


def test_save_json_and_csv(cfg, tmp_path):
    p = build_prescription([{"region_id": 1, "maturity": "young", "confidence": 0.8}], cfg)
    save_prescription(p, tmp_path / "p.json")
    save_prescription(p, tmp_path / "p.csv")
    assert json.loads((tmp_path / "p.json").read_text())["regions"][0]["spray_level"] == "low"
    assert "spray_level" in (tmp_path / "p.csv").read_text().splitlines()[0]
