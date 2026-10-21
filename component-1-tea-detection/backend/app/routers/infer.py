import time
import uuid
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from .. import config
from ..decision import decide, Det
from ..shadow import enhance
from ..services import finalize, gps
from ..vision import get_detector, get_shadow

router = APIRouter(prefix="/api", tags=["inference"])
OUT = config.BACKEND_DIR / "static" / "out"
OUT.mkdir(parents=True, exist_ok=True)
COLORS = {"tea_plant": (0, 200, 0), "person": (0, 0, 255), "animal": (0, 128, 255)}


def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0.0


def _merge(dets):
    """Same class and overlapping box: keep the higher confidence. Enhancement can
    raise tea confidence, but it can never hide a person or animal found in the raw image."""
    out = []
    for d in sorted(dets, key=lambda x: -x["conf"]):
        if not any(d["cls"] == o["cls"] and _iou(d["bbox"], o["bbox"]) > 0.5 for o in out):
            out.append(d)
    return out


def _quality_ok(bgr):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return float(g.mean()) > 25 and float(cv2.Laplacian(g, cv2.CV_64F).var()) > 10


def _save(img, name, max_w=1280):
    h, w = img.shape[:2]
    if w > max_w:
        img = cv2.resize(img, (max_w, int(h * max_w / w)))
    cv2.imwrite(str(OUT / name), img)
    return f"/static/out/{name}"


@router.post("/infer")
async def infer(file: UploadFile = File(...), geofence_ok: bool = True):
    t0 = time.perf_counter()
    img = cv2.imdecode(np.frombuffer(await file.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "File is not a valid image")
    det = get_detector()

    mask, ratio, shadow_method = get_shadow(img)
    raw = det.predict(img)
    enh, method = [], "none"
    if ratio >= config.SHADOW_MIN_RATIO:
        method = config.ENH_METHOD
        enh = det.predict(enhance(img, mask, method))

    merged = _merge(raw + enh)
    dets = [Det(d["cls"], d["conf"], tuple(d["bbox"])) for d in merged]
    tea = lambda L: max([d["conf"] for d in L if d["cls"] == "tea_plant"], default=0.0)
    decision, reason = decide(dets, geofence_ok=geofence_ok, image_ok=_quality_ok(img))

    vis = img.copy()
    for d in merged:
        x1, y1, x2, y2 = d["bbox"]
        col = COLORS.get(d["cls"], (255, 0, 255))
        cv2.rectangle(vis, (x1, y1), (x2, y2), col, 3)
        cv2.putText(vis, f'{d["cls"]} {d["conf"]:.2f}', (x1 + 4, max(y1 + 24, 24)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2)
    shade = img.copy()
    shade[mask > 0] = (0.5 * shade[mask > 0] + 0.5 * np.array([0, 0, 255])).astype(np.uint8)

    uid = uuid.uuid4().hex[:12]
    image_url = _save(vis, f"{uid}.jpg")
    shadow_url = _save(shade, f"{uid}_shadow.jpg")

    latency = (time.perf_counter() - t0) * 1000
    tea_before, tea_after = tea(raw), (tea(enh) if enh else None)
    res = finalize(decision, reason, dets, gps.read(), dict(
        shadow_ratio=ratio, enh_method=method, tea_before=tea_before, tea_after=tea_after,
        latency_ms=latency, image_url=image_url))
    res.update(shadow_ratio=round(ratio, 3), shadow_method=shadow_method, enhancement=method,
               tea_before=tea_before, tea_after=tea_after, latency_ms=round(latency, 1),
               detector_mode=det.mode, image_url=image_url, shadow_url=shadow_url, detections=merged)
    return res