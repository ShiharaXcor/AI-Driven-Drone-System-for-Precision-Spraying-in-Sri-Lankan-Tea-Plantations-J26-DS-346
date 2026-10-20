"""
Component 4 demo - Maturity-Driven Variable-Rate Spray Prescription.

Upload one or more UAV/field photos (one photo = one spray region):
  Function 1  -> maturity class + confidence per photo
  Function 2  -> spray level, rate and review flag per photo
  Output      -> flight summary, map (if photos have GPS), JSON/CSV download

Run from component4_maturity_engine/:
    streamlit run app/streamlit_app.py
"""

import io
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.prescription.engine import (LEVELS, SprayConfig, build_prescription,  # noqa: E402
                                     decide)
from src.preprocess.exif_gps import read_gps  # noqa: E402

LEVEL_COLOURS = {"low": "#4c9be8", "normal": "#3a7d44", "high": "#d1495b"}
LEVEL_RGBA = {"low": [76, 155, 232, 200], "normal": [58, 125, 68, 200],
              "high": [209, 73, 91, 200]}
DEFAULT_MODEL = ROOT / "runs" / "effnet_b0" / "best.pt"

st.set_page_config(page_title="C4 Spray Prescription", page_icon="🍃", layout="wide")


@st.cache_resource(show_spinner="Loading model...")
def load_classifier(path: str):
    # imported here so the page still opens (with a clear message) if torch is missing
    from src.classifier.predict import MaturityClassifier
    return MaturityClassifier(path)


def decode_upload(data: bytes):
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


# ------------------------------------------------------------------ sidebar
st.sidebar.header("Settings")
model_path = st.sidebar.text_input("Model checkpoint", str(DEFAULT_MODEL))
base_cfg = SprayConfig.from_yaml()
threshold = st.sidebar.slider("Confidence threshold", 0.0, 1.0,
                              float(base_cfg.confidence_threshold), 0.05,
                              help="Below this, the prediction is not trusted and the "
                                   "safe fallback level is used.")
st.sidebar.subheader("Maturity → spray mapping")
st.sidebar.caption("Initial rules from the proposal; to be validated with TRI.")
mapping = {m: st.sidebar.selectbox(m.capitalize(), LEVELS, index=LEVELS.index(lvl), key=m)
           for m, lvl in base_cfg.mapping.items()}
cfg = SprayConfig(mapping=mapping, rate_multiplier=base_cfg.rate_multiplier,
                  confidence_threshold=threshold,
                  low_confidence_level=base_cfg.low_confidence_level,
                  baseline_fixed_level=base_cfg.baseline_fixed_level)

# ------------------------------------------------------------------- header
st.title("🍃 Maturity-Driven Spray Prescription")
st.caption("Component 4 · AI-Driven Adaptive UAV System for Precision Tea Spraying (J26-DS-346)")

try:
    clf = load_classifier(model_path)
except FileNotFoundError:
    st.error(f"Model not found: `{model_path}`. Download `best.pt` from Drive "
             "(`C4_data/runs/effnet_b0/`) into `runs/effnet_b0/`.")
    st.stop()
except ImportError as e:
    st.error(f"Missing package: {e}. Run `pip install torch torchvision timm`.")
    st.stop()

flight_id = st.text_input("Flight / block ID", "DEMO-001")
uploads = st.file_uploader("Upload field photos (one photo = one spray region)",
                           type=["jpg", "jpeg", "png"], accept_multiple_files=True)
if not uploads:
    st.info("Upload one or more photos to generate a prescription.")
    st.stop()

# -------------------------------------------------------------- run pipeline
predictions, rejected = [], []
progress = st.progress(0.0, "Classifying...")
for i, up in enumerate(uploads):
    data = up.getvalue()
    img = decode_upload(data)
    if img is None:
        rejected.append(up.name)
        continue
    pred = clf.predict_whole(img)
    gps = read_gps(io.BytesIO(data))
    predictions.append({"region_id": len(predictions) + 1, "image": up.name,
                        "maturity": pred["maturity"], "confidence": pred["confidence"],
                        "probs": pred["probs"], "processing_ms": pred["processing_ms"],
                        "lat": gps[0] if gps else None, "lon": gps[1] if gps else None,
                        "_img": img})
    progress.progress((i + 1) / len(uploads), f"Classified {i + 1}/{len(uploads)}")
progress.empty()

for name in rejected:
    st.warning(f"Skipped **{name}**: not a readable image.")
if not predictions:
    st.error("None of the uploaded files could be read.")
    st.stop()

prescription = build_prescription(
    [{k: v for k, v in p.items() if not k.startswith("_") and k not in ("probs", "processing_ms")}
     for p in predictions], cfg, flight_id)
summary = prescription["summary"]

# ------------------------------------------------------------------ summary
c = st.columns(5)
c[0].metric("Regions", summary["regions"])
c[1].metric("Low", summary["by_level"]["low"])
c[2].metric("Normal", summary["by_level"]["normal"])
c[3].metric("High", summary["by_level"]["high"])
c[4].metric("Needs review", summary["needs_review"])
avg_ms = np.mean([p["processing_ms"] for p in predictions])
st.caption(f"Relative chemical use vs fixed rate: **×{summary['relative_chemical_use']}** "
           f"(placeholder rates) · average inference **{avg_ms:.0f} ms/photo**")

# ------------------------------------------------------------- per region
st.subheader("Regions")
cols = st.columns(3)
for i, (p, r) in enumerate(zip(predictions, prescription["regions"])):
    with cols[i % 3]:
        colour = LEVEL_COLOURS[r["spray_level"]]
        st.image(cv2.cvtColor(p["_img"], cv2.COLOR_BGR2RGB), width="stretch")
        st.markdown(
            f"**#{r['region_id']} · {r['image']}**  \n"
            f"Maturity: **{r['maturity']}** ({r['confidence']:.0%})  \n"
            f"Spray: <span style='background:{colour};color:white;padding:2px 8px;"
            f"border-radius:4px'>{r['spray_level'].upper()} ×{r['rate_multiplier']}</span>"
            + ("  ⚠️ review" if r["needs_review"] else ""),
            unsafe_allow_html=True)
        st.bar_chart(pd.Series(p["probs"], name="probability"), height=120)

# --------------------------------------------------------------------- map
located = [r for r in prescription["regions"] if r["lat"] is not None]
if located:
    st.subheader("Prescription map")
    df = pd.DataFrame(located)
    df["color"] = df["spray_level"].map(lambda l: LEVEL_RGBA[l])
    st.map(df, latitude="lat", longitude="lon", color="color", size=8)
else:
    st.caption("No GPS in these photos. Locations will come from Component 3 (navigation).")

# ----------------------------------------------------------------- outputs
st.subheader("Prescription output")
table = pd.DataFrame(prescription["regions"])
st.dataframe(table, width="stretch", hide_index=True)
d1, d2 = st.columns(2)
d1.download_button("Download JSON", json.dumps(prescription, indent=2),
                   f"{flight_id}_prescription.json", "application/json")
d2.download_button("Download CSV", table.to_csv(index=False),
                   f"{flight_id}_prescription.csv", "text/csv")
