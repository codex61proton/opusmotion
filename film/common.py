"""Shared timeline layout + drawing helpers for the film."""
import json
import math
import os

import numpy as np
import skia

from engine.core import *
from engine.gfx import *
from engine import text as T
from engine import planet as PL
from engine.text import Card, parse_card
from film.script import SEGMENTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD, TAIL = 0.9, 3.4

# site coordinates (lon, lat)
SARY = (73.6, 46.1)          # Sary Shagan test range HQ, Kazakh SSR
STANFORD = (-122.18, 37.41)  # Stanford 150-ft dish, Palo Alto
CHESAPEAKE = (-76.53, 38.66)  # NRL Chesapeake Bay Annex, Maryland
USSR = {"Russia", "Ukraine", "Belarus", "Kazakhstan", "Uzbekistan", "Turkmenistan", "Kyrgyzstan", "Tajikistan",
        "Georgia", "Armenia", "Azerbaijan", "Moldova", "Lithuania", "Latvia", "Estonia"}


# ------------------------------------------------------------------ timeline from narration
_LAYOUT = None


def layout():
    """Absolute segment times, caption cards and total duration from build/vo/timing.json."""
    global _LAYOUT
    if _LAYOUT:
        return _LAYOUT
    tim = json.load(open(os.path.join(ROOT, "build", "vo", "timing.json")))
    t = HEAD
    segs, raw = {}, []
    for i, (sid, gap, cards) in enumerate(SEGMENTS):
        if i:
            t += gap
        d = tim[sid]
        toks = d["tokens"]
        segs[sid] = dict(t0=t, t1=t + d["dur"], dur=d["dur"], words=[(t + a, t + b, w) for a, b, w in d["words"]])
        k = 0
        seg_cards = []
        for c in cards:
            lines = parse_card(c)
            for ln in lines:
                for tok in ln:
                    src = toks[k]
                    assert src["text"] == tok["text"], (sid, src["text"], tok["text"])
                    tok["t"], tok["t_end"] = t + src["t0"], t + src["t1"]
                    k += 1
            seg_cards.append(lines)
        segs[sid]["cards"] = seg_cards
        raw += [(sid, ls) for ls in seg_cards]
        t += d["dur"]
    total = t + TAIL
    cards = []
    for i, (sid, lines) in enumerate(raw):
        first, last = lines[0][0]["t"], lines[-1][-1]["t_end"]
        nxt = raw[i + 1][1][0][0]["t"] if i + 1 < len(raw) else total
        cards.append(Card(lines, first - 0.08, min(nxt - 0.1, last + 1.1)))
    _LAYOUT = (segs, cards, total)
    return _LAYOUT


def S(sid):
    return layout()[0][sid]


def word_t(sid, word, nth=0):
    """Absolute start time of the nth occurrence of `word` (case-insensitive, punctuation-stripped) in a segment."""
    import re
    n = 0
    for a, b, w in S(sid)["words"]:
        if re.sub(r"[^a-z0-9]", "", w.lower()) == re.sub(r"[^a-z0-9]", "", word.lower()):
            if n == nth:
                return a
            n += 1
    raise KeyError((sid, word))


def tok_t(sid, text, nth=0):
    """Absolute time of a caption token (display text, punctuation-insensitive)."""
    import re
    key = re.sub(r"[^a-z0-9]", "", text.lower())
    n = 0
    for lines in S(sid)["cards"]:
        for ln in lines:
            for tok in ln:
                if re.sub(r"[^a-z0-9]", "", tok["text"].lower()) == key:
                    if n == nth:
                        return tok["t"]
                    n += 1
    raise KeyError((sid, text))


# ------------------------------------------------------------------ fonts / text helpers
def F(name, size):
    return T.font(name, size)


def label(c, s, x, y, size=30, color="cyan2", a=1.0, align="left", font="mono", track=0.08):
    T.text(c, s, x, y, F(font, size), color, a, align=align, track=track)


def type_on(s, k):
    """Typewriter reveal of string s at progress k (0..1)."""
    n = int(round(len(s) * clamp(k)))
    return s[:n]


