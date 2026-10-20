# Component 2 – Wind-Adaptive Spraying: Drift Prediction and Correction

Predicts how far spray drifts (metres) from weather and drone settings that are known **before** spraying,
and recommends how to correct for the wind (nozzle tilt, left/right path offset, droplet and height advice).

- **Drift model:** tuned XGBoost regressor trained on 5,000 AgDRIFT simulation runs driven by real hourly
  weather (2023–2025) from four Sri Lankan tea regions (Dataset A).
- **Validation:** checked against 564 real spraying flights from Suleco (Dataset B) and published UAV drift studies.
- **Recommendation:** ML drift prediction + simple physics for the sideways spray shift.

## Results

### Drift model (test set, 1,000 unseen runs)
| Model | R² | MAE |
|---|---|---|
| Linear regression (baseline) | 0.84 | 3.8 m |
| **Tuned XGBoost (final)** | **0.99** | **0.8 m** |

Most important inputs: droplet class > crosswind > flight height.

### Real flights – Suleco (Dataset B)
| Check | Result |
|---|---|
| Flights after cleaning | 564 (May–Aug 2026; Ampara, Badulla, Polonnaruwa) |
| Fully inside training ranges | 503 (89.2 %) – swath was the main out-of-range input |
| Typical predicted drift | VF-F ~35 m · F-M ~17 m · C-VC ~11 m |
| Worst-case drift > 30 m | VF-F 78.5 % · F-M 22.9 % · C-VC 0 % of flights |
| Literature check | Trends match field studies; absolute distances higher (conservative) |

## Folder structure

| Folder / file | Contents |
|---|---|
| `data/` | AgDRIFT dataset (`agdrift_dataset_v3_final.csv`) |
| `data_scripts/` | Scripts used to build the data (e.g. `get_suleco_weather.py` – Open-Meteo weather download) |
| `eda/` | Exploratory data analysis notebook and figures |
| `drift_model/model_experiments.ipynb` | Model comparison, tuning and evaluation |
| `drift_model/features.py` | Input preparation (shared by training and prediction) |
| `drift_model/train.py` | Retrains the final model |
| `drift_model/predict.py` | `predict_drift()` – predicted drift distance (m) |
| `drift_model/recommend.py` | `recommend()` – nozzle tilt, left/right path offset, droplet/height advice, strong-wind flag |
| `drift_model/demo_recommend.py` | Runs 11 test scenarios through `recommend()` |
| `drift_model/saved/drift_xgb.json` | Trained model |
| `validation/suleco_validation.ipynb` | Dataset B: check against real Suleco flights (coverage, predicted drift, literature check) |
| `validation/data/` | Raw Suleco flight records + weather – **not in Git** (company data) |
| `evaluation/recommendation_scenarios.csv` | Output of the scenario table |
| `app/app.py` | Standalone Streamlit demo page |
| `tests/` | Automatic tests (`test_predict.py`, `test_recommend.py`) |

## How to run (from the repo root, venv active)
```bash
pip install pandas numpy scikit-learn xgboost lightgbm pytest streamlit plotly requests

python -m component2_wind_spraying.drift_model.train            # retrain the model
python -m component2_wind_spraying.drift_model.predict          # example prediction
python -m pytest component2_wind_spraying/tests -v              # run all tests
python -m component2_wind_spraying.drift_model.demo_recommend   # scenario table
streamlit run component2_wind_spraying/app/app.py               # demo page (http://localhost:8501)
```

## Interface for other components

### 1. `predict_drift()` – drift distance
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

### 2. `recommend()` – wind correction
```python
from component2_wind_spraying.drift_model.recommend import recommend

r = recommend(wind_ms=3.0, wind_dir_deg=90, heading_deg=0, temp_c=30, rh_pct=60,
              height_m=2.5, swath_m=5.5, droplet_class="F-M", max_drift_m=20)
```

| Input | Unit | Notes |
|---|---|---|
| `wind_ms` | m/s | Wind speed at 2 m height (10 m wind × 0.776) |
| `wind_dir_deg` | deg | Direction the wind comes **from** (0 = N, 90 = E) |
| `heading_deg` | deg | Direction the drone flies **to** (0 = N, 90 = E) |
| `temp_c`, `rh_pct`, `height_m`, `swath_m`, `droplet_class` | | As for `predict_drift()` |
| `max_drift_m` | m | Acceptable drift distance (default 20 m – to be agreed) |

| Output key | Meaning |
|---|---|
| `mode` | `CORRECT`, `NO_CORRECTION` (crosswind < 0.5 m/s) or `STRONG_WIND` (wind > 4.5 m/s, no correction given) |
| `drift_m`, `drift_risk` | Predicted drift (m) and `OK` / `HIGH` vs `max_drift_m` |
| `spray_shift_m` | How far the spray lands off target without correction (m) |
| `nozzle_tilt_deg`, `nozzle_tilt_side` | Nozzle tilt into the wind (max 30°), `left` / `right` |
| `path_offset_m`, `path_offset_side` | Flight-path shift into the wind (max half the swath), `left` / `right` |
| `droplet_advice`, `height_advice` | Coarser droplet class / lower height if needed |
| `needs_external_decision` | `True` in strong wind or when no setting keeps drift under the limit |
| `reason` | Plain-language explanation |

**Method:** spray shift = crosswind × height / (droplet fall speed + rotor downwash). The nozzle is tilted first;
any remaining shift is corrected by moving the path. Left/right is relative to the flight direction.

## Limitations
- Drift model trained on simulation data (AgDRIFT, manned-helicopter proxy) – absolute distances are likely
  over-estimated for small drones; trends agree with published UAV field studies.
- Few training examples above 3 m/s crosswind (8 %) – predictions in strong wind are less reliable.
- Suleco records contain no drift measurements, flight heading or droplet setting, and the flights were not on tea –
  Dataset B is an applicability/plausibility check, not an accuracy test.
- Correction parameters (strong-wind limit 4.5 m/s, max nozzle tilt 30°, downwash 2.0 m/s, droplet fall speeds)
  are assumptions, to be agreed with the team and calibrated in a field trial (e.g. water-sensitive paper downwind).
- Nozzle-tilt compensation has not been tested in published studies.
