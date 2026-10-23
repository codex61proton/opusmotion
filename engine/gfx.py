"""Skia drawing helpers: palette, paints, paths, layers, textures."""
import math
import os
from contextlib import contextmanager

import numpy as np
import skia

from .core import W, H, clamp, lerp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "build", "cache")
os.makedirs(CACHE, exist_ok=True)

# --- palette ------------------------------------------------------------------
P = {
    "paper": "#E9E2D0", "paper2": "#DDD4BE", "paper3": "#C8BDA2", "paper_hi": "#F4EFE3",
    "ink": "#14161A", "ink2": "#2E3138", "ink3": "#5B5E66", "ink4": "#8D8F95",
    "red": "#D2232A", "red2": "#9E1A20", "red3": "#5E0F14",
    "night": "#070A0F", "night2": "#0D131C", "night3": "#16202D", "night4": "#22303F",
    "grid": "#2A3A4D", "steel": "#7F93A8",
    "cyan": "#8FD0FF", "cyan2": "#CFEAFF", "cyan3": "#3C86C4",
    "amber": "#FFB13D", "amber2": "#FFD89A", "amber3": "#B8650F",
    "brass": "#B08A4A", "white": "#FFFFFF", "black": "#000000",
}


def hexrgb(h):
    h = P.get(h, h).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def C(h, a=1.0):
    """Skia ARGB int from hex/palette key and alpha 0..1."""
    if isinstance(h, tuple):
        r, g, b = h[:3]
    else:
        r, g, b = hexrgb(h)
    return skia.Color(int(r), int(g), int(b), int(round(clamp(a) * 255)))


def mix(h1, h2, t):
    a, b = hexrgb(h1) if not isinstance(h1, tuple) else h1, hexrgb(h2) if not isinstance(h2, tuple) else h2
    return tuple(int(round(lerp(a[i], b[i], clamp(t)))) for i in range(3))


def paint(color="ink", a=1.0, stroke=None, cap="round", join="round", blend=None,
          blur=None, shader=None, effect=None, aa=True, miter=4):
    p = skia.Paint(AntiAlias=aa)
    p.setColor(C(color, a))
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap({"round": skia.Paint.kRound_Cap, "butt": skia.Paint.kButt_Cap,
                        "square": skia.Paint.kSquare_Cap}[cap])
        p.setStrokeJoin({"round": skia.Paint.kRound_Join, "miter": skia.Paint.kMiter_Join,
                         "bevel": skia.Paint.kBevel_Join}[join])
        p.setStrokeMiter(miter)
    if blend:
        p.setBlendMode(getattr(skia.BlendMode, "k" + blend))
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None:
        p.setShader(shader)
    if effect is not None:
        p.setPathEffect(effect)
    return p


def lin_grad(p0, p1, stops, pos=None, a=1.0):
    cols = [C(s, a) if not isinstance(s, (list,)) else C(s[0], s[1] * a) for s in stops]
    return skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)], cols, pos)


def rad_grad(c, r, stops, pos=None, a=1.0):
    cols = [C(s, a) if not isinstance(s, (list,)) else C(s[0], s[1] * a) for s in stops]
    return skia.GradientShader.MakeRadial(skia.Point(*c), max(r, 1e-3), cols, pos)


# --- path helpers ----------------------------------------------------------------
def poly(pts, close=True):
    p = skia.Path()
    if not pts:
        return p
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close:
        p.close()
    return p


def smooth(pts, close=False, tension=0.5):
    """Catmull-Rom spline through points as a cubic path."""
    p = skia.Path()
    n = len(pts)
    if n < 2:
        return p
    p.moveTo(*pts[0])
    rng_ = range(n if close else n - 1)
    for i in rng_:
        p0 = pts[(i - 1) % n] if (close or i > 0) else pts[i]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (close or i + 2 < n) else p2
        k = tension / 3 * 2
        c1 = (p1[0] + (p2[0] - p0[0]) * k / 2, p1[1] + (p2[1] - p0[1]) * k / 2)
        c2 = (p2[0] - (p3[0] - p1[0]) * k / 2, p2[1] - (p3[1] - p1[1]) * k / 2)
        p.cubicTo(*c1, *c2, *p2)
    if close:
        p.close()
    return p


def rrect(x, y, w, h, r):
    return skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)


def rect(x, y, w, h):
    return skia.Rect.MakeXYWH(x, y, w, h)


def trim(p, a=0.0, b=1.0):
    a, b = clamp(a), clamp(b)
    if b <= a:
        return None
    return skia.TrimPathEffect.Make(a, b)


