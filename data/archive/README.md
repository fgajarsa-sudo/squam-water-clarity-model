# Archived intermediate files for the Squam Lake regional satellite model

These are the files behind the regional model in the manuscript "Water Clarity, Phosphorus, and Common Loon Chick Survival on Squam Lake, New Hampshire: A Retrospective Association Analysis with Satellite Validation". They are the saved outputs of the scripts in `scripts/` (run order in `docs/METHODOLOGY.md`). Nothing here comes from the Loon Preservation Committee.

| File | Contents | Rows |
|---|---|---|
| `insitu_secchi_clean.csv.gz` | Cleaned Secchi depth readings from the EPA Water Quality Portal (VT, NH, ME): site, state, latitude, longitude, date, depth in metres (output of script 03). | 74,718 |
| `matched_landsat.csv.gz` | Landsat Collection 2 Level-2 band statistics extracted for each reading (output of script 04, from Google Earth Engine). `row_id` is the reading's position (counting from 0) among the 68,640 readings dated 1 January 1984 or later in the cleaned file. | 43,013 |
| `model_training_table.csv.gz` | Readings joined to their Landsat predictors: 35 predictors plus site, date and measured depth (output of script 05). | 19,510 |
| `rf_model_heldout.joblib` | The trained random forest used in the paper (500 trees, trained by script 10 after removing the 107 rows from Squam and Little Squam stations, leaving 19,403 rows at 1,383 sites). A Python dictionary with `model` (scikit-learn `RandomForestRegressor`) and `feature_cols` (the 35 predictor names, in order). Load with `joblib.load`. | |
| `spatial_cv_results_heldout.json` | 10-fold cross-validation, folds grouped by monitoring site: r 0.507, R² 0.256, MAE 1.583 m, RMSE 2.047 m. | |
| `squam_multipoint_coordinates.csv` | The 13 Squam Lakes Association monitoring sites used for validation, with the matched NHDES station and coordinates. Site names are those used by the Squam Lakes Association. | 13 |
| `squam_multipoint_landsat_extracted.csv.gz` | Landsat band statistics extracted at those 13 sites (input to script 11 with `--skip-extract`). | 31,001 |
| `SHA256SUMS.txt` | Checksums of the files above. Check with `sha256sum -c SHA256SUMS.txt`. | |

## About the model file

The trained model was saved by the original run as a 245 MB file (SHA-256 `88c9805c8a6fe9a2b3a3e2f3b0c5d2f5ff9c13775320858a3ea8e7ed4a4a2eb3`). GitHub does not accept files over 100 MB, so the model is stored here compressed with `joblib.dump(..., compress=("xz", 6))`, which is lossless. Checked on 30 October 2026: all 500 trees are identical to the original in every node array, and predictions on the training table agree to 4e-15 m. The compressed file loads with `joblib.load` in scikit-learn 1.9.1, the version used for the re-run on 21 October 2026. Other scikit-learn versions may refuse or warn when loading a saved model; if so, retrain with `scripts/10_train_model_heldout.py` from `model_training_table.csv.gz`.

## What is not here

- The Squam Lakes Association field readings are held by that organisation. The 445 readings matched to Landsat scenes are in `output/matched_tolerance_3day_multipoint.csv`.
- The raw Water Quality Portal download is not archived (see `docs/METHODOLOGY.md`, limitation 1).
- No Loon Preservation Committee data are in this repository.
