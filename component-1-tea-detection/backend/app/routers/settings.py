from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from ..auth import require_key
from ..decision import CFG, DEFAULT_CFG
from ..settings_store import save_settings, reset_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])
SAFETY_MAX_STOP = 0.50     # a person or animal stop threshold above this would be unsafe


def _validate(new):
    for k, v in new.items():
        if not 0.0 <= v <= 1.0:
            raise HTTPException(400, f"{k} must be between 0 and 1")
    for p in ("person", "animal", "anomaly"):
        if new[f"{p}_stop"] < new[f"{p}_uncertain"]:
            raise HTTPException(400, f"{p}_stop must be >= {p}_uncertain")
    if new["tea_spray"] < new["tea_uncertain"]:
        raise HTTPException(400, "tea_spray must be >= tea_uncertain")
    for k in ("person_stop", "animal_stop"):
        if new[k] > SAFETY_MAX_STOP:
            raise HTTPException(400, f"{k} cannot exceed {SAFETY_MAX_STOP} (safety limit)")


@router.get("")
def get_settings():
    return {"current": dict(CFG), "defaults": DEFAULT_CFG, "safety_max_stop": SAFETY_MAX_STOP}


@router.put("", dependencies=[Depends(require_key)])
def update_settings(body: Dict[str, float]):
    unknown = set(body) - set(DEFAULT_CFG)
    if unknown:
        raise HTTPException(400, f"Unknown settings: {sorted(unknown)}")
    new = {**CFG, **body}
    _validate(new)
    CFG.update(new)
    save_settings(body)
    return {"current": dict(CFG)}


@router.post("/reset", dependencies=[Depends(require_key)])
def reset():
    reset_settings()
    return {"current": dict(CFG)}