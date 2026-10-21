"""
Component 4 - load a Roboflow classification export (keeps Roboflow's train/valid/test split).

Supported export formats (auto-detected):
  1. "Folder Structure":      <root>/train/<class>/*.jpg, <root>/valid/..., <root>/test/...
  2. "Multi-Class CSV":       <root>/train/_classes.csv (+ images), same for valid/ and test/
                              columns: filename, <class1>, <class2>, ... (one-hot)

Class names are matched case-insensitively ("Young", "young " -> young). Roboflow renames
files to "<original>_jpg.rf.<hash>.jpg"; the part before ".rf." identifies the source photo,
which is used to (a) check that no photo appears in two splits and (b) keep augmented
copies of one photo together.
"""

import csv
from collections import Counter
from pathlib import Path

from src.classifier.dataset import CLASSES, CLASS_TO_IDX

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLIT_DIRS = {"train": ["train"], "val": ["valid", "val", "validation"], "test": ["test"]}
ALIASES = {"old": "mature", "matured": "mature", "med": "medium", "new": "young"}


def normalise_class(name: str):
    n = name.strip().lower().replace("-", "_").replace(" ", "_")
    n = ALIASES.get(n, n)
    return n if n in CLASS_TO_IDX else None


def source_photo(file_name: str) -> str:
    """IMG_1234_jpg.rf.9f8e7d.jpg -> IMG_1234_jpg (same for every augmented copy)."""
    return Path(file_name).name.split(".rf.")[0] if ".rf." in file_name else Path(file_name).stem


def find_root(path: Path) -> Path:
    """The folder that contains train/ (Roboflow zips sometimes add one extra level)."""
    path = Path(path)
    if (path / "train").is_dir():
        return path
    for p in sorted(path.rglob("train")):
        if p.is_dir():
            return p.parent
    raise SystemExit(f"No 'train' folder found under {path}. Is this a Roboflow classification export?")


def _split_dir(root: Path, split: str):
    for name in SPLIT_DIRS[split]:
        if (root / name).is_dir():
            return root / name
    return None


def _load_folder_split(d: Path, unknown: Counter) -> list:
    items = []
    for class_dir in sorted(p for p in d.iterdir() if p.is_dir()):
        cls = normalise_class(class_dir.name)
        imgs = [f for f in class_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS]
        if cls is None:
            unknown[class_dir.name] += len(imgs)
            continue
        items += [(f, CLASS_TO_IDX[cls], source_photo(f.name)) for f in sorted(imgs)]
    return items


def _load_csv_split(d: Path, unknown: Counter) -> list:
    items = []
    with open(d / "_classes.csv", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = [c for c in reader.fieldnames if c.strip().lower() != "filename"]
        fname_col = next(c for c in reader.fieldnames if c.strip().lower() == "filename")
        for row in reader:
            on = [c for c in cols if str(row[c]).strip() in ("1", "1.0", "True", "true")]
            if len(on) != 1:
                unknown[f"rows with {len(on)} labels"] += 1
                continue
            cls = normalise_class(on[0])
            path = d / row[fname_col].strip()
            if cls is None:
                unknown[on[0].strip()] += 1
            elif path.exists():
                items.append((path, CLASS_TO_IDX[cls], source_photo(path.name)))
            else:
                unknown["missing image files"] += 1
    return items


def load_roboflow(path) -> dict:
    """Return {"train": [...], "val": [...], "test": [...]} of (path, label_idx, source_photo)."""
    root = find_root(Path(path))
    split, unknown = {}, Counter()
    for name in ("train", "val", "test"):
        d = _split_dir(root, name)
        if d is None:
            split[name] = []
            continue
        split[name] = (_load_csv_split(d, unknown) if (d / "_classes.csv").exists()
                       else _load_folder_split(d, unknown))
    if unknown:
        print(f"WARNING - ignored: {dict(unknown)}. Expected classes {CLASSES} "
              f"(case-insensitive; 'old' is read as 'mature').")
    if not split["train"]:
        raise SystemExit(f"No labelled training images found in {root}")
    if not split["val"] and not split["test"]:
        raise SystemExit("Export has no valid/ or test/ split. Re-export from Roboflow with a train/valid/test split.")
    if not split["val"]:            # fall back so training can still early-stop
        split["val"] = split["test"]
    if not split["test"]:
        split["test"] = split["val"]
    return split


def leakage_report(split: dict) -> dict:
    """Source photos that appear in more than one split (inflates test accuracy)."""
    groups = {k: {g for _, _, g in v} for k, v in split.items()}
    return {
        "train_val": sorted(groups["train"] & groups["val"]),
        "train_test": sorted(groups["train"] & groups["test"]),
        "val_test": sorted(groups["val"] & groups["test"]),
    }


def describe_roboflow(split: dict) -> str:
    lines = []
    for name, items in split.items():
        c = Counter(CLASSES[lbl] for _, lbl, _ in items)
        lines.append(f"  {name:<5} {len(items):>5} images from {len({g for *_, g in items}):>4} photos  " +
                     "  ".join(f"{k}:{c.get(k, 0)}" for k in CLASSES))
    leaks = leakage_report(split)
    n = sum(len(v) for v in leaks.values())
    lines.append("  leakage: none - no photo appears in two splits" if n == 0 else
                 f"  leakage WARNING: {n} photos appear in two splits "
                 f"(train/val {len(leaks['train_val'])}, train/test {len(leaks['train_test'])}, "
                 f"val/test {len(leaks['val_test'])}) - test accuracy may be optimistic")
    return "\n".join(lines)
