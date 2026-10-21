from .db import Session, Setting
from .decision import CFG, DEFAULT_CFG


def load_settings():
    """Apply saved thresholds to the live config (called at startup)."""
    with Session() as s:
        for row in s.query(Setting).all():
            if row.key in DEFAULT_CFG:
                CFG[row.key] = row.value


def save_settings(values):
    with Session() as s:
        for k, v in values.items():
            s.merge(Setting(key=k, value=v))
        s.commit()


def reset_settings():
    CFG.update(DEFAULT_CFG)
    with Session() as s:
        s.query(Setting).delete()
        s.commit()