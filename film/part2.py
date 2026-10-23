"""FILE 02 - The Lunik.  Facts: S. W. Finer, "The Kidnaping of the Lunik", Studies in Intelligence;
A. D. Wheelon & S. N. Graybeal, "Intelligence for the Space Race", Studies in Intelligence 5 (Fall 1961)."""
import math
import os

import numpy as np
import skia

from engine.core import *
from engine.gfx import *
from engine import text as T
from engine.render import Shot
from film.common import *
from film.part1 import FileCard, NightShot

SRC2 = "SOURCE: S. W. FINER, \"THE KIDNAPING OF THE LUNIK,\" STUDIES IN INTELLIGENCE"
SRC2B = "SOURCE: WHEELON & GRAYBEAL, \"INTELLIGENCE FOR THE SPACE RACE,\" STUDIES IN INTELLIGENCE 5 (1961)"
WHERE = "COUNTRY UNNAMED IN THE CIA ACCOUNT \u00b7 LATER ACCOUNTS: MEXICO CITY, 1959"
DOCS = os.path.join(ROOT, "assets", "docs")


def doc_image(name):
    from PIL import Image

    def build():
        return to_image(np.asarray(Image.open(os.path.join(DOCS, name)).convert("RGB")))
    return cached_image("doc_" + name, build)


class Night2(NightShot):
    file_no, file_title, src = "02", "THE LUNIK", SRC2


class FileCard2(FileCard):
    num, title = "02", "THE LUNIK"
    sub = ["\u201ca Soviet upper-stage", "space vehicle.\u201d"]
    src = "Studies in Intelligence \u00b7 \u201cThe Kidnaping of the Lunik\u201d"


# --------------------------------------------------------------------------------------- helpers
def metal_lunik(c, cx, cy, scale, rot=0.0, a=1.0, light=0.0, windows=True):
    """Painted exhibition finish: filled silhouette with a cylindrical sheen, plus outline detail."""
    P = lunik_parts()
    oy = LUNIK_L / 2
    tp = lambda p: (p[0] * scale, (p[1] - oy) * scale)
    with xf(c, cx, cy, rot=rot):
        sk = poly([tp(p) for p in P["skin"]])
        r = LUNIK_D / 2 * scale
        sh = lin_grad((-r, 0), (r, 0), ["#3A3F45", "#C9CED3", "#F2F4F5", "#9AA1A8", "#2A2E33"], [0, 0.32, 0.45, 0.7, 1])
        with layer(c, a):
            c.drawPath(sk, paint(shader=sh))
            cap = poly([tp(p) for p in P["base_cap"]])
            c.drawPath(cap, paint(shader=lin_grad((-r * 0.5, 0), (r * 0.5, 0), ["#2C3036", "#9DA3AA", "#3A3F45"])))
            for yy in P["ribs"]:
                hw = min(LUNIK_D / 2, LUNIK_D / 2 * 0.93 * yy / 7.6) if yy < 7.6 else LUNIK_D / 2
                c.drawLine(*tp((-hw, yy)), *tp((hw, yy)), paint("#1C1F23", 0.5, stroke=max(1.2, scale * 0.05)))
            if windows:
                for (x, y) in P["windows"]:
                    X, Y = tp((x, y))
                    rr_ = rrect(X - 0.42 * scale, Y - 0.3 * scale, 0.84 * scale, 0.6 * scale, 0.12 * scale)
                    c.drawRRect(rr_, paint("#0B1016"))
                    c.drawRRect(rr_, paint("amber", 0.35 + 0.4 * light, stroke=max(1.0, scale * 0.04)))
            if light > 0:
                c.drawPath(sk, paint("white", 0.08 * light, blend="Plus"))


def clock_face(c, x, y, r, hours, a=1.0, color="paper_hi", label_s=None):
    """Analog clock; hours as float (e.g. 19.5 = 7:30 PM)."""
    c.drawCircle(x, y, r, paint("#05070A", 0.75 * a))
    c.drawCircle(x, y, r, paint(color, 0.8 * a, stroke=3))
    for i in range(12):
        q = i / 12 * math.tau
        c.drawLine(x + math.sin(q) * r * 0.84, y - math.cos(q) * r * 0.84, x + math.sin(q) * r * 0.95,
                   y - math.cos(q) * r * 0.95, paint(color, 0.8 * a, stroke=3 if i % 3 == 0 else 1.5))
    hq = (hours % 12) / 12 * math.tau
    mq = (hours % 1) * math.tau
    c.drawLine(x, y, x + math.sin(hq) * r * 0.5, y - math.cos(hq) * r * 0.5, paint(color, a, stroke=6))
    c.drawLine(x, y, x + math.sin(mq) * r * 0.78, y - math.cos(mq) * r * 0.78, paint("amber", a, stroke=3.5))
    c.drawCircle(x, y, 5, paint("amber", a))
    h = int(hours) % 24
    m = int(round((hours % 1) * 60)) % 60
    s = f"{(h % 12) or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"
    T.text(c, label_s or s, x, y + r + 40, F("mono_b", 28), color, a, align="center", track=0.06)


def dust(c, t, box, n=60, seed=3, a=0.5, color="amber2"):
    x0, y0, x1, y1 = box
    r = rng(seed)
    for i in range(n):
        px, py = r.random(), r.random()
        sp = 0.01 + 0.02 * r.random()
        x = x0 + (px + 0.03 * math.sin(t * 0.7 + i)) % 1 * (x1 - x0)
        y = y0 + ((py + t * sp) % 1) * (y1 - y0)
        c.drawCircle(x, y, 1 + 1.6 * r.random(), paint(color, a * (0.3 + 0.7 * r.random())))


