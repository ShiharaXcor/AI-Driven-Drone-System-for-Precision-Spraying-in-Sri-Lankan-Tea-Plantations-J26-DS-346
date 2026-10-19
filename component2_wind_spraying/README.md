# Component 2 – Wind-Adaptive Spraying: Drift Prediction

Predicts how far spray drifts (metres) from weather and drone settings that are known **before** spraying.
The model is a tuned XGBoost regressor trained on 5,000 AgDRIFT simulation runs driven by real hourly
weather (2023–2025) from four Sri Lankan tea regions.

## Results (test set, 1,000 unseen runs)
| Model | R² | MAE |
|---|---|---|
| Linear regression (baseline) | 0.84 | 3.8 m |
| **Tuned XGBoost (final)** | **0.99** | **0.8 m** |

Most important inputs: droplet class > crosswind > flight height.

## Folder structure
| Folder / file | Contents |
|---|---|
| `data/` | AgDRIFT dataset (agdrift_dataset_v3_final.csv) |
| `eda/` | Exploratory data analysis notebook and figures |
| `drift_model/model_experiments.ipynb` | Model comparison, tuning and evaluation |
| `drift_model/features.py` | Input preparation (shared by training and prediction) |
| `drift_model/train.py` | Retrains the final model |
| `drift_model/predict.py` | `predict_drift()` – used by other components |
| `drift_model/saved/drift_xgb.json` | Trained model |
| `tests/` | Automatic tests |

## How to run (from the repo root, venv active)
```bash
pip install pandas numpy scikit-learn xgboost lightgbm pytest
python -m component2_wind_spraying.drift_model.train      # retrain the model
python -m component2_wind_spraying.drift_model.predict    # example prediction
python -m pytest component2_wind_spraying/tests -v        # run tests
```

## Interface for other components
```python
from component2_wind_spraying.drift_model.predict import predict_drift

drift_m = predict_drift(crosswind_ms=2.5, height_m=3.0, swath_m=5.5,
                        temp_c=28, rh_pct=60, droplet_class="F-M")
```

| Input | Unit | Valid (training) range | Notes |
|---|---|---|---|
| `crosswind_ms` | m/s | 0.5 – 6.7 | Wind component perpendicular to the flight line |
| `height_m` | m | 2.0 – 3.5 | Spray release height |
| `swath_m` | m | 4.8 – 6.4 | Spray width |
| `temp_c` | °C | 7.7 – 35.9 | Air temperature |
| `rh_pct` | % | 19 – 100 | Relative humidity |
| `droplet_class` | text | "VF-F", "F-M", "M-C", "C-VC" | Finest → coarsest |

**Output:** predicted drift distance in metres (float).
**Errors:** unknown `droplet_class` → `ValueError`. Inputs outside the training range → `UserWarning` (prediction less reliable).

**Crosswind** = wind speed × |sin(wind direction − flight heading)|, with both angles in degrees using the same convention.

## Limitations
- Trained on simulation data (AgDRIFT); real-field accuracy will be lower and will be checked with Suleco flight data (Dataset B).
- Few training examples above 3 m/s crosswind (8 %) – predictions in strong wind are less reliable.