def tag(c, s, x, y, size=26, fg="night", bg="cyan", a=1.0, align="left", pad=(14, 8), font="mono_b"):
    f = F(font, size)
    w = T.width(s, f, 0.08)
    if align == "center":
        x -= w / 2 + pad[0]
    elif align == "right":
        x -= w + pad[0] * 2
    m = f.getMetrics()
    h = -m.fAscent * 0.78 + pad[1] * 2
    c.drawRect(rect(x, y - h + pad[1] * 0.6, w + pad[0] * 2, h), paint(bg, a))
    T.text(c, s, x + pad[0], y, f, fg, a, track=0.08)
    return w + pad[0] * 2


# ------------------------------------------------------------------ backgrounds
def star_image(seed=5, n=1400, w=W, h=H):
    def build():
        r = rng(seed)
        surf = skia.Surface(w, h)
        c = surf.getCanvas()
        c.clear(skia.ColorTRANSPARENT)
        for i in range(n):
            x, y = r.random() * w, r.random() * h
            m = r.random() ** 3.2
            rad = 0.6 + 1.9 * m
            col = mix("cyan2", "amber2", r.random() * 0.35) if r.random() < 0.25 else (255, 255, 255)
            c.drawCircle(x, y, rad, paint(col, 0.25 + 0.75 * m))
            if m > 0.82:
                c.drawCircle(x, y, rad * 5, paint(col, 0.12, blur=rad * 3))
        return surf.makeImageSnapshot()
    return cached_image(f"stars{seed}_{n}_{w}x{h}", build)


def bg_space(c, t, seed=5, drift=(0, 0), a=1.0, glow_at=None):
    c.drawRect(rect(0, 0, W, H), paint("#020306"))
    img = star_image(seed)
    dx, dy = drift
    x, y = (dx * t) % W, (dy * t) % H
    for ox in (-W, 0):
        for oy in (-H, 0):
            draw_image(c, img, x + ox, y + oy, W, H, a * 0.9)
    if glow_at:
        gx, gy, gr, gc, ga = glow_at
        c.drawRect(rect(0, 0, W, H), paint(shader=rad_grad((gx, gy), gr, [[gc, ga], [gc, 0.0]])))


def vignette_band(c, top=True, h=560, a=0.85):
    """Darken behind captions for legibility."""
    if top:
        c.drawRect(rect(0, 0, W, h), paint(shader=lin_grad((0, 0), (0, h), [["black", a], ["black", 0.0]])))
    else:
        c.drawRect(rect(0, H - h, W, h), paint(shader=lin_grad((0, H), (0, H - h), [["black", a], ["black", 0.0]])))


# ------------------------------------------------------------------ HUD chrome
def hud(c, t, file_no="01", title="MOON BOUNCE ELINT", src="", a=1.0, color="cyan2", t0=0.0):
    k = clamp((t - t0) / 0.6) * a
    if k <= 0:
        return
    m = 54
    L = 46
    p = paint(color, 0.55 * k, stroke=3, cap="butt")
    for (x, y, sx, sy) in ((m, 200, 1, 1), (W - m, 200, -1, 1), (m, 1700, 1, -1), (W - m, 1700, -1, -1)):
        c.drawLine(x, y, x + L * sx, y, p)
        c.drawLine(x, y, x, y + L * sy, p)
    f = F("mono", 22)
    T.text(c, f"FILE {file_no}  /  {title}", m + 2, 182, f, color, 0.7 * k, track=0.14)
    rec = (int(t * 2) % 2 == 0)
    c.drawCircle(W - m - 8, 174, 6, paint("red", (0.9 if rec else 0.35) * k))
    T.text(c, "DECLASSIFIED", W - m - 26, 182, f, color, 0.7 * k, align="right", track=0.14)
    if src:
        T.text(c, src, W / 2, 1738, F("mono_r", 20), color, 0.55 * k, align="center", track=0.1)


