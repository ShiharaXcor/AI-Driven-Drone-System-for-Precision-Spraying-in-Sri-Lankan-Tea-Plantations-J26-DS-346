"""Component 2 - Wind-adaptive spraying demo (standalone Streamlit app).

Run from the repo root:
    streamlit run component2_wind_spraying/app/app.py
"""
import math
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import requests
import streamlit as st

# Make the repo root importable (app.py -> app -> component2_wind_spraying -> repo root)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from component2_wind_spraying.drift_model.predict import predict_drift  # noqa: E402
from component2_wind_spraying.drift_model import recommend as rec      # noqa: E402

COMP = ROOT / "component2_wind_spraying"
WIND_10M_TO_2M = math.log(2 / 0.0075) / math.log(10 / 0.0075)   # same log profile as Dataset A (0.776)
REGIONS = {"Nuwara Eliya": (6.97, 80.78), "Badulla": (6.99, 81.06), "Kandy": (7.29, 80.63), "Ratnapura": (6.68, 80.40)}
DROPLET_COLORS = {"VF-F": "#2a78d6", "F-M": "#eb6834", "M-C": "#1baf7a", "C-VC": "#eda100"}   # fixed order
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e0"

st.set_page_config(page_title="C2 Wind-Adaptive Spraying", layout="wide")
st.title("Wind-adaptive spraying – drift prediction and correction")
st.caption("Component 2 · standalone demo · ML drift model (XGBoost trained on AgDRIFT) + physics-based correction")


# ---------------- live weather (optional) ----------------
@st.cache_data(ttl=600)
def get_live_weather(lat, lon):
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}"
           "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m"
           "&wind_speed_unit=ms&timezone=Asia%2FColombo")
    c = requests.get(url, timeout=10).json()["current"]
    return {"temp_c": c["temperature_2m"], "rh_pct": c["relative_humidity_2m"],
            "wind_2m": round(c["wind_speed_10m"] * WIND_10M_TO_2M, 2),
            "wind_dir": c["wind_direction_10m"], "time": c["time"]}


defaults = {"wind": 2.0, "wdir": 90, "temp": 28.0, "rh": 70}
with st.sidebar:
    st.header("1. Weather")
    region = st.selectbox("Tea region (for live weather)", list(REGIONS))
    if st.button("Get live weather (Open-Meteo)"):
        try:
            w = get_live_weather(*REGIONS[region])
            st.session_state.update(wind=min(float(w["wind_2m"]), 7.0), wdir=int(w["wind_dir"]),
                                    temp=float(w["temp_c"]), rh=int(w["rh_pct"]))
            st.success(f"Live weather loaded for {region} ({w['time']})")
        except Exception as e:   # no internet etc. -> keep manual values
            st.error(f"Could not load live weather: {e}")
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    wind = st.slider("Wind speed at 2 m (m/s)", 0.0, 7.0, step=0.1, key="wind")
    wind_dir = st.slider("Wind comes FROM (deg, 0 = N, 90 = E)", 0, 359, key="wdir")
    temp = st.slider("Temperature (°C)", 8.0, 36.0, step=0.5, key="temp")
    rh = st.slider("Relative humidity (%)", 20, 100, key="rh")

    st.header("2. Drone settings")
    heading = st.slider("Flight heading (deg, direction the drone flies TO)", 0, 359, 0)
    height = st.slider("Flight height (m)", 2.0, 3.5, 2.5, step=0.1)
    swath = st.slider("Swath width (m)", 4.8, 6.4, 5.5, step=0.1)
    droplet = st.selectbox("Droplet class", rec.DROPLETS_FINE_TO_COARSE, index=1,
                           help="VF-F very fine · F-M fine/medium · M-C medium/coarse · C-VC coarse/very coarse")

    st.header("3. Safety limit")
    max_drift = st.slider("Maximum acceptable drift distance (m)", 5, 40, 20)

