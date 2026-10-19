"""Train the final drift model (tuned XGBoost) and save it to saved/drift_xgb.json.

Run from the repo root:
    python -m component2_wind_spraying.drift_model.train
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from .features import TARGET, prepare_features

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data" / "agdrift_dataset_v3_final.csv"
MODEL_PATH = HERE / "saved" / "drift_xgb.json"
SEED = 42

# best settings from the tuning step (model_experiments.ipynb, M3c)
BEST_PARAMS = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 6,
    "subsample": 0.7,
    "colsample_bytree": 1.0,
    "min_child_weight": 3,
}


def train():
    df = pd.read_csv(DATA)
    X, y = prepare_features(df), df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)

    model = XGBRegressor(**BEST_PARAMS, random_state=SEED, n_jobs=-1)
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    print(f"Test R² = {r2_score(y_test, pred):.3f} | MAE = {mean_absolute_error(y_test, pred):.2f} m")

    MODEL_PATH.parent.mkdir(exist_ok=True)
    model.save_model(str(MODEL_PATH))
    print("Saved:", MODEL_PATH)


if __name__ == "__main__":
    train()