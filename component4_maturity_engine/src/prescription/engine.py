"""
Component 4 - Function 2: maturity-to-spray prescription engine.

Input : maturity predictions from Function 1 (one per image / region)
Output: a spray prescription per region + a summary for the whole flight

Decision logic
  1. Map maturity -> spray level using configs/spray_mapping.yaml
  2. If confidence < threshold, do not trust the prediction: use the safe
     fallback level and flag the region for review
  3. Attach the relative application rate for the chosen level
  4. Carry through location fields (lat/lon) when Component 3 provides them

The rules live in the YAML config, so they can be changed after validation
with TRI without changing code.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

LEVELS = ["low", "normal", "high"]          # ordered: lowest -> highest dose
DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "spray_mapping.yaml"


@dataclass
class SprayConfig:
    mapping: dict = field(default_factory=lambda: {"young": "low", "medium": "normal",
                                                   "mature": "high"})
    rate_multiplier: dict = field(default_factory=lambda: {"low": 0.7, "normal": 1.0,
                                                           "high": 1.3})
    confidence_threshold: float = 0.60
    low_confidence_level: str = "normal"
    baseline_fixed_level: str = "normal"

    def __post_init__(self):
        for m, lvl in self.mapping.items():
            if lvl not in LEVELS:
                raise ValueError(f"mapping[{m}] = '{lvl}' is not one of {LEVELS}")
        for lvl in (self.low_confidence_level, self.baseline_fixed_level):
            if lvl not in LEVELS:
                raise ValueError(f"'{lvl}' is not one of {LEVELS}")
        missing = set(LEVELS) - set(self.rate_multiplier)
        if missing:
            raise ValueError(f"rate_multiplier is missing levels: {missing}")
        if not 0 <= self.confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be between 0 and 1")

    @classmethod
    def from_yaml(cls, path=DEFAULT_CONFIG) -> "SprayConfig":
        with open(path, encoding="utf-8") as f:
            return cls(**yaml.safe_load(f))


def decide(maturity: str, confidence: float, cfg: SprayConfig) -> dict:
    """Spray decision for one region."""
    if maturity not in cfg.mapping:
        level, reason = cfg.low_confidence_level, f"unknown maturity '{maturity}'"
        review = True
    elif confidence < cfg.confidence_threshold:
        level = cfg.low_confidence_level
        reason = f"low confidence ({confidence:.2f} < {cfg.confidence_threshold:.2f})"
        review = True
    else:
        level, reason, review = cfg.mapping[maturity], f"{maturity} -> {cfg.mapping[maturity]}", False
    return {"spray_level": level, "rate_multiplier": cfg.rate_multiplier[level],
            "needs_review": review, "reason": reason}


def build_prescription(predictions: list, cfg: SprayConfig, flight_id: str = "") -> dict:
    """predictions: [{"region_id", "maturity", "confidence", optional "lat", "lon", "image"}]"""
    regions = []
    for p in predictions:
        rec = {"region_id": p["region_id"], "image": p.get("image", ""),
               "lat": p.get("lat"), "lon": p.get("lon"),   # filled by Component 3
               "maturity": p["maturity"], "confidence": round(float(p["confidence"]), 4)}
        rec.update(decide(p["maturity"], float(p["confidence"]), cfg))
        regions.append(rec)

    n = len(regions)
    by_level = {lvl: sum(r["spray_level"] == lvl for r in regions) for lvl in LEVELS}
    total_rate = sum(r["rate_multiplier"] for r in regions)
    baseline_rate = n * cfg.rate_multiplier[cfg.baseline_fixed_level]
    return {
        "flight_id": flight_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": {"mapping": cfg.mapping, "confidence_threshold": cfg.confidence_threshold,
                   "rate_multiplier": cfg.rate_multiplier},
        "summary": {
            "regions": n,
            "by_level": by_level,
            "needs_review": sum(r["needs_review"] for r in regions),
            "relative_chemical_use": round(total_rate / baseline_rate, 4) if n else None,
        },
        "regions": regions,
    }


def save_prescription(prescription: dict, out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix == ".csv":
        import csv
        cols = ["region_id", "image", "lat", "lon", "maturity", "confidence",
                "spray_level", "rate_multiplier", "needs_review", "reason"]
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(prescription["regions"])
    else:
        out_path.write_text(json.dumps(prescription, indent=2), encoding="utf-8")
