# Results: regional satellite clarity model

These tables back the satellite section of the manuscript. Settings and run order: [`docs/METHODOLOGY.md`](../docs/METHODOLOGY.md). Bias is predicted minus measured, so a negative value means the model underestimates Secchi depth. Every number below is computed from the files in this folder.

## 1. Training data

| Item | Value |
|---|---|
| Source | EPA Water Quality Portal Secchi readings at lake, reservoir and impoundment stations in New Hampshire, Vermont and Maine |
| Reading dates | 1 January 1984 to 1 October 2025 (the latest reading retrieved; the date of the portal query was not recorded) |
| Readings with a usable Landsat scene | 19,510 |
| Removed: Squam and Little Squam stations (excluded by name) | 107 readings at 16 stations |
| Training set | 19,403 readings at 1,383 monitoring locations |
| Training readings by state | Vermont 14,734 (76%), New Hampshire 2,768 (14%), Maine 1,901 (10%) |
| Secchi depth in training | median 4.50 m; 5th to 95th percentile 1.50 to 9.30 m; maximum 18.80 m |

## 2. Cross-validation (10 folds, grouped by monitoring site)

Each fold is predicted by a model that has not seen the fold's monitoring sites. The first row is the file saved by the original run; the second is a re-run on the rebuilt training table (scikit-learn 1.9.1). They agree to six decimals.

| Source | Readings | Sites | r | R² | Mean absolute error (m) | RMSE (m) |
|---|---|---|---|---|---|---|
| saved by original run | 19,403 | 1,383 | 0.5070 | 0.2565 | 1.5829 | 2.0468 |
| re-run on rebuilt table (scikit-learn 1.9.1) | 19,403 | 1,383 | 0.5070 | 0.2565 | 1.5829 | 2.0468 |

## 3. Check for Squam-area records in the training data

The 16 excluded stations were matched by name. The training table was then searched by station name, station code and position. No other record from Squam or Little Squam Lake was found; the other stations in the area belong to separate ponds and lakes (`training_squam_check.txt`). The NHDES codes SQUAM1WEST, SQU14AL and SQU20BL, which a name pattern would miss, are not in the Water Quality Portal training data.

## 4. Validation at 13 Squam and Little Squam monitoring sites

Field readings were paired with the satellite prediction at the same site within ±3 days: 445 pairs (68 sampling dates in 33 years).

| Pooled | Value |
|---|---|
| Pearson r | 0.264 (r² = 0.07) |
| RMSE | 2.29 m |
| Mean absolute error | 1.91 m |
| Bias | −1.70 m |
| Slope of predicted on measured depth | 0.16 |

Bias by measured depth:

| Measured depth (m) | Pairs | Bias (m) | RMSE (m) |
|---|---|---|---|
| 3–5 | 22 | +1.08 | 1.37 |
| 5–7 | 120 | −0.66 | 1.16 |
| 7–9 | 221 | −1.87 | 2.13 |
| ≥9 | 82 | −3.55 | 3.71 |

By site (sites with fewer than 3 pairs have no correlation):

| Site | Pairs | r | RMSE (m) | Bias (m) |
|---|---|---|---|---|
| 1 West | 52 | 0.165 | 2.34 | −1.91 |
| 10 Sandwich Bay | 39 | 0.204 | 3.01 | −2.68 |
| 11 Kent Island | 2 | n/a | 1.49 | −1.10 |
| 12 Moultonboro Bay | 38 | 0.224 | 2.44 | −2.11 |
| 14 Sturtevant Bay | 37 | 0.101 | 2.41 | −2.07 |
| 16 Dog Cove | 33 | 0.143 | 1.56 | −1.04 |
| 18 Piper Cove | 44 | 0.119 | 1.81 | −1.36 |
| 2 Cotton Cove | 29 | 0.344 | 1.34 | −0.93 |
| 5 Livermore Cove | 37 | 0.463 | 1.89 | −1.60 |
| 8 Rattlesnake Cove | 32 | 0.317 | 1.32 | −0.81 |
| 9A Inner Squaw Cove | 25 | 0.266 | 1.39 | +1.02 |
| Deep Haven | 41 | 0.186 | 3.02 | −2.73 |
| Loon Reef | 36 | 0.146 | 3.20 | −2.85 |

## 5. National product compared with the regional model

| Comparison | n | r | RMSE (m) | Bias (m) |
|---|---|---|---|---|
| National LAGOS-US LANDSAT (QAQC-TRUE July mean), 29 annual July means | 29 | −0.12 | 3.23 | −2.85 |
| Regional model, aggregation A (13 sites; per-date mean), 29 annual July means | 29 | −0.30 | 2.45 | −2.22 |
| National product, site-dates covered by both | 292 | 0.26 | 2.73 | −2.20 |
| Regional model, same site-dates | 292 | 0.24 | 2.22 | −1.59 |

## 6. How these were checked

On 21 October 2026 the training table was rebuilt from the authors' saved matching output and reproduced the paper's counts. The validation was re-run from the saved 13-site extraction; it reproduced all 445 pairs, with predictions identical to 1e-15 m (`validation_rerun_vs_committed.txt`).

## Files

| File | Contents |
|---|---|
| `training_summary.txt` | Training-set counts, dates, states, Secchi range |
| `training_squam_check.txt` | Squam-area check of the training table |
| `training_cv_comparison.csv, training_cv_results_saved_by_original_run.json` | Cross-validation results |
| `regional_metrics_pooled_and_by_site.csv` | Validation metrics, pooled and by site |
| `regional_bias_by_measured_depth.csv, regional_bias_by_predicted_value.csv` | Bias by depth class |
| `regional_nonindependence_sensitivity.csv` | Sensitivity to repeated pairs on the same date |
| `duplicate_scene_sensitivity.csv` | Sensitivity to the choice among overlapping scenes |
| `matched_pairs_with_image_info.csv` | The 445 matched pairs with scene dates |
| `comparable_sample_metrics.csv, supp_datelevel_national_vs_regional.csv` | National product versus regional model |
| `validation_rerun_vs_committed.txt` | Re-run of the validation compared with the committed output |

The scripts that produced these files are in [`analysis/`](../analysis/); the model pipeline is in [`scripts/`](../scripts/).
