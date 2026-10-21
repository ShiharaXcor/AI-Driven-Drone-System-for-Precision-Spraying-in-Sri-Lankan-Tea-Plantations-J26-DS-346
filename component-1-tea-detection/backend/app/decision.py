from dataclasses import dataclass

from typing import Optional, Tuple

@dataclass
class Det:
    cls: str
    conf: float
    bbox: Optional[Tuple[int, int, int, int]] = None


# Safety classes use LOW stop thresholds: stopping by mistake is safer than missing a person.
CFG = {
    "person_stop": 0.30,  "person_uncertain": 0.15,
    "animal_stop": 0.30,  "animal_uncertain": 0.15,
    "anomaly_stop": 0.60, "anomaly_uncertain": 0.40,
    "tea_spray": 0.70,    "tea_uncertain": 0.50,
}
ANOMALY = {"road", "rock", "bare_soil", "building", "water", "non_tea_vegetation"}


def _max(dets, names):
    vals = [d.conf for d in dets if d.cls in names]
    return max(vals) if vals else 0.0


def decide(dets, cfg=CFG, geofence_ok=True, image_ok=True):
    """Return (decision, reason). decision is SPRAY, NO_SPRAY or UNCERTAIN."""
    person = _max(dets, {"person"})
    animal = _max(dets, {"animal"})
    anomaly = _max(dets, ANOMALY)
    tea = _max(dets, {"tea_plant"})

    if not geofence_ok:
        return "NO_SPRAY", "Outside geofence"
    if person >= cfg["person_stop"]:
        return "NO_SPRAY", f"Person detected ({person:.2f})"
    if animal >= cfg["animal_stop"]:
        return "NO_SPRAY", f"Animal detected ({animal:.2f})"
    if person >= cfg["person_uncertain"] or animal >= cfg["animal_uncertain"]:
        return "UNCERTAIN", "Possible person or animal, low confidence"
    if anomaly >= cfg["anomaly_stop"]:
        return "NO_SPRAY", f"Non-target area detected ({anomaly:.2f})"
    if not image_ok:
        return "UNCERTAIN", "Poor image quality"
    if anomaly >= cfg["anomaly_uncertain"]:
        return "UNCERTAIN", "Possible non-target area"
    if tea >= cfg["tea_spray"]:
        return "SPRAY", f"Tea detected ({tea:.2f}), no hazards"
    if tea >= cfg["tea_uncertain"]:
        return "UNCERTAIN", f"Tea confidence low ({tea:.2f})"
    return "NO_SPRAY", "No tea detected"

DEFAULT_CFG = dict(CFG)     # factory thresholds, used by the spray tests and "reset"