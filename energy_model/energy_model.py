# energy_model.py
# Component 3 - Physics-Based Energy Cost Model  (version 3.0)
#
#   E_total = integral of [ P_hover(m(t)) + P_climb(m(t), theta(t), v(t)) ] dt
#
# CALIBRATION (fit) uses only Kenilworth telemetry:
#   full tank  (~18.8 L) -> 18 %/min ,  near-empty (~6 L) -> 11 %/min  (slope 12 deg, 8.7 km/h)
#   Two unknowns are fitted: empty mass m0 and effective battery energy B_eff.
#
# SULEKO LEVEL SCALE: one number that sets the overall drain level to the
#   SULEKO T20P aircraft (mean drain %/min). The SHAPE (how drain depends on
#   tank weight and slope) still comes from Kenilworth. Needed because the
#   DRL result is compared with the SULEKO baseline (0.506 ha per charge).
#
# INDEPENDENT VALIDATION uses SULEKO T25 flat flights, which are used in
#   neither the fit nor the scale.
#
# Run (Ubuntu / WSL):
#   cd ~/component3 && source venv/bin/activate
#   python3 energy_model/energy_model.py

import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares

# ---- Kenilworth targets (OCR telemetry, screen recordings) ----
KEN_DRAIN_HEAVY = 18.0     # %/min, tank ~18.8 L
KEN_DRAIN_LIGHT = 11.0     # %/min, tank ~6.0 L
KEN_L_HEAVY     = 18.8
KEN_L_LIGHT     = 6.0
KEN_SPEED_KMH   = 8.7
KEN_SLOPE_DEG   = 12.0

# ---- Assumptions used for SULEKO validation (stated, not fitted) ----
SUL_SPEED_KMH   = 6.4
SUL_SLOPE_T20P  = 22.8     # mean SRTM slope of the estate (terrain_processor.py)
SUL_SLOPE_T25   = 3.0      # flat paddy-type terrain, assumed


class EnergyModel:
    """
    Battery drain model for a DJI Agras class spray drone.
    P_hover  : momentum-theory hover power, grows as mass^1.5
    P_climb  : extra power to gain height on a slope + small drag term
    rho, rotor_area, eta are lumped; the absolute scale is carried by
    battery_wh, which is an EFFECTIVE energy fitted to telemetry
    (not the datasheet battery size).
    """

    def __init__(self):
        self.mass_empty_kg   = 26.51    # fitted (Kenilworth)
        self.tank_capacity_L = 20.0
        self.battery_wh      = 777.6    # effective energy, fitted (Kenilworth)
        self.g               = 9.81
        self.n_rotors        = 4
        self.rho             = 1.15
        self.rotor_area      = 0.20
        self.eta             = 0.72
        self.k_drag          = 0.025
        self.k_climb         = 1.15
        self.level_scale     = 1.0      # 1.0 = Kenilworth aircraft; <1 = SULEKO level

    def current_mass(self, liquid_L):
        return self.mass_empty_kg + liquid_L

    def hover_power(self, mass_kg):
        thrust = mass_kg * self.g
        return thrust ** 1.5 / np.sqrt(
            2 * self.rho * self.rotor_area * self.n_rotors * self.eta)

    def climb_power(self, mass_kg, slope_deg, velocity_ms):
        s = np.radians(np.clip(slope_deg, 0, 60))
        p_grav = mass_kg * self.g * velocity_ms * np.sin(s) * self.k_climb
        p_drag = 0.5 * self.k_drag * velocity_ms ** 2
        return max(0.0, p_grav) + p_drag

    def total_power(self, mass_kg, slope_deg, velocity_ms):
        return self.hover_power(mass_kg) + self.climb_power(mass_kg, slope_deg, velocity_ms)

    def battery_drain_per_minute(self, mass_kg, slope_deg, velocity_ms):
        return (self.total_power(mass_kg, slope_deg, velocity_ms)
                * self.level_scale / (self.battery_wh * 60) * 100)

    def energy_cost(self, liquid_L, slope_deg, velocity_ms, dt=0.1):
        """Battery % used in one timestep (10 Hz default) - used by the DRL reward."""
        p = self.total_power(self.current_mass(liquid_L), slope_deg, velocity_ms)
        return p * self.level_scale * dt / 3600 / self.battery_wh * 100

    def drain_at(self, liquid_L, slope_deg, speed_kmh):
        return self.battery_drain_per_minute(
            self.current_mass(liquid_L), slope_deg, speed_kmh / 3.6)