# --------------------------------------------------------------------------------------- 1. exhibition
class Exhibit(Night2):
    def setup(self):
        self.t_lunik = tok_t("exhibit", "Lunik:")
        self.t_stage = tok_t("exhibit", "final")
        self.t_mock = tok_t("exhibit", "mock-up.")

    def draw(self, c, t):
        lt = self.lt(t)
        c.drawRect(rect(0, 0, W, H), paint(shader=lin_grad((0, 0), (0, H), ["#050608", "#0B0D11", "#141414"])))
        # floor
        c.drawRect(rect(0, 1500, W, 420), paint(shader=lin_grad((0, 1500), (0, H), ["#1A1814", "#07070A"])))
        push = 1 + 0.06 * io_sine(clamp(lt / 8))
        with xf(c, 540, 1100, s=push):
            c.translate(-540, -1100)
            k = out_cubic(clamp(lt / 1.0))
            # spotlight cone (additive)
            cone = poly([(470, 0), (610, 0), (920, 1560), (160, 1560)])
            c.drawPath(cone, paint(shader=lin_grad((0, 0), (0, 1560), [["amber2", 0.22 * k], ["amber2", 0.05 * k]]),
                                  blend="Plus"))
            c.drawOval(skia.Rect.MakeLTRB(170, 1490, 910, 1620), paint(shader=rad_grad((540, 1555), 380,
                                                                                      [["amber2", 0.35 * k], ["amber2", 0.0]])))
            dust(c, t, (180, 200, 900, 1500), 70, 3, 0.35 * k)
            # pedestal + vehicle (17'6" tall)
            sc = 40
            c.drawRRect(rrect(330, 1470, 420, 70, 6), paint(shader=lin_grad((330, 0), (750, 0), ["#222222", "#555555", "#1A1A1A"])))
            metal_lunik(c, 540, 1470 - LUNIK_L * sc / 2, sc, a=k, light=k)
            # visitors (silhouettes with rim light) for scale
            for (x, h, col) in ((150, 238, "#0A0A0C"), (950, 250, "#0A0A0C"), (860, 226, "#0A0A0C")):
                human(c, x, 1640, h, col, 1.0)
            # labels
            kl = clamp((t - self.t_lunik) / 0.4)
            if kl > 0:
                tx, ty = 730, 820
                c.drawLine(630, 900, tx - 10, ty + 10, paint("amber", kl, stroke=2))
                tag(c, "LUNIK", tx, ty, 30, "night", "amber", kl)
                T.text(c, type_on("LAST STAGE", clamp((t - self.t_stage) / 0.4)), tx, ty + 44, F("mono_b", 22), "amber2",
                       kl, track=0.08)
                T.text(c, type_on("OF A MOON ROCKET", clamp((t - self.t_stage - 0.3) / 0.5)), tx, ty + 74, F("mono_r", 20),
                       "amber2", kl * 0.9, track=0.08)
            km = clamp((t - self.t_mock) / 0.25)
            if km > 0:
                with xf(c, 300, 1000, rot=-6, s=lerp(1.4, 1, out_cubic(km))):
                    tag(c, "MOCK-UP?", 0, 0, 44, "paper_hi", "red", km, align="center", font="black")
        vignette_band(c, True, 560, 0.8)
        self.chrome(c, t)
        T.text(c, WHERE, W / 2, 1700, F("mono_r", 19), "steel", 0.7 * clamp(lt / 1.0), align="center", track=0.08)

    def post(self, t):
        return self.base_post(bloom=0.35, bthresh=0.6, vig=0.75)


# --------------------------------------------------------------------------------------- 2. blueprint: a real production vehicle
def blueprint_bg(c, a=1.0):
    c.drawRect(rect(0, 0, W, H), paint(shader=rad_grad((540, 1000), 1300, ["#0E2747", "#061226"])))
    gp = paint("#6FA8DC", 0.10 * a, stroke=1)
    for x in range(0, W, 40):
        c.drawLine(x, 0, x, H, gp)
    for y in range(0, H, 40):
        c.drawLine(0, y, W, y, gp)
    gp2 = paint("#6FA8DC", 0.2 * a, stroke=1.5)
    for x in range(0, W, 200):
        c.drawLine(x, 0, x, H, gp2)
    for y in range(0, H, 200):
        c.drawLine(0, y, W, y, gp2)


