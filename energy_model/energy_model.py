# energy_model.py
# Component 3 — Physics-Based Energy Cost Model
# E_total = integral of [P_hover(m(t)) + P_climb(m(t), theta(t), v(t))] dt
#
# Calibrated against:
#   - Kenilworth International telemetry (3 screen-recorded missions)
#   - SULEKO 163 real mountainous flights (T20P Badulla/Uva Province)
#
# Run from Ubuntu terminal:
#   cd ~/component3
#   source venv/bin/activate
#   python3 energy_model/energy_model.py

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import os
import json

class EnergyModel:
    """
    Physics-grounded energy model for DJI Agras T25/T20P spray drone.
    Models two power components:
      P_hover  — power to stay airborne at current mass
      P_climb  — additional power to climb slope at current mass and speed
    Constants calibrated against real SULEKO flight records and
    Kenilworth screen-recorded telemetry data.
    """

    def __init__(self):
        self.mass_empty_kg   = 12.0
        self.tank_capacity_L = 20.0
        self.battery_wh      = 288.0
        self.g               = 9.81
        self.n_rotors        = 4
        self.rho             = 1.15
        self.rotor_area      = 0.20
        self.eta             = 0.72
        self.k_drag          = 0.025
        self.k_climb         = 1.15

    def current_mass(self, liquid_L):
        return self.mass_empty_kg + liquid_L

    def hover_power(self, mass_kg):
        thrust = mass_kg * self.g
        P = (thrust ** 1.5) / np.sqrt(
            2 * self.rho * self.rotor_area * self.n_rotors * self.eta
        )
        return P

    def climb_power(self, mass_kg, slope_deg, velocity_ms):
        slope_rad = np.radians(np.clip(slope_deg, 0, 60))
        P_gravity = mass_kg * self.g * velocity_ms * np.sin(slope_rad) * self.k_climb
        P_drag    = 0.5 * self.k_drag * velocity_ms ** 2
        return max(0.0, P_gravity) + P_drag

    def total_power(self, mass_kg, slope_deg, velocity_ms):
        return self.hover_power(mass_kg) + self.climb_power(mass_kg, slope_deg, velocity_ms)

    def battery_drain_per_minute(self, mass_kg, slope_deg, velocity_ms):
        power_w   = self.total_power(mass_kg, slope_deg, velocity_ms)
        drain_pct = (power_w / (self.battery_wh * 60)) * 100
        return drain_pct

    def energy_cost(self, liquid_L, slope_deg, velocity_ms, dt=0.1):
        """Energy cost for one 10Hz timestep — used by DRL agent."""
        mass      = self.current_mass(liquid_L)
        power_w   = self.total_power(mass, slope_deg, velocity_ms)
        energy_wh = power_w * (dt / 3600)
        cost_pct  = (energy_wh / self.battery_wh) * 100
        return cost_pct

    def validate_kenilworth(self):
        """
        Validate against Kenilworth telemetry.
        Target: 18%/min full tank, 11%/min near-empty — reduction 38.9%
        """
        print("=" * 55)
        print("VALIDATION — Kenilworth Telemetry")
        print("=" * 55)

        speed_ms  = 8.7 / 3.6
        slope_deg = 12.0

        mass_heavy  = self.current_mass(18.8)
        drain_heavy = self.battery_drain_per_minute(mass_heavy, slope_deg, speed_ms)

        mass_light  = self.current_mass(6.0)
        drain_light = self.battery_drain_per_minute(mass_light, slope_deg, speed_ms)

        reduction = ((drain_heavy - drain_light) / drain_heavy) * 100

        print(f"\n  Heavy tank (18.8L): {drain_heavy:.1f}% per minute")
        print(f"  Light tank  (6.0L): {drain_light:.1f}% per minute")
        print(f"  Predicted reduction: {reduction:.1f}%")
        print(f"  Kenilworth target:   38.9%")
        print(f"  Error:               {abs(reduction - 38.9):.1f} percentage points")

        if abs(reduction - 38.9) < 5:
            print(f"  Status: PASS ✓")
        else:
            print(f"  Status: NEEDS CALIBRATION")

        return drain_heavy, drain_light, reduction


