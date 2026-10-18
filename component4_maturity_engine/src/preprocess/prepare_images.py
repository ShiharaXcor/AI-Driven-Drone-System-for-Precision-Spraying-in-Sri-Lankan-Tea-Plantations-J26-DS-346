"""
Component 4 - Step 1: Image quality check and preparation.

Reads raw tea images and:
  1. rejects unreadable, blurry, too-dark, too-bright and near-duplicate images
  2. resizes accepted images (longest side <= --max-side)
  3. renames them consistently (img_00001.jpg, ...)
  4. optionally cuts them into square tiles (--tile 224), skipping tiles
     with little vegetation
  5. writes a CSV report with the quality scores of every image

Usage (run from the component4_maturity_engine/ folder):
    python -m src.preprocess.prepare_images --input data/raw --output data/processed
    python -m src.preprocess.prepare_images --input data/raw --output data/processed --tile 224
"""

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


@dataclass
class QualityConfig:
    min_blur: float = 100.0        # Laplacian variance; lower = blurrier
    min_brightness: float = 40.0   # mean V channel (0-255)
    max_brightness: float = 220.0
    dup_distance: int = 5          # max Hamming distance (of 64 bits) to count as duplicate
    max_side: int = 1024           # resize so longest side is at most this
    tile: int = 0                  # 0 = no tiling
    min_green: float = 0.30        # min vegetation fraction for a tile to be kept


# ---------------------------------------------------------------- I/O helpers
# np.fromfile/imdecode handle Windows paths with spaces or non-ASCII characters.
def read_image(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def write_image(path: Path, img) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ok:
        raise IOError(f"Could not encode image for {path}")
    buf.tofile(str(path))


# ------------------------------------------------------------ quality metrics
def blur_score(gray) -> float:
    """Variance of the Laplacian: sharp images have strong edges -> high variance."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def brightness_score(img) -> float:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return float(hsv[..., 2].mean())


def dhash(gray, size: int = 8) -> np.ndarray:
    """Difference hash: 64-bit fingerprint, similar images -> similar hashes."""
    small = cv2.resize(gray, (size + 1, size), interpolation=cv2.INTER_AREA)
    bits = small[:, 1:] > small[:, :-1]
    return np.packbits(bits.flatten())


def green_fraction(img) -> float:
    """Fraction of pixels classed as vegetation by the Excess Green index (2G-R-B)."""
    b, g, r = cv2.split(img.astype(np.float32))
    exg = 2 * g - r - b
    return float((exg > 20).mean())


def resize_max_side(img, max_side: int):
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale >= 1:
        return img
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def iter_tiles(img, tile: int):
    h, w = img.shape[:2]
    for row, y in enumerate(range(0, h - tile + 1, tile)):
        for col, x in enumerate(range(0, w - tile + 1, tile)):
            yield row, col, img[y:y + tile, x:x + tile]


# ----------------------------------------------------------------- main logic
def find_images(input_dir: Path):
    return sorted(p for p in input_dir.rglob("*") if p.suffix.lower() in IMAGE_EXTS)


def prepare(input_dir: Path, output_dir: Path, cfg: QualityConfig) -> dict:
    files = find_images(input_dir)
    if not files:
        raise SystemExit(f"No images found in {input_dir}")

    accepted_dir = output_dir / "images"
    tiles_dir = output_dir / "tiles"
    report_rows = []
    seen_hashes = np.empty((0, 8), dtype=np.uint8)
    seen_names = []
    counts = {"accepted": 0, "unreadable": 0, "blurry": 0, "too_dark": 0,
              "too_bright": 0, "duplicate": 0, "tiles": 0}

    for i, path in enumerate(files, 1):
        row = {"source": str(path.relative_to(input_dir)), "new_name": "",
               "blur": "", "brightness": "", "status": "", "reason": ""}

        img = read_image(path)
        if img is None:
            row.update(status="rejected", reason="unreadable")
            counts["unreadable"] += 1
            report_rows.append(row)
            continue

        img = resize_max_side(img, cfg.max_side)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur, bright = blur_score(gray), brightness_score(img)
        row.update(blur=round(blur, 1), brightness=round(bright, 1))

        # Brightness is checked before blur: a very dark image also has weak
        # edges, so checking blur first would report the wrong reason.
        reason = ""
        if bright < cfg.min_brightness:
            reason = "too_dark"
        elif bright > cfg.max_brightness:
            reason = "too_bright"
        elif blur < cfg.min_blur:
            reason = "blurry"
        else:
            h = dhash(gray)
            if len(seen_hashes):
                dists = np.unpackbits(np.bitwise_xor(seen_hashes, h), axis=1).sum(axis=1)
                j = int(dists.argmin())
                if dists[j] <= cfg.dup_distance:
                    reason = "duplicate"
                    row["reason_detail"] = f"similar to {seen_names[j]}"
            if not reason:
                seen_hashes = np.vstack([seen_hashes, h])

        if reason:
            row.update(status="rejected", reason=reason)
            counts[reason] += 1
            report_rows.append(row)
            continue

        counts["accepted"] += 1
        new_name = f"img_{counts['accepted']:05d}.jpg"
        seen_names.append(new_name)
        write_image(accepted_dir / new_name, img)
        row.update(new_name=new_name, status="accepted")

        if cfg.tile:
            for r, c, t in iter_tiles(img, cfg.tile):
                if green_fraction(t) >= cfg.min_green:
                    write_image(tiles_dir / f"{Path(new_name).stem}_r{r}_c{c}.jpg", t)
                    counts["tiles"] += 1

        report_rows.append(row)
        if i % 100 == 0:
            print(f"  processed {i}/{len(files)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = ["source", "new_name", "blur", "brightness", "status", "reason", "reason_detail"]
    with open(output_dir / "quality_report.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report_rows)

    counts["total"] = len(files)
    return counts


def parse_args():
    p = argparse.ArgumentParser(description="C4 image quality check and preparation")
    p.add_argument("--input", required=True, type=Path, help="folder with raw images")
    p.add_argument("--output", required=True, type=Path, help="output folder")
    p.add_argument("--min-blur", type=float, default=QualityConfig.min_blur)
    p.add_argument("--min-brightness", type=float, default=QualityConfig.min_brightness)
    p.add_argument("--max-brightness", type=float, default=QualityConfig.max_brightness)
    p.add_argument("--dup-distance", type=int, default=QualityConfig.dup_distance)
    p.add_argument("--max-side", type=int, default=QualityConfig.max_side)
    p.add_argument("--tile", type=int, default=0, help="tile size in px (0 = no tiling)")
    p.add_argument("--min-green", type=float, default=QualityConfig.min_green)
    return p.parse_args()


if __name__ == "__main__":
    a = parse_args()
    cfg = QualityConfig(a.min_blur, a.min_brightness, a.max_brightness,
                        a.dup_distance, a.max_side, a.tile, a.min_green)
    print(f"Preparing images from {a.input} ...")
    summary = prepare(a.input, a.output, cfg)
    print("\nSummary")
    for k, v in summary.items():
        print(f"  {k:<11} {v}")
    print(f"\nReport written to {a.output / 'quality_report.csv'}")