class Real(Night2):
    def setup(self):
        self.t_wasnt = S("real")["t0"]
        self.t_day = tok_t("real", "spent")
        self.t_prod = tok_t("real", "production")
        self.t_engine = tok_t("real", "engine")

    def draw(self, c, t):
        lt = self.lt(t)
        blueprint_bg(c)
        sc = 46
        cx, cy = 470, 1140
        dk = io_cubic(clamp(lt / 2.2))
        draw_lunik(c, cx, cy, sc, draw_k=dk, color="#D6EBFF", engine_ghost=clamp((t - self.t_engine) / 0.4))
        # dimension lines (from the CIA layout figure)
        kd = clamp((lt - 1.0) / 0.6)
        top, bot = cy - LUNIK_L / 2 * sc, cy + LUNIK_L / 2 * sc
        xr = cx + LUNIK_D / 2 * sc + 60
        p = paint("#D6EBFF", 0.8 * kd, stroke=2)
        c.drawLine(xr, top, xr, bot, p)
        for yy in (top, bot):
            c.drawLine(xr - 14, yy, xr + 14, yy, p)
        T.text(c, "17\u2032 6\u2033", xr + 22, (top + bot) / 2, F("mono_b", 30), "#D6EBFF", kd, track=0.04)
        yb = bot + 60
        c.drawLine(cx - LUNIK_D / 2 * sc, yb, cx + LUNIK_D / 2 * sc, yb, p)
        T.text(c, "8\u2032 5\u2033", cx, yb + 40, F("mono_b", 30), "#D6EBFF", kd, align="center", track=0.04)
        # part labels
        for (s_, px, py, lx, ly, tt) in (("PAYLOAD", 0, 6.9, 790, 760, 1.4), ("PROPELLANT TANKS", 2.8, 10.9, 790, 1080, 1.8)):
            kk = clamp((lt - tt) / 0.5)
            if kk > 0:
                X, Y = cx + px * sc, cy + (py - LUNIK_L / 2) * sc
                c.drawLine(X, Y, lx - 10, ly - 8, paint("#D6EBFF", 0.6 * kk, stroke=1.5))
                T.text(c, s_, lx, ly, F("mono_b", 22), "#D6EBFF", kk, track=0.08)
        ke = clamp((t - self.t_engine) / 0.4)
        if ke > 0:
            X, Y = cx, cy + (16.2 - LUNIK_L / 2) * sc
            c.drawLine(X + 70, Y, 780, 1520, paint("red", ke, stroke=2))
            tag(c, "ENGINE: REMOVED", 790, 1530, 24, "paper_hi", "red", ke)
        # 24 hours ring
        kday = clamp((t - self.t_day + 0.1) / 0.4)
        if kday > 0:
            x, y, r = 170, 660, 64
            c.drawCircle(x, y, r, paint("#D6EBFF", 0.25 * kday, stroke=8))
            arc = skia.Path()
            arc.addArc(skia.Rect.MakeLTRB(x - r, y - r, x + r, y + r), -90, 360 * io_cubic(clamp((t - self.t_day) / 1.8)))
            c.drawPath(arc, paint("amber", kday, stroke=8, cap="butt"))
            T.text(c, "24", x, y + 14, F("black", 50), "white", kday, align="center")
            T.text(c, "HOURS", x, y + r + 34, F("mono_b", 20), "amber", kday, align="center", track=0.2)
        # "It wasn't": strike the mock-up tag, then PRODUCTION ITEM stamp
        kw = clamp((t - self.t_wasnt + 0.2) / 0.3) * (1 - clamp((t - self.t_prod + 0.3) / 0.3))
        if kw > 0:
            with xf(c, 300, 1000, rot=-6):
                tag(c, "MOCK-UP?", 0, 0, 44, "paper_hi", "red", kw, align="center", font="black")
                c.drawLine(-150, -18, 150 * (2 * clamp((t - self.t_wasnt) / 0.25) - 1), -18, paint("white", kw, stroke=8))
        ks = clamp((t - self.t_prod) / 0.14)
        if ks > 0:
            with xf(c, 470, 1000, rot=-8, s=lerp(1.6, 1.0, out_cubic(ks))):
                with layer(c, ks * 0.95):
                    f = F("black", 76)
                    s_ = "PRODUCTION ITEM"
                    w_ = T.width(s_, f, 0.04)
                    c.drawRRect(rrect(-w_ / 2 - 24, -82, w_ + 48, 108, 8), paint("red", 1, stroke=8))
                    T.text(c, s_, 0, 0, f, "red", 1, align="center", track=0.04)
        vignette_band(c, True, 560, 0.75)
        self.chrome(c, t)

    def post(self, t):
        return self.base_post(bloom=0.25)


# --------------------------------------------------------------------------------------- 3. what the ICBM could throw
class ICBM(Night2):
    src = SRC2B

    def setup(self):
        self.t_meas = tok_t("icbm", "measure")
        self.t_lb = tok_t("icbm", "18,000 pounds")
        self.t_mi = tok_t("icbm", "3,800 miles")

    def draw(self, c, t):
        lt = self.lt(t)
        bg_space(c, t, seed=51)
        # archival figure card
        img = doc_image("wheelon_fig1.png")
        k = out_expo(clamp(lt / 0.6))
        shrink = io_cubic(clamp((t - self.t_meas - 0.2) / 0.9))
        cw = lerp(640, 300, shrink)
        ch = cw * img.height() / img.width()
        x = lerp(540 - 320, 80, shrink)
        y = lerp(600, 600, shrink)
        with xf(c, x + cw / 2, y + ch / 2, rot=lerp(-2.5, -4, shrink)):
            c.translate(-(x + cw / 2), -(y + ch / 2))
            shadow(c, rect(x, y, cw, ch), 0, 24, 30, 0.6)
            draw_image(c, img, x, y, cw, ch, k)
            c.drawRect(rect(x, y, cw, ch), paint("paper", 0.15 * k, blend="Multiply"))
        T.text(c, "CIA LAYOUT OF THE LUNIK STAGE, 1961", x, y + ch + 34, F("mono_b", lerp(22, 17, shrink)), "paper_hi",
               k * 0.85, track=0.06)
        # weights
        kw = clamp((t - self.t_meas) / 0.5)
        if kw > 0:
            T.text(c, "LUNIK STAGE", 430, 700, F("mono_r", 22), "steel", kw * shrink, track=0.1)
            T.text(c, "\u2248 2,600 LB DRY", 430, 745, F("mono_b", 30), "white", kw * shrink, track=0.04)
            T.text(c, "\u2248 18,000 LB FUELED + PAYLOAD", 430, 790, F("mono_b", 30), "amber2", kw * shrink, track=0.04)
        # trajectory arc above a curved horizon
        ka = clamp((t - self.t_lb + 0.4) / 0.4)
        if ka > 0:
            ex, ey, R = 540, 3100, 1700
            c.drawCircle(ex, ey, R, paint(shader=lin_grad((0, ey - R), (0, ey - R + 400), ["#13263A", "#05090F"]), a=ka))
            c.drawCircle(ex, ey, R + 2, paint("cyan", 0.5 * ka, stroke=2))
            p0, p1 = (150, ey - R + 70), (930, ey - R + 70)
            path = skia.Path()
            path.moveTo(*p0)
            path.cubicTo(330, 820, 750, 820, *p1)
            u = io_cubic(clamp((t - self.t_lb) / 2.6))
            stroke_path(c, path, "amber", 4, ka, 0, u)
            glow(c, lambda cc: stroke_path(cc, path, "amber", 7, 1, 0, u), 12, 0.8, bounds=rect(80, 700, 920, 900))
            (px, py), _ = point_at(path, u)
            c.drawCircle(px, py, 10, paint("white", ka))
            ring_pulse(c, px, py, t, "amber", 10, 40, 0.8, ka)
            tag(c, "18,000 LB", px + 20, py - 24, 26, "night", "amber", clamp((t - self.t_lb) / 0.3))
            kmi = clamp((t - self.t_mi) / 0.4)
            if kmi > 0:
                c.drawLine(p0[0], p0[1] + 50, p1[0], p1[1] + 50, paint("white", 0.7 * kmi, stroke=2))
                for xx in (p0[0], p1[0]):
                    c.drawLine(xx, p0[1] + 36, xx, p0[1] + 64, paint("white", 0.7 * kmi, stroke=2))
                big_number(c, "3,800 MI", 540, p0[1] + 150, 96, "white", kmi)
                T.text(c, "SOVIET ICBM CAPABILITY (CIA ESTIMATE)", 540, p0[1] + 196, F("mono_r", 21), "steel", kmi,
                       align="center", track=0.08)
        vignette_band(c, True, 560, 0.75)
        self.chrome(c, t)

    def post(self, t):
        return self.base_post(bloom=0.3)


