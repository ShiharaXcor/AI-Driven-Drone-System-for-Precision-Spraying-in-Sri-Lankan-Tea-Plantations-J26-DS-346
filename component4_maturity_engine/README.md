# Component 4 – Maturity-Driven Variable-Rate Actuation Engine

Part of: AI-Driven Adaptive UAV System for Precision Tea Spraying (J26-DS-346)
Owner: Gunawardhana G.A.V (IT23186156)

## Purpose
Classifies tea maturity (Young / Medium / Mature) from UAV RGB imagery and
converts it into a variable-rate spray prescription (Low / Normal / High).

## Pipeline
UAV RGB image → Preprocess (quality check, resize, tiling)
→ Maturity classification (EfficientNet-B0 / MobileNetV3)
→ Maturity-to-spray decision engine → Spray prescription (JSON + grid)

## Key functions (PP1)
- F1: Tea maturity classification pipeline
- F2: Maturity-to-spray prescription engine

## Structure
- `src/preprocess/`   – image quality check, resizing, tiling
- `src/classifier/`   – training, evaluation, prediction
- `src/prescription/` – spray decision rules and prescription output
- `configs/`          – configurable maturity-to-spray mapping
- `notebooks/`        – training/experiment notebooks (Colab)
- `app/`              – Streamlit demo
- `tests/`            – unit and failure-path tests

## Setup
pip install -r requirements.txt

## Data
Raw images and trained models are not stored in Git. See `data/README.md`.

## Status
- [x] Component structure
- [ ] Preprocessing and tiling
- [ ] Dataset labelling
- [ ] Baseline classifier
- [ ] Prescription engine
- [ ] Demo app