import asyncio
from . import config
from .db import Session, GpsLog
from .services import gps


def log_fix():
    p = gps.read()
    with Session() as s:
        s.add(GpsLog(lat=p["lat"], lon=p["lon"], alt=p.get("alt"), sats=p.get("sats"),
                     hdop=p.get("hdop"), source=p.get("source")))
        s.commit()
    return p


async def gps_loop():
    """Save one GPS fix every GPS_LOG_INTERVAL_S seconds. Serial reads block, so use a thread."""
    while True:
        try:
            await asyncio.to_thread(log_fix)
        except Exception as e:
            print("GPS logging error:", e)
        await asyncio.sleep(config.GPS_LOG_INTERVAL_S)