"""
Step 6 (per-site rerun): match each real Secchi reading to the prediction
from its OWN monitoring site, using the Site column in the per-site
validation file, instead of comparing every reading to one lake-wide
prediction. Uses the multi-point predictions from 11_predict_multipoint.py
(Squam-excluded/"heldout" model).

Real-data sites without a matching coordinate (not in the 13-site list)
are reported separately as unmatched, not silently dropped or fuzzy-matched.

Output: output/validation_report_multipoint.txt, output/validation_scatter_multipoint.png
"""
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

PROJECT_DIR = Path(__file__).resolve().parents[1]
BYSITE_PATH = PROJECT_DIR / "data" / "raw" / "squam_real_secchi_validation_bysite.csv"
PRED_PATH = PROJECT_DIR / "output" / "squam_predicted_secchi_multipoint.csv"
REPORT_PATH = PROJECT_DIR / "output" / "validation_report_multipoint.txt"
PLOT_PATH = PROJECT_DIR / "output" / "validation_scatter_multipoint.png"

TOLERANCE_DAYS = 3


def load_real():
    real = pd.read_csv(BYSITE_PATH)
    real["Date"] = pd.to_datetime(real["Date"])
    agg = real.groupby(["Lake", "Site", "Date"]).agg(
        real_secchi_m=("Secchi", "mean"), n_readings=("Secchi", "count")
    ).reset_index()
    return agg


def load_pred():
    pred = pd.read_csv(PRED_PATH)
    pred["Date"] = pd.to_datetime(pred["date"])
    return pred[["site", "Date", "predicted_secchi_m"]]


def match_exact(real, pred):
    return real.merge(pred, left_on=["Site", "Date"], right_on=["site", "Date"], how="inner")


def match_tolerance(real, pred, days):
    results = []
    for site in real["Site"].unique():
        r = real[real["Site"] == site].sort_values("Date")
        p = pred[pred["site"] == site].sort_values("Date")
        if p.empty:
            continue
        m = pd.merge_asof(
            r, p, on="Date", direction="nearest",
            tolerance=pd.Timedelta(days=days),
        )
        results.append(m)
    if not results:
        return pd.DataFrame(columns=list(real.columns) + ["site", "predicted_secchi_m"])
    combined = pd.concat(results, ignore_index=True)
    return combined.dropna(subset=["predicted_secchi_m"])


def report_stats(df, label, value_col="real_secchi_m"):
    x = df[value_col].values
    y = df["predicted_secchi_m"].values
    if len(x) < 3:
        return f"{label}: only {len(x)} matched pairs -- not enough to compute a meaningful correlation\n"
    r, p = stats.pearsonr(x, y)
    r2 = r ** 2
    mae = np.mean(np.abs(x - y))
    rmse = np.sqrt(np.mean((x - y) ** 2))
    return (
        f"{label}: n={len(x)}\n"
        f"  Pearson r = {r:.3f} (p={p:.4f})\n"
        f"  R^2       = {r2:.3f}\n"
        f"  MAE       = {mae:.3f} m\n"
        f"  RMSE      = {rmse:.3f} m\n"
    )


def main():
    real = load_real()
    pred = load_pred()

    real_sites = set(real["Site"].unique())
    pred_sites = set(pred["site"].unique())
    unmatched_sites = real_sites - pred_sites

    print(f"Real dated site-readings: {len(real)}")
    print(f"Real-data sites: {len(real_sites)}, sites with a coordinate/prediction: {len(real_sites & pred_sites)}")
    print(f"Real-data sites with NO coordinate provided (excluded from this comparison): {sorted(unmatched_sites)}")

    exact = match_exact(real, pred)
    tol = match_tolerance(real, pred, TOLERANCE_DAYS)

    lines = []
    lines.append("=" * 70)
    lines.append("PER-SITE VALIDATION: EACH READING MATCHED TO ITS OWN MONITORING SITE")
    lines.append("=" * 70)
    lines.append("")
    lines.append("National model (LAGOS-US LANDSAT) baseline at these lakes: r = -0.22, p = 0.26")
    lines.append(f"Real-data sites with no coordinate provided, excluded here: {sorted(unmatched_sites)}")
    lines.append("")
    lines.append("--- Exact date match, all sites pooled ---")
    lines.append(report_stats(exact, "All sites"))

    lines.append(f"--- +/- {TOLERANCE_DAYS} day tolerance match, all sites pooled ---")
    lines.append(report_stats(tol, f"All sites, tolerance ({TOLERANCE_DAYS}d)"))

    lines.append("--- Per-site breakdown (tolerance match) ---")
    for site in sorted(tol["Site"].unique()):
        sub = tol[tol["Site"] == site]
        lines.append(report_stats(sub, f"  {site}"))

    report_text = "\n".join(lines)
    print("\n" + report_text)
    REPORT_PATH.write_text(report_text)

    exact.to_csv(PROJECT_DIR / "output" / "matched_exact_date_multipoint.csv", index=False)
    tol.to_csv(PROJECT_DIR / "output" / "matched_tolerance_3day_multipoint.csv", index=False)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 7))
        sites = sorted(tol["Site"].unique())
        cmap = matplotlib.colormaps.get_cmap("tab20").resampled(len(sites))
        for i, site in enumerate(sites):
            sub = tol[tol["Site"] == site]
            ax.scatter(sub["real_secchi_m"], sub["predicted_secchi_m"], label=site, alpha=0.7, color=cmap(i))
        lims = [0, max(tol["real_secchi_m"].max(), tol["predicted_secchi_m"].max()) + 1]
        ax.plot(lims, lims, "k--", alpha=0.5, label="1:1 line")
        ax.set_xlabel("Real Secchi depth (m)")
        ax.set_ylabel("Predicted Secchi depth (m)")
        ax.set_title(f"Per-site predictions vs. real readings ({TOLERANCE_DAYS}-day tolerance)")
        ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1))
        fig.tight_layout()
        fig.savefig(PLOT_PATH, dpi=150)
        print(f"\nSaved scatter plot to {PLOT_PATH}")
    except ImportError:
        print("\n(matplotlib not installed -- skipping scatter plot)")


if __name__ == "__main__":
    main()
