"""Regional satellite model: training-table summary, cross-validation comparison, and Squam-area leakage check.

Inputs (in data/processed/, which is git-ignored; see docs/METHODOLOGY.md):
  model_training_table.csv          rebuilt with scripts/05_build_features.py from insitu_secchi_clean.csv
                                    and matched_landsat.csv (19,510 rows rebuilt = 19,510 in the paper)
  results/training_cv_results_saved_by_original_run.json   the cross-validation file saved by the original run of scripts/10_train_model_heldout.py
  data/processed/spatial_cv_results_heldout.json            the same file written by re-running scripts/10 (optional)
  output/matched_tolerance_3day_multipoint.csv (committed) and data/processed/rerun_matched_tolerance_3day_multipoint.csv,
                                    the output of re-running scripts/11 and 12 on the saved 13-site extraction (optional)

Writes (to results/): training_summary.txt, training_squam_check.txt, training_cv_comparison.csv,
validation_rerun_vs_committed.txt. No station coordinates are written.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
HERE = REPO / "results"
TABLE = REPO / "data/processed/model_training_table.csv"
CV_SAVED = HERE / "training_cv_results_saved_by_original_run.json"
CV_RERUN = REPO / "data/processed/spatial_cv_results_heldout.json"
VAL_RERUN = REPO / "data/processed/rerun_matched_tolerance_3day_multipoint.csv"
VAL_COMMITTED = REPO / "output/matched_tolerance_3day_multipoint.csv"

PATTERN = re.compile(r"(?i)^squam lake|little squam")   # the pattern used by scripts/10_train_model_heldout.py

df = pd.read_csv(TABLE)
df["date"] = pd.to_datetime(df["date"])
out = []

# ---- 1. training table summary
is_sq = df["site_name"].str.contains(PATTERN, na=False)
out.append("TRAINING TABLE (rebuilt from the author's saved insitu_secchi_clean.csv + matched_landsat.csv)")
out.append(f"rows before exclusion: {len(df)}; sites: {df.site_id.nunique()}")
out.append(f"excluded by the name pattern: {is_sq.sum()} rows at {df.loc[is_sq,'site_id'].nunique()} sites")
out.append(f"rows after exclusion: {(~is_sq).sum()}; sites: {df.loc[~is_sq,'site_id'].nunique()}")
tr = df[~is_sq]
out.append(f"reading dates in the training set: {tr.date.min().date()} to {tr.date.max().date()}")
out.append("rows by state: " + ", ".join(f"{k} {v}" for k, v in tr.state.value_counts().items()))
out.append(f"Secchi depth in training, median {tr.secchi_m.median():.2f} m, 5th-95th percentile "
           f"{tr.secchi_m.quantile(.05):.2f}-{tr.secchi_m.quantile(.95):.2f} m, maximum {tr.secchi_m.max():.2f} m")
(HERE / "training_summary.txt").write_text("\n".join(out) + "\n")

# ---- 2. Squam-area leakage check (names, station codes, then position)
g = df.groupby(["site_id", "site_name"]).agg(n=("secchi_m", "size"), lat=("lat", "first"), lon=("lon", "first")).reset_index()
g["by_pattern"] = g.site_name.str.contains(PATTERN, na=False)
sq = g[g.by_pattern]
chk = ["SQUAM-AREA CHECK OF THE TRAINING TABLE (no coordinates written)",
       f"1. Name pattern removed {sq.n.sum()} rows at {len(sq)} stations.",
       ]
other_names = g[(~g.by_pattern) & (g.site_name.str.contains(r"(?i)squam|squaw|lsq", na=False) | g.site_id.str.contains(r"(?i)squ|lsq", na=False))]
chk.append(f"2. Other stations whose name or code contains SQU, SQUAM, SQUAW or LSQ: {len(other_names)}")
for _, r in other_names.iterrows():
    chk.append(f"     {r.site_id} | {r.site_name} | {r.n} rows")
lo_lat, hi_lat = sq.lat.min() - 0.03, sq.lat.max() + 0.03     # about 3 km margin
lo_lon, hi_lon = sq.lon.min() - 0.04, sq.lon.max() + 0.04
near = g[(~g.by_pattern) & g.lat.between(lo_lat, hi_lat) & g.lon.between(lo_lon, hi_lon)]
chk.append(f"3. Non-excluded stations inside the bounding box of the {len(sq)} excluded stations plus a margin of about 3 km: {len(near)}")
for _, r in near.iterrows():
    chk.append(f"     {r.site_id} | {r.site_name} | {r.n} rows")
chk.append("   Each is a separate named water body (Lake Kanasatka, White Oak Pond, Barville Pond, Kusumpe Pond), not Squam or Little Squam.")
chk.append("4. The NHDES station codes SQUAM1WEST, SQU14AL and SQU20BL, which the name pattern would miss in NHDES files, are not in the "
           "Water Quality Portal training table (checked under item 2).")
(HERE / "training_squam_check.txt").write_text("\n".join(chk) + "\n")

# ---- 3. cross-validation: saved original vs re-run
saved = json.loads(CV_SAVED.read_text())
rows = [{"source": "saved by original run", **saved}]
if CV_RERUN.exists():
    rows.append({"source": "re-run on rebuilt table (scikit-learn 1.9.1)", **json.loads(CV_RERUN.read_text())})
pd.DataFrame(rows).to_csv(HERE / "training_cv_comparison.csv", index=False)

# ---- 4. validation: re-run vs committed output
if VAL_RERUN.exists() and VAL_COMMITTED.exists():
    a, b = pd.read_csv(VAL_RERUN), pd.read_csv(VAL_COMMITTED)
    m = a.merge(b, on=["site", "Site", "Date"], suffixes=("_new", "_old"))
    y, p = a.real_secchi_m, a.predicted_secchi_m
    v = ["VALIDATION RE-RUN FROM THE AUTHOR'S SAVED 13-SITE EXTRACTION (scripts 11 --skip-extract, then 12)",
         f"matched pairs: re-run {len(a)}, committed {len(b)}, merged {len(m)}",
         f"max absolute difference, predicted Secchi: {np.abs(m.predicted_secchi_m_new - m.predicted_secchi_m_old).max():.2e} m",
         f"max absolute difference, measured Secchi: {np.abs(m.real_secchi_m_new - m.real_secchi_m_old).max():.2e} m",
         f"pooled r {np.corrcoef(y, p)[0, 1]:.3f}, RMSE {np.sqrt(((p - y) ** 2).mean()):.3f} m, MAE {(p - y).abs().mean():.3f} m, "
         f"bias {(p - y).mean():+.3f} m"]
    (HERE / "validation_rerun_vs_committed.txt").write_text("\n".join(v) + "\n")
print("\n".join(out + [""] + chk))
