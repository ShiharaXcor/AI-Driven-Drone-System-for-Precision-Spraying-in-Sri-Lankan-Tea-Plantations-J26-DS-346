"""
Component 4 - Step 2: Keyboard labelling tool.

Shows each image and lets you label it with one key press:
    1 = young     2 = medium     3 = mature
    s = skip (unclear / not tea)   u = undo last   q = save and quit

Labels are saved to labels.csv after every key press, so you can stop at any
time and resume later - already-labelled images are skipped automatically.
With --copy, each labelled image is also copied into labelled/<class>/.

Usage (run from the component4_maturity_engine/ folder):
    python -m src.preprocess.label_images --images data/processed/images --out data/labels.csv --copy data/labelled
"""

import argparse
import csv
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

KEYS = {ord("1"): "young", ord("2"): "medium", ord("3"): "mature", ord("s"): "skip"}
CLASSES = ["young", "medium", "mature"]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
FIELDS = ["image", "label", "timestamp"]


def load_labels(csv_path: Path) -> dict:
    if not csv_path.exists():
        return {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        return {row["image"]: row for row in csv.DictReader(f)}


def save_labels(csv_path: Path, labels: dict) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = csv_path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(labels.values())
    tmp.replace(csv_path)  # atomic: a crash never leaves a half-written file


def draw_overlay(img, name: str, done: int, total: int, counts: dict):
    h, w = img.shape[:2]
    scale = 800 / max(h, w)
    view = cv2.resize(img, (int(w * scale), int(h * scale)))
    bar = np.zeros((70, view.shape[1], 3), dtype=np.uint8)
    line1 = f"{done}/{total}  {name}"
    line2 = "1=young 2=medium 3=mature s=skip u=undo q=quit   " + \
            "  ".join(f"{c}:{counts.get(c, 0)}" for c in CLASSES)
    cv2.putText(bar, line1, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(bar, line2, (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 255, 180), 1)
    return np.vstack([bar, view])


def copy_to_class(src: Path, copy_dir: Path, label: str) -> None:
    if copy_dir and label in CLASSES:
        dst = copy_dir / label / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def remove_from_class(src: Path, copy_dir: Path, label: str) -> None:
    if copy_dir and label in CLASSES:
        (copy_dir / label / src.name).unlink(missing_ok=True)


def run(images_dir: Path, csv_path: Path, copy_dir: Path | None) -> None:
    files = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not files:
        raise SystemExit(f"No images in {images_dir}")

    labels = load_labels(csv_path)
    todo = [p for p in files if p.name not in labels]
    history = []
    print(f"{len(files)} images, {len(labels)} already labelled, {len(todo)} to go.")

    i = 0
    while i < len(todo):
        path = todo[i]
        img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print(f"  could not read {path.name}, skipping")
            i += 1
            continue

        counts = {}
        for row in labels.values():
            counts[row["label"]] = counts.get(row["label"], 0) + 1
        cv2.imshow("C4 labeller", draw_overlay(img, path.name, len(labels), len(files), counts))
        key = cv2.waitKey(0) & 0xFF

        if key == ord("q"):
            break
        if key == ord("u") and history:
            prev_path, prev_label = history.pop()
            labels.pop(prev_path.name, None)
            remove_from_class(prev_path, copy_dir, prev_label)
            save_labels(csv_path, labels)
            i = todo.index(prev_path)
            continue
        if key in KEYS:
            label = KEYS[key]
            labels[path.name] = {"image": path.name, "label": label,
                                 "timestamp": datetime.now().isoformat(timespec="seconds")}
            copy_to_class(path, copy_dir, label)
            save_labels(csv_path, labels)
            history.append((path, label))
            i += 1
        # any other key: ignore and show the same image again

    cv2.destroyAllWindows()
    final = {}
    for row in labels.values():
        final[row["label"]] = final.get(row["label"], 0) + 1
    print(f"Saved {len(labels)} labels to {csv_path}: {final}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="C4 keyboard labelling tool")
    p.add_argument("--images", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path, help="labels CSV path")
    p.add_argument("--copy", type=Path, default=None,
                   help="also copy labelled images into <copy>/<class>/")
    a = p.parse_args()
    run(a.images, a.out, a.copy)