# --------------------------------------------------------------------------------------- 4. factory markings -> borrow it
class Borrow(Night2):
    def setup(self):
        self.t_mark = tok_t("borrow", "factory")
        self.t_borrow = tok_t("borrow", "borrowed")
        self.t_night = tok_t("borrow", "Overnight.")

    def draw(self, c, t):
        lt = self.lt(t)
        # brushed metal plate
        def build():
            r = rng(9)
            a = (r.random((H // 2, W // 2)) * 0.5 + 0.5)
            from scipy.ndimage import gaussian_filter
            a = gaussian_filter(a, (0.6, 18))
            a = (a - a.min()) / (a.max() - a.min())
            img = (np.dstack([a * 70 + 70, a * 74 + 72, a * 78 + 76])).astype(np.uint8)
            return to_image(img)
        draw_image(c, cached_image("brushed", build), 0, 0, W, H)
        c.drawRect(rect(0, 0, W, H), paint(shader=rad_grad((540, 1050), 1100, [["white", 0.10], ["black", 0.65]])))
        push = 1 + 0.12 * io_sine(clamp(lt / 4))
        with xf(c, 540, 1080, s=push):
            c.translate(-540, -1080)
            for (x, y) in ((170, 800), (910, 800), (170, 1360), (910, 1360)):
                c.drawCircle(x, y, 18, paint(shader=rad_grad((x - 5, y - 5), 22, ["#D0D4D8", "#4A4F55"])))
            plate = rrect(230, 880, 620, 400, 14)
            c.drawRRect(plate, paint("#2A2E33", 0.6, stroke=4))
            # stamped markings: the CIA article redacts them, so we do too
            rr = rng(4)
            for row in range(4):
                xx = 280
                while xx < 800:
                    wd = rr.uniform(40, 130)
                    c.drawRect(rect(xx, 930 + row * 86, wd, 46), paint("#101215", 0.92))
                    xx += wd + rr.uniform(16, 30)
            T.text(c, "[MARKINGS REDACTED IN THE CIA ARTICLE]", 540, 1330, F("mono_r", 20), "paper_hi", 0.7,
                   align="center", track=0.06)
        # loupe
        km = clamp((t - self.t_mark + 0.2) / 0.4)
        if km > 0:
            q = (t - self.t_mark) * 1.3
            lx, ly = 540 + 210 * math.sin(q), 1060 + 90 * math.sin(q * 1.7)
            c.drawCircle(lx, ly, 150, paint("white", 0.06 * km))
            c.drawCircle(lx, ly, 150, paint("cyan2", 0.8 * km, stroke=6))
            c.drawLine(lx + 106, ly + 106, lx + 230, ly + 230, paint("cyan2", 0.8 * km, stroke=16))
            tag(c, "FACTORY MARKINGS", 540, 800, 30, "night", "cyan2", km, align="center")
        # night falls on "borrowed it. Overnight."
        kn = clamp((t - self.t_borrow) / 0.8)
        if kn > 0:
            c.drawRect(rect(0, 0, W, H), paint("#030509", 0.82 * kn))
            clock_face(c, 540, 1150, 170, 18.5 + 1.0 * clamp((t - self.t_night) / 1.2), kn)
        vignette_band(c, True, 560, 0.8)
        self.chrome(c, t)


# --------------------------------------------------------------------------------------- 5. the truck run (schematic street map)
class Truck(Night2):
    def setup(self):
        self.t_last = tok_t("truck", "last")
        self.t_turn = tok_t("truck", "turnoff,")
        self.t_driver = tok_t("truck", "new")
        self.t_hotel = tok_t("truck", "hotel.")
        # street graph (map units = px). Route: grounds -> ... -> turnoff -> salvage yard; planned: -> rail yard
        self.G = (200, 700)
        self.J = (620, 1180)
        self.RAIL = (900, 1560)
        self.YARD = (400, 1400)
        self.HOTEL = (860, 840)
        self.route = [self.G, (200, 900), (620, 900), self.J]
        self.planned = [self.J, (620, 1560), self.RAIL]
        self.divert = [self.J, (400, 1180), self.YARD]

    def poly_at(self, pts, u):
        segs = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        L = sum(segs) * clamp(u)
        for i, s in enumerate(segs):
            if L <= s:
                f = L / s if s else 0
                return lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f), \
                    math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0])
            L -= s
        return pts[-1][0], pts[-1][1], 0.0

    def draw(self, c, t):
        lt = self.lt(t)
        c.drawRect(rect(0, 0, W, H), paint("#05070B"))
        # blocks
        r = rng(2)
        with xf(c, 540, 1130, rot=0, s=1 + 0.04 * io_sine(clamp(lt / 7))):
            c.translate(-540, -1130)
            for gx in range(-1, 7):
                for gy in range(2, 11):
                    x, y = 60 + gx * 140 + 18, 560 + (gy - 2) * 120 + 18
                    c.drawRRect(rrect(x, y, 104, 84, 6), paint("#0E131B"))
                    for _ in range(2):
                        if r.random() < 0.5:
                            c.drawCircle(x + r.random() * 104, y + r.random() * 84, 1.6, paint("amber2", 0.35))
            for gx in range(0, 8):
                c.drawLine(60 + gx * 140, 520, 60 + gx * 140, 1700, paint("#1B2430", 1, stroke=24))
            for gy in range(0, 11):
                c.drawLine(0, 560 + gy * 120 - 22 + 22, W, 560 + gy * 120, paint("#1B2430", 1, stroke=24))
            # places
            for (pt, name, col) in ((self.G, "EXHIBITION GROUNDS", "amber2"), (self.RAIL, "RAIL YARD", "red"),
                                    (self.YARD, "RENTED SALVAGE YARD", "cyan2"), (self.HOTEL, "HOTEL", "paper_hi")):
                ka = 1.0 if name != "RENTED SALVAGE YARD" else clamp((t - self.t_turn) / 0.4)
                if name == "HOTEL":
                    ka = clamp((t - self.t_driver) / 0.4)
                if ka <= 0:
                    continue
                c.drawRect(rect(pt[0] - 40, pt[1] - 30, 80, 60), paint(col, 0.18 * ka))
                c.drawRect(rect(pt[0] - 40, pt[1] - 30, 80, 60), paint(col, 0.9 * ka, stroke=3))
                T.text(c, name, pt[0], pt[1] - 46, F("mono_b", 22), col, ka, align="center", track=0.06)
            # the Soviet checker waits at the rail yard
            c.drawCircle(self.RAIL[0] + 18, self.RAIL[1] + 4, 9, paint("red"))
            T.text(c, "SOVIET CHECKER", self.RAIL[0], self.RAIL[1] + 60, F("mono_r", 18), "red", 0.85, align="center",
                   track=0.06)
            # planned route (dashed) vs actual
            pp = poly(self.route + self.planned[1:], close=False)
            stroke_path(c, pp, "steel", 4, 0.5, 0, 1, d=(14, 12))
            u1 = io_quad(clamp((t - self.t0 - 0.2) / max(0.1, self.t_turn - self.t0 - 0.2)))
            stroke_path(c, poly(self.route, close=False), "amber", 6, 0.9, 0, u1)
            u2 = io_cubic(clamp((t - self.t_driver - 0.3) / 1.6))
            if u2 > 0:
                stroke_path(c, poly(self.divert, close=False), "cyan", 6, 0.9, 0, u2)
            if u2 > 0:
                x, y, ang = self.poly_at(self.divert, u2)
            else:
                x, y, ang = self.poly_at(self.route, u1)
            # escort cars ahead/behind on the route
            for off, col in ((0.12, "cyan"), (-0.12, "cyan")):
                if u2 <= 0:
                    ex_, ey_, _ = self.poly_at(self.route, clamp(u1 + off))
                    c.drawCircle(ex_, ey_, 9, paint(col, 0.95))
                    glow(c, lambda cc: cc.drawCircle(ex_, ey_, 9, paint(col, 1)), 10, 0.8, bounds=around(ex_, ey_, 50))
            with xf(c, x, y, rot=math.degrees(ang)):
                c.drawPath(poly([(30, -26), (220, -110), (220, 110), (30, 26)]), paint(shader=lin_grad((30, 0), (220, 0),
                                                                                                        [["amber2", 0.25], ["amber2", 0.0]])))
                c.drawRRect(rrect(-34, -18, 68, 36, 5), paint("amber"))
                c.drawRect(rect(-28, -13, 40, 26), paint("#5A3A08"))
            # canvas + driver swap at the turnoff
            ks = clamp((t - self.t_turn) / 0.3)
            if ks > 0:
                jx, jy = self.J
                ring_pulse(c, jx, jy, t - self.t_turn, "white", 20, 90, 1.2, ks * (1 - clamp((t - self.t_hotel) / 0.5)))
                kd = clamp((t - self.t_driver) / 0.4)
                if kd > 0:
                    hp = poly([self.J, (860, 1180), (860, 900), self.HOTEL], close=False)
                    stroke_path(c, hp, "paper_hi", 3, 0.8 * kd, 0, io_cubic(clamp((t - self.t_driver) / 1.8)), d=(8, 8))
                    T.text(c, "ORIGINAL DRIVER \u2192", jx + 30, jy - 24, F("mono_r", 18), "paper_hi", kd * 0.9, track=0.04)
                    T.text(c, "NEW DRIVER", jx - 40, jy + 50, F("mono_r", 18), "cyan2", kd * 0.9, align="right", track=0.04)
            kh = clamp((t - self.t_hotel) / 0.4)
            if kh > 0:
                hx, hy = self.HOTEL
                c.drawRect(rect(hx - 12, hy - 12, 24, 24), paint("amber2", kh))
                glow(c, lambda cc: cc.drawRect(rect(hx - 12, hy - 12, 24, 24), paint("amber2", 1)), 16, kh, bounds=around(hx, hy, 80))
                T.text(c, "ALL NIGHT", hx, hy + 60, F("mono_b", 20), "amber2", kh, align="center", track=0.12)
        vignette_band(c, True, 560, 0.85)
        self.chrome(c, t)
        T.text(c, "SCHEMATIC \u00b7 ROUTES AS DESCRIBED IN THE CIA ACCOUNT", W / 2, 1700, F("mono_r", 18), "steel", 0.7,
               align="center", track=0.08)


