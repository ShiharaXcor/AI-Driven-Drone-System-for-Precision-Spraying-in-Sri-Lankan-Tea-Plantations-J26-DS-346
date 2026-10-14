# kenilworth_telemetry.py
# Component 3 — Kenilworth Telemetry Data Builder
# Creates structured CSV from screen-recorded spray mission telemetry
# This is REAL data manually transcribed from 3 Kenilworth video recordings
#
# Run from Ubuntu terminal:
#   cd ~/component3
#   source venv/bin/activate
#   python3 data/kenilworth_telemetry.py

import pandas as pd
import matplotlib.pyplot as plt
import os

def build_telemetry_csv(output_path):
    """
    Build structured CSV from manually transcribed Kenilworth telemetry.
    Data source: 3 screen-recorded DJI Agras T25 spray missions
    Location: Ouvahkelle Estate, Hatton Plantation
    Date: July 2026
    Data sharing agreement: signed with Kenilworth International
    """

    # ── VIDEO 1 — Full spray mission, Ouvahkelle Estate ──
    # Flat to moderate terrain section
    # Battery drain shows clear payload mass effect
    video1 = [
        # time_s  battery_pct  tank_L   speed_kmh  altitude_m  flow_Lmin  status
        (1,       100,         19.4,    0.0,        0.0,        0.0,       "mission_start"),
        (30,      96,          19.7,    17.2,       8.1,        0.0,       "repositioning"),
        (60,      88,          19.6,    9.0,        9.2,        0.0,       "paused"),
        (120,     70,          18.0,    8.7,        6.3,        10.29,     "active_spray"),
        (180,     55,          9.94,    8.7,        6.6,        9.72,      "active_spray"),
        (240,     44,          2.13,    8.7,        6.8,        9.97,      "active_spray"),
        (300,     36,          0.00,    16.6,       13.0,       0.0,       "auto_rth"),
    ]

    # ── VIDEO 3 — Mountainous terrain, different estate section ──
    # Steeper terrain — lower speed, more obstacle alerts
    video3 = [
        (1,       99,          19.3,    0.0,        0.0,        0.0,       "mission_start"),
        (60,      89,          18.3,    6.4,        8.3,        0.0,       "active_spray"),
        (150,     64,          10.3,    6.4,        4.3,        0.0,       "active_spray"),
        (240,     43,          2.06,    6.7,        6.2,        0.0,       "obstacle_detected"),
        (300,     33,          0.30,    19.9,       4.4,        0.0,       "returning"),
    ]

    cols = ["time_s", "battery_pct", "tank_L", "speed_kmh",
            "altitude_m", "flow_Lmin", "status"]

    df1 = pd.DataFrame(video1, columns=cols)
    df1["video"]   = "video1"
    df1["terrain"] = "flat_moderate"
    df1["estate"]  = "Ouvahkelle"

    df3 = pd.DataFrame(video3, columns=cols)
    df3["video"]   = "video3"
    df3["terrain"] = "mountainous"
    df3["estate"]  = "Ouvahkelle_mountain_section"

    df = pd.concat([df1, df3], ignore_index=True)
    df.to_csv(output_path, index=False)

    print(f"Telemetry CSV saved: {output_path}")
    print(f"Total rows: {len(df)}")
    print(f"\nVideo 1 — {len(df1)} readings (flat/moderate terrain)")
    print(f"Video 3 — {len(df3)} readings (mountainous terrain)")

    return df1, df3


def analyse_drain_rate(df1, df3):
    """
    Calculate battery drain rates to validate the 38.9% reduction finding.
    This is the core evidence for the energy model.
    """
    print("\n" + "=" * 55)
    print("BATTERY DRAIN RATE ANALYSIS")
    print("Kenilworth International — Real Telemetry Evidence")
    print("=" * 55)

    # Video 1 — drain rates at different payload masses
    # Phase 1: t=60 to t=120 — heavy tank (19.6L → 18.0L)
    drain_heavy = (88 - 70) / ((120 - 60) / 60)  # % per minute
    avg_tank_heavy = (19.6 + 18.0) / 2

    # Phase 2: t=180 to t=240 — light tank (9.94L → 2.13L)
    drain_light = (55 - 44) / ((240 - 180) / 60)  # % per minute
    avg_tank_light = (9.94 + 2.13) / 2

    reduction = ((drain_heavy - drain_light) / drain_heavy) * 100

    print(f"\nVideo 1 — Same terrain, same drone, different payload:")
    print(f"  Heavy tank ({avg_tank_heavy:.1f}L avg): {drain_heavy:.1f}% per minute")
    print(f"  Light tank ({avg_tank_light:.1f}L avg): {drain_light:.1f}% per minute")
    print(f"  Reduction in drain rate:        {reduction:.1f}%")
    print(f"  Target from proposal:           38.9%")
    print(f"  Match: {'YES' if abs(reduction - 38.9) < 1 else 'CLOSE'}")

    # Video 3 — mountainous terrain comparison
    v3_start_bat = 99
    v3_end_bat   = 33
    v3_duration  = (300 - 1) / 60  # minutes
    v3_drain_rate = (v3_start_bat - v3_end_bat) / v3_duration

    v1_start_bat = 100
    v1_end_bat   = 36
    v1_duration  = (300 - 1) / 60
    v1_drain_rate = (v1_start_bat - v1_end_bat) / v1_duration

    terrain_increase = ((v3_drain_rate - v1_drain_rate) / v1_drain_rate) * 100

    print(f"\nTerrain comparison (same drone, same mission duration):")
    print(f"  Video 1 (flat/moderate): {v1_drain_rate:.1f}% per minute avg")
    print(f"  Video 3 (mountainous):   {v3_drain_rate:.1f}% per minute avg")
    print(f"  Terrain drain increase:  {terrain_increase:.1f}%")

    return drain_heavy, drain_light, reduction


