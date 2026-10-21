import cv2
from . import config

COCO_ANIMALS = {"bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear"}


def green_ratio_tea(bgr):
    """DEMO FALLBACK ONLY: crude HSV green ratio, used until your own tea model exists."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    r = float((cv2.inRange(hsv, (35, 40, 30), (85, 255, 255)) > 0).mean())
    if r < 0.2:
        return None
    h, w = bgr.shape[:2]
    return {"cls": "tea_plant", "conf": min(0.95, r * 1.3), "bbox": [0, 0, w, h]}


class Detector:
    def __init__(self):
        from ultralytics import YOLO
        self.custom = config.MODEL_PATH.exists()
        self.main = YOLO(str(config.MODEL_PATH)) if self.custom else None
        self.safety = YOLO(config.SAFETY_MODEL) if (config.USE_COCO_SAFETY or not self.custom) else None
        if self.custom:
            self.mode = "custom model + COCO safety" if config.USE_COCO_SAFETY else "custom model"
        else:
            self.mode = "DEMO (COCO + green ratio)"

    @staticmethod
    def _run(model, bgr, conf):
        res = model.predict(bgr, conf=conf, imgsz=640, verbose=False)[0]
        out = []
        for b in res.boxes:
            x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
            out.append({"cls": res.names[int(b.cls)], "conf": float(b.conf), "bbox": [x1, y1, x2, y2]})
        return out

    def predict(self, bgr, conf=0.10):
        out = []
        if self.custom:
            for d in self._run(self.main, bgr, 0.25):
                if config.USE_COCO_SAFETY and d["cls"] in ("person", "animal"):
                    continue                      # safety classes come from the safety model
                out.append(d)
        if self.safety is not None:
            for d in self._run(self.safety, bgr, conf):    # low threshold on purpose
                if d["cls"] == "person":
                    out.append(d)
                elif d["cls"] in COCO_ANIMALS:
                    d["cls"] = "animal"
                    out.append(d)
        if not self.custom:
            t = green_ratio_tea(bgr)
            if t:
                out.append(t)
        return out