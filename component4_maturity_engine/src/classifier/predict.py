"""
Component 4 - Function 1 interface: photo in -> maturity per tile out.

    clf = MaturityClassifier("runs/effnet_b0/best.pt")
    result = clf.predict_image("data/raw/IMG_1234.jpg")
    # result["tiles"] = [{"row": 0, "col": 0, "maturity": "medium",
    #                     "confidence": 0.91, "probs": {...}}, ...]

Uses the same resizing and tiling as the preprocessing step, so the model sees
exactly what it was trained on. Tiles with too little vegetation are not
classified (classified = False); the prescription engine decides what to do with them.

CLI:
    python -m src.classifier.predict --model runs/effnet_b0/best.pt --image path/to/photo.jpg
"""

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import timm
import torch
from PIL import Image

from src.classifier.train import build_transforms
from src.preprocess.prepare_images import (QualityConfig, green_fraction, iter_tiles,
                                           read_image, resize_max_side)


class MaturityClassifier:
    def __init__(self, checkpoint: str, device: str | None = None,
                 tile: int = 224, max_side: int = QualityConfig.max_side,
                 min_green: float = 0.15):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        ckpt = torch.load(checkpoint, map_location=self.device)
        self.classes = ckpt["classes"]
        self.model = timm.create_model(ckpt["model"], pretrained=False,
                                       num_classes=len(self.classes))
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.to(self.device).eval()
        self.tf = build_transforms(train=False)
        self.tile, self.max_side, self.min_green = tile, max_side, min_green

    @torch.no_grad()
    def predict_tiles(self, tiles_bgr: list) -> list:
        """Classify a list of BGR tiles. Returns [{maturity, confidence, probs}]."""
        if not tiles_bgr:
            return []
        batch = torch.stack([self.tf(Image.fromarray(cv2.cvtColor(t, cv2.COLOR_BGR2RGB)))
                             for t in tiles_bgr]).to(self.device)
        probs = torch.softmax(self.model(batch), dim=1).cpu().numpy()
        return [{"maturity": self.classes[int(p.argmax())],
                 "confidence": round(float(p.max()), 4),
                 "probs": {c: round(float(v), 4) for c, v in zip(self.classes, p)}}
                for p in probs]

    def predict_image(self, image) -> dict:
        """Accepts a file path or a BGR numpy array."""
        t0 = time.perf_counter()
        img = read_image(Path(image)) if not isinstance(image, np.ndarray) else image
        if img is None:
            raise ValueError(f"Could not read image: {image}")
        img = resize_max_side(img, self.max_side)
        h, w = img.shape[:2]
        if min(h, w) < self.tile:
            raise ValueError(f"Image too small ({w}x{h}) for {self.tile}px tiles")

        cells, to_classify = [], []
        for r, c, t in iter_tiles(img, self.tile):
            cell = {"row": r, "col": c, "classified": green_fraction(t) >= self.min_green}
            cells.append(cell)
            if cell["classified"]:
                to_classify.append((cell, t))

        for (cell, _), pred in zip(to_classify, self.predict_tiles([t for _, t in to_classify])):
            cell.update(pred)

        return {
            "image": str(image) if not isinstance(image, np.ndarray) else "<array>",
            "grid": {"rows": h // self.tile, "cols": w // self.tile, "tile_px": self.tile},
            "tiles": cells,
            "processing_ms": round((time.perf_counter() - t0) * 1000, 1),
        }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Predict tea maturity per tile")
    p.add_argument("--model", required=True)
    p.add_argument("--image", required=True)
    a = p.parse_args()
    print(json.dumps(MaturityClassifier(a.model).predict_image(a.image), indent=2))