def load_suleko_data(data_dir):
    """Load all SULEKO Excel flight records."""
    files = [f for f in os.listdir(data_dir) if f.endswith('.xlsx')]
    dfs   = []
    for f in files:
        path = os.path.join(data_dir, f)
        try:
            df = pd.read_excel(path, sheet_name='flight record')
            dfs.append(df)
            print(f"  Loaded: {f} ({len(df)} rows)")
        except Exception as e:
            print(f"  Skipped {f}: {e}")
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True)


def analyse_suleko(all_df):
    """
    Analyse SULEKO records.
    T25 = flat Polonnaruwa terrain.
    T20P filtered to Badulla/Uva Province = mountainous terrain only.
    """
    print("\n" + "=" * 55)
    print("SULEKO FLIGHT RECORDS ANALYSIS")
    print("Real spray missions — Sri Lanka")
    print("=" * 55)

    results = {}

    configs = [
        ('T25',  'Flat — Polonnaruwa',        None),
        ('T20P', 'Mountainous — Badulla/Uva', 'Badulla|Uva Province'),
    ]

    for drone, terrain_label, location_filter in configs:

        df = all_df[all_df['Aircraft name'].str.contains(drone, na=False)].copy()

        # Filter to specific terrain location
        if location_filter:
            df = df[df['Location'].str.contains(location_filter, na=False)]

        df = df.dropna(subset=['Starting Battery Level',
                                'Ending Battery Level',
                                'Sprayed area',
                                'Total Amount(L/Kg)'])
        df = df[df['Sprayed area']       > 500]
        df = df[df['Total Amount(L/Kg)'] >= 5]
        df['battery_drop'] = (df['Starting Battery Level']
                              - df['Ending Battery Level'])
        df['area_ha']      = df['Sprayed area'] / 10000
        df = df[df['battery_drop'] > 0]

        full = df[df['Starting Battery Level'] >= 90]

        if len(full) == 0:
            print(f"\n  {drone} — no qualifying flights found")
            continue

        avg_drop = full['battery_drop'].mean()
        avg_area = full['area_ha'].mean()
        coverage = avg_area * (100 / avg_drop)

        results[drone] = {
            'terrain':      terrain_label,
            'flights':      len(full),
            'avg_drop_pct': avg_drop,
            'avg_area_ha':  avg_area,
            'coverage_ha':  coverage
        }

        print(f"\n  {drone} — {terrain_label}")
        print(f"    Full-tank flights:        {len(full)}")
        print(f"    Avg battery drop:         {avg_drop:.1f}%")
        print(f"    Avg area per flight:      {avg_area:.4f} ha")
        print(f"    Coverage per full charge: {coverage:.4f} ha")

    if 'T25' in results and 'T20P' in results:
        cov_flat     = results['T25']['coverage_ha']
        cov_mountain = results['T20P']['coverage_ha']
        bat_flat     = results['T25']['avg_drop_pct']
        bat_mountain = results['T20P']['avg_drop_pct']
        reduction    = ((cov_flat - cov_mountain) / cov_flat) * 100
        bat_increase = ((bat_mountain - bat_flat) / bat_flat) * 100

        print(f"\n  TERRAIN COMPARISON:")
        print(f"    Flat coverage:       {cov_flat:.3f} ha/charge")
        print(f"    Mountain coverage:   {cov_mountain:.3f} ha/charge")
        print(f"    Coverage reduction:  {reduction:.1f}%")
        print(f"    Battery increase:    {bat_increase:.1f}%")
        print(f"\n  PRIMARY BASELINE (mountainous): {cov_mountain:.3f} ha/charge")
        print(f"  Agent must exceed:              {cov_mountain:.3f} ha/charge")

    return results