def ring_pulse(c, x, y, t, color="red", r0=10, r1=60, period=1.4, a=1.0, n=2):
    for i in range(n):
        ph = ((t / period) + i / n) % 1.0
        c.drawCircle(x, y, r0 + (r1 - r0) * out_cubic(ph), paint(color, a * (1 - ph) * 0.8, stroke=3))


def pin(c, x, y, t, t_in, text_s="", color="red", side=1, size=26, sub=None, a=1.0, lead=110):
    k = clamp((t - t_in) / 0.45)
    if k <= 0:
        return
    e = out_back(k)
    c.drawCircle(x, y, 9 * e, paint(color, a))
    c.drawCircle(x, y, 16 * e, paint(color, a * 0.8, stroke=2.5))
    ring_pulse(c, x, y, t - t_in, color, 16, 70, 1.6, a * k)
    if text_s:
        kk = out_expo(clamp((t - t_in - 0.15) / 0.6))
        x1 = x + side * lead * kk
        y1 = y - 60 * kk
        c.drawPath(poly([(x + side * 18, y - 10), (x1 - side * 0, y1), (x1 + side * 22, y1)], close=False),
                   paint(color, a * kk, stroke=2.5))
        f = F("mono_b", size)
        s = type_on(text_s, clamp((t - t_in - 0.3) / 0.5))
        T.text(c, s, x1 + side * 30, y1 + size * 0.35, f, "white", a * kk, align="left" if side > 0 else "right",
               track=0.08)
        if sub:
            T.text(c, type_on(sub, clamp((t - t_in - 0.55) / 0.6)), x1 + side * 30, y1 + size * 0.35 + size * 1.25,
                   F("mono_r", size * 0.75), color, a * kk * 0.9, align="left" if side > 0 else "right", track=0.08)


def brackets(c, x, y, w, h, color="cyan2", a=1.0, L=28, sw=3):
    p = paint(color, a, stroke=sw, cap="butt")
    for (px, py, sx, sy) in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        c.drawLine(px, py, px + L * sx, py, p)
        c.drawLine(px, py, px, py + L * sy, p)


# ------------------------------------------------------------------ pulses / beams
def pulse_along(c, p0, p1, k, color="cyan", width=6, length=0.12, a=1.0, glow_s=14):
    """A bright pulse segment travelling from p0 to p1 at progress k (0..1)."""
    if k <= 0 or k >= 1 + length:
        return
    a0, a1 = clamp(k - length), clamp(k)
    x0, y0 = lerp(p0[0], p1[0], a0), lerp(p0[1], p1[1], a0)
    x1, y1 = lerp(p0[0], p1[0], a1), lerp(p0[1], p1[1], a1)
    sh = lin_grad((x0, y0), (x1, y1), [[color, 0.0], [color, a], ["white", a]], [0, 0.8, 1])
    p = paint(color, a, stroke=width, shader=sh)
    c.drawLine(x0, y0, x1, y1, p)
    pad = glow_s * 3 + width * 2
    bnd = skia.Rect.MakeLTRB(min(x0, x1) - pad, min(y0, y1) - pad, max(x0, x1) + pad, max(y0, y1) + pad)
    with layer(c, 0.9, blend="Plus", filt=skia.ImageFilters.Blur(glow_s, glow_s), bounds=bnd):
        c.drawLine(x0, y0, x1, y1, paint(color, a, stroke=width * 2.2, shader=sh))


def beam_cone(c, origin, ang, spread, length, color="red", a=0.35):
    """Soft radial beam (wedge) from origin at angle ang (radians) with half-angle spread."""
    ox, oy = origin
    pts = [origin]
    for i in range(13):
        q = ang - spread + 2 * spread * i / 12
        pts.append((ox + length * math.cos(q), oy + length * math.sin(q)))
    sh = rad_grad(origin, length, [[color, a], [color, a * 0.35], [color, 0.0]], [0, 0.5, 1])
    c.drawPath(poly(pts), paint(color, 1.0, shader=sh))


