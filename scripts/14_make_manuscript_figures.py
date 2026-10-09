#!/usr/bin/env python3
"""Step 14: manuscript Figures 1 and 2 for the Squam Lake loon / water clarity paper.

Both figures are drawn from ONE file: output/matched_tolerance_3day_multipoint.csv in the
squam-water-clarity-model repository (real Secchi readings matched, within +/- 3 days, to the
regional model's prediction for the same monitoring site; 445 pairs at 13 sites; the model was
trained with all Squam-area data excluded).  This is the same data behind Table 3 of the paper.

  Figure 1  all 445 pairs pooled          -> n = 445, r = 0.264, p < 0.0001   (matches the text and Table 3)
  Figure 2  one panel per site (the 12 sites with >= 20 matched readings, ordered by RMSE)
                                          -> n, RMSE and r per site           (matches the text and Table 3)
            The 13th site (Kent Island) has only 2 matched readings; it is in Figure 1 but not shown in Figure 2.

Nothing is hard-coded: every number printed on the figures is computed from the CSV, and the
script stops if any of them differs from the value reported in the paper.

Usage:  python3 scripts/14_make_manuscript_figures.py        (run after 12_validate_multipoint.py)
Output: output/manuscript_figure_1.png (4.5 x 4.5 in) and output/manuscript_figure_2.png (6.5 x 6.1 in), 300 dpi.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy import stats

PROJECT_DIR = Path(__file__).resolve().parents[1]
CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_DIR / "output" / "matched_tolerance_3day_multipoint.csv"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else PROJECT_DIR / "output"
OUT.mkdir(parents=True, exist_ok=True)

DPI = 300
INK = "#222222"        # text / axes
GRID = "#D9D9D9"       # recessive grid
POINT = "#1F5FA8"      # one hue: every point in both figures is the same kind of thing
REF = "#7A7A7A"        # 1:1 reference line
LIM = (0, 12)
TICKS = [0, 4, 8, 12]

plt.rcParams.update({
    "font.family": "Liberation Serif",   # metric-compatible with Times New Roman (the manuscript font)
    "font.size": 10,
    "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK,
    "axes.linewidth": 0.8,
    "savefig.dpi": DPI,
})

d = pd.read_csv(CSV)
x_all, y_all = d["real_secchi_m"].to_numpy(), d["predicted_secchi_m"].to_numpy()

# ----------------------------------------------------------------------------- numbers used in the paper
r_all, p_all = stats.pearsonr(x_all, y_all)
assert len(d) == 445, len(d)
assert round(r_all, 3) == 0.264 and p_all < 0.0001 and round(r_all ** 2, 2) == 0.07, (r_all, p_all)
assert d["Site"].nunique() == 13

rows = []
for site, g in d.groupby("Site"):
    x, y = g["real_secchi_m"].to_numpy(), g["predicted_secchi_m"].to_numpy()
    rmse = float(np.sqrt(np.mean((x - y) ** 2)))
    if len(g) >= 3:
        r, p = stats.pearsonr(x, y)
    else:
        r, p = np.nan, np.nan
    rows.append(dict(site=site, n=len(g), rmse=rmse, r=r, p=p, x=x, y=y))
sites = pd.DataFrame(rows)
big = sites[sites["n"] >= 20]
# the paper's per-site statements
assert len(big) == 12
assert sites.loc[sites["n"] < 20, "n"].tolist() == [2]
by_rmse = big.sort_values("rmse")
assert by_rmse["rmse"].iloc[:6].between(1.31, 1.89).all(), by_rmse["rmse"].iloc[:6].tolist()      # six coves 1.3-1.9 m
assert by_rmse["rmse"].iloc[-2:].between(3.0, 3.2).all(), by_rmse["rmse"].iloc[-2:].tolist()      # two largest 3.0-3.2 m
sig = big[big["p"] < 0.05]
assert len(sig) == 1 and sig["site"].iloc[0] == "5 Livermore Cove" and round(sig["r"].iloc[0], 3) == 0.463


def style(ax, grid=True):
    ax.set_xlim(*LIM)
    ax.set_ylim(*LIM)
    ax.set_xticks(TICKS)
    ax.set_yticks(TICKS)
    ax.set_aspect("equal", adjustable="box")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if grid:
        ax.grid(True, color=GRID, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)


# ----------------------------------------------------------------------------- Figure 1: pooled
fig, ax = plt.subplots(figsize=(4.5, 4.5))
style(ax)
ax.plot(LIM, LIM, linestyle="--", color=REF, linewidth=1.0, zorder=1)
ax.scatter(x_all, y_all, s=16, color=POINT, alpha=0.55, linewidths=0, zorder=2)
ax.set_xlabel("Real Secchi depth (m)", fontsize=11)
ax.set_ylabel("Predicted Secchi depth (m)", fontsize=11)
ax.tick_params(labelsize=10)
ax.legend(handles=[Line2D([0], [0], linestyle="--", color=REF, linewidth=1.0, label="1:1 line")],
          loc="lower right", frameon=False, fontsize=10)
ax.text(0.5, 11.5, "n = 445\nr = 0.264, p < 0.0001", ha="left", va="top", fontsize=10)
fig.tight_layout()
fig.savefig(OUT / "manuscript_figure_1.png", dpi=DPI, facecolor="white")
plt.close(fig)

# ----------------------------------------------------------------------------- Figure 2: one panel per site
order = list(by_rmse["site"])                      # 12 sites with >= 20 matched readings, lowest -> highest RMSE
ncol, nrow = 4, 3
W, H = 6.5, 6.1                                    # figure size, inches
P = 1.22                                           # panel side, inches
LEFT, GAP = 0.60, (6.5 - 0.60 - 0.08 - 4 * 1.22) / 3
TOP_ZONE, BOT_ZONE = 0.48, 0.22                    # space for title + stats above a panel, tick labels below
fig = plt.figure(figsize=(W, H))
for k, name in enumerate(order):
    row, col = divmod(k, ncol)
    x0 = LEFT + col * (P + GAP)
    y0 = H - 0.04 - (row + 1) * (TOP_ZONE + P + BOT_ZONE) + BOT_ZONE
    ax = fig.add_axes([x0 / W, y0 / H, P / W, P / H])
    style(ax)
    ax.tick_params(labelsize=7.5, length=2.5)
    s = sites[sites["site"] == name].iloc[0]
    ax.plot(LIM, LIM, linestyle="--", color=REF, linewidth=0.8, zorder=1)
    ax.scatter(s["x"], s["y"], s=9, color=POINT, alpha=0.6, linewidths=0, zorder=2)
    star = "*" if s["p"] < 0.05 else ""
    ax.text(0.0, 1 + 0.33 / P, name, transform=ax.transAxes, fontsize=8.5, fontweight="bold", ha="left", va="bottom")
    ax.text(0.0, 1 + 0.03 / P, "n = %d, RMSE = %.2f m\nr = %.2f%s" % (s["n"], s["rmse"], s["r"], star),
            transform=ax.transAxes, fontsize=7.5, ha="left", va="bottom", linespacing=1.15)
fig.text((LEFT + (4 * P + 3 * GAP) / 2) / W, 0.08 / H, "Real Secchi depth (m)", ha="center", va="bottom", fontsize=10)
fig.text(0.14 / W, (H - 0.04 - (TOP_ZONE + 3 * (P + TOP_ZONE + BOT_ZONE)) / 2 + 0.2) / H, "Predicted Secchi depth (m)",
         rotation=90, ha="left", va="center", fontsize=10)
fig.savefig(OUT / "manuscript_figure_2.png", dpi=DPI, facecolor="white")
plt.close(fig)

# ----------------------------------------------------------------------------- printout for the audit trail
print("Figure 1: n = %d, r = %.4f, p = %.2e, r2 = %.4f" % (len(d), r_all, p_all, r_all ** 2))
print(sites.drop(columns=["x", "y"]).assign(order=lambda t: t["site"].map({s: i for i, s in enumerate(order)}))
      .sort_values("order").to_string(index=False, float_format=lambda v: "%.3f" % v))
print("wrote", OUT / "manuscript_figure_1.png", OUT / "manuscript_figure_2.png")