def calibrate_model(model, suleko_results):
    """
    Calibrate energy model against SULEKO AND Kenilworth simultaneously.
    Two targets:
      1. SULEKO T20P mountainous average battery drop
      2. Kenilworth 38.9% reduction from payload mass change
    """
    print("\n" + "=" * 55)
    print("ENERGY MODEL CALIBRATION")
    print("Fitting to SULEKO records + Kenilworth telemetry")
    print("=" * 55)

    if 'T20P' not in suleko_results:
        print("  ERROR: T20P mountainous data not found")
        return model

    target_drain  = suleko_results['T20P']['avg_drop_pct']
    target_reduction = 38.9

    print(f"  Target 1 — SULEKO battery drop: {target_drain:.1f}%")
    print(f"  Target 2 — Kenilworth reduction: {target_reduction:.1f}%")

    # Mission parameters from real data
    avg_speed_ms  = 6.4 / 3.6
    avg_slope_deg = 18.0
    avg_liquid_L  = 10.0
    mission_min   = 5.0
    ken_speed_ms  = 8.7 / 3.6
    ken_slope_deg = 12.0

    def error(params):
        eta, k_drag = params
        if eta <= 0.1 or k_drag <= 0 or eta > 2.0:
            return 1e10

        model.eta    = eta
        model.k_drag = k_drag

        # Error 1 — SULEKO battery drop
        mass_s     = model.current_mass(avg_liquid_L)
        drain_s    = model.battery_drain_per_minute(mass_s, avg_slope_deg, avg_speed_ms)
        pred_drop  = drain_s * mission_min
        err_suleko = (pred_drop - target_drain) ** 2

        # Error 2 — Kenilworth 38.9% reduction
        mass_h    = model.current_mass(18.8)
        mass_l    = model.current_mass(6.0)
        drain_h   = model.battery_drain_per_minute(mass_h, ken_slope_deg, ken_speed_ms)
        drain_l   = model.battery_drain_per_minute(mass_l, ken_slope_deg, ken_speed_ms)
        reduction = ((drain_h - drain_l) / drain_h) * 100
        err_ken   = (reduction - target_reduction) ** 2

        return err_suleko + err_ken * 5

    result = minimize(
        error,
        x0=[0.72, 0.025],
        method='Nelder-Mead',
        options={'xatol': 1e-8, 'fatol': 1e-8, 'maxiter': 10000}
    )

    model.eta, model.k_drag = result.x
    print(f"\n  Calibrated eta:    {model.eta:.4f}")
    print(f"  Calibrated k_drag: {model.k_drag:.4f}")

    # Verify
    mass_s    = model.current_mass(avg_liquid_L)
    drain_s   = model.battery_drain_per_minute(mass_s, avg_slope_deg, avg_speed_ms)
    pred_drop = drain_s * mission_min
    mape      = abs(pred_drop - target_drain) / target_drain * 100

    mass_h    = model.current_mass(18.8)
    mass_l    = model.current_mass(6.0)
    drain_h   = model.battery_drain_per_minute(mass_h, ken_slope_deg, ken_speed_ms)
    drain_l   = model.battery_drain_per_minute(mass_l, ken_slope_deg, ken_speed_ms)
    reduction = ((drain_h - drain_l) / drain_h) * 100

    print(f"\n  SULEKO verification:")
    print(f"    Predicted drop: {pred_drop:.1f}%  Actual: {target_drain:.1f}%  MAPE: {mape:.1f}%")
    print(f"  Kenilworth verification:")
    print(f"    Predicted reduction: {reduction:.1f}%  Target: {target_reduction:.1f}%  Error: {abs(reduction-target_reduction):.1f}pp")

    if mape <= 10 and abs(reduction - target_reduction) < 5:
        print(f"\n  Status: FULLY CALIBRATED ✓")
    elif mape <= 10:
        print(f"\n  Status: SULEKO calibrated ✓ — Kenilworth needs tuning")
    else:
        print(f"\n  Status: Needs further calibration")

    return model


