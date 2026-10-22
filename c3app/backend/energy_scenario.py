"""Energy-model scenarios for sensitivity tests (optional; nothing changes unless the environment variables are set).

Real flight logs (SULEKO, 640 T20P sorties) show that the saved model fits well on average but the data cannot pin down how strongly
the weight of the liquid changes battery use. This module lets us re-run the same planner and agents under other settings:

  C3_LOAD_ALPHA   weight of the liquid in the hover-power formula. 1.0 = physics as saved; 0.5 = half; 0.2 = barely matters.
  C3_ENERGY_SCALE overall power scale (the 'level_scale'). Pair it with alpha so the average sortie still matches the real logs:
                  alpha 1.0 -> 0.888, alpha 0.5 -> 1.174, alpha 0.2 -> 1.38   (fitted on the earlier 70 % of flights, tested on the later 30 %)
  C3_SCENARIO     short name added to output file names (for example a10, a05, a02)
"""
import os, types

PRESETS = {"a10": (1.0, 0.888), "a05": (0.5, 1.174), "a02": (0.2, 1.38)}


def settings():
    name = os.environ.get("C3_SCENARIO", "")
    if name in PRESETS:
        return name, PRESETS[name]
    a, s = os.environ.get("C3_LOAD_ALPHA"), os.environ.get("C3_ENERGY_SCALE")
    if a is None and s is None:
        return "", None
    return name, (float(a if a is not None else 1.0), float(s) if s is not None else None)


def tag():
    n, st = settings()
    return ("_" + (n or "custom")) if st else ""


def apply(model):
    """returns the same model object, changed in place when a scenario is set"""
    n, st = settings()
    if not st:
        return model
    alpha, scale = st
    if scale is not None:
        model.level_scale = scale
    if alpha != 1.0:
        empty = float(model.mass_empty_kg)
        orig = model.hover_power
        model.hover_power = lambda m, _o=orig, _e=empty, _a=alpha: _o(_e + _a * (m - _e))
    model.scenario = (alpha, model.level_scale)
    return model