def dash(on, off, phase=0.0):
    return skia.DashPathEffect.Make([on, off], phase)


def path_len(path):
    m = skia.PathMeasure(path, False)
    total = 0.0
    while True:
        total += m.getLength()
        if not m.nextContour():
            break
    return total


def point_at(path, t):
    """Position and tangent angle at fraction t of the first contour."""
    m = skia.PathMeasure(path, False)
    L = m.getLength()
    r = m.getPosTan(clamp(t) * L)
    pos, tan = r[-2], r[-1]
    return (pos.x(), pos.y()), math.atan2(tan.y(), tan.x())


def stroke_path(c, path, color="ink", w=3, a=1.0, t0=0.0, t1=1.0, cap="round", d=None, blend=None, blur=None):
    if t1 - t0 <= 1e-4 or a <= 0.002:
        return
    p = paint(color, a, stroke=w, cap=cap, blend=blend, blur=blur)
    effs = []
    if t0 > 0 or t1 < 1:
        effs.append(skia.TrimPathEffect.Make(clamp(t0), clamp(t1)))
    if d:
        effs.append(dash(*d))
    if len(effs) == 1:
        p.setPathEffect(effs[0])
    elif len(effs) == 2:
        p.setPathEffect(skia.PathEffect.MakeCompose(effs[1], effs[0]))
    c.drawPath(path, p)


def arrow_head(c, tip, ang, size=18, color="ink", a=1.0):
    l = (tip[0] - size * math.cos(ang - 0.45), tip[1] - size * math.sin(ang - 0.45))
    r = (tip[0] - size * math.cos(ang + 0.45), tip[1] - size * math.sin(ang + 0.45))
    c.drawPath(poly([tip, l, r]), paint(color, a))


# --- layers & transforms -----------------------------------------------------------
@contextmanager
def layer(c, alpha=1.0, blend=None, filt=None, bounds=None):
    p = skia.Paint()
    p.setAlphaf(clamp(alpha))
    if blend:
        p.setBlendMode(getattr(skia.BlendMode, "k" + blend))
    if filt is not None:
        p.setImageFilter(filt)
    c.saveLayer(bounds, p)
    try:
        yield c
    finally:
        c.restore()


@contextmanager
def xf(c, tx=0.0, ty=0.0, s=1.0, rot=0.0, px=0.0, py=0.0, sx=None, sy=None):
    """Translate, then scale/rotate around pivot (px, py) in local coords."""
    c.save()
    c.translate(tx, ty)
    if rot or s != 1 or sx is not None or sy is not None:
        c.translate(px, py)
        if rot:
            c.rotate(rot)
        c.scale(sx if sx is not None else s, sy if sy is not None else s)
        c.translate(-px, -py)
    try:
        yield c
    finally:
        c.restore()


@contextmanager
def clip(c, shape):
    c.save()
    if isinstance(shape, skia.Path):
        c.clipPath(shape, doAntiAlias=True)
    elif isinstance(shape, skia.RRect):
        c.clipRRect(shape, doAntiAlias=True)
    else:
        c.clipRect(shape, doAntiAlias=True)
    try:
        yield c
    finally:
        c.restore()


def blur_filter(sigma):
    return skia.ImageFilters.Blur(sigma, sigma) if sigma > 0.05 else None


def glow(c, draw, sigma=18, a=0.8, blend="Plus", bounds=None):
    """Render draw(c) blurred and added on top (bloom-ish halo). bounds limits the offscreen layer (big speed win)."""
    with layer(c, a, blend=blend, filt=skia.ImageFilters.Blur(sigma, sigma), bounds=bounds):
        draw(c)


def around(x, y, r):
    return skia.Rect.MakeLTRB(x - r, y - r, x + r, y + r)


def shadow(c, shape, dx=0, dy=14, sigma=22, a=0.28, color="black"):
    p = paint(color, a, blur=sigma)
    with xf(c, dx, dy):
        if isinstance(shape, skia.Path):
            c.drawPath(shape, p)
        elif isinstance(shape, skia.RRect):
            c.drawRRect(shape, p)
        else:
            c.drawRect(shape, p)


# --- images & textures --------------------------------------------------------------
def to_image(arr):
    arr = np.ascontiguousarray(arr)
    if arr.ndim == 2:
        arr = np.dstack([arr, arr, arr, np.full_like(arr, 255)])
    if arr.shape[2] == 3:
        arr = np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)])
    return skia.Image.fromarray(arr.astype(np.uint8), colorType=skia.kRGBA_8888_ColorType,
                                alphaType=skia.kUnpremul_AlphaType)