r = rec.recommend(wind, wind_dir, heading, temp, rh, height_m=height, swath_m=swath,
                  droplet_class=droplet, max_drift_m=max_drift)

tab1, tab2, tab3 = st.tabs(["Recommendation", "Drift vs wind", "Validation evidence"])

# ---------------- TAB 1: recommendation ----------------
with tab1:
    if r["mode"] == "STRONG_WIND":
        st.error(f"⛔ STRONG WIND – {r['reason']} A decision from the flight/mission side is needed.")
    elif r["mode"] == "NO_CORRECTION":
        st.success(f"✅ NO CORRECTION NEEDED – {r['reason']}")
    else:
        st.info(f"🔧 CORRECTION – {r['reason']}")
    if r["drift_risk"] == "HIGH":
        msg = f"⚠️ Predicted drift {r['drift_m']} m is above the {max_drift} m limit."
        msg += (f" Switch to **{r['droplet_advice']}** droplets." if r["droplet_advice"]
                else " No droplet class brings it under the limit – consider not spraying now.")
        st.warning(msg)
    if r["height_advice"]:
        st.warning(f"⚠️ Fly at {r['height_advice']} m or lower to reduce drift.")

    c = st.columns(5)
    c[0].metric("Predicted drift distance", "–" if r["drift_m"] is None else f"{r['drift_m']} m")
    c[1].metric("Crosswind", f"{r['crosswind_ms']} m/s", help=f"from the {r['wind_from_side']}")
    c[2].metric("Spray lands off target", f"{r['spray_shift_m']} m")
    c[3].metric("Nozzle tilt" + (f" ({r['nozzle_tilt_side']})" if r["nozzle_tilt_side"] else ""), f"{r['nozzle_tilt_deg']}°")
    c[4].metric("Path offset" + (f" ({r['path_offset_side']})" if r["path_offset_side"] else ""), f"{r['path_offset_m']} m")

    # ---- top view: drone always flies "up"; everything drawn relative to the drone ----
    rel = math.radians(wind_dir - heading)          # wind FROM, relative to the drone, clockwise from "up"
    fx, fy = math.sin(rel), math.cos(rel)           # unit vector pointing to where the wind comes from
    sign = 1 if r["wind_from_side"] == "right" else -1
    shift = r["spray_shift_m"] if r["mode"] == "CORRECT" else 0.0
    offset = sign * r["path_offset_m"]
    half = swath / 2
    fig = go.Figure()
    fig.add_shape(type="rect", x0=-half, x1=half, y0=-6, y1=6, fillcolor="rgba(27,175,122,0.12)", line_width=0)
    fig.add_annotation(x=0, y=6.4, text="target tea rows (swath)", showarrow=False, font=dict(color=MUTED))
    fig.add_trace(go.Scatter(x=[0, 0], y=[-6, 6], mode="lines", line=dict(color=MUTED, dash="dot", width=2),
                             name="Planned path", hovertemplate="Planned flight line<extra></extra>"))
    if shift > 0:
        fig.add_trace(go.Scatter(x=[-sign * shift] * 2, y=[-6, 6], mode="lines",
                                 line=dict(color="#e34948", dash="dash", width=2), name="Spray without correction",
                                 hovertemplate=f"Spray lands {shift} m off target<extra></extra>"))
        fig.add_trace(go.Scatter(x=[offset, offset], y=[-6, 6], mode="lines", line=dict(color="#2a78d6", width=2),
                                 name="Corrected path", hovertemplate=f"Corrected flight line ({r['path_offset_m']} m)<extra></extra>"))
    fig.add_annotation(x=offset, y=-4.5, ax=offset, ay=-6, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowwidth=2, arrowcolor=INK, text="")
    fig.add_annotation(x=offset, y=-6.6, text="drone (flies up ↑)", showarrow=False, font=dict(color=INK))
    if wind > 0:
        sx, sy = 6.5 * fx, 6.5 * fy                 # wind arrow starts on the windward side
        fig.add_annotation(x=sx - 3 * fx, y=sy - 3 * fy, ax=sx, ay=sy, xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowwidth=3, arrowcolor="#6250d6",
                           text=f"wind {wind} m/s", font=dict(color=INK))
    fig.update_layout(height=520, plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb", margin=dict(l=10, r=10, t=30, b=10),
                      title=dict(text="Top view (relative to the drone)", font=dict(color=INK)),
                      legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"), font=dict(color=MUTED))
    fig.update_xaxes(range=[-8, 8], title="sideways distance (m)  ← left | right →", gridcolor=GRID, zeroline=False)
    fig.update_yaxes(range=[-8, 10], showticklabels=False, gridcolor=GRID, zeroline=False)
    st.plotly_chart(fig, width="stretch")

    with st.expander("Full output (what the shared frontend / API will receive)"):
        st.json(r)

# ---------------- TAB 2: drift vs crosswind ----------------
with tab2:
    cws = np.round(np.arange(0.5, 6.75, 0.25), 2)
    fig2 = go.Figure()
    for d in rec.DROPLETS_FINE_TO_COARSE:
        ys = [predict_drift(cw, height, swath, temp, rh, d) for cw in cws]
        fig2.add_trace(go.Scatter(x=cws, y=ys, mode="lines", name=d, line=dict(color=DROPLET_COLORS[d], width=2),
                                  hovertemplate=f"{d}<br>crosswind %{{x}} m/s<br>drift %{{y:.1f}} m<extra></extra>"))
        fig2.add_annotation(x=cws[-1], y=ys[-1], text=d, showarrow=False, xanchor="left", font=dict(color=INK))
    fig2.add_hline(y=max_drift, line=dict(color=MUTED, dash="dash", width=1),
                   annotation_text=f"limit {max_drift} m", annotation_font_color=MUTED)
    if r["drift_m"] is not None:
        fig2.add_trace(go.Scatter(x=[min(max(r["crosswind_ms"], 0.5), 6.7)], y=[r["drift_m"]], mode="markers",
                                  marker=dict(size=12, color=DROPLET_COLORS[droplet], line=dict(color="#fcfcfb", width=2)),
                                  name="Current condition", hovertemplate="Now: %{y} m<extra></extra>"))
    fig2.update_layout(height=450, hovermode="x unified", plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
                       title=dict(text=f"Predicted drift distance vs crosswind (height {height} m, {temp} °C, {rh} % RH)",
                                  font=dict(color=INK)), font=dict(color=MUTED), margin=dict(l=10, r=40, t=50, b=10))
    fig2.update_xaxes(title="crosswind (m/s)", gridcolor=GRID)
    fig2.update_yaxes(title="drift distance (m)", gridcolor=GRID, rangemode="tozero")
    st.plotly_chart(fig2, width="stretch")
    st.caption("Coarser droplets drift much less at the same wind – the main lever for reducing drift.")

# ---------------- TAB 3: evidence ----------------
with tab3:
    st.markdown("**Model:** XGBoost, test R² 0.992, MAE 0.77 m (5,000 AgDRIFT runs driven by real Sri Lankan weather).  \n"
                "**Real flights (Suleco, 564 flights):** 89.2 % inside the training ranges; coarse droplets removed "
                "all worst-case drift > 30 m.")
    figs = [("Model predicted vs actual", COMP / "drift_model" / "fig_m6_pred_vs_actual.png"),
            ("Suleco flights: coverage of training ranges", COMP / "validation" / "fig_b4_coverage.png"),
            ("Suleco flights: predicted drift", COMP / "validation" / "fig_b6_suleco_drift.png")]
    for title, p in figs:
        if p.exists():
            st.subheader(title)
            st.image(str(p), width="stretch")
    st.info("Limitations: no measured drift in Suleco data; AgDRIFT uses a manned-helicopter proxy (conservative); "
            "nozzle-tilt and downwash values are assumptions to be calibrated in a field trial.")
