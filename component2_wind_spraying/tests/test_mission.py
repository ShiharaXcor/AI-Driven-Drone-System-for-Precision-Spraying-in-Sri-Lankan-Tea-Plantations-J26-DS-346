from component2_wind_spraying.mission.simulate import plan_lines, simulate


def test_lines_cover_field_and_alternate_heading():
    lines = plan_lines(length_m=100, width_m=60, swath_m=5.5, row_bearing_deg=0)
    assert len(lines) == 11
    assert lines[0]["heading_deg"] == 0 and lines[1]["heading_deg"] == 180


def test_mission_finishes_all_lines():
    m = simulate(scenario="steady", wind_ms=2.0)
    assert m["summary"]["lines_completed"] == m["summary"]["lines"]


def test_gusty_mission_holds_in_strong_wind():
    m = simulate(scenario="gusty", wind_ms=2.5)
    assert m["summary"]["hold_s"] > 0
    assert all(s["status"] == "HOLD" for s in m["steps"] if s["decision_wind_ms"] > 4.5)


def test_calm_mission_never_holds():
    assert simulate(scenario="calm")["summary"]["hold_s"] == 0


def test_correction_reduces_miss_distance():
    s = simulate(scenario="steady", wind_ms=3.0)["summary"]
    assert s["mean_miss_corrected_m"] < s["mean_miss_uncorrected_m"]


def test_correction_side_flips_between_lines():
    steps = simulate(scenario="steady", wind_ms=3.0, wind_dir_deg=90)["steps"]
    side_line1 = next(s["nozzle_tilt_side"] for s in steps if s["line"] == 1 and s["mode"] == "CORRECT")
    side_line2 = next(s["nozzle_tilt_side"] for s in steps if s["line"] == 2 and s["mode"] == "CORRECT")
    assert side_line1 != side_line2