def draw_image(c, img, x, y, w=None, h=None, a=1.0, blend=None, sampling=True):
    w = w or img.width()
    h = h or img.height()
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(a))
    if blend:
        p.setBlendMode(getattr(skia.BlendMode, "k" + blend))
    s = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear) if sampling else skia.SamplingOptions()
    c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h), s, p)


_IMG = {}


def cached_image(key, builder):
    if key in _IMG:
        return _IMG[key]
    path = os.path.join(CACHE, key + ".png")
    if os.path.exists(path):
        img = skia.Image.open(path)
    else:
        arr = builder()
        img = to_image(arr)
        img.save(path, skia.kPNG)
    _IMG[key] = img
    return img


def _fbm2(h, w, seed, scales=(4, 16, 64, 256), weights=(1, .5, .25, .12)):
    from scipy.ndimage import zoom
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    for s, wt in zip(scales, weights):
        gh, gw = max(2, h // s + 2), max(2, w // s + 2)
        g = r.standard_normal((gh, gw)).astype(np.float32)
        z = zoom(g, (h / (gh - 1), w / (gw - 1)), order=3)[:h, :w]
        out += wt * z
    out -= out.mean()
    out /= (out.std() + 1e-6)
    return out


def paper_texture(seed=7, w=W, h=H):
    """Archival paper: warm base, blotchy aging, fibres, faint foxing."""
    def build():
        from scipy.ndimage import gaussian_filter
        r = np.random.default_rng(seed)
        base = np.array(hexrgb("paper"), np.float32)
        blot = _fbm2(h, w, seed, scales=(3, 9, 40, 160), weights=(1, .7, .35, .2))
        fine = gaussian_filter(r.standard_normal((h, w)).astype(np.float32), 0.7)
        img = np.ones((h, w, 3), np.float32) * base
        img += blot[..., None] * np.array([5.5, 5.0, 6.5]) + fine[..., None] * 3.2
        # fibres
        fib = np.zeros((h, w), np.float32)
        for _ in range(2600):
            x0, y0 = r.uniform(0, w), r.uniform(0, h)
            ang, L = r.uniform(0, np.pi), r.uniform(8, 46)
            n = int(L)
            xs = (x0 + np.cos(ang) * np.arange(n) + np.cumsum(r.normal(0, .25, n))).astype(int) % w
            ys = (y0 + np.sin(ang) * np.arange(n) + np.cumsum(r.normal(0, .25, n))).astype(int) % h
            fib[ys, xs] += r.uniform(-1, 1)
        fib = gaussian_filter(fib, 0.6)
        img += fib[..., None] * 9
        # foxing spots
        fox = np.zeros((h, w), np.float32)
        for _ in range(40):
            cx, cy, rad = r.uniform(0, w), r.uniform(0, h), r.uniform(3, 18)
            yy, xx = np.ogrid[:h, :w]
            m = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rad * rad)))
            fox += m * r.uniform(.2, 1)
        img -= fox[..., None] * np.array([6, 12, 22])
        # edge darkening
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.minimum(np.minimum(xx, w - xx), np.minimum(yy, h - yy)) / min(w, h)
        img *= (0.93 + 0.07 * np.clip(d * 6, 0, 1))[..., None]
        return np.clip(img, 0, 255).astype(np.uint8)
    return cached_image(f"paper_{seed}_{w}x{h}", build)


def night_texture(seed=3, w=W, h=H):
    """Deep blue-black backdrop with subtle mottling."""
    def build():
        blot = _fbm2(h, w, seed, scales=(3, 10, 50, 200), weights=(1, .6, .3, .15))
        base = np.array(hexrgb("night2"), np.float32)
        img = np.ones((h, w, 3), np.float32) * base + blot[..., None] * np.array([1.6, 2.0, 2.8])
        return np.clip(img, 0, 255).astype(np.uint8)
    return cached_image(f"night_{seed}_{w}x{h}", build)


def bg_paper(c, seed=7, tint=None, a=1.0):
    draw_image(c, paper_texture(seed), 0, 0, W, H, a)
    if tint:
        c.drawRect(rect(0, 0, W, H), paint(tint[0], tint[1], blend="Multiply"))


def bg_night(c, seed=3, glow_at=None, glow_col="night4", glow_r=1100):
    draw_image(c, night_texture(seed), 0, 0, W, H)
    if glow_at:
        c.drawRect(rect(0, 0, W, H), paint(shader=rad_grad(glow_at, glow_r, [[glow_col, .9], [glow_col, 0]])))
