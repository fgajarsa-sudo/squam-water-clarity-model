"""
Step 6 (rerun): Same validation as 08_validate.py, but for Squam Lake only
uses readings from the "Deep Haven" monitoring site (from the per-site
file), instead of averaging across all of Squam's many bays/stations.
Little Squam's comparison is unchanged from the original run (still uses
the lake-wide average, since no site filter was requested for it).

Output: output/validation_report_deephaven.txt, output/validation_scatter_deephaven.png
"""
import argparse

import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

PROJECT_DIR = Path(__file__).resolve().parents[1]
BYSITE_PATH = PROJECT_DIR / "data" / "raw" / "squam_real_secchi_validation_bysite.csv"
ORIGINAL_REAL_PATH = PROJECT_DIR / "data" / "raw" / "squam_real_secchi_validation.csv"

_parser = argparse.ArgumentParser()
_parser.add_argument("--heldout", action="store_true", help="Use the Squam-excluded model's predictions")
_args = _parser.parse_args()

if _args.heldout:
    PRED_PATH = PROJECT_DIR / "output" / "squam_predicted_secchi_1984_present_heldout.csv"
    REPORT_PATH = PROJECT_DIR / "output" / "validation_report_deephaven_heldout.txt"
    PLOT_PATH = PROJECT_DIR / "output" / "validation_scatter_deephaven_heldout.png"
else:
    PRED_PATH = PROJECT_DIR / "output" / "squam_predicted_secchi_1984_present.csv"
    REPORT_PATH = PROJECT_DIR / "output" / "validation_report_deephaven.txt"
    PLOT_PATH = PROJECT_DIR / "output" / "validation_scatter_deephaven.png"

TOLERANCE_DAYS = 3
SITE_FILTER = "Deep Haven"


def load_squam_deephaven():
    df = pd.read_csv(BYSITE_PATH)
    df = df[(df["Lake"] == "Squam") & (df["Site"] == SITE_FILTER)].copy()
    df["Lake"] = "Squam Lake"
    df["Date"] = pd.to_datetime(df["Date"])
    agg = df.groupby(["Lake", "Date"]).agg(
        real_secchi_m=("Secchi", "mean"), n_stations=("Secchi", "count")
    ).reset_index()
    return agg


def load_little_squam_original():
    real = pd.read_csv(ORIGINAL_REAL_PATH)
    real = real[real["Lake"] == "Little Squam"].copy()
    real["Lake"] = "Little Squam Lake"
    real["Date"] = pd.to_datetime(real["Date"])
    agg = real.groupby(["Lake", "Date"]).agg(
        real_secchi_m=("Secchi", "mean"), n_stations=("Secchi", "count")
    ).reset_index()
    return agg


def load_pred():
    pred = pd.read_csv(PRED_PATH)
    pred["Date"] = pd.to_datetime(pred["date"])
    return pred.rename(columns={"lake": "Lake"})[["Lake", "Date", "predicted_secchi_m"]]


def match_exact(real, pred):
    return real.merge(pred, on=["Lake", "Date"], how="inner")


def match_tolerance(real, pred, days):
    results = []
    for lake in real["Lake"].unique():
        r = real[real["Lake"] == lake].sort_values("Date")
        p = pred[pred["Lake"] == lake].sort_values("Date")
        m = pd.merge_asof(
            r, p, on="Date", direction="nearest",
            tolerance=pd.Timedelta(days=days),
        )
        m["Lake"] = lake
        results.append(m)
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
    squam_dh = load_squam_deephaven()
    little_squam = load_little_squam_original()
    real = pd.concat([squam_dh, little_squam], ignore_index=True)
    pred = load_pred()

    print(f"Squam Lake ('{SITE_FILTER}' site only): {len(squam_dh)} dated readings")
    print(f"Little Squam Lake (lake-wide average, unchanged): {len(little_squam)} dated readings")
    print(f"Squam/{SITE_FILTER} date range: {squam_dh['Date'].min().date()} to {squam_dh['Date'].max().date()}")

    exact = match_exact(real, pred)
    tol = match_tolerance(real, pred, TOLERANCE_DAYS)

    lines = []
    lines.append("=" * 70)
    lines.append(f"SQUAM (site='{SITE_FILTER}' only) / LITTLE SQUAM (lake-wide, unchanged)")
    lines.append("VALIDATION AGAINST REAL READINGS")
    lines.append("=" * 70)
    lines.append("")
    lines.append("National model (LAGOS-US LANDSAT) baseline at these lakes: r = -0.22, p = 0.26")
    lines.append("Previous run (Squam = full lake-wide average): Squam-only r ranged -0.16 to 0.18, not significant")
    lines.append("")
    lines.append("--- Exact date match ---")
    lines.append(report_stats(exact, "All (Squam/Deep Haven + Little Squam)"))
    for lake in ["Squam Lake", "Little Squam Lake"]:
        sub = exact[exact["Lake"] == lake]
        tag = f" [{SITE_FILTER} only]" if lake == "Squam Lake" else " [lake-wide, unchanged]"
        lines.append(report_stats(sub, f"  {lake}{tag}"))

    lines.append(f"--- +/- {TOLERANCE_DAYS} day tolerance match ---")
    lines.append(report_stats(tol, f"All, tolerance ({TOLERANCE_DAYS}d)"))
    for lake in ["Squam Lake", "Little Squam Lake"]:
        sub = tol[tol["Lake"] == lake]
        tag = f" [{SITE_FILTER} only]" if lake == "Squam Lake" else " [lake-wide, unchanged]"
        lines.append(report_stats(sub, f"  {lake}{tag}"))

    report_text = "\n".join(lines)
    print("\n" + report_text)
    REPORT_PATH.write_text(report_text)

    suffix = "_heldout" if _args.heldout else ""
    exact.to_csv(PROJECT_DIR / "output" / f"matched_exact_date_deephaven{suffix}.csv", index=False)
    tol.to_csv(PROJECT_DIR / "output" / f"matched_tolerance_3day_deephaven{suffix}.csv", index=False)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 6))
        for lake, color in [("Squam Lake", "tab:blue"), ("Little Squam Lake", "tab:orange")]:
            sub = tol[tol["Lake"] == lake]
            label = f"{lake} (Deep Haven)" if lake == "Squam Lake" else lake
            ax.scatter(sub["real_secchi_m"], sub["predicted_secchi_m"], label=label, alpha=0.6, color=color)
        lims = [0, max(tol["real_secchi_m"].max(), tol["predicted_secchi_m"].max()) + 1]
        ax.plot(lims, lims, "k--", alpha=0.5, label="1:1 line")
        ax.set_xlabel("Real Secchi depth (m)")
        ax.set_ylabel("Predicted Secchi depth (m)")
        ax.set_title(f"Predictions vs. real readings (Squam=Deep Haven only, {TOLERANCE_DAYS}-day tolerance)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(PLOT_PATH, dpi=150)
        print(f"\nSaved scatter plot to {PLOT_PATH}")
    except ImportError:
        print("\n(matplotlib not installed -- skipping scatter plot)")


if __name__ == "__main__":
    main()