# ------------------------------------------------------------------ globe / moon
def moon_img(size, light=(-0.35, 0.15, 1.0), lon0=0.0, lat0=0.0, bump=1.2, exposure=1.0, amb=0.022):
    alb, hgt = PL.moon_photo_maps()
    return PL.render(size, "moonp", alb, "moonp_h", hgt, lon0=lon0, lat0=lat0, light=light, margin=1.02,
                     bump=bump, amb=amb, lunar=1.0, terminator=0.035, rim_dark=0.0)


def draw_moon(c, cx, cy, R, light=(-0.35, 0.15, 1.0), lon0=0.0, lat0=0.0, glow_a=0.35, bump=1.2, exposure=1.15):
    size = int(min(2048, max(64, R * 2 * 1.02)))
    img = moon_img(size, light, lon0, lat0, bump)
    s = (R * 2 * 1.02)
    if glow_a > 0:
        c.drawCircle(cx, cy, R * 1.6, paint(shader=rad_grad((cx, cy), R * 1.6, [["#9FB4CC", glow_a * 0.35], ["#9FB4CC", 0.0]])))
    p = skia.Paint(AntiAlias=True)
    if exposure != 1.0:
        e = exposure
        p.setColorFilter(skia.ColorFilters.Matrix([e, 0, 0, 0, 0, 0, e, 0, 0, 0, 0, 0, e, 0, 0, 0, 0, 0, 1, 0]))
    c.drawImageRect(img, skia.Rect.MakeXYWH(cx - s / 2, cy - s / 2, s, s),
                    skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p)


def earth_img(size, lon0, lat0, light=(0.8, 0.4, 0.6), margin=1.12, atm=0.75, lights=1.3, roll=0.0):
    ea = PL.earth_maps("night")
    em = PL.earth_lights()
    return PL.render(size, "earthn", ea, lon0=lon0, lat0=lat0, roll=roll, light=light, margin=margin, amb=0.05,
                     atm=atm, atm_w=0.05, emit_key="lights", emit=em, emit_amt=lights, spec=0.18, rim_dark=0.15)


def globe_xy(lon, lat, lon0, lat0, cx, cy, R, roll=0.0):
    v = PL.project(lon, lat, lon0, lat0, roll)
    return cx + v[0] * R, cy - v[1] * R, v[2]


_RING_CACHE = {}


def country_rings(names, src="ne_50m_admin_0_countries"):
    key = (tuple(sorted(names)), src)
    if key not in _RING_CACHE:
        from engine import geo
        out = []
        for props, ring in geo.rings(src, lambda p: p.get("ADMIN") in names or p.get("NAME") in names):
            if len(ring) > 6:
                out.append(np.array(ring, float))
        _RING_CACHE[key] = out
    return _RING_CACHE[key]


def globe_path(rings, lon0, lat0, cx, cy, R, roll=0.0, close=True):
    """Project lon/lat rings onto the globe; hidden points break the path."""
    Rm = PL.rot(lon0, lat0, roll).T
    path = skia.Path()
    for ring in rings:
        la, lo = np.radians(ring[:, 1]), np.radians(ring[:, 0])
        P3 = np.stack([np.cos(la) * np.sin(lo), np.sin(la), np.cos(la) * np.cos(lo)], 1) @ Rm.T
        vis = P3[:, 2] > 0.0
        started = False
        for (x, y, z), v in zip(P3, vis):
            if not v:
                started = False
                continue
            X, Y = cx + x * R, cy - y * R
            if not started:
                path.moveTo(X, Y)
                started = True
            else:
                path.lineTo(X, Y)
        if close and vis.all():
            path.close()
    return path


