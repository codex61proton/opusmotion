"""Natural Earth geometry: projections, Skia paths, equirectangular textures."""
import json
import math
import os

import numpy as np
import skia

from .gfx import ROOT, CACHE

GEO = os.path.join(ROOT, "assets", "geo")
_DATA = {}


def load(name="ne_50m_land"):
    if name not in _DATA:
        with open(os.path.join(GEO, name + ".geojson")) as fh:
            _DATA[name] = json.load(fh)
    return _DATA[name]


def rings(name="ne_50m_land", filt=None):
    """Yield (feature_props, ring[[lon,lat],...]) for all polygon rings."""
    for ft in load(name)["features"]:
        props = ft.get("properties", {})
        if filt and not filt(props):
            continue
        g = ft["geometry"]
        if g is None:
            continue
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]] if g["type"] == "Polygon" else []
        if g["type"] in ("LineString", "MultiLineString"):
            lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
            for ln in lines:
                yield props, ln
            continue
        for poly in polys:
            for ring in poly:
                yield props, ring


def country(name, iso=None):
    def f(p):
        return (p.get("ADMIN") == name or p.get("NAME") == name or (iso and p.get("ISO_A3") == iso))
    return f


# --- projections ---------------------------------------------------------------
def ortho(lon0, lat0, R, cx, cy):
    """Orthographic projection; returns f(lon,lat)->(x,y,visible)."""
    l0, p0 = math.radians(lon0), math.radians(lat0)
    sp0, cp0 = math.sin(p0), math.cos(p0)

    def f(lon, lat):
        l, p = math.radians(lon), math.radians(lat)
        cosc = sp0 * math.sin(p) + cp0 * math.cos(p) * math.cos(l - l0)
        x = R * math.cos(p) * math.sin(l - l0)
        y = R * (cp0 * math.sin(p) - sp0 * math.cos(p) * math.cos(l - l0))
        return cx + x, cy - y, cosc >= 0
    return f


def mercator(lon0, lat0, scale, cx, cy):
    def my(lat):
        lat = max(-85, min(85, lat))
        return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    y0 = my(lat0)

    def f(lon, lat):
        return cx + math.radians(lon - lon0) * scale, cy - (my(lat) - y0) * scale, True
    return f


def path_for(proj, name="ne_50m_land", filt=None, clip_hidden=True, min_pts=3, close=True):
    p = skia.Path()
    for _, ring in rings(name, filt):
        if len(ring) < min_pts:
            continue
        started = False
        for lon, lat in ring:
            x, y, vis = proj(lon, lat)
            if clip_hidden and not vis:
                started = False
                continue
            if not started:
                p.moveTo(x, y)
                started = True
            else:
                p.lineTo(x, y)
        if close and started:
            p.close()
    return p


def equirect_mask(name="ne_50m_land", w=4096, h=2048, filt=None, key=None):
    """Land mask as uint8 (h, w), cached."""
    key = key or f"eq_{name}_{w}"
    path = os.path.join(CACHE, key + ".npy")
    if os.path.exists(path):
        return np.load(path)
    surf = skia.Surface(w, h)
    c = surf.getCanvas()
    c.clear(skia.ColorBLACK)
    p = skia.Path()
    for _, ring in rings(name, filt):
        if len(ring) < 3:
            continue
        pts = [((lon + 180) / 360 * w, (90 - lat) / 180 * h) for lon, lat in ring]
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        p.close()
    c.drawPath(p, skia.Paint(AntiAlias=True, Color=skia.ColorWHITE))
    arr = surf.makeImageSnapshot().toarray()[..., 0].copy()
    np.save(path, arr)
    return arr


def gc_path(proj, a, b, n=96):
    """Great-circle arc between (lon,lat) a and b, projected."""
    la1, lo1 = math.radians(a[1]), math.radians(a[0])
    la2, lo2 = math.radians(b[1]), math.radians(b[0])
    v1 = np.array([math.cos(la1) * math.cos(lo1), math.cos(la1) * math.sin(lo1), math.sin(la1)])
    v2 = np.array([math.cos(la2) * math.cos(lo2), math.cos(la2) * math.sin(lo2), math.sin(la2)])
    om = math.acos(max(-1, min(1, float(v1 @ v2))))
    pts = []
    for i in range(n + 1):
        t = i / n
        v = (math.sin((1 - t) * om) * v1 + math.sin(t * om) * v2) / max(math.sin(om), 1e-9)
        lat = math.degrees(math.asin(v[2]))
        lon = math.degrees(math.atan2(v[1], v[0]))
        pts.append(proj(lon, lat))
    return pts
