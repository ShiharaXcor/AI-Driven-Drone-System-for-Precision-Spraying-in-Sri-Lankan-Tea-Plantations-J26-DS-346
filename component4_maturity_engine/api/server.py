"""
Component 4 REST API - connects the TeaDrone dashboard to the maturity model
(Function 1) and the spray prescription engine (Function 2).

Endpoints (all JSON):
    GET  /api/health                     model status
    GET  /api/config                     current maturity -> spray rules
    PUT  /api/config                     update rules (validated, saved to YAML)
    POST /api/prescriptions              upload photos -> new mission + prescription
    GET  /api/missions                   mission list (newest first)
    GET  /api/missions/{id}              full prescription for one mission
    GET  /api/missions/{id}/images/{n}   thumbnail of region n
    GET  /api/metrics                    model test results + fixed-rate comparison

Run from component4_maturity_engine/:
    uvicorn api.server:app --reload --port 8000
Environment variables (optional):
    C4_MODEL     path to best.pt         (default runs/effnet_b0/best.pt)
    C4_DATA      where missions are kept (default data/missions)
    C4_CORS      allowed dashboard URLs, comma separated (default http://localhost:5173)
"""

import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.prescription.engine import DEFAULT_CONFIG, SprayConfig, build_prescription  # noqa: E402
from src.preprocess.exif_gps import read_gps  # noqa: E402

MODEL_PATH = Path(os.environ.get("C4_MODEL", ROOT / "runs" / "effnet_b0" / "best.pt"))
MISSIONS_DIR = Path(os.environ.get("C4_DATA", ROOT / "data" / "missions"))
RUNS_DIR = ROOT / "runs"
MAX_FILES, MAX_MB = 200, 25
MISSION_ID = re.compile(r"^MSN-\d{8}-\d{6}(-\d+)?$")

app = FastAPI(title="TeaDrone C4 - Maturity & Spray Prescription API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("C4_CORS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["*"], allow_headers=["*"],
)

# Set in tests to a fake object with .predict_whole(img) and .classes
app.state.classifier = None
app.state.model_error = None


def get_classifier():
    if app.state.classifier is None and app.state.model_error is None:
        try:
            from src.classifier.predict import MaturityClassifier
            app.state.classifier = MaturityClassifier(str(MODEL_PATH))
        except FileNotFoundError:
            app.state.model_error = f"Model file not found: {MODEL_PATH}"
        except ImportError as e:
            app.state.model_error = f"Missing package: {e}. pip install torch torchvision timm"
        except Exception as e:  # corrupt checkpoint, etc.
            app.state.model_error = f"Could not load model: {e}"
    return app.state.classifier


def mission_path(mission_id: str) -> Path:
    if not MISSION_ID.match(mission_id):
        raise HTTPException(400, "Invalid mission id")
    path = MISSIONS_DIR / mission_id
    if not (path / "prescription.json").exists():
        raise HTTPException(404, f"Mission {mission_id} not found")
    return path


# ------------------------------------------------------------------ health
@app.get("/api/health")
def health():
    clf = get_classifier()
    return {"status": "ok" if clf else "model_unavailable",
            "model_loaded": clf is not None,
            "model_path": str(MODEL_PATH),
            "classes": list(clf.classes) if clf else [],
            "error": app.state.model_error}


# ------------------------------------------------------------------ config
@app.get("/api/config")
def get_config():
    return SprayConfig.from_yaml(DEFAULT_CONFIG).to_dict()


@app.put("/api/config")
def put_config(body: dict):
    current = SprayConfig.from_yaml(DEFAULT_CONFIG).to_dict()
    unknown = set(body) - set(current)
    if unknown:
        raise HTTPException(422, f"Unknown settings: {sorted(unknown)}")
    try:
        cfg = SprayConfig(**{**current, **body})
    except (ValueError, TypeError) as e:
        raise HTTPException(422, str(e))
    cfg.to_yaml(DEFAULT_CONFIG)
    return cfg.to_dict()