# --------------------------------------------------------------------------------------- 6. the salvage yard, overnight
class Yard(Night2):
    def setup(self):
        y = S("yard")
        self.t_roof = tok_t("yard", "opened")
        self.t_base = tok_t("yard", "unbolted")
        self.t_in = tok_t("yard", "slipped")
        self.t_shoes = tok_t("yard", "shoes")
        self.T0, self.T1 = self.t0, y["t1"] + 0.3

    def hours(self, t):
        return lerp(19.5, 28.0, clamp((t - self.T0) / (self.T1 - self.T0)))  # 7:30 PM -> 4:00 AM

    def draw(self, c, t):
        lt = self.lt(t)
        c.drawRect(rect(0, 0, W, H), paint(shader=lin_grad((0, 0), (0, H), ["#03050A", "#0A0F18", "#0B0B0C"])))
        sc = 40
        gy = 1500
        cx0, cx1 = 140, 940
        # street lamp (comes on during the work - "not an ambush")
        kl = clamp((t - self.t0 - 1.0) / 0.15)
        c.drawLine(80, gy, 80, 720, paint("#2A2E35", 1, stroke=10))
        c.drawLine(80, 720, 170, 720, paint("#2A2E35", 1, stroke=8))
        if kl > 0:
            fl = 1 if lt > 1.5 else (0.4 + 0.6 * ((int(lt * 30) % 3) > 0))
            c.drawPath(poly([(150, 730), (190, 730), (520, gy), (-180, gy)]),
                       paint(shader=lin_grad((0, 730), (0, gy), [["amber2", 0.26 * kl * fl], ["amber2", 0.03]]), blend="Plus"))
            c.drawCircle(170, 730, 14, paint("amber2", kl * fl))
            glow(c, lambda cc: cc.drawCircle(170, 730, 18, paint("amber2", 1)), 26, kl * fl, bounds=around(170, 730, 120))
        # ground
        c.drawRect(rect(0, gy, W, H - gy), paint("#0D0E10"))
        # crate (20 ft long, walls ~11 ft, 14 ft at the peak) drawn as a cut-away
        wall = gy - 11 * sc
        peak = gy - 14 * sc
        c.drawRect(rect(cx0, wall, cx1 - cx0, gy - wall), paint("#1E1710", 0.55))
        c.drawRect(rect(cx0, wall, cx1 - cx0, gy - wall), paint("#8A6A44", 0.9, stroke=4))
        for i in range(1, 8):
            x = cx0 + i * (cx1 - cx0) / 8
            c.drawLine(x, wall, x, gy, paint("#8A6A44", 0.25, stroke=2))
        # roof planks lifted off one by one
        n = 10
        kr = clamp((t - self.t_roof) / 1.4)
        for i in range(n):
            f = clamp(kr * n - i)
            x0 = cx0 + i * (cx1 - cx0) / n
            x1 = x0 + (cx1 - cx0) / n
            # gable: left half rises to the peak, right half falls
            yl = lerp(wall, peak, 1 - abs(((x0 + x1) / 2 - 540) / 400))
            lift = io_cubic(f) * 160
            with layer(c, 1 - f * 0.85):
                c.drawRect(rect(x0 + 2, yl - 18 - lift, x1 - x0 - 4, 18), paint("#9C7A4E"))
        if kr > 0:
            T.text(c, "2-INCH PLANKS \u00b7 5-INCH SPIKES", 540, peak - 210, F("mono_b", 22), "amber2", clamp(kr * 3),
                   align="center", track=0.06)
        # the Lunik on its side inside, nose to the left
        ly = gy - 20 - LUNIK_D / 2 * sc - 30
        cap_off = 1.8 * io_cubic(clamp((t - self.t_base - 0.6) / 0.8))
        draw_lunik(c, 520, ly, sc, rot=90, color="cyan2", cap_off=cap_off, xray=0.6, a=0.95)
        # cradle
        for x in (330, 700):
            c.drawRect(rect(x, gy - 60, 30, 60), paint("#8A6A44"))
        # base-cap bolts counter (~130 square-headed bolts)
        kb = clamp((t - self.t_base) / 0.3)
        if kb > 0:
            nb = int(130 * clamp((t - self.t_base) / 1.6))
            bx = 520 + LUNIK_L / 2 * sc - 40
            T.text(c, f"{nb:3d}", bx + 120, ly - 220, F("black", 84), "white", kb, align="center")
            T.text(c, "/ 130 BOLTS", bx + 120, ly - 180, F("mono_b", 22), "amber2", kb, align="center", track=0.08)
        # team silhouettes + strobe flashes
        ki = clamp((t - self.t_in) / 0.4)
        nose_x = 520 - LUNIK_L / 2 * sc + 120
        if kr > 0.3:
            human(c, 330, wall - 4, 120, "#050505", 1.0)
            human(c, 760, wall - 4, 120, "#050505", 1.0)
        if ki > 0:
            human(c, nose_x + 40, ly + 60, 110, "#050505", ki)
            for j in range(3):
                tf = t - self.t_in - 0.3 - j * 0.55
                if 0 < tf < 0.12:
                    c.drawCircle(nose_x + 40, ly - 30, 260, paint(shader=rad_grad((nose_x + 40, ly - 30), 260,
                                                                                   [["white", 0.9], ["white", 0.0]]), blend="Plus"))
        ksh = clamp((t - self.t_shoes) / 0.3)
        if ksh > 0:
            for dx in (0, 34):
                c.drawRRect(rrect(170 + dx, gy - 22, 30, 18, 7), paint("#C9B48A", ksh))
            T.text(c, "SHOES OFF \u2014 NO SCRATCHES", 210, gy + 60, F("mono_b", 22), "amber2", ksh, align="left", track=0.06)
        # fence in the foreground (10 ft)
        for x in range(0, W, 46):
            c.drawRect(rect(x, gy - 10 * sc + 380, 40, 10 * sc - 380 + 40), paint("#07080A", 0.0))
        clock_face(c, 880, 700, 70, self.hours(t), 1.0)
        vignette_band(c, True, 560, 0.85)
        self.chrome(c, t)

    def post(self, t):
        return self.base_post(bloom=0.35, bthresh=0.55)


