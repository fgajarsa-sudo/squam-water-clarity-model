"""
Step 4: Train a random forest regression model predicting Secchi depth
from the Landsat-derived predictor variables, evaluated with a SPATIAL
hold-out cross-validation -- each fold holds out a distinct set of lakes
entirely (by site_id), so performance reflects generalization to lakes
the model has never seen, not just unseen rows from familiar lakes.

Outputs:
  data/processed/rf_model.joblib          -- final model trained on all data
  data/processed/spatial_cv_results.json  -- honest out-of-fold metrics
  data/processed/feature_importances.csv
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

PROJECT_DIR = Path(__file__).resolve().parents[1]
IN_PATH = PROJECT_DIR / "data" / "processed" / "model_training_table.csv"
MODEL_PATH = PROJECT_DIR / "data" / "processed" / "rf_model.joblib"
CV_RESULTS_PATH = PROJECT_DIR / "data" / "processed" / "spatial_cv_results.json"
IMPORTANCE_PATH = PROJECT_DIR / "data" / "processed" / "feature_importances.csv"

NON_FEATURE_COLS = {
    "site_id", "site_name", "state", "lat", "lon", "date", "secchi_m",
    "row_id", "matched_image_date",
}
N_SPLITS = 10
RANDOM_STATE = 42


def main():
    df = pd.read_csv(IN_PATH)
    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLS]
    print(f"Training rows: {len(df)}, features: {len(feature_cols)}")

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
        print(f"  fold {fold+1}/{N_SPLITS}: {len(test_idx)} held-out rows "
              f"from lakes not in training, R2={fold_r2:.3f}")

    r2 = r2_score(y, oof_pred)
    mae = mean_absolute_error(y, oof_pred)
    rmse = float(np.sqrt(mean_squared_error(y, oof_pred)))
    corr = float(np.corrcoef(y, oof_pred)[0, 1])

    print("\n--- Spatial hold-out cross-validation results ---")
    print(f"  Pearson r  = {corr:.3f}")
    print(f"  R^2        = {r2:.3f}")
    print(f"  MAE        = {mae:.3f} m")
    print(f"  RMSE       = {rmse:.3f} m")

    cv_results = {
        "n_splits": N_SPLITS, "n_rows": len(df), "n_sites": df["site_id"].nunique(),
        "pearson_r": corr, "r2": r2, "mae_m": mae, "rmse_m": rmse,
    }
    CV_RESULTS_PATH.write_text(json.dumps(cv_results, indent=2))

    # Final production model trained on ALL available data
    final_model = RandomForestRegressor(
        n_estimators=500, max_depth=None, min_samples_leaf=3,
        n_jobs=-1, random_state=RANDOM_STATE,
    )
    final_model.fit(X, y)
    joblib.dump({"model": final_model, "feature_cols": feature_cols}, MODEL_PATH)
    print(f"\nFinal model (trained on all {len(df)} rows) saved to {MODEL_PATH}")

    importances = pd.DataFrame({
        "feature": feature_cols, "importance": final_model.feature_importances_,
    }).sort_values("importance", ascending=False)
    importances.to_csv(IMPORTANCE_PATH, index=False)
    print("\nTop 10 predictors:")
    print(importances.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
