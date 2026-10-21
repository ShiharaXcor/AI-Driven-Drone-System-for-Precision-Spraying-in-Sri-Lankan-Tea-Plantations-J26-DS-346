"""
Component 4 - Function 1 interface: photo in -> maturity out.

Whole-image mode (matches the current model, trained on whole photos):
    clf = MaturityClassifier("runs/effnet_b0/best.pt")
    clf.predict_whole("photo.jpg")
    # {"maturity": "medium", "confidence": 0.91, "probs": {...}, "processing_ms": 12.3}

Tile mode (for a future tile-trained model): clf.predict_image("photo.jpg")
returns one prediction per 224x224 tile.

CLI:
    # one photo
    python -m src.classifier.predict --model runs/effnet_b0/best.pt --image photo.jpg
    # every image in the test split -> CSV for the baseline comparison
    python -m src.classifier.predict --model runs/effnet_b0/best.pt \
        --split runs/effnet_b0/splits.csv --images data/pack/images \
        --out runs/effnet_b0/test_predictions.csv
"""

import argparse
import csv
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

    def predict_whole(self, image) -> dict:
        """Classify a whole photo (file path or BGR array) as one region."""
        t0 = time.perf_counter()
        img = read_image(Path(image)) if not isinstance(image, np.ndarray) else image
        if img is None:
            raise ValueError(f"Could not read image: {image}")
        pred = self.predict_tiles([img])[0]
        pred["processing_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return pred

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


def predict_split(clf: MaturityClassifier, split_csv: Path, images_dir: Path,
                  out_csv: Path, which: str = "test") -> int:
    """Predict every image of one split and save image,true_label,predicted,confidence."""
    with open(split_csv, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == which]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["image", "true_label", "predicted", "confidence"] +
                   [f"p_{c}" for c in clf.classes])
        for r in rows:
            full = Path(r["path"]) if r.get("path") else None
            img_path = full if full is not None and full.exists() else Path(images_dir or ".") / r["image"]
            pred = clf.predict_whole(img_path)
            w.writerow([r["image"], r["label"], pred["maturity"], pred["confidence"]] +
                       [pred["probs"][c] for c in clf.classes])
    return len(rows)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Predict tea maturity")
    p.add_argument("--model", required=True)
    p.add_argument("--image", help="single photo")
    p.add_argument("--tiles", action="store_true", help="per-tile output for --image")
    p.add_argument("--split", type=Path, help="splits.csv from training")
    p.add_argument("--images", type=Path, help="folder with the split's images "
                   "(not needed when splits.csv has full paths, e.g. Roboflow runs)")
    p.add_argument("--which", default="test", choices=["train", "val", "test"])
    p.add_argument("--out", type=Path, default=Path("test_predictions.csv"))
    a = p.parse_args()
    clf = MaturityClassifier(a.model)
    if a.split:
        n = predict_split(clf, a.split, a.images, a.out, a.which)
        print(f"Predicted {n} {a.which} images -> {a.out}")
    elif a.image:
        res = clf.predict_image(a.image) if a.tiles else clf.predict_whole(a.image)
        print(json.dumps(res, indent=2))
    else:
        p.error("give --image or --split")
