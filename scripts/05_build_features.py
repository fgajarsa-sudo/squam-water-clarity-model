"""
Step 3: Build the predictor variable table.

For each usable matched Landsat scene (median/min/stdDev of blue, green,
red, nir, swir1, swir2 already extracted in step 04), compute every
pairwise ratio between the 6 bands (using median reflectance), then join
back to the in-situ Secchi depth readings to attach the target variable
and site metadata needed for spatial hold-out validation.

Output: data/processed/model_training_table.csv
"""
from itertools import combinations

import pandas as pd
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
INSITU_PATH = PROJECT_DIR / "data" / "processed" / "insitu_secchi_clean.csv"
MATCHED_PATH = PROJECT_DIR / "data" / "processed" / "matched_landsat.csv"
OUT_PATH = PROJECT_DIR / "data" / "processed" / "model_training_table.csv"

BANDS = ["blue", "green", "red", "nir", "swir1", "swir2"]
STATS = ["median", "min", "stdDev"]
EPS = 1e-6


def main():
    insitu = pd.read_csv(INSITU_PATH)
    insitu = insitu[insitu["date"] >= "1984-01-01"].reset_index(drop=True)
    insitu["row_id"] = insitu.index.astype(str)

    matched = pd.read_csv(MATCHED_PATH, low_memory=False)
    matched["row_id"] = matched["row_id"].astype(str)

    print(f"In-situ readings (>=1984): {len(insitu)}")
    print(f"Matched rows: {len(matched)}")

    usable = matched[matched["has_match"] == 1].copy()
    band_cols = [f"{b}_median" for b in BANDS]
    usable = usable.dropna(subset=band_cols)
    print(f"Usable matched rows (valid pixels in all 6 bands): {len(usable)}")

    # Single representative pixel count (mask is shared across bands, so
    # counts are identical/near-identical across bands for a given scene)
    usable["pixel_count"] = usable["blue_count"]

    # Every pairwise ratio between the 6 bands, using median reflectance
    for b1, b2 in combinations(BANDS, 2):
        usable[f"ratio_{b1}_{b2}"] = usable[f"{b1}_median"] / (usable[f"{b2}_median"] + EPS)

    keep_cols = (
        ["row_id", "matched_image_date", "cloud_cover_pct", "pixel_count"]
        + [f"{b}_{s}" for b in BANDS for s in STATS]
        + [f"ratio_{b1}_{b2}" for b1, b2 in combinations(BANDS, 2)]
    )
    features = usable[keep_cols]

    merged = insitu.merge(features, on="row_id", how="inner")
    print(f"Final training table rows: {len(merged)}")
    print(f"Unique sites in training table: {merged['site_id'].nunique()}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_PATH, index=False)
    print(f"\nSaved to {OUT_PATH}")
    print(f"Columns ({len(merged.columns)}): {merged.columns.tolist()}")


if __name__ == "__main__":
    main()
