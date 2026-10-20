"""
Read GPS coordinates from a photo's EXIF data (phones and most drones store it).

Used by the demo so each region in the prescription gets a real location until
Component 3 provides positions from the flight log. Returns None when the photo
has no GPS (e.g. images re-saved by the preprocessing step, which drops EXIF).
"""

from PIL import Image

GPS_TAG = 34853  # EXIF GPSInfo


def _to_degrees(dms, ref) -> float:
    d, m, s = (float(x) for x in dms)
    value = d + m / 60 + s / 3600
    return -value if ref in ("S", "W") else value


def read_gps(file_or_path):
    """Return (lat, lon) as floats, or None if the image has no usable GPS."""
    try:
        with Image.open(file_or_path) as img:
            gps = img.getexif().get_ifd(GPS_TAG)
        if not gps or 2 not in gps or 4 not in gps:
            return None
        lat = _to_degrees(gps[2], gps.get(1, "N"))
        lon = _to_degrees(gps[4], gps.get(3, "E"))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            return None
        return round(lat, 7), round(lon, 7)
    except Exception:
        return None