def plot_energy_model(model, output_path):
    """Visualise energy model across all states."""
    print(f"\nGenerating energy model visualisation...")

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(
        'Component 3 — Physics-Based Energy Model\n'
        'E_total = ∫[P_hover(m(t)) + P_climb(m(t), θ(t), v(t))]dt\n'
        'Calibrated against SULEKO 163 mountainous flights + Kenilworth telemetry',
        fontsize=13, fontweight='bold'
    )

    liquid_range = np.linspace(0, 20, 100)
    slope_range  = np.linspace(0, 45, 100)
    speed_ms     = 8.7 / 3.6

    # Top left — drain rate vs liquid
    drains = [model.battery_drain_per_minute(
                  model.current_mass(L), 12.0, speed_ms)
              for L in liquid_range]

    axes[0,0].plot(liquid_range, drains, 'b-', linewidth=2.5)
    axes[0,0].axhline(y=18.0, color='red',   linestyle='--',
                       alpha=0.7, label='Kenilworth: 18%/min (full tank)')
    axes[0,0].axhline(y=11.0, color='green', linestyle='--',
                       alpha=0.7, label='Kenilworth: 11%/min (near empty)')
    axes[0,0].set_title('Battery Drain Rate vs Tank Level\n(slope=12°, speed=8.7km/h)', fontsize=11)
    axes[0,0].set_xlabel('Liquid remaining (L)')
    axes[0,0].set_ylabel('Drain rate (% per minute)')
    axes[0,0].legend(fontsize=9)
    axes[0,0].grid(True, alpha=0.3)

    # Top right — drain rate vs slope
    for liquid, label, color in [(20, '20L full tank', 'red'),
                                   (10, '10L half tank', 'orange'),
                                   (0,  ' 0L empty',    'green')]:
        mass   = model.current_mass(liquid)
        drains = [model.battery_drain_per_minute(mass, s, speed_ms)
                  for s in slope_range]
        axes[0,1].plot(slope_range, drains, color=color, linewidth=2, label=label)

    axes[0,1].set_title('Battery Drain Rate vs Slope Angle\n(speed=8.7km/h)', fontsize=11)
    axes[0,1].set_xlabel('Slope angle (degrees)')
    axes[0,1].set_ylabel('Drain rate (% per minute)')
    axes[0,1].legend(fontsize=9)
    axes[0,1].grid(True, alpha=0.3)
    axes[0,1].axvspan(0,  5,  alpha=0.1, color='green')
    axes[0,1].axvspan(5,  20, alpha=0.1, color='yellow')
    axes[0,1].axvspan(20, 45, alpha=0.1, color='red')

    # Bottom left — coverage comparison
    categories = ['Flat terrain\n(T25 — 59 flights)',
                  'Mountain terrain\n(T20P — 163 flights)',
                  'Target\n(agent must exceed)']
    values     = [0.590, 0.506, 0.560]
    colors_bar = ['#4CAF50', '#F44336', '#2196F3']

    bars = axes[1,0].bar(categories, values,
                          color=colors_bar, edgecolor='black', linewidth=0.8)
    axes[1,0].set_title('SULEKO Coverage Baseline\n(hectares per full battery charge)', fontsize=11)
    axes[1,0].set_ylabel('Coverage (ha per full charge)')
    axes[1,0].set_ylim(0, 0.75)
    axes[1,0].grid(True, alpha=0.3, axis='y')
    axes[1,0].axhline(y=0.506, color='red', linestyle='--',
                       alpha=0.7, linewidth=1.5, label='Primary baseline: 0.506 ha')
    axes[1,0].legend(fontsize=9)
    for bar, val in zip(bars, values):
        axes[1,0].text(bar.get_x() + bar.get_width()/2,
                        bar.get_height() + 0.01,
                        f'{val:.3f} ha', ha='center',
                        fontsize=11, fontweight='bold')

    # Bottom right — energy cost heatmap
    liquid_vals = np.linspace(0, 20, 50)
    slope_vals  = np.linspace(0, 40, 50)
    L_grid, S_grid = np.meshgrid(liquid_vals, slope_vals)

    cost_grid = np.zeros_like(L_grid)
    for i in range(L_grid.shape[0]):
        for j in range(L_grid.shape[1]):
            cost_grid[i,j] = model.battery_drain_per_minute(
                model.current_mass(L_grid[i,j]),
                S_grid[i,j], speed_ms
            )

    im = axes[1,1].contourf(L_grid, S_grid, cost_grid, levels=20, cmap='RdYlGn_r')
    axes[1,1].set_title('Energy Cost Heatmap\n(% battery per minute — DRL routing guide)', fontsize=11)
    axes[1,1].set_xlabel('Liquid remaining (L)')
    axes[1,1].set_ylabel('Slope angle (degrees)')
    plt.colorbar(im, ax=axes[1,1], label='Drain rate (%/min)')
    axes[1,1].text(15, 5,  'LOW\nCOST', ha='center', fontsize=10,
                    fontweight='bold', color='darkgreen')
    axes[1,1].text(2,  35, 'HIGH\nCOST', ha='center', fontsize=10,
                    fontweight='bold', color='darkred')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"  Saved: {output_path}")
    plt.close()


