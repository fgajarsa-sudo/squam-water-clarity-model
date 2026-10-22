"""
Deliverable 2: metrics for the regional model on the +/-3-day multipoint sample
(repo: output/matched_tolerance_3day_multipoint.csv; columns real_secchi_m, predicted_secchi_m, Site).

Sign convention: bias = mean(predicted - real)  (negative = model UNDER-predicts clarity).
Slope/intercept: OLS of predicted (y) on real (x):  predicted = intercept + slope * real.
r2          = Pearson r squared (what the manuscript's "r^2" column reports).
R2_1to1     = 1 - SSE/SST_real, with SSE = sum((pred-real)^2), SST_real = sum((real-mean(real))^2): skill relative to the 1:1 line.
CCC         = Lin's concordance correlation coefficient.

Writes: regional_metrics_pooled_and_by_site.csv, regional_bias_by_measured_depth.csv,
        regional_bias_by_predicted_value.csv, regional_nonindependence_sensitivity.csv, regional_metrics_checks.txt
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results"
CSV = REPO / "output" / "matched_tolerance_3day_multipoint.csv"

d = pd.read_csv(CSV, parse_dates=["Date"])
chk = []
def log(s=""):
    print(s); chk.append(s)


def metrics(g, label):
    x = g["real_secchi_m"].to_numpy(float)
    y = g["predicted_secchi_m"].to_numpy(float)
    n = len(x)
    out = dict(group=label, n=n, mean_real=x.mean(), mean_pred=y.mean(), sd_real=x.std(ddof=1) if n > 1 else np.nan,
               sd_pred=y.std(ddof=1) if n > 1 else np.nan)
    err = y - x
    out.update(bias_m=err.mean(), rmse_m=np.sqrt(np.mean(err ** 2)), mae_m=np.mean(np.abs(err)))
    out.update(rmse_centered_m=np.sqrt(np.mean((err - err.mean()) ** 2)), bias_share_of_mse=err.mean() ** 2 / np.mean(err ** 2))
    if n >= 3:
        r, p = stats.pearsonr(x, y)
        lr = stats.linregress(x, y)
        sst = np.sum((x - x.mean()) ** 2)
        ccc = 2 * np.cov(x, y, ddof=0)[0, 1] / (x.var() + y.var() + (x.mean() - y.mean()) ** 2)
        out.update(r=r, p=p, r2=r * r, R2_1to1=1 - np.sum(err ** 2) / sst, slope=lr.slope, intercept=lr.intercept, ccc=ccc,
                   bias_pct_of_mean_real=100 * err.mean() / x.mean())
    else:
        out.update(r=np.nan, p=np.nan, r2=np.nan, R2_1to1=np.nan, slope=np.nan, intercept=np.nan, ccc=np.nan,
                   bias_pct_of_mean_real=100 * err.mean() / x.mean())
    return out

rows = [metrics(d, "POOLED (13 sites)")]
for s, g in d.groupby("Site"):
    m = metrics(g, s)
    m["flag"] = "n<3: r/slope undefined; do not interpret" if len(g) < 3 else ("n<20 (not shown in Fig 2)" if len(g) < 20 else "")
    rows.append(m)
res = pd.DataFrame(rows)
cols = ["group", "n", "mean_real", "mean_pred", "sd_real", "sd_pred", "r", "p", "r2", "R2_1to1", "ccc", "rmse_m", "mae_m", "bias_m",
        "rmse_centered_m", "bias_share_of_mse", "bias_pct_of_mean_real", "slope", "intercept", "flag"]
res = res[cols]
res.to_csv(OUT / "regional_metrics_pooled_and_by_site.csv", index=False, float_format="%.6f")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(res.round(3).to_string(index=False))

# --------- reproduce paper numbers
P = res.set_index("group")
log("")
log("=== reproduction of paper numbers (same file / same sample?) ===")
pool = P.loc["POOLED (13 sites)"]
log(f"n = {int(pool.n)}  (paper 445)   r = {pool.r:.4f} (paper 0.264)   p = {pool.p:.2e} (paper <0.0001)   r2 = {pool.r2:.4f} (paper 0.07 / Table 3 0.070)")
assert int(pool.n) == 445 and round(pool.r, 3) == 0.264 and pool.p < 1e-4 and round(pool.r2, 3) == 0.070
big = res[(res.group != "POOLED (13 sites)") & (res.n >= 20)].sort_values("rmse_m")
log(f"sites with n>=20: {len(big)} (paper: 12 of 13); site with n<20: {res[(res.group != 'POOLED (13 sites)') & (res.n < 20)][['group','n']].values.tolist()}")
six = big.head(6)
log("six lowest-RMSE sites (paper: 'six small, sheltered coves, RMSE 1.3 to 1.9 m'): " + "; ".join(f"{g} {v:.3f}" for g, v in zip(six.group, six.rmse_m)))
assert six.rmse_m.min() >= 1.3 and six.rmse_m.max() <= 1.9
log("highest-RMSE sites: " + "; ".join(f"{g} {v:.3f}" for g, v in zip(big.group.iloc[::-1].head(4), big.rmse_m.iloc[::-1].head(4))))
log(f"Deep Haven RMSE {P.loc['Deep Haven','rmse_m']:.3f} (paper 3.0); Loon Reef RMSE {P.loc['Loon Reef','rmse_m']:.3f} (paper 3.2)")
for site, (n, r, p, r2) in {"5 Livermore Cove": (37, 0.463, 0.004, 0.215), "Deep Haven": (41, 0.186, 0.245, 0.034), "Loon Reef": (36, 0.146, 0.397, 0.021)}.items():
    q = P.loc[site]
    log(f"Table 3 row {site}: paper n={n} r={r} p={p} r2={r2} | file n={int(q.n)} r={q.r:.3f} p={q.p:.3f} r2={q.r2:.3f}")
    assert int(q.n) == n and round(q.r, 3) == r and round(q.p, 3) == p and round(q.r2, 3) == r2
sig = big[big.p < 0.05]
log(f"sites (n>=20) with p<0.05: {sig.group.tolist()} (paper: exactly one, r=0.463)")
log(f"RMSE >= 3.0 m sites: {big[big.rmse_m >= 3.0][['group','rmse_m']].round(3).values.tolist()}  (paper text names Deep Haven 3.0 and Loon Reef 3.2 only)")

# --------- site-level confounding: does site RMSE track site mean measured depth?
s12 = res[(res.group != "POOLED (13 sites)") & (res.n >= 20)]
for col in ["rmse_m", "bias_m", "rmse_centered_m"]:
    rr, pp = stats.pearsonr(s12.mean_real, s12[col])
    log(f"across the 12 sites (n>=20): corr(site mean measured Secchi, site {col}) = {rr:.3f} (p = {pp:.4f})")
rr, pp = stats.spearmanr(s12.mean_real, s12.rmse_m)
log(f"  Spearman(site mean measured Secchi, site RMSE) = {rr:.3f} (p = {pp:.4f}); centered RMSE range across the 12 sites: {s12.rmse_centered_m.min():.3f}-{s12.rmse_centered_m.max():.3f} m")
log(f"pooled MSE decomposition: bias^2 = {pool.bias_m**2:.3f}, MSE = {pool.rmse_m**2:.3f}, bias share = {pool.bias_share_of_mse:.3f}; centered RMSE = {pool.rmse_centered_m:.3f} m")

# --------- bias by measured depth bins
def bin_table(df, col, edges, labels):
    df = df.copy()
    df["bin"] = pd.cut(df[col], edges, right=False, labels=labels)
    rows = []
    for b, g in df.groupby("bin", observed=True):
        m = metrics(g, str(b))
        rows.append(dict(bin=str(b), n=m["n"], mean_real=m["mean_real"], mean_pred=m["mean_pred"], bias_m=m["bias_m"], rmse_m=m["rmse_m"], mae_m=m["mae_m"],
                         frac_underpredicted=float((g.predicted_secchi_m < g.real_secchi_m).mean())))
    return pd.DataFrame(rows)

edges = [0, 3, 5, 7, 9, 99]
labels = ["<3", "3-<5", "5-<7", "7-<9", ">=9"]
t1 = bin_table(d, "real_secchi_m", edges, labels)
t1.insert(0, "binning", "measured (real) depth, fixed bins")
# terciles of measured depth
q = d.real_secchi_m.quantile([1 / 3, 2 / 3]).values
log("")
log(f"tercile cut-points of measured depth: {q.round(3).tolist()}")
d["tercile"] = pd.qcut(d.real_secchi_m, 3, labels=["T1 low", "T2 mid", "T3 high"])
rows = []
for b, g in d.groupby("tercile", observed=True):
    m = metrics(g, str(b))
    rows.append(dict(bin=f"{b} [{g.real_secchi_m.min():.1f}-{g.real_secchi_m.max():.1f}]", n=m["n"], mean_real=m["mean_real"], mean_pred=m["mean_pred"], bias_m=m["bias_m"],
                     rmse_m=m["rmse_m"], mae_m=m["mae_m"], frac_underpredicted=float((g.predicted_secchi_m < g.real_secchi_m).mean())))
t2 = pd.DataFrame(rows); t2.insert(0, "binning", "measured (real) depth, terciles")
bydepth = pd.concat([t1, t2], ignore_index=True)
bydepth.to_csv(OUT / "regional_bias_by_measured_depth.csv", index=False, float_format="%.6f")
print(); print(bydepth.round(3).to_string(index=False))

# binning on PREDICTED value (the reverse conditioning) -- shows regression-to-the-mean part of the pattern
predq = d.predicted_secchi_m.quantile([1 / 3, 2 / 3]).values
d["pred_tercile"] = pd.qcut(d.predicted_secchi_m, 3, labels=["P1 low", "P2 mid", "P3 high"])
rows = []
for b, g in d.groupby("pred_tercile", observed=True):
    m = metrics(g, str(b))
    rows.append(dict(bin=f"{b} [{g.predicted_secchi_m.min():.1f}-{g.predicted_secchi_m.max():.1f}]", n=m["n"], mean_real=m["mean_real"], mean_pred=m["mean_pred"], bias_m=m["bias_m"],
                     rmse_m=m["rmse_m"], mae_m=m["mae_m"]))
t3 = pd.DataFrame(rows); t3.insert(0, "binning", "PREDICTED depth, terciles (reverse conditioning)")
t3.to_csv(OUT / "regional_bias_by_predicted_value.csv", index=False, float_format="%.6f")
print(); print(t3.round(3).to_string(index=False))

# fraction of readings above/below
log("")
log(f"pooled: predicted<real in {(d.predicted_secchi_m < d.real_secchi_m).mean()*100:.1f}% of pairs; max predicted = {d.predicted_secchi_m.max():.2f} m; max real = {d.real_secchi_m.max():.2f} m; "
    f"readings >=9 m: {(d.real_secchi_m>=9).sum()}, predictions >=9 m: {(d.predicted_secchi_m>=9).sum()}; real >= 7 m: {(d.real_secchi_m>=7).sum()}")
log(f"pooled SD real = {d.real_secchi_m.std(ddof=1):.3f} m, SD pred = {d.predicted_secchi_m.std(ddof=1):.3f} m; ratio = {d.predicted_secchi_m.std(ddof=1)/d.real_secchi_m.std(ddof=1):.3f}")
log(f"pooled min real = {d.real_secchi_m.min():.2f} (no readings < 3 m exist in the validation file, so the '<3 m' bin is empty)")

# bias by site, sorted, and test of site-mean bias
# ---------- non-independence sensitivity: cluster by sampling date
rng = np.random.default_rng(20261021)
dates = d.Date.unique()
idx_by_date = {dt: np.where(d.Date.values == dt)[0] for dt in dates}
x_all, y_all = d.real_secchi_m.to_numpy(), d.predicted_secchi_m.to_numpy()
B = 10000
rs, biases, rmses = [], [], []
for _ in range(B):
    pick = rng.choice(len(dates), len(dates), replace=True)
    ii = np.concatenate([idx_by_date[dates[k]] for k in pick])
    x, y = x_all[ii], y_all[ii]
    rs.append(np.corrcoef(x, y)[0, 1]); biases.append((y - x).mean()); rmses.append(np.sqrt(np.mean((y - x) ** 2)))
def ci(a): return np.percentile(a, [2.5, 97.5])
# date-level aggregation (mean across sites on each sampling date) -> n = number of dates
dm = d.groupby("Date").agg(real=("real_secchi_m", "mean"), pred=("predicted_secchi_m", "mean"), n_sites=("Site", "size")).reset_index()
r_dm, p_dm = stats.pearsonr(dm.real, dm.pred)
# year-level aggregation
ym = d.assign(Year=d.Date.dt.year).groupby("Year").agg(real=("real_secchi_m", "mean"), pred=("predicted_secchi_m", "mean")).reset_index()
r_ym, p_ym = stats.pearsonr(ym.real, ym.pred)
# within-site-demeaned? (removes between-site differences) -- shows how much of pooled r is between-site
d["real_dm"] = d.real_secchi_m - d.groupby("Site").real_secchi_m.transform("mean")
d["pred_dm"] = d.predicted_secchi_m - d.groupby("Site").predicted_secchi_m.transform("mean")
r_within, p_within = stats.pearsonr(d.real_dm, d.pred_dm)
# site-mean level
sm = d.groupby("Site").agg(real=("real_secchi_m", "mean"), pred=("predicted_secchi_m", "mean")).reset_index()
r_sm, p_sm = stats.pearsonr(sm.real, sm.pred)
sens = pd.DataFrame([
    dict(quantity="pooled r (445 pairs, as in paper)", value=pool.r, ci_lo=np.nan, ci_hi=np.nan, note="p treats 445 pairs as independent"),
    dict(quantity="pooled r, date-cluster bootstrap (68 dates, 10,000 resamples, seed 20261021)", value=np.mean(rs), ci_lo=ci(rs)[0], ci_hi=ci(rs)[1], note="resamples whole sampling dates"),
    dict(quantity="pooled bias_m, date-cluster bootstrap", value=np.mean(biases), ci_lo=ci(biases)[0], ci_hi=ci(biases)[1], note="pred - real"),
    dict(quantity="pooled RMSE_m, date-cluster bootstrap", value=np.mean(rmses), ci_lo=ci(rmses)[0], ci_hi=ci(rmses)[1], note=""),
    dict(quantity=f"r after averaging sites within each sampling date (n={len(dm)} dates)", value=r_dm, ci_lo=np.nan, ci_hi=np.nan, note=f"p = {p_dm:.4f}"),
    dict(quantity=f"r after averaging within sampling year (n={len(ym)} years)", value=r_ym, ci_lo=np.nan, ci_hi=np.nan, note=f"p = {p_ym:.4f}"),
    dict(quantity="r after removing each site's own mean (within-site r, n=445)", value=r_within, ci_lo=np.nan, ci_hi=np.nan, note=f"p = {p_within:.4f} (naive)"),
    dict(quantity="r across the 13 site means (between-site)", value=r_sm, ci_lo=np.nan, ci_hi=np.nan, note=f"p = {p_sm:.4f}, n=13"),
])
sens.to_csv(OUT / "regional_nonindependence_sensitivity.csv", index=False, float_format="%.6f")
print(); print(sens.round(4).to_string(index=False))
log("")
log(f"independence: 445 pairs come from {len(dates)} sampling dates in {d.Date.dt.year.nunique()} years at 13 sites; "
    f"pairs per date: min {dm.n_sites.min()}, median {dm.n_sites.median()}, max {dm.n_sites.max()}")
(OUT / "regional_metrics_checks.txt").write_text("\n".join(chk))
