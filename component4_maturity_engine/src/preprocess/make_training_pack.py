"""
Component 4 - pack labelled images into a small zip for Colab training.

The model only sees 224x224 inputs, so full-size photos waste upload time and
Drive space. This script takes only the images listed in the labels CSV
(ignoring "skip"), shrinks them so the longest side is --size px, and writes
them into one zip together with the labels CSV.

Usage (from component4_maturity_engine/):
    python -m src.preprocess.make_training_pack --labels data/labels.csv \
        --images data/processed/images --out training_pack.zip
"""

import argparse
import csv
import zipfile
from pathlib import Path

import cv2

from src.preprocess.prepare_images import read_image, resize_max_side

CLASSES = {"young", "medium", "mature"}


def make_pack(labels_csv: Path, images_dir: Path, out_zip: Path,
              size: int = 384, quality: int = 90) -> dict:
    with open(labels_csv, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["label"] in CLASSES]
    if not rows:
        raise SystemExit(f"No young/medium/mature labels in {labels_csv}")

    stats = {"packed": 0, "missing": 0, "unreadable": 0}
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_STORED) as zf:  # JPEGs don't compress further
        zf.write(labels_csv, "labels.csv")
        for i, r in enumerate(rows, 1):
            src = images_dir / r["image"]
            if not src.exists():
                stats["missing"] += 1
                continue
            img = read_image(src)
            if img is None:
                stats["unreadable"] += 1
                continue
            ok, buf = cv2.imencode(".jpg", resize_max_side(img, size),
                                   [cv2.IMWRITE_JPEG_QUALITY, quality])
            zf.writestr(f"images/{r['image']}", buf.tobytes())
            stats["packed"] += 1
            if i % 200 == 0:
                print(f"  {i}/{len(rows)}")
    stats["zip_mb"] = round(out_zip.stat().st_size / 1e6, 1)
    return stats


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Pack labelled images for Colab")
    p.add_argument("--labels", required=True, type=Path)
    p.add_argument("--images", required=True, type=Path)
    p.add_argument("--out", default=Path("training_pack.zip"), type=Path)
    p.add_argument("--size", type=int, default=384, help="longest side in px")
    p.add_argument("--quality", type=int, default=90)
    a = p.parse_args()
    s = make_pack(a.labels, a.images, a.out, a.size, a.quality)
    print(f"Packed {s['packed']} images ({s['missing']} missing, {s['unreadable']} unreadable) "
          f"-> {a.out} ({s['zip_mb']} MB)")
