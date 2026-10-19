"""Tests for the C4 dataset split: no leakage between splits, classes preserved."""

import csv

import pytest

from src.classifier.dataset import CLASSES, group_split, load_labelled, source_photo


def test_source_photo_from_tile_name():
    assert source_photo("img_00042_r1_c3.jpg") == "img_00042"
    assert source_photo("img_00042.jpg") == "img_00042"


@pytest.fixture
def labelled(tmp_path):
    """60 photos x 6 tiles, labels imbalanced like the real data (few young)."""
    tiles = tmp_path / "tiles"
    tiles.mkdir()
    rows = []
    for p in range(60):
        label = "young" if p < 8 else "medium" if p < 34 else "mature"
        for t in range(6):
            name = f"img_{p:05d}_r{t // 3}_c{t % 3}.jpg"
            (tiles / name).write_bytes(b"x")
            rows.append({"image": name, "label": label, "timestamp": ""})
    rows.append({"image": "img_09999_r0_c0.jpg", "label": "skip", "timestamp": ""})
    csv_path = tmp_path / "labels.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["image", "label", "timestamp"])
        w.writeheader()
        w.writerows(rows)
    return load_labelled(csv_path, tiles)


def test_skip_labels_are_ignored(labelled):
    assert len(labelled) == 360


def test_no_photo_appears_in_two_splits(labelled):
    split = group_split(labelled)
    photos = {k: {g for _, _, g in v} for k, v in split.items()}
    assert not photos["train"] & photos["val"]
    assert not photos["train"] & photos["test"]
    assert not photos["val"] & photos["test"]
    assert sum(len(v) for v in split.values()) == len(labelled)


def test_every_split_contains_every_class(labelled):
    split = group_split(labelled)
    for name, items in split.items():
        present = {CLASSES[lbl] for _, lbl, _ in items}
        assert present == set(CLASSES), f"{name} is missing {set(CLASSES) - present}"


def test_split_is_repeatable(labelled):
    a, b = group_split(labelled, seed=7), group_split(labelled, seed=7)
    assert [p for p, _, _ in a["test"]] == [p for p, _, _ in b["test"]]


def test_missing_labels_fail_clearly(tmp_path):
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text("image,label,timestamp\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_labelled(csv_path, tmp_path)
