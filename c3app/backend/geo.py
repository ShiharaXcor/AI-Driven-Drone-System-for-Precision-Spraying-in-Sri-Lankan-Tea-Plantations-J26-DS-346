# geo.py - new-estate support: KML/KMZ boundary, latitude/longitude, elevation tiles and satellite imagery
#
#   parse_kml(text)                  -> polygon (lon, lat), trees and refill point from a Google Earth KML
#   build_site(lat0, lon0, size)     -> 5 m elevation grid (and imagery png) for a square site around a point
#
# Elevation: Terrarium tiles (public, worldwide, derived from SRTM and other open DEMs; about 30 m real resolution).
# Imagery:   Esri World Imagery tiles (for display only; keep the attribution on screen).
# Both are downloaded once and cached on disk (c3app/cache), so a demo works offline after the first load.
# Override the sources with TERRARIUM_URL / IMAGERY_URL (templates with {z} {x} {y}).
import os, io, re, math, json, hashlib, zipfile, urllib.request
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get("C3_CACHE", os.path.abspath(os.path.join(HERE, "..", "cache")))
TERRARIUM = os.environ.get("TERRARIUM_URL", "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png")
IMAGERY = os.environ.get("IMAGERY_URL", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}")
UA = {"User-Agent": "TeaSprayPlanner/0.1 (university research project)"}
M_LAT = 110574.0


def m_lon(lat):
    return 111320.0 * math.cos(math.radians(lat))


def to_local(lon, lat, lon0, lat0):
    return (np.asarray(lon) - lon0) * m_lon(lat0), (np.asarray(lat) - lat0) * M_LAT


def to_geo(x, y, lon0, lat0):
    return lon0 + np.asarray(x) / m_lon(lat0), lat0 + np.asarray(y) / M_LAT


# ------------------------------------------------------------------ KML / KMZ
def _strip(tag):
    return tag.split("}", 1)[-1]


def parse_kml(data):
    """bytes (kml or kmz) -> dict(polygon=[(lon,lat)...], points=[dict(name,lon,lat)])"""
    if isinstance(data, str):
        data = data.encode("utf-8")
    if data[:2] == b"PK":                               # KMZ = zip with a kml inside
        z = zipfile.ZipFile(io.BytesIO(data))
        name = next((n for n in z.namelist() if n.lower().endswith(".kml")), None)
        if name is None:
            raise ValueError("this KMZ file contains no KML")
        data = z.read(name)
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise ValueError(f"cannot read the KML file: {e}")
    polys, points = [], []

    def coords(text):
        out = []
        for tok in re.split(r"\s+", (text or "").strip()):
            p = tok.split(",")
            if len(p) >= 2:
                try:
                    out.append((float(p[0]), float(p[1])))
                except ValueError:
                    pass
        return out

    for pm in root.iter():
        if _strip(pm.tag) != "Placemark":
            continue
        name = ""
        for ch in pm:
            if _strip(ch.tag) == "name":
                name = (ch.text or "").strip()
        for el in pm.iter():
            t = _strip(el.tag)
            if t == "Polygon":
                for ob in el.iter():
                    if _strip(ob.tag) == "outerBoundaryIs":
                        for c in ob.iter():
                            if _strip(c.tag) == "coordinates":
                                ring = coords(c.text)
                                if len(ring) >= 4:
                                    polys.append(ring[:-1] if ring[0] == ring[-1] else ring)
            elif t == "Point":
                for c in el.iter():
                    if _strip(c.tag) == "coordinates":
                        cc = coords(c.text)
                        if cc:
                            points.append(dict(name=name, lon=cc[0][0], lat=cc[0][1]))
    if not polys and not points:
        raise ValueError("the KML has no polygon or point")

    def area(r):
        a = np.asarray(r)
        return abs(float(np.dot(a[:, 0], np.roll(a[:, 1], -1)) - np.dot(a[:, 1], np.roll(a[:, 0], -1)))) / 2

    poly = max(polys, key=area) if polys else None
    return dict(polygon=poly, points=points)