# --------------------------------------------------------------------------------------- 7. dawn at the rail yard
class Dawn(Night2):
    def setup(self):
        self.t_seven = tok_t("dawn", "7 a.m.,")
        self.t_checker = tok_t("dawn", "checker")
        self.t_no = tok_t("dawn", "no surprise.")

    def draw(self, c, t):
        lt = self.lt(t)
        k = clamp(lt / 3.0)
        top = mix("#060A14", "#1B2A44", k)
        mid = mix("#0B1220", "#6B5A6E", k)
        hor = mix("#121826", "#F0A060", k)
        c.drawRect(rect(0, 0, W, 1380), paint(shader=lin_grad((0, 0), (0, 1380), [top, mid, hor], [0, 0.6, 1])))
        c.drawCircle(760, 1380, 320, paint(shader=rad_grad((760, 1380), 320, [["amber2", 0.45 * k], ["amber2", 0.0]])))
        # skyline / yard silhouettes
        r = rng(13)
        x = 0
        while x < W:
            w_ = r.uniform(60, 160)
            h_ = r.uniform(60, 220)
            c.drawRect(rect(x, 1380 - h_, w_, h_), paint("#07080B"))
            x += w_
        c.drawRect(rect(0, 1380, W, H - 1380), paint("#08090B"))
        # rails (perspective)
        for xo in (-1, 1):
            for off in (60, 150):
                c.drawLine(540 + xo * off * 0.25, 1380, 540 + xo * off * 3.2, H, paint("#3A3F48", 1, stroke=4))
        # flatcar + crate leaving
        leave = io_quad(clamp((t - self.t_no - 0.8) / 1.6))
        fx = 300 + 900 * leave
        c.drawRect(rect(fx - 230, 1420, 460, 30), paint("#14161A"))
        for wx in (-170, -110, 110, 170):
            c.drawCircle(fx + wx, 1462, 18, paint("#1D2026"))
        c.drawPath(poly([(fx - 200, 1420), (fx - 200, 1290), (fx, 1240), (fx + 200, 1290), (fx + 200, 1420)]),
                   paint("#2A1F14"))
        c.drawPath(poly([(fx - 200, 1420), (fx - 200, 1290), (fx, 1240), (fx + 200, 1290), (fx + 200, 1420)]),
                   paint("#8A6A44", 0.7, stroke=3))
        # checker with clipboard
        kc = clamp((t - self.t_checker + 0.3) / 0.4)
        human(c, 840, 1560, 240, "#040404", 1.0)
        c.drawRect(rect(862, 1390, 34, 46), paint("#C9B48A", 0.9 * kc))
        kn = clamp((t - self.t_no) / 0.35)
        if kn > 0:
            c.drawPath(poly([(868, 1414), (878, 1426), (893, 1400)], close=False), paint("#1A6A2A", kn, stroke=4))
            tag(c, "CHECKED IN \u2713", 840, 1250, 28, "night", "paper_hi", kn, align="center")
        clock_face(c, 200, 760, 90, 7.0, clamp((t - self.t_seven + 0.3) / 0.4), "paper_hi")
        vignette_band(c, True, 560, 0.75)
        self.chrome(c, t)


