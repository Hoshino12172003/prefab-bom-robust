"""Plot discrete policy classes from the certified Phase 3.2P CSV."""
import csv
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
OUT = HERE/"figures"
COLORS = {"C_ONLY": "#d7e5f4", "T_ONLY": "#caeee7", "O_ONLY": "#fbe0c5",
          "C_T": "#ddd9f2", "C_O": "#f4d2d7", "T_O": "#f3e8bd",
          "C_T_O": "#e8d6ed", "ZERO_BUFFER": "#e9ecef"}
NAMES = {"R1": "Cell receipts", "R2": "Pack production", "R3": "Pack transport",
         "R4": "Gear transport", "R5": "Seat JIT", "R6": "Joint battery–gear–seat"}

mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8, "pdf.fonttype": 42,
    "axes.linewidth": 0.6, "xtick.major.size": 0, "ytick.major.size": 0,
    "figure.dpi": 120, "savefig.facecolor": "white",
})


def panel(ax, matrix, x_labels, y_labels):
    for y, row in enumerate(matrix):
        for x, r in enumerate(row):
            status = r["status"]
            cls = r["representative_class"]
            label = cls.replace("_ONLY", "").replace("_", "+") if cls != "ZERO_BUFFER" else "0"
            multiple = r["optimal_set_taxonomy"] == "MULTIPLE_OPTIMA"
            if status == "EXACT_FINITE":
                ax.add_patch(Rectangle((x, y), 1, 1, facecolor=COLORS[cls], edgecolor="white", linewidth=1.3))
                ax.text(x+0.5, y+0.5, label+("*" if multiple else ""), ha="center", va="center", color="#17283c")
            else:
                ax.add_patch(Rectangle((x, y), 1, 1, facecolor="white", edgecolor="#b5beca", linewidth=0.8, hatch="//"))
                ax.text(x+0.5, y+0.5, "—", ha="center", va="center", color="#17283c")
    ax.set(xlim=(0, len(x_labels)), ylim=(len(y_labels), 0))
    ax.set_xticks([i+0.5 for i in range(len(x_labels))], x_labels)
    ax.set_yticks([i+0.5 for i in range(len(y_labels))], y_labels)
    for spine in ax.spines.values():
        spine.set_color("#b5beca")


def export(fig, stem):
    fig.text(0.04, 0.059, "Cells show one representative optimum.  * = multiple optimal policies.",
             fontsize=7.5, color="#364556")
    fig.text(0.97, 0.059, "STRESS TEST ONLY", ha="right", fontsize=7.5, color="#364556")
    fig.text(0.04, 0.025, "C = cell kit   T = T1 pack   O = OEM pack   0 = zero protective buffer",
             fontsize=7.5, color="#364556")
    fig.savefig(OUT/f"{stem}.pdf")
    fig.savefig(OUT/f"{stem}.png", dpi=300)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    with (HERE/"buffer_policy_full_grid.csv").open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    budgets = (25, 50, 75, 100, 125, 150, 200)
    budget = {(r["risk"], int(r["budget_multiplier"])): r for r in rows if "LOCATION_BUDGET" in r["tags"]}
    fig, ax = plt.subplots(figsize=(7.16, 3.05))
    fig.subplots_adjust(left=0.26, right=0.98, bottom=0.22, top=0.86)
    panel(ax, [[budget[r, b] for b in budgets] for r in NAMES],
          [f"{b/100:.2f}" for b in budgets], list(NAMES.values()))
    ax.set_title("A  Budget and risk location", loc="left", fontweight="bold", pad=10)
    ax.set_xlabel(r"Budget multiplier $B/B_0$")
    export(fig, "map_A_budget_location")

    days, severities = (4, 7, 11), (25, 50, 75)
    stress = {(r["risk"], int(r["severity_pct"]), int(r["duration"])): r
              for r in rows if "SEVERITY_DURATION" in r["tags"]}
    fig, axes = plt.subplots(2, 3, figsize=(7.16, 4.3))
    fig.subplots_adjust(left=0.115, right=0.98, bottom=0.16, top=0.83, wspace=0.37, hspace=0.57)
    fig.text(0.115, 0.945, "B  Severity and duration at the reference budget", fontsize=9, fontweight="bold")
    for i, (ax, risk) in enumerate(zip(axes.flat, NAMES)):
        panel(ax, [[stress[risk, s, d] for d in days] for s in severities], days, severities)
        ax.set_title(f"({chr(97+i)}) {NAMES[risk]}", loc="left", pad=4)
        if i % 3:
            ax.set_yticklabels([])
    fig.text(0.56, 0.090, "Disruption duration (days)", ha="center", fontsize=8)
    fig.text(0.025, 0.48, "Disruption severity (%)", va="center", rotation=90, fontsize=8)
    export(fig, "map_B_severity_duration")

    levels = (80, 90, 100, 110, 120)
    cost = {(int(r["alpha_T_multiplier"]), int(r["alpha_O_multiplier"])): r
            for r in rows if "COST" in r["tags"].split("|")}
    fig, ax = plt.subplots(figsize=(7.16, 3.65))
    fig.subplots_adjust(left=0.18, right=0.95, bottom=0.19, top=0.86)
    panel(ax, [[cost[t, o] for t in levels] for o in levels],
          [f"{k/100:.2f}" for k in levels], [f"{k/100:.2f}" for k in levels])
    ax.set_title("C  Relative buffer cost sensitivity", loc="left", fontweight="bold", pad=10)
    ax.set_xlabel(r"T1-to-component cost ratio multiplier $\alpha_T/\alpha_T^0$")
    ax.set_ylabel(r"OEM-to-T1 ratio multiplier $\alpha_O/\alpha_O^0$")
    export(fig, "map_C_relative_costs")


if __name__ == "__main__":
    main()