# ----------------------------------------------------------- prescriptions
@app.post("/api/prescriptions", status_code=201)
async def create_prescription(files: list[UploadFile] = File(...),
                              field: str = Form("Unnamed field")):
    clf = get_classifier()
    if clf is None:
        raise HTTPException(503, app.state.model_error or "Model not loaded")
    if len(files) > MAX_FILES:
        raise HTTPException(413, f"At most {MAX_FILES} photos per mission")

    cfg = SprayConfig.from_yaml(DEFAULT_CONFIG)
    now = datetime.now()
    mission_id = now.strftime("MSN-%Y%m%d-%H%M%S")
    n = 1
    while (MISSIONS_DIR / mission_id).exists():
        mission_id = f"{now.strftime('MSN-%Y%m%d-%H%M%S')}-{n}"
        n += 1
    out = MISSIONS_DIR / mission_id
    (out / "images").mkdir(parents=True)

    predictions, rejected, timings = [], [], []
    for up in files:
        data = await up.read()
        name = Path(up.filename or "photo").name
        if len(data) > MAX_MB * 1e6:
            rejected.append({"image": name, "reason": f"larger than {MAX_MB} MB"})
            continue
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            rejected.append({"image": name, "reason": "not a readable image"})
            continue
        pred = clf.predict_whole(img)
        timings.append(pred.get("processing_ms", 0))
        region_id = len(predictions) + 1
        gps = read_gps(io.BytesIO(data))
        thumb = cv2.resize(img, (320, int(320 * img.shape[0] / img.shape[1])),
                           interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out / "images" / f"{region_id}.jpg"), thumb,
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
        predictions.append({"region_id": region_id, "image": name,
                            "maturity": pred["maturity"], "confidence": pred["confidence"],
                            "probs": pred.get("probs", {}),
                            "lat": gps[0] if gps else None, "lon": gps[1] if gps else None})

    if not predictions:
        (out / "images").rmdir()
        out.rmdir()
        raise HTTPException(422, {"message": "None of the uploaded files could be read",
                                  "rejected": rejected})

    prescription = build_prescription(predictions, cfg, flight_id=mission_id)
    for region, pred in zip(prescription["regions"], predictions):
        region["probs"] = pred["probs"]
    prescription.update({
        "mission_id": mission_id,
        "field": field.strip() or "Unnamed field",
        "rejected": rejected,
        "avg_processing_ms": round(float(np.mean(timings)), 1) if timings else None,
        "located_regions": sum(r["lat"] is not None for r in prescription["regions"]),
    })
    (out / "prescription.json").write_text(json.dumps(prescription, indent=2), encoding="utf-8")
    return prescription


# ----------------------------------------------------------------- missions
@app.get("/api/missions")
def list_missions():
    items = []
    if MISSIONS_DIR.exists():
        for d in MISSIONS_DIR.iterdir():
            f = d / "prescription.json"
            if not f.exists():
                continue
            p = json.loads(f.read_text(encoding="utf-8"))
            items.append({"mission_id": p["mission_id"], "field": p.get("field", ""),
                          "generated_at": p["generated_at"], **p["summary"]})
    return sorted(items, key=lambda m: m["generated_at"], reverse=True)


@app.get("/api/missions/{mission_id}")
def get_mission(mission_id: str):
    return json.loads((mission_path(mission_id) / "prescription.json").read_text(encoding="utf-8"))


@app.get("/api/missions/{mission_id}/images/{region_id}")
def get_image(mission_id: str, region_id: int):
    f = mission_path(mission_id) / "images" / f"{region_id}.jpg"
    if not f.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(f, media_type="image/jpeg")


# ------------------------------------------------------------------ metrics
@app.get("/api/metrics")
def metrics():
    models, comparison = [], None
    if RUNS_DIR.exists():
        for run in sorted(RUNS_DIR.iterdir()):
            r = run / "results.json"
            if r.exists():
                res = json.loads(r.read_text(encoding="utf-8"))
                res.pop("history", None)
                res["run"] = run.name
                models.append(res)
            c = run / "baseline_comparison" / "comparison.json"
            if c.exists() and comparison is None:
                comparison = json.loads(c.read_text(encoding="utf-8"))
                comparison["run"] = run.name
    return {"models": models, "baseline_comparison": comparison}
