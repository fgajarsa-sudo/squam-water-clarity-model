"""
Corrected Step 4/5 prep: retrain the model EXCLUDING every Squam Lake and
Little Squam Lake monitoring site from the training data, so the model
used to predict Squam/Little Squam has genuinely never seen data from
either lake. The original 06_train_model.py trained on all 19,510 rows,
which included 107 rows from 16 Squam-area sites -- meaning the Step 6
validation against real Squam readings was partly circular. This script
fixes that.

Outputs:
  data/processed/rf_model_heldout.joblib
  data/processed/spatial_cv_results_heldout.json
"""
import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

PROJECT_DIR = Path(__file__).resolve().parents[1]
IN_PATH = PROJECT_DIR / "data" / "processed" / "model_training_table.csv"
MODEL_PATH = PROJECT_DIR / "data" / "processed" / "rf_model_heldout.joblib"
CV_RESULTS_PATH = PROJECT_DIR / "data" / "processed" / "spatial_cv_results_heldout.json"

NON_FEATURE_COLS = {
    "site_id", "site_name", "state", "lat", "lon", "date", "secchi_m",
    "row_id", "matched_image_date",
}
N_SPLITS = 10
RANDOM_STATE = 42
SQUAM_PATTERN = re.compile(r"(?i)^squam lake|little squam")


def main():
    df = pd.read_csv(IN_PATH)
    is_squam = df["site_name"].str.contains(SQUAM_PATTERN, na=False)
    print(f"Excluding {is_squam.sum()} rows from {df.loc[is_squam, 'site_id'].nunique()} "
          f"Squam/Little Squam sites from training")
    df = df[~is_squam].reset_index(drop=True)
    print(f"Remaining training rows: {len(df)}, sites: {df['site_id'].nunique()}")

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLS]
    X = df[feature_cols].values
    y = df["secchi_m"].values
    groups = df["site_id"].values

    gkf = GroupKFold(n_splits=N_SPLITS)
    oof_pred = np.full(len(df), np.nan)

    for fold, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups)):
        model = RandomForestRegressor(
            n_estimators=500, max_depth=None, min_samples_leaf=3,
            n_jobs=-1, random_state=RANDOM_STATE,
        )
        model.fit(X[train_idx], y[train_idx])
        oof_pred[test_idx] = model.predict(X[test_idx])
        fold_r2 = r2_score(y[test_idx], oof_pred[test_idx])
        print(f"  fold {fold+1}/{N_SPLITS}: R2={fold_r2:.3f}")

    r2 = r2_score(y, oof_pred)
    mae = mean_absolute_error(y, oof_pred)
    rmse = float(np.sqrt(mean_squared_error(y, oof_pred)))
    corr = float(np.corrcoef(y, oof_pred)[0, 1])
    print(f"\nSpatial CV (Squam-excluded training pool): r={corr:.3f}, R2={r2:.3f}, MAE={mae:.3f}, RMSE={rmse:.3f}")

    CV_RESULTS_PATH.write_text(json.dumps({
        "n_splits": N_SPLITS, "n_rows": len(df), "n_sites": df["site_id"].nunique(),
        "pearson_r": corr, "r2": r2, "mae_m": mae, "rmse_m": rmse,
        "excluded_squam_rows": int(is_squam.sum()),
    }, indent=2))

    final_model = RandomForestRegressor(
        n_estimators=500, max_depth=None, min_samples_leaf=3,
        n_jobs=-1, random_state=RANDOM_STATE,
    )
    final_model.fit(X, y)
    joblib.dump({"model": final_model, "feature_cols": feature_cols}, MODEL_PATH)
    print(f"Saved Squam-excluded model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