# ------------------------------------------------------------------
# SULEKO real flight records
# ------------------------------------------------------------------
def load_suleko_data(data_dir):
    files = sorted(f for f in os.listdir(data_dir) if f.endswith(".xlsx"))
    dfs = []
    for f in files:
        try:
            dfs.append(pd.read_excel(os.path.join(data_dir, f), sheet_name="flight record"))
            print(f"  Loaded: {f} ({len(dfs[-1])} rows)")
        except Exception as e:
            print(f"  Skipped {f}: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else None


def _minutes(s):
    try:
        m, sec = str(s).split(":")
        return int(m) + int(sec) / 60
    except Exception:
        return np.nan


def analyse_suleko(all_df):
    print("\n" + "=" * 60)
    print("SULEKO FLIGHT RECORDS  (real spray missions, Sri Lanka)")
    print("=" * 60)
    all_df = all_df.copy()
    all_df["duration_min"] = all_df["Flight duration(min:sec)"].map(_minutes)

    configs = [("T25", "Flat - Polonnaruwa", None),
               ("T20P", "Mountainous - Badulla/Uva", "Badulla|Uva Province")]
    results = {}
    for drone, label, loc in configs:
        df = all_df[all_df["Aircraft name"].str.contains(drone, na=False)]
        if loc:
            df = df[df["Location"].str.contains(loc, na=False)]
        df = df.dropna(subset=["Starting Battery Level", "Ending Battery Level",
                               "Sprayed area", "Total Amount(L/Kg)", "duration_min"])
        df = df[(df["Sprayed area"] > 500) & (df["Total Amount(L/Kg)"] >= 5)]
        df = df.assign(battery_drop=df["Starting Battery Level"] - df["Ending Battery Level"],
                       area_ha=df["Sprayed area"] / 10000)
        df = df[(df["battery_drop"] > 0) & (df["duration_min"] > 0.5)]
        full = df[df["Starting Battery Level"] >= 90]
        if len(full) == 0:
            print(f"\n  {drone}: no qualifying flights")
            continue
        drop, area = full["battery_drop"].mean(), full["area_ha"].mean()
        dur   = full["duration_min"].mean()
        drain = (full["battery_drop"] / full["duration_min"]).mean()
        liq   = full["Total Amount(L/Kg)"].mean()
        results[drone] = dict(terrain=label, flights=int(len(full)), avg_drop_pct=float(drop),
                              avg_area_ha=float(area), coverage_ha=float(area * 100 / drop),
                              avg_duration_min=float(dur), avg_drain_pct_min=float(drain),
                              avg_liquid_L=float(liq))
        print(f"\n  {drone} - {label}")
        print(f"    Full-battery flights:      {len(full)}")
        print(f"    Avg battery drop:          {drop:.1f} %")
        print(f"    Avg flight duration:       {dur:.2f} min")
        print(f"    Measured drain rate:       {drain:.1f} %/min")
        print(f"    Avg liquid sprayed:        {liq:.1f} L")
        print(f"    Coverage per full charge:  {area*100/drop:.3f} ha")
    if "T25" in results and "T20P" in results:
        print(f"\n  PRIMARY BASELINE (mountainous): {results['T20P']['coverage_ha']:.3f} ha/charge")
    return results


# ------------------------------------------------------------------
# Calibration (Kenilworth only) and validation (SULEKO)
# ------------------------------------------------------------------
def calibrate_model(model):
    print("\n" + "=" * 60)
    print("CALIBRATION  - fitted to Kenilworth only")
    print("=" * 60)

    def residuals(p):
        model.mass_empty_kg, model.battery_wh = p
        return [model.drain_at(KEN_L_HEAVY, KEN_SLOPE_DEG, KEN_SPEED_KMH) - KEN_DRAIN_HEAVY,
                model.drain_at(KEN_L_LIGHT, KEN_SLOPE_DEG, KEN_SPEED_KMH) - KEN_DRAIN_LIGHT]

    sol = least_squares(residuals, x0=[25.0, 1000.0])
    model.mass_empty_kg, model.battery_wh = sol.x
    dh = model.drain_at(KEN_L_HEAVY, KEN_SLOPE_DEG, KEN_SPEED_KMH)
    dl = model.drain_at(KEN_L_LIGHT, KEN_SLOPE_DEG, KEN_SPEED_KMH)
    red = (dh - dl) / dh * 100
    print(f"  Fitted empty mass:        {model.mass_empty_kg:.2f} kg")
    print(f"  Fitted effective energy:  {model.battery_wh:.1f} Wh")
    print(f"  Full tank  : model {dh:.2f} %/min   real {KEN_DRAIN_HEAVY}")
    print(f"  Near-empty : model {dl:.2f} %/min   real {KEN_DRAIN_LIGHT}")
    print(f"  Reduction  : model {red:.1f} %      real 38.9 %")
    return model, dict(drain_heavy=dh, drain_light=dl, reduction=red)


def calibrate_suleko_scale(model, results):
    """Set level_scale so the model matches the mean SULEKO T20P battery drop."""
    print("\n" + "=" * 60)
    print("SULEKO LEVEL SCALE  - fitted on T20P only")
    print("=" * 60)
    if "T20P" not in results:
        return 1.0
    r = results["T20P"]
    model.level_scale = 1.0
    pred = model.drain_at(r["avg_liquid_L"] / 2, SUL_SLOPE_T20P, SUL_SPEED_KMH) * r["avg_duration_min"]
    scale = r["avg_drop_pct"] / pred
    model.level_scale = scale
    print(f"  Kenilworth-level prediction: {pred:.1f} %   SULEKO T20P real: {r['avg_drop_pct']:.1f} %")
    print(f"  Fitted level_scale: {scale:.3f}  (SULEKO aircraft uses {100*(1-scale):.1f} % less energy)")
    return float(scale)


def validate_suleko(model, results):
    """Independent test. Mean mass over a flight ~ empty + half of the liquid sprayed."""
    print("\n" + "=" * 60)
    print("VALIDATION  - T25 flat flights are fully independent")
    print("=" * 60)
    out = {}
    for drone, slope in [("T20P", SUL_SLOPE_T20P), ("T25", SUL_SLOPE_T25)]:
        if drone not in results:
            continue
        r = results[drone]
        pred_rate = model.drain_at(r["avg_liquid_L"] / 2, slope, SUL_SPEED_KMH)
        pred_drop = pred_rate * r["avg_duration_min"]
        err = abs(pred_drop - r["avg_drop_pct"]) / r["avg_drop_pct"] * 100
        out[drone] = dict(pred_drain=float(pred_rate), real_drain=r["avg_drain_pct_min"],
                          pred_drop=float(pred_drop), real_drop=r["avg_drop_pct"],
                          error_pct=float(err))
        print(f"\n  {drone}  (slope {slope} deg, {SUL_SPEED_KMH} km/h assumed)")
        print(f"    Drain rate : model {pred_rate:.1f}  real {r['avg_drain_pct_min']:.1f} %/min")
        print(f"    Battery drop per flight: model {pred_drop:.1f}  real {r['avg_drop_pct']:.1f} %")
        tag = 'fitted (scale)' if drone == 'T20P' else 'INDEPENDENT TEST'
        print(f"    Error: {err:.1f} %   {'PASS' if err <= 10 else 'CHECK'}   [{tag}]")
    if "T20P" in results:
        print("\n  Sensitivity of T20P prediction to the slope assumption:")
        r = results["T20P"]
        for s in (10, 15, 22.8, 30):
            d = model.drain_at(r["avg_liquid_L"] / 2, s, SUL_SPEED_KMH) * r["avg_duration_min"]
            print(f"    slope {s:>4} deg -> predicted drop {d:.1f} %")
    return out


def validate_kenilworth(model):
    dh = model.drain_at(KEN_L_HEAVY, KEN_SLOPE_DEG, KEN_SPEED_KMH)
    dl = model.drain_at(KEN_L_LIGHT, KEN_SLOPE_DEG, KEN_SPEED_KMH)
    return dh, dl, (dh - dl) / dh * 100


# ------------------------------------------------------------------
# Plot and save
# ------------------------------------------------------------------
def plot_energy_model(model, results, output_path):
    print("\nGenerating energy model figure (Kenilworth level)...")
    fig, ax = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Component 3 - Physics-Based Energy Model\n"
                 "E_total = integral[ P_hover(m(t)) + P_climb(m(t), theta(t), v(t)) ] dt\n"
                 "Fitted to Kenilworth telemetry, validated on SULEKO flights",
                 fontsize=13, fontweight="bold")
    spd = KEN_SPEED_KMH
    L = np.linspace(0, 20, 100)
    ax[0, 0].plot(L, [model.drain_at(x, KEN_SLOPE_DEG, spd) for x in L], "b-", lw=2.5, label="Model")
    ax[0, 0].scatter([KEN_L_HEAVY, KEN_L_LIGHT], [KEN_DRAIN_HEAVY, KEN_DRAIN_LIGHT],
                     c="red", s=80, zorder=5, label="Kenilworth (real)")
    ax[0, 0].set_title("Drain rate vs tank level (slope 12 deg, 8.7 km/h)")
    ax[0, 0].set_xlabel("Liquid remaining (L)"); ax[0, 0].set_ylabel("%/min")
    ax[0, 0].legend(); ax[0, 0].grid(alpha=.3)

    S = np.linspace(0, 45, 100)
    for liq, c in [(20, "red"), (10, "orange"), (0, "green")]:
        ax[0, 1].plot(S, [model.drain_at(liq, s, spd) for s in S], color=c, lw=2, label=f"{liq} L")
    ax[0, 1].set_title("Drain rate vs slope (8.7 km/h)")
    ax[0, 1].set_xlabel("Slope (deg)"); ax[0, 1].set_ylabel("%/min")
    ax[0, 1].legend(); ax[0, 1].grid(alpha=.3)

    flat = results.get("T25", {}).get("coverage_ha", 0.590)
    mtn  = results.get("T20P", {}).get("coverage_ha", 0.506)
    bars = ax[1, 0].bar(["Flat (T25)", "Mountain (T20P)"], [flat, mtn],
                        color=["#4CAF50", "#F44336"], edgecolor="black")
    for b, v in zip(bars, [flat, mtn]):
        ax[1, 0].text(b.get_x() + b.get_width() / 2, v + .01, f"{v:.3f} ha", ha="center", fontweight="bold")
    ax[1, 0].axhline(mtn, color="red", ls="--", label=f"Baseline to beat: {mtn:.3f} ha")
    ax[1, 0].set_ylim(0, .75); ax[1, 0].set_ylabel("ha per full charge")
    ax[1, 0].set_title("SULEKO coverage baseline"); ax[1, 0].legend(); ax[1, 0].grid(alpha=.3, axis="y")

    Lg, Sg = np.meshgrid(np.linspace(0, 20, 50), np.linspace(0, 40, 50))
    G = np.vectorize(lambda l, s: model.drain_at(l, s, spd))(Lg, Sg)
    im = ax[1, 1].contourf(Lg, Sg, G, levels=20, cmap="RdYlGn_r")
    plt.colorbar(im, ax=ax[1, 1], label="%/min")
    ax[1, 1].set_title("Energy cost map (routing guide for DRL)")
    ax[1, 1].set_xlabel("Liquid remaining (L)"); ax[1, 1].set_ylabel("Slope (deg)")
    plt.tight_layout(); plt.savefig(output_path, dpi=150, bbox_inches="tight"); plt.close()
    print(f"  Saved: {output_path}")


