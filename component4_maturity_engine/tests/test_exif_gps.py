"""Tests for reading GPS from photo EXIF (used to place regions on the map)."""

import numpy as np
from PIL import Image

from src.preprocess.exif_gps import read_gps


def _save(path, gps=None):
    img = Image.fromarray(np.zeros((20, 20, 3), np.uint8))
    exif = Image.Exif()
    if gps:
        exif[34853] = gps
    img.save(path, exif=exif)


def test_reads_north_east_coordinates(tmp_path):
    _save(tmp_path / "a.jpg", {1: "N", 2: (6.0, 58.0, 10.0), 3: "E", 4: (80.0, 45.0, 30.0)})
    lat, lon = read_gps(tmp_path / "a.jpg")
    assert abs(lat - 6.969444) < 1e-5 and abs(lon - 80.758333) < 1e-5


def test_south_west_are_negative(tmp_path):
    _save(tmp_path / "b.jpg", {1: "S", 2: (1.0, 0.0, 0.0), 3: "W", 4: (2.0, 0.0, 0.0)})
    assert read_gps(tmp_path / "b.jpg") == (-1.0, -2.0)


def test_missing_gps_returns_none(tmp_path):
    _save(tmp_path / "c.jpg")
    assert read_gps(tmp_path / "c.jpg") is None


def test_corrupt_file_returns_none(tmp_path):
    (tmp_path / "d.jpg").write_bytes(b"not an image")
    assert read_gps(tmp_path / "d.jpg") is None