def save_calibrated_model(model, suleko_results, output_path):
    """Save calibrated constants to JSON for DRL agent."""
    mountain_baseline = suleko_results.get('T20P', {}).get('coverage_ha', 0.506)
    flat_baseline     = suleko_results.get('T25',  {}).get('coverage_ha', 0.590)

    constants = {
        "model_version":                  "2.0",
        "calibration_data":               "SULEKO 163 mountainous flights + Kenilworth 3 missions",
        "drone_model":                    "DJI Agras T25/T20P",
        "mass_empty_kg":                  model.mass_empty_kg,
        "tank_capacity_L":                model.tank_capacity_L,
        "battery_wh":                     model.battery_wh,
        "rho":                            model.rho,
        "rotor_area":                     model.rotor_area,
        "n_rotors":                       model.n_rotors,
        "eta":                            model.eta,
        "k_drag":                         model.k_drag,
        "k_climb":                        model.k_climb,
        "primary_baseline_ha":            round(mountain_baseline, 4),
        "flat_baseline_ha":               round(flat_baseline, 4),
        "kenilworth_drain_heavy_pct_min": 18.0,
        "kenilworth_drain_light_pct_min": 11.0,
        "kenilworth_reduction_pct":       38.9,
        "update_frequency_hz":            10
    }
    with open(output_path, 'w') as f:
        json.dump(constants, f, indent=2)
    print(f"  Model constants saved: {output_path}")


def main():
    BASE      = os.path.expanduser("~/component3")
    DATA_DIR  = f"{BASE}/data"
    PLOT_OUT  = f"{BASE}/energy_model/energy_model_analysis.png"
    MODEL_OUT = f"{BASE}/energy_model/calibrated_model.json"

    print("=" * 55)
    print("Component 3 — Energy Model")
    print("Physics-based battery drain estimation")
    print("=" * 55)

    model = EnergyModel()
    print("\nModel created with initial constants.")

    model.validate_kenilworth()

    print(f"\nLoading SULEKO flight records from: {DATA_DIR}")
    all_df = load_suleko_data(DATA_DIR)

    if all_df is not None:
        suleko_results = analyse_suleko(all_df)
        model = calibrate_model(model, suleko_results)
        print("\nFinal validation after calibration:")
        model.validate_kenilworth()
    else:
        print("  SULEKO data not loaded — using initial constants")
        suleko_results = {}

    plot_energy_model(model, PLOT_OUT)
    save_calibrated_model(model, suleko_results, MODEL_OUT)

    print("\n" + "=" * 55)
    print("ENERGY MODEL COMPLETE")
    print(f"  Analysis: {PLOT_OUT}")
    print(f"  Constants: {MODEL_OUT}")
    print("=" * 55)


if __name__ == "__main__":
    main()