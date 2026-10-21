"""
Component 4 - dataset loading and leakage-free splitting.

Tiles cut from the same photo look almost identical. If they end up in both
train and test, accuracy is inflated. So the split is done by SOURCE PHOTO:
every tile of img_00042 goes to exactly one of train / val / test.
"""

import csv
from collections import Counter
from pathlib import Path

CLASSES = ["young", "medium", "mature"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}


def source_photo(tile_name: str) -> str:
    """img_00042_r1_c3.jpg -> img_00042 (the photo the tile was cut from)."""
    stem = Path(tile_name).stem
    return stem.split("_r")[0] if "_r" in stem else stem


def load_labelled(labels_csv: Path, tiles_dir: Path) -> list:
    """Return [(path, label_idx, group)] for tiles labelled young/medium/mature."""
    items = []
    with open(labels_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            label = row["label"]
            if label not in CLASS_TO_IDX:          # "skip" and any other label
                continue
            path = tiles_dir / row["image"]
            if path.exists():
                items.append((path, CLASS_TO_IDX[label], source_photo(row["image"])))
    if not items:
        raise SystemExit(f"No usable labelled tiles found ({labels_csv}, {tiles_dir})")
    return items


def group_split(items: list, val: float = 0.15, test: float = 0.15, seed: int = 42):
    """Split by source photo AND keep class proportions similar in every split.

    StratifiedGroupKFold guarantees no photo appears in more than one split,
    while trying to keep each split's class balance close to the overall one.
    This matters because "young" is the smallest class: a purely random photo
    split could leave the test set with almost no young tiles.
    """
    from sklearn.model_selection import StratifiedGroupKFold

    y = [lbl for _, lbl, _ in items]
    g = [grp for _, _, grp in items]

    def one_fold(idx, frac, rs):
        n_splits = max(2, round(1 / frac))
        sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=rs)
        sub_y, sub_g = [y[i] for i in idx], [g[i] for i in idx]
        rest, held = next(sgkf.split(idx, sub_y, sub_g))
        return [idx[i] for i in rest], [idx[i] for i in held]

    all_idx = list(range(len(items)))
    remaining, test_idx = one_fold(all_idx, test, seed)
    train_idx, val_idx = one_fold(remaining, val / (1 - test), seed + 1)
    return {"train": [items[i] for i in train_idx],
            "val": [items[i] for i in val_idx],
            "test": [items[i] for i in test_idx]}


def describe(split: dict) -> str:
    lines = []
    for name, items in split.items():
        c = Counter(CLASSES[lbl] for _, lbl, _ in items)
        photos = len({g for _, _, g in items})
        lines.append(f"  {name:<5} {len(items):>5} tiles from {photos:>4} photos  " +
                     "  ".join(f"{k}:{c.get(k, 0)}" for k in CLASSES))
    return "\n".join(lines)


def save_split(split: dict, out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["split", "image", "label", "source_photo", "path"])
        for name, items in split.items():
            for path, lbl, g in items:
                w.writerow([name, path.name, CLASSES[lbl], g, str(path)])
