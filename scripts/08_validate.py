"""
Step 6: Compare model predictions against the user-supplied real in-lake
Secchi readings for Squam and Little Squam. Reports the honest correlation,
both for exact-date matches and for a +/-3-day tolerance match (since field
sampling and satellite passes rarely land on the same calendar day), and
compares against the national model's r = -0.22 baseline.

Output: output/validation_report.txt, output/validation_scatter.png
"""
import argparse

import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

PROJECT_DIR = Path(__file__).resolve().parents[1]
REAL_PATH = PROJECT_DIR / "data" / "raw" / "squam_real_secchi_validation.csv"

_parser = argparse.ArgumentParser()
_parser.add_argument("--heldout", action="store_true", help="Use the Squam-excluded model's predictions")
_args = _parser.parse_args()

if _args.heldout:
    PRED_PATH = PROJECT_DIR / "output" / "squam_predicted_secchi_1984_present_heldout.csv"
    REPORT_PATH = PROJECT_DIR / "output" / "validation_report_heldout.txt"
    PLOT_PATH = PROJECT_DIR / "output" / "validation_scatter_heldout.png"
else:
    PRED_PATH = PROJECT_DIR / "output" / "squam_predicted_secchi_1984_present.csv"
    REPORT_PATH = PROJECT_DIR / "output" / "validation_report.txt"
    PLOT_PATH = PROJECT_DIR / "output" / "validation_scatter.png"

LAKE_NAME_MAP = {"Little Squam": "Little Squam Lake", "Squam": "Squam Lake"}
TOLERANCE_DAYS = 3


def load_real():
    real = pd.read_csv(REAL_PATH)
    real["Lake"] = real["Lake"].map(LAKE_NAME_MAP)
    real["Date"] = pd.to_datetime(real["Date"])
    # Multiple readings per date (different sampling stations) -> average
    # to a single lake-wide value per date, matching the single-point
    # prediction's intent as a lake-representative estimate.
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
    real = load_real()
    pred = load_pred()

    print(f"Real readings (aggregated to lake-date): {len(real)}")
    print(f"Predictions available: {len(pred)}")
    print(real["Lake"].value_counts())
    print(f"Real date range: {real['Date'].min().date()} to {real['Date'].max().date()}")
    print(f"Prediction date range: {pred['Date'].min().date()} to {pred['Date'].max().date()}")

    exact = match_exact(real, pred)
    tol = match_tolerance(real, pred, TOLERANCE_DAYS)

    lines = []
    lines.append("=" * 70)
    lines.append("SQUAM / LITTLE SQUAM MODEL VALIDATION AGAINST REAL READINGS")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"National model (LAGOS-US LANDSAT) baseline at these lakes: r = -0.22, p = 0.26 (no real relationship)")
    lines.append("")
    lines.append("--- Exact date match ---")
    lines.append(report_stats(exact, "Exact-date matches"))
    for lake in ["Squam Lake", "Little Squam Lake"]:
        sub = exact[exact["Lake"] == lake]
        lines.append(report_stats(sub, f"  {lake} only"))

    lines.append(f"--- +/- {TOLERANCE_DAYS} day tolerance match ---")
    lines.append(report_stats(tol, f"Tolerance matches ({TOLERANCE_DAYS}d)"))
    for lake in ["Squam Lake", "Little Squam Lake"]:
        sub = tol[tol["Lake"] == lake]
        lines.append(report_stats(sub, f"  {lake} only"))

    report_text = "\n".join(lines)
    print("\n" + report_text)
    REPORT_PATH.write_text(report_text)

    suffix = "_heldout" if _args.heldout else ""
    exact.to_csv(PROJECT_DIR / "output" / f"matched_exact_date{suffix}.csv", index=False)
    tol.to_csv(PROJECT_DIR / "output" / f"matched_tolerance_3day{suffix}.csv", index=False)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 6))
        for lake, color in [("Squam Lake", "tab:blue"), ("Little Squam Lake", "tab:orange")]:
            sub = tol[tol["Lake"] == lake]
            ax.scatter(sub["real_secchi_m"], sub["predicted_secchi_m"], label=lake, alpha=0.6, color=color)
        lims = [0, max(tol["real_secchi_m"].max(), tol["predicted_secchi_m"].max()) + 1]
        ax.plot(lims, lims, "k--", alpha=0.5, label="1:1 line")
        ax.set_xlabel("Real Secchi depth (m)")
        ax.set_ylabel("Predicted Secchi depth (m)")
        ax.set_title(f"Model predictions vs. real readings ({TOLERANCE_DAYS}-day tolerance match)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(PLOT_PATH, dpi=150)
        print(f"\nSaved scatter plot to {PLOT_PATH}")
    except ImportError:
        print("\n(matplotlib not installed -- skipping scatter plot)")


if __name__ == "__main__":
    main()
