"""Tests for reading Roboflow classification exports (folder and CSV formats)."""

import csv

import pytest

from src.classifier.dataset import CLASSES, save_split
from src.classifier.roboflow import leakage_report, load_roboflow, source_photo


def _img(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xd8fake")


def make_folder_export(root, extra_level=True):
    base = root / "tea-maturity-1" if extra_level else root
    for split, n in [("train", 4), ("valid", 2), ("test", 2)]:
        for cls in ["Young", "medium", "Mature"]:
            for i in range(n):
                _img(base / split / cls / f"{split}{cls}{i}_jpg.rf.abc{i}.jpg")
    _img(base / "train" / "Mature" / "train_aug_jpg.rf.x1.jpg")     # augmented copy 1
    _img(base / "train" / "Mature" / "train_aug_jpg.rf.x2.jpg")     # augmented copy 2
    _img(base / "train" / "unlabeled" / "junk_jpg.rf.z.jpg")        # not one of our classes
    return root


def make_csv_export(root):
    for split, n in [("train", 3), ("valid", 1), ("test", 1)]:
        d = root / split
        rows = []
        for cls in ["young", "medium", "mature"]:
            for i in range(n):
                name = f"{split}_{cls}_{i}_jpg.rf.h{i}.jpg"
                _img(d / name)
                rows.append([name] + [1 if c == cls else 0 for c in ["young", "medium", "mature"]])
        with open(d / "_classes.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["filename", " Young", " Medium", " Mature"])   # Roboflow adds spaces
            w.writerows(rows)
    return root


def test_source_photo_strips_roboflow_suffix():
    assert source_photo("IMG_1234_jpg.rf.9f8e7d.jpg") == "IMG_1234_jpg"
    assert source_photo("plain.jpg") == "plain"


def test_folder_export_with_extra_level_and_case(tmp_path):
    split = load_roboflow(make_folder_export(tmp_path))
    assert len(split["train"]) == 4 * 3 + 2          # unknown "unlabeled" folder ignored
    assert len(split["val"]) == 6 and len(split["test"]) == 6
    assert {CLASSES[l] for _, l, _ in split["train"]} == set(CLASSES)
    groups = [g for _, _, g in split["train"]]
    assert groups.count("train_aug_jpg") == 2         # augmented copies share one group


def test_csv_export(tmp_path):
    split = load_roboflow(make_csv_export(tmp_path))
    assert (len(split["train"]), len(split["val"]), len(split["test"])) == (9, 3, 3)
    assert sorted(CLASSES[l] for _, l, _ in split["test"]) == ["mature", "medium", "young"]


def test_leakage_detected(tmp_path):
    root = make_folder_export(tmp_path, extra_level=False)
    _img(root / "test" / "Young" / "trainYoung0_jpg.rf.other.jpg")   # same photo as a train image
    leaks = leakage_report(load_roboflow(root))
    assert leaks["train_test"] == ["trainYoung0_jpg"]


def test_missing_validation_split_falls_back(tmp_path):
    root = make_folder_export(tmp_path, extra_level=False)
    import shutil
    shutil.rmtree(root / "valid")
    split = load_roboflow(root)
    assert split["val"] == split["test"]


def test_not_a_roboflow_export(tmp_path):
    (tmp_path / "random").mkdir()
    with pytest.raises(SystemExit):
        load_roboflow(tmp_path)


def test_splits_csv_keeps_full_paths(tmp_path):
    split = load_roboflow(make_csv_export(tmp_path / "rf"))
    save_split(split, tmp_path / "splits.csv")
    with open(tmp_path / "splits.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert all((tmp_path / "rf").as_posix() in r["path"].replace("\\", "/") for r in rows)