# ------------------------------------------------------------------ tiles
def _tile_xy(lon, lat, z):
    n = 2 ** z
    x = (np.asarray(lon) + 180.0) / 360.0 * n
    y = (1.0 - np.log(np.tan(np.radians(lat)) + 1.0 / np.cos(np.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def _get_tile(tmpl, z, x, y):
    url = tmpl.format(z=z, x=x, y=y)
    os.makedirs(CACHE, exist_ok=True)
    fn = os.path.join(CACHE, hashlib.md5(url.encode()).hexdigest() + ".png")
    if os.path.exists(fn):
        return Image.open(fn)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
    except Exception as e:
        raise RuntimeError(f"could not download a map tile ({e}). Check the internet connection, "
                           f"or load this estate once online so it is cached.")
    open(fn, "wb").write(raw)
    return Image.open(io.BytesIO(raw))


def _mosaic(tmpl, z, lon_a, lon_b, lat_a, lat_b):
    xa, ya = _tile_xy(min(lon_a, lon_b), max(lat_a, lat_b), z)
    xb, yb = _tile_xy(max(lon_a, lon_b), min(lat_a, lat_b), z)
    tx0, tx1, ty0, ty1 = int(math.floor(xa)), int(math.floor(xb)), int(math.floor(ya)), int(math.floor(yb))
    if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) > 60:
        raise RuntimeError("the area needs too many map tiles; use a smaller area")
    first = None
    rows = []
    for ty in range(ty0, ty1 + 1):
        row = []
        for tx in range(tx0, tx1 + 1):
            im = _get_tile(tmpl, z, tx, ty).convert("RGB")
            row.append(np.asarray(im))
        rows.append(np.concatenate(row, axis=1))
    return np.concatenate(rows, axis=0), tx0, ty0


def _warp(img, z, tx0, ty0, lon, lat, order=1):
    """sample the mosaic at the given lon/lat arrays (any shape)"""
    x, y = _tile_xy(lon, lat, z)
    px, py = (x - tx0) * 256.0 - 0.5, (y - ty0) * 256.0 - 0.5
    out = np.stack([map_coordinates(img[..., c].astype(float), [py.ravel(), px.ravel()], order=order, mode="nearest")
                    for c in range(img.shape[2])], -1)
    return out.reshape(lon.shape + (img.shape[2],))


# ------------------------------------------------------------------ site
def site_dem(lat0, lon0, size, grid=5.0, zoom=14):
    n = int(round(size / grid))
    xs = (np.arange(n) + 0.5) * grid
    X, Y = np.meshgrid(xs, xs, indexing="ij")               # [i][j]: i east, j north (engine convention)
    lon, lat = to_geo(X - size / 2, Y - size / 2, lon0, lat0)
    pad = 20.0 / m_lon(lat0)
    img, tx0, ty0 = _mosaic(TERRARIUM, zoom, lon.min() - pad, lon.max() + pad, lat.min() - 20 / M_LAT, lat.max() + 20 / M_LAT)
    rgb = _warp(img, zoom, tx0, ty0, lon, lat)
    z = rgb[..., 0] * 256.0 + rgb[..., 1] + rgb[..., 2] / 256.0 - 32768.0
    return z


def site_imagery(lat0, lon0, size, px=1024):
    zoom = 18 if size <= 400 else 17
    xs = (np.arange(px) + 0.5) / px * size
    X, Y = np.meshgrid(xs, xs[::-1], indexing="xy")          # image row 0 = north
    lon, lat = to_geo(X - size / 2, Y - size / 2, lon0, lat0)
    img, tx0, ty0 = _mosaic(IMAGERY, zoom, lon.min() - 2 / m_lon(lat0), lon.max() + 2 / m_lon(lat0), lat.min() - 2 / M_LAT, lat.max() + 2 / M_LAT)
    rgb = _warp(img, zoom, tx0, ty0, lon, lat)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
