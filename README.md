# Squam Lake Water Clarity Model

A regionally calibrated satellite water clarity model for Squam Lake and Little Squam Lake, NH, built because the national LAGOS-US LANDSAT model does not correlate with real field measurements at these lakes (r = -0.12, p = 0.52, n = 29).

Methodology follows Piper, Glines & Rose (2024), *Ecology* 105(5): e4291, using in-situ Secchi depth readings from the EPA Water Quality Portal (NH/VT/ME) matched to Landsat Collection 2 Level 2 surface reflectance via Google Earth Engine, with a random forest regression model.

## Pipeline (`scripts/`)

| Script | Purpose |
|---|---|
| `01_pull_epa_secchi.py` | Pull in-situ Secchi depth readings from EPA Water Quality Portal (NH/VT/ME) |
| `02_pull_epa_stations.py` | Pull station coordinate metadata |
| `03_clean_insitu_data.py` | Merge, clean, and sanity-bound the in-situ dataset |
| `04_match_landsat.py` | Match each reading to the nearest Landsat scene (±3 days), with cloud masking and ice-season exclusion |
| `05_build_features.py` | Build predictor variables: band statistics and pairwise ratios |
| `06_train_model.py` | Train random forest with spatial hold-out cross-validation (10 folds grouped by monitoring site) |
| `07_predict_squam.py` | Generate predictions for Squam/Little Squam, 1984-present |
| `08_validate.py` / `09_validate_deephaven.py` | Validate predictions against real Secchi readings |
| `10_train_model_heldout.py` | Retrain excluding the Squam and Little Squam stations (matched by name) so the model has not seen either lake. A check by station name, code and position found no other Squam-area record in the training data (`results/training_squam_check.txt`) |
| `11_predict_multipoint.py` | Regenerate predictions at 13 named monitoring sites instead of one central point per lake. Scenes with fewer than 5 valid pixels in the window are dropped (training scenes have no minimum). `--skip-extract` rebuilds the predictions from a saved extraction without Earth Engine |
| `12_validate_multipoint.py` | Validate each real reading against its own site's prediction |
| `14_make_manuscript_figures.py` | Draw manuscript Figures 1 and 2 (300 dpi) from `output/matched_tolerance_3day_multipoint.csv`: Figure 1 pools all 445 matched readings (r = 0.264); Figure 2 shows one panel per site with at least 20 readings. Writes `output/manuscript_figure_1.png` and `output/manuscript_figure_2.png`, and stops if any number differs from the manuscript |

## Archived files

`data/archive/` holds the saved intermediate files behind the paper: the cleaned Secchi readings, the Landsat matching output, the training table, the trained random forest, the cross-validation result and the 13-site validation extraction. Its README describes each file and how to check it. Release v1.0.0 is archived on Zenodo: [10.5281/zenodo.23827897](https://doi.org/10.5281/zenodo.23827897).

## What's not in this repo

The raw download and other working files (`data/raw/`, `data/processed/`) are excluded via `.gitignore` — they're large (500+ MB), and some raw EPA fields contained incidental free-text volunteer field notes unrelated to this project's purpose that were stripped before any further use.

## Methodology and results

- **Methodology:** [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) gives the exact settings of every step, the run order, how to re-run without Earth Engine, and what cannot be reproduced exactly.
- **Results:** [`results/README.md`](results/README.md) gives the training-data summary, cross-validation, the Squam-area check, the validation against field readings and the comparison with the national product. The scripts that produce them are in [`analysis/`](analysis/).

The Water Quality Portal query in `01_pull_epa_secchi.py` has no end date and its retrieval date was not recorded, so a new pull will not match the paper's training data exactly. The latest reading in the paper's training data is dated 1 October 2025.

## Data

`data/nhdes/` holds the three unmodified extracts from the NHDES Environmental Monitoring Database
(physical/chemical grab samples, Squam Lake and Little Squam Lake, 1979-2024) that were used to cross-check and extend
the Squam Lakes Association water quality record in the accompanying manuscript. See `data/nhdes/README.md` for
provenance, checksums, the NHDES data-use notice and the citation. Please cite NHDES when using these data.

## Results

See `output/` for prediction CSVs/Excel files and validation reports. Full write-up of validation methodology and results: see the project's compiled PDF report.

**Cross-validation** (10 folds grouped by monitoring site, 19,403 training readings): r = 0.51, RMSE 2.05 m. **At the 13 Squam and Little Squam sites** (445 pairs): r = 0.264, RMSE 2.29 m, bias −1.70 m (the model underestimates clarity, most at the greatest depths).

**Bottom line:** the model shows a real, statistically significant improvement over the national model (best result: r ≈ 0.26–0.34 depending on matching method, vs. the national model's r = -0.12), but explanatory power remains modest (R² typically 0.03–0.11), and performance varies meaningfully by specific monitoring site.
