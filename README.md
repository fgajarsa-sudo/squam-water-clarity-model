# Squam Lake Water Clarity Model

A regionally calibrated satellite water clarity model for Squam Lake and Little Squam Lake, NH, built because the national LAGOS-US LANDSAT model does not correlate with real field measurements at these lakes (r = -0.22, p = 0.26).

Methodology follows Piper, Glines & Rose (2024), *Ecology* 105(5): e4291, using in-situ Secchi depth readings from the EPA Water Quality Portal (NH/VT/ME) matched to Landsat Collection 2 Level 2 surface reflectance via Google Earth Engine, with a random forest regression model.

## Pipeline (`scripts/`)

| Script | Purpose |
|---|---|
| `01_pull_epa_secchi.py` | Pull in-situ Secchi depth readings from EPA Water Quality Portal (NH/VT/ME) |
| `02_pull_epa_stations.py` | Pull station coordinate metadata |
| `03_clean_insitu_data.py` | Merge, clean, and sanity-bound the in-situ dataset |
| `04_match_landsat.py` | Match each reading to the nearest Landsat scene (±3 days), with cloud masking and ice-season exclusion |
| `05_build_features.py` | Build predictor variables: band statistics and pairwise ratios |
| `06_train_model.py` | Train random forest with spatial (lake-level) hold-out cross-validation |
| `07_predict_squam.py` | Generate predictions for Squam/Little Squam, 1984-present |
| `08_validate.py` / `09_validate_deephaven.py` | Validate predictions against real Secchi readings |
| `10_train_model_heldout.py` | Retrain excluding all Squam-area sites from training (fixes a data leakage issue found during validation) |
| `11_predict_multipoint.py` | Regenerate predictions at 13 named monitoring sites instead of one central point per lake |
| `12_validate_multipoint.py` | Validate each real reading against its own site's prediction |

## What's not in this repo

Raw and intermediate data (`data/raw/`, `data/processed/`) are excluded via `.gitignore` — they're large (500+ MB), fully reproducible by re-running the scripts against the EPA and Earth Engine APIs, and some raw EPA fields contained incidental free-text volunteer field notes unrelated to this project's purpose that were stripped before any further use.

## Results

See `output/` for prediction CSVs/Excel files and validation reports. Full write-up of validation methodology and results: see the project's compiled PDF report.

**Bottom line:** the model shows a real, statistically significant improvement over the national model (best result: r ≈ 0.26–0.34 depending on matching method, vs. the national model's r = -0.22), but explanatory power remains modest (R² typically 0.03–0.11), and performance varies meaningfully by specific monitoring site.
