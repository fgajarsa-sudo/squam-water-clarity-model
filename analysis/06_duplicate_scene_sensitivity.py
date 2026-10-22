"""
Sensitivity of the pooled +/-3-day result to the arbitrary choice among DUPLICATE prediction rows
(same site, same date; overlapping Landsat scenes) in output/squam_predicted_secchi_multipoint.csv,
and the exact-date file's double counting.  Uses the committed matched file's (Site, Date) keys and
re-selects the prediction using different rules.

Sign: bias = mean(predicted - real).
Writes: duplicate_scene_sensitivity.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results"
pairs = pd.read_csv(REPO / "output" / "matched_tolerance_3day_multipoint.csv", parse_dates=["Date"])
pred = pd.read_csv(REPO / "output" / "squam_predicted_secchi_multipoint.csv", parse_dates=["date"])

sel = {"committed (merge_asof pick)": [], "mean of same-day rows": [], "min of same-day rows": [], "max of same-day rows": []}
real = []
rng = np.random.default_rng(1)
rand_runs = [[] for _ in range(1000)]
for _, r in pairs.iterrows():
    p = pred[pred.site == r.Site]
    dd = (p.date - r.Date).dt.days.abs()
    win = p[dd <= 3]
    near = win[(win.date - r.Date).dt.days.abs() == (win.date - r.Date).dt.days.abs().min()]
    v = near.predicted_secchi_m.to_numpy()
    sel["committed (merge_asof pick)"].append(r.predicted_secchi_m)
    sel["mean of same-day rows"].append(v.mean()); sel["min of same-day rows"].append(v.min()); sel["max of same-day rows"].append(v.max())
    real.append(r.real_secchi_m)
    for k in range(1000):
        rand_runs[k].append(v[rng.integers(len(v))])
real = np.array(real)

def st(y):
    y = np.array(y); r_, p_ = stats.pearsonr(real, y)
    return r_, p_, np.sqrt(np.mean((y - real) ** 2)), (y - real).mean()

rows = []
for k, y in sel.items():
    r_, p_, rm, b = st(y); rows.append(dict(rule=k, n=len(y), r=r_, p=p_, rmse_m=rm, bias_m=b))
rr = np.array([st(y) for y in rand_runs])
rows.append(dict(rule="random pick among same-day rows (1,000 draws): median [2.5%, 97.5%] of r", n=len(real), r=np.median(rr[:, 0]), p=np.nan, rmse_m=np.median(rr[:, 2]), bias_m=np.median(rr[:, 3])))
rows[-1]["r_lo"], rows[-1]["r_hi"] = np.percentile(rr[:, 0], [2.5, 97.5])
rows[-1]["rmse_lo"], rows[-1]["rmse_hi"] = np.percentile(rr[:, 2], [2.5, 97.5])
res = pd.DataFrame(rows)
res.to_csv(OUT / "duplicate_scene_sensitivity.csv", index=False, float_format="%.6f")
pd.set_option("display.width", 250)
print(res.round(4).to_string(index=False))

# exact-date file
e = pd.read_csv(REPO / "output" / "matched_exact_date_multipoint.csv", parse_dates=["Date"])
print()
print(f"exact-date file: {len(e)} rows, {e.drop_duplicates(['Site','Date']).shape[0]} unique (Site,Date); duplicated rows {e.duplicated(['Site','Date']).sum()}")
x, y = e.real_secchi_m, e.predicted_secchi_m
r_, p_ = stats.pearsonr(x, y)
print(f"  as committed: n={len(e)} r={r_:.3f} p={p_:.4f} RMSE={np.sqrt(np.mean((y-x)**2)):.3f} bias={np.mean(y-x):.3f}")
u = e.groupby(["Site", "Date"]).agg(real=("real_secchi_m", "first"), pred=("predicted_secchi_m", "mean")).reset_index()
r_, p_ = stats.pearsonr(u.real, u.pred)
print(f"  de-duplicated (mean of duplicate rows): n={len(u)} r={r_:.3f} p={p_:.4f} RMSE={np.sqrt(np.mean((u.pred-u.real)**2)):.3f} bias={np.mean(u.pred-u.real):.3f}")