# ------------------------------------------------------------------ oscilloscope
def scope(c, x, y, w, h, t, trace_fn, color="#7CFFB2", a=1.0, grid=True, label_s=None, n=600, sweep=None):
    """Green-phosphor CRT: trace_fn(u in 0..1, t) -> value in -1..1."""
    r = rrect(x, y, w, h, 26)
    c.drawRRect(r, paint("#03100A", a))
    with clip(c, r):
        c.drawRect(rect(x, y, w, h), paint(shader=rad_grad((x + w / 2, y + h / 2), max(w, h) * 0.7,
                                                           [["#0E3A24", 0.9 * a], ["#03100A", 0.0]])))
        if grid:
            gp = paint(color, 0.13 * a, stroke=1.5)
            for i in range(1, 10):
                c.drawLine(x + w * i / 10, y, x + w * i / 10, y + h, gp)
            for j in range(1, 8):
                c.drawLine(x, y + h * j / 8, x + w, y + h * j / 8, gp)
            c.drawLine(x, y + h / 2, x + w, y + h / 2, paint(color, 0.25 * a, stroke=2))
        path = skia.Path()
        umax = 1.0 if sweep is None else clamp(sweep)
        for i in range(n + 1):
            u = i / n * umax
            v = trace_fn(u, t)
            X, Y = x + u * w, y + h / 2 - v * h * 0.42
            (path.moveTo if i == 0 else path.lineTo)(X, Y)
        c.drawPath(path, paint(color, a, stroke=3.2))
        with layer(c, 0.9 * a, blend="Plus", filt=skia.ImageFilters.Blur(9, 9), bounds=rect(x, y, w, h)):
            c.drawPath(path, paint(color, 1, stroke=6))
        # scanlines
        sp = paint("black", 0.18 * a)
        for yy in range(int(y), int(y + h), 6):
            c.drawRect(rect(x, yy, w, 2), sp)
    c.drawRRect(r, paint("#1E2A24", a, stroke=10))
    c.drawRRect(r, paint(color, 0.25 * a, stroke=2))
    if label_s:
        T.text(c, label_s, x + 24, y + 44, F("mono", 24), color, 0.85 * a, track=0.1)


# ------------------------------------------------------------------ the Lunik stage (redrawn from the CIA layout figure)
# Proportions from "Figure 1. Internal Layout of the Lunik Stage Vehicle", Studies in Intelligence 5:4 (1961), p.10:
# overall length 17'-6", body diameter 8'-5".  Units below are feet; origin at nose tip, +y toward the base.
LUNIK_L, LUNIK_D = 17.5, 8.42


def lunik_parts():
    r = LUNIK_D / 2
    parts = {}
    # outer skin: cone from tip to y=7.4 widening to r, then cylinder to base flange, slight taper at the bottom
    parts["skin"] = [(0, 0), (r * 0.93, 7.6), (r, 9.0), (r, 15.2), (r * 0.94, 15.9), (-r * 0.94, 15.9), (-r, 15.2),
                     (-r, 9.0), (-r * 0.93, 7.6)]
    parts["base_cap"] = [(-r * 0.94, 15.9), (r * 0.94, 15.9), (r * 0.52, 16.1), (r * 0.52, 17.5), (-r * 0.52, 17.5),
                         (-r * 0.52, 16.1)]
    parts["payload"] = (0, 6.9, 1.25)                # orb centre (x, y) and radius
    parts["antenna"] = [(0, 0.5), (0, 5.7)]          # probe extended toward the tip
    parts["tanks"] = [(-2.75, 10.9, 1.45, 1.95), (2.75, 10.9, 1.45, 1.95), (-2.6, 14.0, 1.3, 1.3), (2.6, 14.0, 1.3, 1.3)]
    parts["baffle"] = [(-r * 0.98, 9.15), (r * 0.98, 9.15)]
    parts["windows"] = [(-1.7, 5.4), (0.0, 4.4), (1.7, 5.4)]  # three inspection windows in the nose (Finer)
    parts["engine_bay"] = [(-1.4, 15.0), (1.4, 15.0), (1.1, 17.2), (-1.1, 17.2)]
    parts["ribs"] = [3.9, 6.0, 7.6, 9.0]
    return parts