# --------------------------------------------------------------------------------------- 8/9. the document itself
class DocPage(Shot):
    theme = "paper"
    cap_y = 300
    img_name = "lunik_p-7.png"
    page_w_pt = 612.0
    # highlight boxes in PDF points (x0, y0, x1, y1) with reveal times set in setup
    marks = []
    focus = (0, 300)

    def draw(self, c, t):
        lt = self.lt(t)
        bg_paper(c, seed=21, tint=None)
        c.drawRect(rect(0, 0, W, H), paint(shader=rad_grad((540, 1100), 1200, [["black", 0.0], ["black", 0.5]])))
        self._top_band = True
        img = doc_image(self.img_name)
        s = 1500 / img.width() * (1 + 0.05 * io_sine(clamp(lt / 5)))
        pw, ph = img.width() * s, img.height() * s
        k = self.page_w_pt / img.width()   # pt per px of source
        fy = self.focus_y(t)
        x0 = 540 - pw / 2 + 120
        y0 = 1080 - fy / k * s
        with xf(c, 540, 1080, rot=-2.0):
            c.translate(-540, -1080)
            shadow(c, rect(x0, y0, pw, ph), 0, 30, 40, 0.5)
            draw_image(c, img, x0, y0, pw, ph)
            for (bx0, by0, bx1, by1, tt, col) in self.marks:
                u = io_cubic(clamp((t - tt) / 0.6))
                if u <= 0:
                    continue
                X0, Y0 = x0 + bx0 / k * s, y0 + by0 / k * s
                X1, Y1 = x0 + bx1 / k * s, y0 + by1 / k * s
                c.drawRect(skia.Rect.MakeLTRB(X0 - 6, Y0 - 2, X0 + (X1 - X0 + 12) * u, Y1 + 2),
                           paint(col, 0.55, blend="Multiply"))
        self.extra(c, t)
        # paper-coloured band so captions stay legible over the page text
        c.drawRect(rect(0, 0, W, 640), paint(shader=lin_grad((0, 0), (0, 640), [["paper_hi", 0.97], ["paper_hi", 0.9],
                                                                              ["paper_hi", 0.0]], [0, 0.72, 1])))
        hud(c, t, "02", "THE LUNIK", SRC2, color="ink2", t0=self.t0)

    def focus_y(self, t):
        return self.focus[1]

    def extra(self, c, t):
        pass

    def post(self, t):
        return self.base_post(vig=0.5)


