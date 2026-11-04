"""Make a report graph from a c2_live.py timeline CSV.

Usage (WSL, with the venv active):
    python simulation/c2_plot.py simulation/logs/c2_windy_timeline_XXXX.csv

It saves a PNG with the same name next to the CSV.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # no window needed, just save a file
import matplotlib.pyplot as plt
import pandas as pd

BLUE, ORANGE = "#2a78d6", "#eb6834"
TEXT, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BAND = ["#f3f2ee", "#ffffff"]  # alternating stage backgrounds


def stage_blocks(df):
    """Group consecutive rows with the same stage -> (start, end, stage, mode)."""
    block_id = (df["stage"] != df["stage"].shift()).cumsum()
    out = []
    for _, g in df.groupby(block_id):
        out.append((g["t"].iloc[0], g["t"].iloc[-1] + 1,
                    g["stage"].iloc[0], g["mode"].mode().iloc[0]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--duration", type=float, default=240,
                    help="timeline length in seconds; rows after it are dropped")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df["t"] = df["t_s"] - df["t_s"].iloc[0]          # start the clock at 0
    df = df[df["t"] < args.duration].copy()          # cut the extra hover rows
    blocks = stage_blocks(df)

    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED,
                         "axes.labelcolor": TEXT, "xtick.color": MUTED,
                         "ytick.color": MUTED})
    has_move = "side_pos_m" in df.columns          # CSV made with --move
    n = 4 if has_move else 3
    fig, axes = plt.subplots(n, 1, figsize=(10, 2.5 * n), sharex=True)

    panels = [
        (axes[0], [("wind_ms", "Wind speed", BLUE),
                   ("crosswind_ms", "Crosswind", ORANGE)], "m/s"),
        (axes[1], [("roll_deg", "Drone roll", BLUE)], "degrees"),
        (axes[2], [("tilt_deg", "Nozzle tilt (C2)", BLUE)], "degrees"),
    ]
    titles = ["Wind given to the drone (Gazebo)",
              "Drone reaction: roll angle",
              "C2 decision: nozzle tilt"]
    if has_move:
        panels.append((axes[3], [("offset_cmd_m", "C2 path offset (command)", ORANGE),
                                 ("side_pos_m", "Drone position (measured)", BLUE)],
                       "metres (+ = right)"))
        titles.append("C2 path offset: drone moves sideways")

    for (ax, series, unit), title in zip(panels, titles):
        for i, (s, e, stage, mode) in enumerate(blocks):
            ax.axvspan(s, e, color=BAND[i % 2], zorder=0, lw=0)
        for col, label, color in series:
            ax.plot(df["t"], df[col], color=color, lw=2, label=label, zorder=3)
        ax.set_ylabel(unit)
        ax.set_title(title, loc="left", color=TEXT, fontsize=11)
        ax.grid(axis="y", color=GRID, lw=0.8, zorder=1)
        ax.spines[["top", "right"]].set_visible(False)
        if len(series) > 1:
            ax.legend(loc="upper left", frameon=False)

    # stage name + C2 mode written above each band on the top panel
    for s, e, stage, mode in blocks:
        axes[0].text((s + e) / 2, 1.18, f"{stage}\n{mode}",
                     transform=axes[0].get_xaxis_transform(),
                     ha="center", va="bottom", color=MUTED, fontsize=9)

    axes[-1].set_xlabel("time since timeline start (s)")
    fig.suptitle("C2 wind handling in the simulator (PX4 + Gazebo)",
                 x=0.01, ha="left", color=TEXT, fontsize=13, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.97))

    out = args.csv.with_suffix(".png")
    fig.savefig(out, dpi=200)
    print(f"Saved graph: {out}  ({len(df)} rows used)")


if __name__ == "__main__":
    main()