def draw_lunik(c, cx, cy, scale, t=0.0, mode="blueprint", draw_k=1.0, show=("skin", "base_cap", "tanks", "payload",
               "antenna", "baffle", "windows", "ribs"), rot=0.0, color="cyan2", a=1.0, fill=None, engine_ghost=0.0,
               cap_off=0.0, xray=1.0):
    """Line drawing of the Lunik stage. (cx, cy) = centre of the vehicle; scale = px per foot."""
    P = lunik_parts()
    oy = LUNIK_L / 2

    def tp(pt):
        return (pt[0] * scale, (pt[1] - oy) * scale)

    with xf(c, cx, cy, rot=rot):
        lw = max(1.6, scale * 0.11)
        if fill:
            sk = poly([tp(p) for p in P["skin"]])
            c.drawPath(sk, paint(shader=lin_grad(tp((-4.2, 0)), tp((4.2, 0)), fill)))
        if "skin" in show:
            stroke_path(c, poly([tp(p) for p in P["skin"]]), color, lw * 1.3, a, 0, draw_k)
        if "ribs" in show and xray > 0:
            r = LUNIK_D / 2
            for yy in P["ribs"]:
                hw = min(r, r * 0.93 * yy / 7.6) if yy < 7.6 else r * (0.93 + 0.07 * (yy - 7.6) / 1.4)
                stroke_path(c, poly([tp((-hw, yy)), tp((hw, yy))], close=False), color, lw * 0.7, a * 0.5 * xray, 0,
                            draw_k)
        if "baffle" in show and xray > 0:
            stroke_path(c, poly([tp(p) for p in P["baffle"]], close=False), color, lw, a * 0.8 * xray, 0, draw_k)
        if "tanks" in show and xray > 0:
            for (x, y, rx, ry) in P["tanks"]:
                X, Y = tp((x, y))
                path = skia.Path()
                path.addOval(skia.Rect.MakeLTRB(X - rx * scale, Y - ry * scale, X + rx * scale, Y + ry * scale))
                stroke_path(c, path, color, lw, a * 0.85 * xray, 0, draw_k)
        if "payload" in show and xray > 0:
            x, y, rr = P["payload"]
            X, Y = tp((x, y))
            path = skia.Path()
            path.addCircle(X, Y, rr * scale)
            stroke_path(c, path, "amber", lw * 1.2, a * xray, 0, draw_k)
            # basket struts
            for sx in (-1, 1):
                stroke_path(c, poly([tp((sx * 0.9, y + 0.9)), tp((sx * 1.7, 9.15))], close=False), color, lw * 0.7,
                            a * 0.6 * xray, 0, draw_k)
        if "antenna" in show and xray > 0:
            stroke_path(c, poly([tp(p) for p in P["antenna"]], close=False), "amber", lw, a * xray, 0, draw_k)
        if "windows" in show:
            for (x, y) in P["windows"]:
                X, Y = tp((x, y))
                c.drawRRect(rrect(X - 0.42 * scale, Y - 0.3 * scale, 0.84 * scale, 0.6 * scale, 0.12 * scale),
                            paint(color, a * 0.9 * clamp(draw_k * 2 - 1), stroke=lw))
        if "base_cap" in show:
            with xf(c, 0, cap_off * scale):
                stroke_path(c, poly([tp(p) for p in P["base_cap"]]), color, lw * 1.1, a, 0, draw_k)
        if engine_ghost > 0:
            stroke_path(c, poly([tp(p) for p in P["engine_bay"]]), "red", lw, a * engine_ghost, 0, 1, d=(10, 9))


