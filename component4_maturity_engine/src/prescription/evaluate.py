"""
Component 4 - Objective 4: compare the adaptive engine with fixed-rate spraying.

For every test image we know the TRUE maturity (label) and the PREDICTED
maturity + confidence (from Function 1). The "correct" spray level is the one
the true maturity maps to. We then count, for each strategy:
    correct      - applied level == correct level
    over-spray   - applied level higher than needed
    under-spray  - applied level lower than needed
plus relative chemical use (1.0 = fixed rate everywhere).

Input CSV columns: image, true_label, predicted, confidence
(produced by: python -m src.classifier.predict --split ... --out test_predictions.csv)

Usage:
    python -m src.prescription.evaluate --predictions runs/effnet_b0/test_predictions.csv \
        --out runs/effnet_b0/baseline_comparison
"""

import argparse
import csv
import json
from pathlib import Path

from src.prescription.engine import LEVELS, SprayConfig, build_prescription, save_prescription


def _score(applied: list, needed: list, cfg: SprayConfig) -> dict:
    rank = {lvl: i for i, lvl in enumerate(LEVELS)}
    n = len(needed)
    over = sum(rank[a] > rank[t] for a, t in zip(applied, needed))
    under = sum(rank[a] < rank[t] for a, t in zip(applied, needed))
    correct = n - over - under
    base = cfg.rate_multiplier[cfg.baseline_fixed_level]
    return {
        "regions": n,
        "correct": correct, "correct_pct": round(100 * correct / n, 1),
        "over_spray": over, "over_spray_pct": round(100 * over / n, 1),
        "under_spray": under, "under_spray_pct": round(100 * under / n, 1),
        "relative_chemical_use": round(sum(cfg.rate_multiplier[a] for a in applied) / (n * base), 4),
    }


def compare(rows: list, cfg: SprayConfig) -> dict:
    if not rows:
        raise ValueError("No predictions to evaluate")
    needed = [cfg.mapping[r["true_label"]] for r in rows]
    preds = [{"region_id": i, "image": r["image"], "maturity": r["predicted"],
              "confidence": float(r["confidence"])} for i, r in enumerate(rows)]
    prescription = build_prescription(preds, cfg, flight_id="test_set")
    adaptive = [r["spray_level"] for r in prescription["regions"]]
    fixed = [cfg.baseline_fixed_level] * len(rows)
    oracle_rate = _score(needed, needed, cfg)["relative_chemical_use"]
    return {
        "fixed_rate_baseline": _score(fixed, needed, cfg),
        "adaptive_engine": _score(adaptive, needed, cfg),
        "ideal_if_labels_perfect": {"relative_chemical_use": oracle_rate},
        "flagged_for_review": prescription["summary"]["needs_review"],
        "confidence_threshold": cfg.confidence_threshold,
    }, prescription


def load_predictions(path: Path) -> list:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_chart(result: dict, out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = ["Fixed-rate", "Adaptive (C4)"]
    keys = ["fixed_rate_baseline", "adaptive_engine"]
    parts = [("correct_pct", "Correct", "#3a7d44"), ("over_spray_pct", "Over-spray", "#d1495b"),
             ("under_spray_pct", "Under-spray", "#edae49")]
    fig, ax = plt.subplots(figsize=(6, 3))
    left = [0, 0]
    for k, label, color in parts:
        vals = [result[s][k] for s in keys]
        ax.barh(names, vals, left=left, label=label, color=color)
        for i, v in enumerate(vals):
            if v >= 6:
                ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center", color="white")
        left = [a + b for a, b in zip(left, vals)]
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of test regions")
    ax.set_title("Spray decisions vs. needed level (test set)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Adaptive engine vs fixed-rate baseline")
    p.add_argument("--predictions", required=True, type=Path)
    p.add_argument("--config", type=Path, default=None)
    p.add_argument("--out", type=Path, default=Path("runs/baseline_comparison"))
    a = p.parse_args()
    cfg = SprayConfig.from_yaml(a.config) if a.config else SprayConfig.from_yaml()
    result, prescription = compare(load_predictions(a.predictions), cfg)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "comparison.json").write_text(json.dumps(result, indent=2))
    save_prescription(prescription, a.out / "test_prescription.json")
    save_prescription(prescription, a.out / "test_prescription.csv")
    save_chart(result, a.out / "comparison.png")
    for name in ("fixed_rate_baseline", "adaptive_engine"):
        r = result[name]
        print(f"{name:<20} correct {r['correct_pct']:>5}%  over {r['over_spray_pct']:>5}%  "
              f"under {r['under_spray_pct']:>5}%  chemical x{r['relative_chemical_use']}")
    print(f"Flagged for review: {result['flagged_for_review']}   Saved to {a.out}/")
