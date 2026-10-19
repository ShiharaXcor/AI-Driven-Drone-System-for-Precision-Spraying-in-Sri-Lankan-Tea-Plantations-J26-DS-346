import pytest

from component2_wind_spraying.drift_model import recommend as rec

BASE = dict(temp_c=28, rh_pct=70)


def test_result_has_all_keys():
    r = rec.recommend(wind_ms=3.0, wind_dir_deg=90, heading_deg=0, **BASE)
    for key in ["mode", "drift_m", "drift_risk", "crosswind_ms", "spray_shift_m", "nozzle_tilt_deg",
                "nozzle_tilt_side", "path_offset_m", "path_offset_side", "droplet_advice",
                "height_advice", "needs_external_decision", "reason"]:
        assert key in r


def test_strong_wind_gives_no_correction():
    r = rec.recommend(wind_ms=6.0, wind_dir_deg=90, heading_deg=0, **BASE)
    assert r["mode"] == "STRONG_WIND"
    assert r["nozzle_tilt_deg"] == 0 and r["path_offset_m"] == 0
    assert r["needs_external_decision"] is True


def test_wind_along_flight_line_needs_no_correction():
    r = rec.recommend(wind_ms=3.0, wind_dir_deg=0, heading_deg=0, **BASE)
    assert r["mode"] == "NO_CORRECTION"


def test_wind_from_right_corrects_to_right():
    r = rec.recommend(wind_ms=3.0, wind_dir_deg=90, heading_deg=0, **BASE)
    assert r["mode"] == "CORRECT" and r["nozzle_tilt_side"] == "right"


def test_wind_from_left_corrects_to_left():
    r = rec.recommend(wind_ms=3.0, wind_dir_deg=270, heading_deg=0, **BASE)
    assert r["mode"] == "CORRECT" and r["nozzle_tilt_side"] == "left"


def test_more_wind_gives_bigger_correction():
    low = rec.recommend(wind_ms=1.5, wind_dir_deg=90, heading_deg=0, **BASE)
    high = rec.recommend(wind_ms=4.0, wind_dir_deg=90, heading_deg=0, **BASE)
    assert high["spray_shift_m"] > low["spray_shift_m"]


@pytest.mark.parametrize("wind", [1, 2, 3, 4, 4.5])
def test_limits_are_never_exceeded(wind):
    r = rec.recommend(wind_ms=wind, wind_dir_deg=90, heading_deg=0, swath_m=5.5, **BASE)
    assert r["nozzle_tilt_deg"] <= rec.MAX_NOZZLE_TILT_DEG
    assert r["path_offset_m"] <= 5.5 / 2


def test_coarser_droplets_shift_less():
    assert rec.spray_shift_m(3, 2.5, "C-VC") < rec.spray_shift_m(3, 2.5, "VF-F")


def test_high_flight_gets_height_advice():
    r = rec.recommend(wind_ms=3.0, wind_dir_deg=90, heading_deg=0, height_m=3.2, **BASE)
    assert r["height_advice"] == 2.5


def test_unknown_droplet_class_raises_error():
    with pytest.raises(ValueError):
        rec.recommend(wind_ms=3.0, wind_dir_deg=90, heading_deg=0, droplet_class="XYZ", **BASE)