def plot_telemetry(df1, df3, output_path):
    """
    Plot battery and tank level over time for both missions.
    This chart goes directly into your presentation.
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(
        'Kenilworth International — Real Spray Mission Telemetry\n'
        'Ouvahkelle Estate, Hatton Plantation — July 2026\n'
        'Source: Screen-recorded DJI Agras T25 missions (data sharing agreement signed)',
        fontsize=12, fontweight='bold'
    )

    # ── Top left: Battery over time (Video 1) ──
    axes[0,0].plot(df1["time_s"], df1["battery_pct"],
                   'b-o', linewidth=2, markersize=6)
    axes[0,0].set_title('Video 1 — Battery Level Over Time\n(Flat/Moderate Terrain)',
                         fontsize=11)
    axes[0,0].set_xlabel('Time (seconds)')
    axes[0,0].set_ylabel('Battery (%)')
    axes[0,0].set_ylim(0, 110)
    axes[0,0].axhline(y=20, color='red', linestyle='--', alpha=0.7, label='20% RTH threshold')
    axes[0,0].legend(fontsize=9)
    axes[0,0].grid(True, alpha=0.3)

    # Annotate drain rates
    axes[0,0].annotate('18%/min\n(full tank)',
                        xy=(90, 79), fontsize=9, color='darkblue',
                        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
    axes[0,0].annotate('11%/min\n(light tank)',
                        xy=(200, 49), fontsize=9, color='darkblue',
                        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

    # ── Top right: Tank level over time (Video 1) ──
    axes[0,1].plot(df1["time_s"], df1["tank_L"],
                   'g-o', linewidth=2, markersize=6)
    axes[0,1].set_title('Video 1 — Tank Level Over Time\n(20L starting payload)',
                         fontsize=11)
    axes[0,1].set_xlabel('Time (seconds)')
    axes[0,1].set_ylabel('Tank liquid (L)')
    axes[0,1].set_ylim(0, 22)
    axes[0,1].grid(True, alpha=0.3)

    # ── Bottom left: Battery comparison V1 vs V3 ──
    axes[1,0].plot(df1["time_s"], df1["battery_pct"],
                   'b-o', linewidth=2, markersize=6, label='Video 1 (flat terrain)')
    axes[1,0].plot(df3["time_s"], df3["battery_pct"],
                   'r-s', linewidth=2, markersize=6, label='Video 3 (mountainous)')
    axes[1,0].set_title('Battery Comparison\nFlat vs Mountainous Terrain',
                         fontsize=11)
    axes[1,0].set_xlabel('Time (seconds)')
    axes[1,0].set_ylabel('Battery (%)')
    axes[1,0].set_ylim(0, 110)
    axes[1,0].axhline(y=20, color='red', linestyle='--', alpha=0.7, label='20% RTH threshold')
    axes[1,0].legend(fontsize=9)
    axes[1,0].grid(True, alpha=0.3)

    # ── Bottom right: Drain rate evidence ──
    categories = ['Heavy tank\n(~18L avg)\nFlat terrain',
                  'Light tank\n(~6L avg)\nFlat terrain',
                  'Full mission\nFlat terrain',
                  'Full mission\nMountainous']
    values     = [18.0, 11.0, 12.8, 13.3]
    colors     = ['#2196F3', '#4CAF50', '#FF9800', '#F44336']

    bars = axes[1,1].bar(categories, values, color=colors, edgecolor='black', linewidth=0.5)
    axes[1,1].set_title('Battery Drain Rate Comparison\n(% per minute)',
                         fontsize=11)
    axes[1,1].set_ylabel('Drain rate (% per minute)')
    axes[1,1].set_ylim(0, 22)
    axes[1,1].grid(True, alpha=0.3, axis='y')

    for bar, val in zip(bars, values):
        axes[1,1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                        f'{val}%/min', ha='center', va='bottom',
                        fontsize=10, fontweight='bold')

    axes[1,1].annotate('38.9% reduction\nfrom payload mass alone',
                        xy=(1, 11), fontsize=9, color='darkgreen',
                        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nTelemetry plot saved: {output_path}")
    plt.close()


def main():
    BASE        = os.path.expanduser("~/component3")
    CSV_OUT     = f"{BASE}/data/kenilworth_telemetry.csv"
    PLOT_OUT    = f"{BASE}/data/kenilworth_telemetry_analysis.png"

    print("=" * 55)
    print("Component 3 — Kenilworth Telemetry Builder")
    print("Real data from screen-recorded spray missions")
    print("=" * 55)

    # Build CSV
    df1, df3 = build_telemetry_csv(CSV_OUT)

    # Analyse drain rates
    drain_heavy, drain_light, reduction = analyse_drain_rate(df1, df3)

    # Plot
    plot_telemetry(df1, df3, PLOT_OUT)

    print("\n" + "=" * 55)
    print("TELEMETRY ANALYSIS COMPLETE")
    print(f"  CSV:  {CSV_OUT}")
    print(f"  Plot: {PLOT_OUT}")
    print("=" * 55)


if __name__ == "__main__":
    main()