class Results(DocPage):
    def setup(self):
        tp = tok_t("results", "likely")
        tf = tok_t("results", "fifth")
        Y = "#FFD84A"
        self.marks = [(24.6, 334.8, 530.2, 355.4, tp - 0.2, Y), (24.6, 355.8, 566.3, 373.4, tp + 0.3, Y),
                      (24.6, 373.8, 547.4, 391.4, tf + 0.5, Y)]
        self.tf = tf

    def focus_y(self, t):
        return 365

    def extra(self, c, t):
        k = clamp((t - self.tf) / 0.2)
        if k > 0:
            with xf(c, 860, 1460, s=lerp(1.5, 1, out_cubic(k)), rot=-8):
                with layer(c, k * 0.9, blend="Multiply"):
                    c.drawCircle(0, 0, 110, paint("red", 1, stroke=10))
                    T.text(c, "No.5", 0, 26, F("black", 84), "red", 1, align="center")


class NoSign(DocPage):
    def setup(self):
        t0 = S("nosign")["t0"]
        Y = "#FFD84A"
        self.marks = [(24.6, 266.8, 565.5, 284.4, t0 + 0.1, Y), (24.6, 284.8, 507.3, 302.4, t0 + 0.9, Y)]

    def focus_y(self, t):
        return lerp(365, 285, io_cubic(clamp((t - self.t0) / 0.8)))


# --------------------------------------------------------------------------------------- 10. end
class End(Shot):
    theme = "night"
    cap_y = 300

    def setup(self):
        self.t_end = S("end")["t1"]

    def draw(self, c, t):
        lt = self.lt(t)
        bg_space(c, t, seed=61)
        km = clamp((t - self.t_end - 0.2) / 1.2)
        # the two files
        kf = out_expo(clamp(lt / 0.7)) * (1 - io_cubic(km))
        if kf > 0:
            for i, (name, stamp, rot, x) in enumerate((("eliot_scan-1.png", "APPROVED FOR RELEASE 1994", -6, 300),
                                                       ("finer_scan-1.png", "RELEASE AS SANITIZED 1995", 5, 780))):
                img = doc_image(name)
                if name.startswith("finer"):
                    src = skia.Rect.MakeXYWH(img.width() * 0.46, 0, img.width() * 0.54, img.height())
                else:
                    src = skia.Rect.MakeXYWH(0, 0, img.width(), img.height())
                w_ = 440
                h_ = w_ * src.height() / src.width()
                y = 1080 - h_ / 2 + (1 - kf) * 200
                with xf(c, x, y + h_ / 2, rot=rot):
                    c.translate(-x, -(y + h_ / 2))
                    shadow(c, rect(x - w_ / 2, y, w_, h_), 0, 26, 30, 0.6)
                    p = skia.Paint(AntiAlias=True)
                    p.setAlphaf(kf)
                    c.drawImageRect(img, src, skia.Rect.MakeXYWH(x - w_ / 2, y, w_, h_),
                                    skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p)
                    ks = clamp((lt - 0.6 - i * 0.35) / 0.14)
                    if ks > 0:
                        with xf(c, x, y + h_ * 0.62, rot=-10, s=lerp(1.6, 1, out_cubic(ks))):
                            with layer(c, ks * kf * 0.9, blend="Multiply"):
                                f = F("black", 34)
                                ww = T.width(stamp, f, 0.04)
                                c.drawRRect(rrect(-ww / 2 - 16, -42, ww + 32, 58, 6), paint("red", 1, stroke=5))
                                T.text(c, stamp, 0, 0, f, "red", 1, align="center", track=0.04)
        # final card: moon + sources
        if km > 0:
            draw_moon(c, 540, 860, 260 + 20 * km, light=(-0.5, 0.2, 0.85), glow_a=0.4 * km, exposure=1.1 * km)
            T.text(c, "SOURCES \u2014 ALL DECLASSIFIED", 540, 1290, F("mono_b", 26), "paper_hi", km, align="center", track=0.18)
            lines = ["F. Eliot, \u201cMoon Bounce Elint,\u201d Studies in Intelligence 11:2 (1967)",
                     "S. W. Finer, \u201cThe Kidnaping of the Lunik,\u201d Studies in Intelligence",
                     "A. D. Wheelon & S. N. Graybeal, \u201cIntelligence for the Space Race,\u201d",
                     "Studies in Intelligence 5 (1961)"]
            for i, ln in enumerate(lines):
                T.text(c, ln, 540, 1350 + i * 44, F("serif_i", 34), "paper", km * 0.9, align="center")
            T.text(c, "Moon & Earth textures: Solar System Scope (CC BY 4.0), from NASA data", 540, 1560, F("mono_r", 18),
                   "steel", km * 0.7, align="center", track=0.04)

    def post(self, t):
        return self.base_post(bloom=0.3)


# --------------------------------------------------------------------------------------- shot list
def shots(b):
    return [
        FileCard2(S("practice")["t1"] + 0.4, b("exhibit", -0.05), tin=("redact", 0.55, {})),
        Exhibit(b("exhibit", -0.05), b("real"), tin=("iris", 0.5, {"at": (540, 1000), "ring": "amber"})),
        Real(b("real"), b("icbm"), tin=("flash", 0.3, {"amt": 0.55})),
        ICBM(b("icbm"), b("borrow"), tin=("zoom", 0.45, {})),
        Borrow(b("borrow"), b("truck"), tin=("slide", 0.45, {})),
        Truck(b("truck"), b("yard"), tin=("push", 0.45, {"dir": 1})),
        Yard(b("yard"), b("dawn"), tin=("fade", 0.4, {})),
        Dawn(b("dawn"), b("results"), tin=("fade", 0.6, {})),
        Results(b("results"), b("nosign"), tin=("redact", 0.55, {})),
        NoSign(b("nosign"), b("end"), tin=("cut", 0.05, {})),
        End(b("end"), layout()[2], tin=("fade", 0.5, {})),
    ]