# ------------------------------------------------------------------ 150-ft dish (3D wireframe)
def dish_lines(el=35.0, az=-30.0, n_r=7, n_s=24):
    """Parabolic reflector (f/D ~0.4) + feed legs + pedestal as 3D polylines (metres)."""
    D = 45.7  # 150 ft
    f = 0.4 * D
    lines = []
    def surf(r, th):
        z = r * r / (4 * f)
        return np.array([r * math.cos(th), r * math.sin(th), z])
    for i in range(1, n_r + 1):
        r = D / 2 * i / n_r
        lines.append(("ring", [surf(r, 2 * math.pi * k / 72) for k in range(73)]))
    for j in range(n_s):
        th = 2 * math.pi * j / n_s
        lines.append(("rib", [surf(D / 2 * k / 20, th) for k in range(21)]))
    feed = np.array([0, 0, f])
    for j in range(4):
        th = math.pi / 4 + j * math.pi / 2
        lines.append(("leg", [surf(D / 2 * 0.62, th), feed]))
    # orient dish: axis +z -> pointing at elevation el, azimuth az
    e, a_ = math.radians(90 - el), math.radians(az)
    Rx = np.array([[1, 0, 0], [0, math.cos(e), -math.sin(e)], [0, math.sin(e), math.cos(e)]])
    Rz = np.array([[math.cos(a_), -math.sin(a_), 0], [math.sin(a_), math.cos(a_), 0], [0, 0, 1]])
    hub = np.array([0, 0, 30.0])
    out = [(k, [Rz @ (Rx @ p) + hub for p in pts]) for k, pts in lines]
    # pedestal: A-frame legs to ground
    for sx in (-1, 1):
        out.append(("ped", [hub + np.array([sx * 4, 0, 0]), np.array([sx * 14, -6, 0])]))
        out.append(("ped", [hub + np.array([sx * 4, 0, 0]), np.array([sx * 14, 6, 0])]))
    out.append(("ped", [np.array([-16, -8, 0]), np.array([16, -8, 0]), np.array([16, 8, 0]), np.array([-16, 8, 0]),
                        np.array([-16, -8, 0])]))
    return out


def project3(p, cam_az, cam_el, dist, cx, cy, fpx, target=(0, 0, 22)):
    a, e = math.radians(cam_az), math.radians(cam_el)
    eye = np.array(target) + dist * np.array([math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e)])
    fwd = np.array(target) - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 0, 1])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    d = np.asarray(p) - eye
    z = d @ fwd
    return cx + fpx * (d @ right) / z, cy - fpx * (d @ up) / z, z


def draw_dish(c, cx, cy, t, k=1.0, cam_az=25.0, scale=1.0, color="cyan2", a=1.0, el=40.0):
    lines = dish_lines(el=el)
    order = {"ped": 0, "ring": 1, "rib": 2, "leg": 3}
    for kind, pts in sorted(lines, key=lambda l: order[l[0]]):
        idx = order[kind]
        kk = clamp(k * 4 - idx * 0.7)
        if kk <= 0:
            continue
        path = skia.Path()
        for i, p in enumerate(pts):
            x, y, z = project3(p, cam_az, 14, 120, cx, cy, 980 * scale)
            (path.moveTo if i == 0 else path.lineTo)(x, y)
        w = {"ring": 2.0, "rib": 1.6, "leg": 2.4, "ped": 2.6}[kind] * scale
        al = {"ring": 0.9, "rib": 0.55, "leg": 0.9, "ped": 0.75}[kind]
        stroke_path(c, path, color, w, a * al, 0, kk)


def human(c, x, y, h, color="amber", a=1.0, rim=None):
    """Simple standing figure (feet at x,y), height h px. rim: colour of a soft edge light for dark silhouettes."""
    if rim is None and color.startswith("#0"):
        rim = "amber2"
    if rim:
        with layer(c, 0.35 * a, filt=skia.ImageFilters.Blur(h * 0.02, h * 0.02),
                   bounds=skia.Rect.MakeLTRB(x - h * 0.45, y - h * 1.15, x + h * 0.45, y + h * 0.1)):
            with xf(c, x, y, s=1.04, px=0, py=0):
                human(c, 0, 0, h, rim, 1.0, rim=False)
    hd = h * 0.13
    c.drawCircle(x, y - h + hd, hd, paint(color, a))
    body = poly([(x - h * 0.11, y - h + hd * 2.2), (x + h * 0.11, y - h + hd * 2.2), (x + h * 0.08, y - h * 0.45),
                 (x + h * 0.07, y), (x + h * 0.01, y), (x, y - h * 0.4), (x - h * 0.01, y), (x - h * 0.07, y),
                 (x - h * 0.08, y - h * 0.45)])
    c.drawPath(body, paint(color, a))


def big_number(c, s, x, y, size=150, color="white", a=1.0, align="center", font="black", track=-0.03):
    T.text(c, s, x, y, F(font, size), color, a, align=align, track=track)
