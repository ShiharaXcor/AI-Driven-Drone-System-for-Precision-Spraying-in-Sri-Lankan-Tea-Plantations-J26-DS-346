import time
from .db import Session, SprayTest
from .decision import decide, Det, DEFAULT_CFG
from .services import STATE, relay, resolve_control


ANOMALY_CLASSES = ["road", "rock", "bare_soil", "building", "water", "non_tea_vegetation"]
TEA = ("tea_plant", 0.90)


def _r(a, b, step=1):
    """Confidence values from a/100 to b/100."""
    return [round(i / 100, 2) for i in range(a, b + 1, step)]


def build_scenarios():
    """Expected pump action (ON/OFF) comes from the written spray rules, NOT from the engine:
      - person/animal >= 0.30            -> OFF (stop)
      - person/animal 0.15 to 0.29       -> OFF (UNCERTAIN)
      - person/animal < 0.15             -> ignored
      - other anomaly >= 0.60            -> OFF (stop); 0.40 to 0.59 -> OFF (UNCERTAIN); < 0.40 ignored
      - tea >= 0.70 and no hazard        -> ON;  0.50 to 0.69 -> OFF (UNCERTAIN);  < 0.50 -> OFF
      - outside geofence, poor image, emergency stop -> OFF
    If you change the thresholds in decision.py, update these families too."""
    S = []

    def add(family, label, dets, expected, **flags):
        S.append(dict(family=family, label=label, dets=dets, expected=expected, **flags))

    for c in _r(72, 99):
        add("clean_tea", f"tea={c}", [("tea_plant", c)], "ON")
    for c in _r(50, 69):
        add("tea_uncertain", f"tea={c}", [("tea_plant", c)], "OFF")
    for c in _r(5, 49):
        add("tea_low", f"tea={c}", [("tea_plant", c)], "OFF")
    add("no_detection", "no objects", [], "OFF")

    for cls in ("person", "animal"):
        for c in _r(30, 99):
            add(f"{cls}_stop", f"{cls}={c}", [TEA, (cls, c)], "OFF")
        for c in _r(15, 29):
            add(f"{cls}_uncertain", f"{cls}={c}", [TEA, (cls, c)], "OFF")
        for c in _r(1, 14):
            add(f"{cls}_low_ignored", f"{cls}={c}", [TEA, (cls, c)], "ON")

    for cls in ANOMALY_CLASSES:
        for c in _r(60, 95, 5):
            add("anomaly_stop", f"{cls}={c}", [TEA, (cls, c)], "OFF")
        for c in _r(40, 58, 2):
            add("anomaly_uncertain", f"{cls}={c}", [TEA, (cls, c)], "OFF")
        for c in _r(10, 38, 4):
            add("anomaly_low_ignored", f"{cls}={c}", [TEA, (cls, c)], "ON")

    add("safety_gate", "outside geofence", [TEA], "OFF", geofence_ok=False)
    add("safety_gate", "poor image quality", [TEA], "OFF", image_ok=False)

    add("boundary", "tea exactly 0.70", [("tea_plant", 0.70)], "ON")
    add("boundary", "person exactly 0.30", [TEA, ("person", 0.30)], "OFF")
    add("boundary", "person exactly 0.15", [TEA, ("person", 0.15)], "OFF")
    add("boundary", "road exactly 0.60", [TEA, ("road", 0.60)], "OFF")

    add("control", "emergency stop with clean tea", [TEA], "OFF", emergency=True)
    add("control", "emergency stop beats manual ON", [TEA], "OFF", emergency=True, manual="ON")
    add("control", "manual OFF with clean tea", [TEA], "OFF", manual="OFF")
    add("control", "manual ON with clean tea", [TEA], "ON", manual="ON")
    return S


def run_all(reset=True):
    """Run every scenario through decide() and the control priority, save results to MySQL."""
    saved = dict(STATE)
    rows = []
    try:
        for sc in build_scenarios():
            STATE["emergency"] = sc.get("emergency", False)
            STATE["manual"] = sc.get("manual")
            dets = [Det(c, v) for c, v in sc["dets"]]

            t0 = time.perf_counter()
            decision, reason = decide(dets, cfg=DEFAULT_CFG, geofence_ok=sc.get("geofence_ok", True),
                    image_ok=sc.get("image_ok", True))
            _, _, status = resolve_control(decision, reason)
            relay.set(status == "ON")
            ms = (time.perf_counter() - t0) * 1000

            actual = "ON" if relay.on else "OFF"
            rows.append(SprayTest(scenario=f"{sc['family']} | {sc['label']}", expected=sc["expected"],
                                  actual=actual, passed=(actual == sc["expected"]), response_ms=ms))
    finally:
        STATE.update(saved)
        relay.set(False)

    with Session() as s:
        if reset:
            s.query(SprayTest).delete()
        s.add_all(rows)
        s.commit()
    return summarize()


def summarize():
    with Session() as s:
        rows = s.query(SprayTest).all()
    if not rows:
        return {"total": 0}
    times = sorted(r.response_ms for r in rows if r.response_ms is not None)
    fam = {}
    for r in rows:
        f = r.scenario.split(" | ")[0]
        a = fam.setdefault(f, {"total": 0, "passed": 0})
        a["total"] += 1
        a["passed"] += 1 if r.passed else 0
    passed = sum(1 for r in rows if r.passed)
    return {
        "total": len(rows), "passed": passed, "failed": len(rows) - passed,
        "pass_rate": round(passed / len(rows), 4),
        "avg_ms": round(sum(times) / len(times), 3),
        "p95_ms": round(times[int(0.95 * (len(times) - 1))], 3),
        "max_ms": round(times[-1], 3),
        "by_family": fam,
        "failures": [{"scenario": r.scenario, "expected": r.expected, "actual": r.actual}
                     for r in rows if not r.passed][:20],
    }