"""Tests for the C4 preprocessing step: happy path and failure paths."""

import csv

import cv2
import numpy as np
import pytest

from src.preprocess.prepare_images import (QualityConfig, blur_score, green_fraction,
                                           prepare, write_image)


def _leafy(seed=0, size=600):
    """Synthetic sharp, green, textured image (stands in for a tea photo)."""
    rng = np.random.default_rng(seed)
    img = np.zeros((size, size, 3), np.uint8)
    img[..., 1] = 140
    for _ in range(200):
        x, y = rng.integers(0, size, 2)
        cv2.ellipse(img, (int(x), int(y)), (int(rng.integers(10, 40)), int(rng.integers(5, 15))),
                    float(rng.integers(0, 180)), 0, 360,
                    (int(rng.integers(0, 60)), int(rng.integers(120, 255)), int(rng.integers(0, 80))), -1)
    return img


@pytest.fixture
def raw_dir(tmp_path):
    d = tmp_path / "raw"
    write_image(d / "good1.jpg", _leafy(1))
    write_image(d / "good2.jpg", _leafy(2))
    write_image(d / "dup_of_good1.jpg", _leafy(1))                          # duplicate
    write_image(d / "blurry.jpg", cv2.GaussianBlur(_leafy(3), (51, 51), 0))  # blurry
    write_image(d / "dark.jpg", (_leafy(4) * 0.1).astype(np.uint8))         # too dark
    (d / "corrupt.jpg").write_bytes(b"not an image")                        # unreadable
    return d


def test_quality_filter_rejects_bad_images(raw_dir, tmp_path):
    out = tmp_path / "out"
    summary = prepare(raw_dir, out, QualityConfig())
    assert summary["total"] == 6
    assert summary["accepted"] == 2
    assert summary["duplicate"] == 1
    assert summary["blurry"] == 1
    assert summary["too_dark"] == 1
    assert summary["unreadable"] == 1
    assert len(list((out / "images").glob("*.jpg"))) == 2


def test_report_lists_every_image(raw_dir, tmp_path):
    out = tmp_path / "out"
    prepare(raw_dir, out, QualityConfig())
    with open(out / "quality_report.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 6
    assert {r["status"] for r in rows} == {"accepted", "rejected"}


def test_tiling_produces_square_tiles(raw_dir, tmp_path):
    out = tmp_path / "out"
    summary = prepare(raw_dir, out, QualityConfig(tile=224))
    tiles = list((out / "tiles").glob("*.jpg"))
    assert summary["tiles"] == len(tiles) > 0
    t = cv2.imread(str(tiles[0]))
    assert t.shape[:2] == (224, 224)


def test_empty_folder_fails_clearly(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(SystemExit):
        prepare(tmp_path / "empty", tmp_path / "out", QualityConfig())


def test_metrics_behave_sensibly():
    sharp = _leafy(5)
    gray = cv2.cvtColor(sharp, cv2.COLOR_BGR2GRAY)
    assert blur_score(gray) > blur_score(cv2.GaussianBlur(gray, (51, 51), 0))
    assert green_fraction(sharp) > green_fraction(np.full_like(sharp, 120))