def save_calibrated_model(model, results, fit, val, path):
    scale = float(model.level_scale)
    c = dict(
        model_version="3.0",
        fitted_on="Kenilworth OCR telemetry (full 18 %/min, near-empty 11 %/min)",
        level_scale_fitted_on="SULEKO T20P mean battery drop",
        validated_on="SULEKO T25 flat flights (independent)",
        mass_empty_kg=float(model.mass_empty_kg), tank_capacity_L=model.tank_capacity_L,
        battery_wh_effective=float(model.battery_wh), rho=model.rho,
        rotor_area=model.rotor_area, n_rotors=model.n_rotors, eta=model.eta,
        k_drag=model.k_drag, k_climb=model.k_climb, suleko_level_scale=scale,
        primary_baseline_ha=round(results.get("T20P", {}).get("coverage_ha", 0.506), 4),
        flat_baseline_ha=round(results.get("T25", {}).get("coverage_ha", 0.590), 4),
        kenilworth_fit=fit, suleko_validation=val, update_frequency_hz=10)
    with open(path, "w") as f:
        json.dump(c, f, indent=2)
    print(f"  Constants saved: {path}")


def main():
    BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
    DATA = f"{BASE}/data"
    PLOT = f"{BASE}/energy_model/energy_model_analysis.png"
    OUT  = f"{BASE}/energy_model/calibrated_model.json"

    print("=" * 60); print("Component 3 - Energy Model v3.0"); print("=" * 60)
    model = EnergyModel()
    print(f"\nLoading SULEKO records from: {DATA}")
    df = load_suleko_data(DATA)
    results = analyse_suleko(df) if df is not None else {}
    model, fit = calibrate_model(model)
    plot_energy_model(model, results, PLOT)        # Kenilworth-level curves
    if results:
        calibrate_suleko_scale(model, results)
    val = validate_suleko(model, results) if results else {}
    save_calibrated_model(model, results, fit, val, OUT)
    print("\n" + "=" * 60); print("ENERGY MODEL COMPLETE"); print("=" * 60)


if __name__ == "__main__":
    main()