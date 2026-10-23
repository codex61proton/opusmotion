"""FILE 01 - Moon Bounce ELINT.  Facts: F. Eliot, "Moon Bounce Elint", Studies in Intelligence 11:2 (1967)."""
import math

import numpy as np
import skia

from engine.core import *
from engine.gfx import *
from engine import text as T
from engine.render import Shot
from film.common import *

SRC1 = "SOURCE: F. ELIOT, \"MOON BOUNCE ELINT,\" STUDIES IN INTELLIGENCE 11:2 (1967)"

# Earth-Moon side view: Moon over the North Pacific (30N,150W); Sary Shagan then sits ~94 deg away (on its
# horizon) while Stanford sees the Moon high.  View chosen so the sub-lunar point is straight "up".
GEO_VIEW = dict(lon0=-44.72, lat0=24.54, roll=56.7)


class NightShot(Shot):
    theme = "night"
    cap_y = 300
    file_no, file_title, src = "01", "MOON BOUNCE ELINT", SRC1

    def chrome(self, c, t, a=1.0):
        hud(c, t, self.file_no, self.file_title, self.src, a=a, t0=self.t0)


# ------------------------------------------------------------------------------------------- 0. cold open
class Open(NightShot):
    def setup(self):
        self.t_echo = word_t("open", "Moon")          # echo lands on "Moon"
        self.t_launch = self.t_echo - 2.56             # 1.28 s up + 1.28 s down (mean Earth-Moon distance)

    def draw(self, c, t):
        lt = self.lt(t)
        bg_space(c, t, seed=5, drift=(0, 4))
        push = 1.0 + 0.07 * io_sine(clamp(lt / 9))
        with xf(c, W / 2, 1000, s=push, px=0, py=0):
            c.translate(-W / 2, -1000)
            # moon: light swings from behind (thin crescent) to the front over the shot
            k = io_cubic(clamp((lt - 0.4) / 6.0))
            ang = lerp(math.radians(160), math.radians(28), k)
            L = (-math.sin(ang), 0.18, math.cos(ang))
            draw_moon(c, 540, 930, 330, light=L, glow_a=0.15 + 0.3 * k, exposure=1.2)
            # earth limb at the bottom
            img = cached_image("open_earth", lambda: earth_img(2048, 40, 52, light=(0.9, 0.5, 0.2), margin=1.03,
                                                                atm=0.9, lights=1.6))
            draw_image(c, img, 540 - 1500, 1630, 3000, 3000)
            # radar pulse up (red), echo down (cyan)
            src, moon, rx = (470, 1660), (520, 1265), (640, 1655)
            u = (t - self.t_launch) / 1.28
            pulse_along(c, src, moon, u, "red", 7, 0.22)
            v = (t - self.t_launch - 1.28) / 1.28
            pulse_along(c, moon, rx, v, "cyan", 6, 0.22)
            if 0 < u - 1 < 0.6:
                f = 1 - (u - 1) / 0.6
                c.drawCircle(520, 1265, 90 * (1.4 - f), paint("cyan2", 0.5 * f, stroke=4))
                glow(c, lambda cc: cc.drawCircle(520, 1265, 30, paint("cyan2", f)), 30, 0.9)
            if v > 1:
                f = clamp(1 - (v - 1) / 1.2)
                ring_pulse(c, rx[0], rx[1], v, "cyan", 10, 90, 1.0, f)
        vignette_band(c, True, 620, 0.7)
        # little receiver trace bottom
        a = clamp((lt - 1.0) / 0.6) * (1 - clamp((lt - 8.5) / 0.5))
        if a > 0:
            def tr(uu, tt):
                spike = math.exp(-((uu - 0.72) / 0.012) ** 2) * clamp((t - self.t_echo) * 3)
                return 0.08 * fbm1(uu * 40 + tt * 6, 3) + 0.85 * spike
            scope(c, 300, 1500, 480, 130, t, tr, a=a * 0.9, grid=False)
            label(c, "RX  CHESAPEAKE BAY  150 FT", 300, 1665, 20, "#7CFFB2", 0.7 * a)

    def post(self, t):
        return self.base_post(bloom=0.35, vig=0.7)


# ------------------------------------------------------------------------------------------- file title cards
class FileCard(Shot):
    theme = "paper"
    cap_alpha = 0.0
    num, title, sub, src = "01", "MOON BOUNCE ELINT", ["\u201cThe monitoring of Soviet radars", "by way of the lunar surface.\u201d"], \
        "Studies in Intelligence \u00b7 Vol. 11 No. 2 \u00b7 1967"
    stamp_s = "SECRET"

    def draw(self, c, t):
        lt = self.lt(t)
        bg_paper(c, seed=11)
        c.drawRect(rect(0, 0, W, H), paint(shader=rad_grad((540, 900), 1300, [["black", 0.0], ["black", 0.45]])))
        k = out_expo(clamp(lt / 0.5))
        with xf(c, 0, (1 - k) * 60):
            T.text(c, "FILE", 120, 760, F("mono_b", 40), "ink2", k, track=0.3)
            T.text(c, self.num, 104, 1010, F("black", 280), "ink", k, track=-0.04)
            T.text(c, self.title, 120, 1110, F("xbold", 74), "ink", k, track=-0.01)
            n = 0
            for i, ln in enumerate(self.sub):
                T.text(c, type_on(ln, clamp((lt - 0.2 - i * 0.25) / 0.45)), 120, 1190 + i * 56, F("serif_i", 50), "ink2", k)
            T.text(c, self.src, 120, 1200 + len(self.sub) * 56 + 20, F("mono", 26), "ink3", k * 0.9, track=0.06)
        ks = clamp((lt - 0.35) / 0.12)
        if ks > 0:
            s = lerp(1.6, 1.0, out_cubic(ks))
            with xf(c, 760, 760, s=s, rot=-9):
                with layer(c, 0.85 * ks, blend="Multiply"):
                    f = F("black", 104)
                    w_ = T.width(self.stamp_s, f, 0.08)
                    c.drawRRect(rrect(-w_ / 2 - 26, -112, w_ + 52, 140, 10), paint("red", 1, stroke=9))
                    T.text(c, self.stamp_s, 0, 0, f, "red", 1, align="center", track=0.08)

    def post(self, t):
        return self.base_post(vig=0.55)


# ------------------------------------------------------------------------------------------- 1. U-2 / Sary Shagan
class U2(NightShot):
    def setup(self):
        self.t_ant = tok_t("u2", "antenna")
        self.t_sary = tok_t("u2", "Sary Shagan")

    def draw(self, c, t):
        lt = self.lt(t)
        bg_space(c, t, seed=8, drift=(-3, 0))
        k = io_cubic(clamp(lt / 4.2))
        lon0, lat0 = lerp(20, SARY[0] - 6, k), lerp(28, SARY[1] - 8, k)
        R = lerp(430, 900, io_quart(clamp(lt / 4.6)))
        cx, cy = 540, lerp(1130, 1300, k)
        size = int(min(2048, R * 2 * 1.12))
        img = earth_img(size, lon0, lat0, light=(0.5, 0.6, 0.65), margin=1.12, lights=1.1)
        s = R * 2 * 1.12
        draw_image(c, img, cx - s / 2, cy - s / 2, s, s)
        # USSR outline
        path = globe_path(country_rings(USSR), lon0, lat0, cx, cy, R)
        ka = clamp((lt - 0.2) / 0.8)
        c.drawPath(path, paint("red", 0.10 * ka))
        stroke_path(c, path, "red", 2.2, 0.85 * ka, 0, 1)
        glow(c, lambda cc: stroke_path(cc, path, "red", 4, ka), 10, 0.6)
        lakes = globe_path(country_rings({"Lake Balkhash", "Balkhash"}, "ne_50m_lakes"), lon0, lat0, cx, cy, R)
        c.drawPath(lakes, paint("cyan", 0.35 * ka))
        x, y, z = globe_xy(SARY[0], SARY[1], lon0, lat0, cx, cy, R)
        pin(c, x, y, t, self.t_sary - 0.3, "SARY SHAGAN", "red", side=-1, sub="MISSILE TEST RANGE", size=30, lead=90)
        # U-2 reconnaissance inset (schematic, not a photograph)
        ki = clamp((t - self.t_ant + 0.15) / 0.5)
        if ki > 0:
            e = out_expo(ki)
            bx, by, bw, bh = 470, 575, 530, 420
            with layer(c, e):
                with xf(c, bx + bw / 2, by + bh / 2, s=lerp(0.85, 1.0, e)):
                    c.translate(-(bx + bw / 2), -(by + bh / 2))
                    r = rect(bx, by, bw, bh)
                    shadow(c, r, 0, 20, 30, 0.5)
                    c.drawRect(r, paint("#0B0F14", 0.92))
                    with clip(c, r):
                        rr = rng(4)
                        for i in range(220):  # terrain speckle
                            c.drawCircle(bx + rr.random() * bw, by + rr.random() * bh, 1 + rr.random() * 2.5,
                                         paint("steel", 0.06 + 0.06 * rr.random()))
                        with xf(c, bx + bw / 2, by + bh / 2 + 10, rot=-14):
                            dk = clamp((t - self.t_ant - 0.1) / 0.9)
                            for sx in (-1, 1):  # two long antenna wings (schematic)
                                wing = poly([(0, 0), (sx * 200, -46), (sx * 205, -26), (0, 18)])
                                stroke_path(c, wing, "cyan2", 3, 0.9, 0, dk)
                            stroke_path(c, poly([(-34, -6), (34, -6), (34, 40), (-34, 40)]), "cyan2", 3, 0.9, 0, dk)
                        brackets(c, bx + 60, by + 90, bw - 120, bh - 170, "amber", 0.9, 30, 3)
                        c.drawLine(bx + bw / 2, by + 40, bx + bw / 2, by + bh - 40, paint("amber", 0.35, stroke=1.5))
                        c.drawLine(bx + 40, by + bh / 2, bx + bw - 40, by + bh / 2, paint("amber", 0.35, stroke=1.5))
                    c.drawRect(r, paint("cyan2", 0.6, stroke=2))
                    tag(c, "U-2  \u00b7  1960", bx, by - 14, 24, "night", "amber")
                    label(c, type_on("\u201cA VERY LARGE ANTENNA STRUCTURE\u201d", clamp((t - self.t_ant - 0.3) / 0.8)),
                          bx + 18, by + bh - 24, 21, "amber2")
                    label(c, "SCHEMATIC", bx + bw - 18, by + 36, 18, "steel", 0.8, align="right")
            # leader from inset to pin
            c.drawLine(bx + bw * 0.3, by + bh, x, y, paint("amber", 0.5 * e, stroke=2, effect=dash(8, 8)))
        vignette_band(c, True, 560, 0.75)
        self.chrome(c, t)

    def post(self, t):
        return self.base_post(bloom=0.25)


# ------------------------------------------------------------------------------------------- 2. horizon problem + 1962 nuclear cloud
class Horizon(NightShot):
    EC = (540, 2700)   # earth centre for the side-view arc
    ER = 1460

    def setup(self):
        self.t_straight = tok_t("horizon", "straight")
        self.t_deep = tok_t("horizon", "From")
        self.t_space = tok_t("horizon", "into")
        self.t_nuke = S("nuke")["t0"]
        self.t_cloud = tok_t("nuke", "off")
        self.t_needed = tok_t("nuke", "They")
        a = math.radians(19)
        ex, ey = self.EC
        self.radar = (ex - self.ER * math.sin(a), ey - self.ER * math.cos(a))
        self.rx = (ex + self.ER * math.sin(a), ey - self.ER * math.cos(a))
        self.tan = (math.cos(a), -math.sin(a))  # tangent at radar, pointing toward the US

    def cam(self, t):
        """Vertical camera offset: tilt up into space at 'into space', back down for the cloud, up at 'needed'."""
        up1 = io_cubic(clamp((t - self.t_space) / 1.4)) * (1 - io_cubic(clamp((t - self.t_nuke + 0.2) / 1.0)))
        up2 = io_quart(clamp((t - self.t_needed - 0.3) / 1.6))
        return 520 * up1 + 900 * up2

    def draw(self, c, t):
        lt = self.lt(t)
        oy = self.cam(t)
        bg_space(c, t, seed=12, drift=(0, 0))
        with xf(c, 0, oy):
            ex, ey = self.EC
            R = self.ER
            # atmosphere + earth
            c.drawCircle(ex, ey, R + 70, paint(shader=rad_grad((ex, ey), R + 70, [["#3C86C4", 0.0], ["#3C86C4", 0.0],
                                                                              ["#5FA8E8", 0.45], ["#5FA8E8", 0.0]],
                                                              [0, R / (R + 70) - 0.01, R / (R + 70), 1])))
            c.drawCircle(ex, ey, R, paint(shader=lin_grad((0, ey - R), (0, ey - R + 500), ["#0F2235", "#060B12"])))
            rr = rng(7)
            for i in range(260):  # city lights along the arc
                a = math.radians(rr.uniform(-40, 40))
                d = rr.uniform(4, 40) ** 1.2
                x, y = ex + (R - d) * math.sin(a), ey - (R - d) * math.cos(a)
                c.drawCircle(x, y, rr.uniform(0.8, 2.2), paint("amber2", rr.uniform(0.2, 0.7)))
            c.drawCircle(ex, ey, R, paint("cyan", 0.5, stroke=2))
            # sites
            k_in = clamp(lt / 0.6)
            rxp, ryp = self.radar
            sxp, syp = self.rx
            # radio shadow below the radar's tangent line, beyond the horizon
            tx, ty = self.tan
            ks = clamp((t - self.t_deep) / 0.8)
            if ks > 0:
                far = (rxp + tx * 2400, ryp + ty * 2400)
                stroke_path(c, poly([self.radar, far], close=False), "white", 2, 0.45 * ks, 0, 1, d=(14, 12))
                label(c, "LINE OF SIGHT", rxp + tx * 560, ryp + ty * 560 - 22, 22, "white", 0.6 * ks, align="center")
            # beam wedge (search radars sweep low, close to the horizon)
            kb = clamp((t - S("horizon")["t0"] - 0.3) / 0.6)
            ang = math.atan2(ty, tx) - math.radians(4)
            beam_cone(c, self.radar, ang, math.radians(5), 2600, "red", 0.30 * kb)
            # travelling pulses
            for i in range(12):
                u = ((t - S("horizon")["t0"]) * 0.42 - i * 0.16)
                if u < 0:
                    continue
                u = u % 1.6
                d = u * 2600
                q = ang + math.radians(((i * 37) % 9 - 4) * 0.6)
                p0 = (rxp + math.cos(q) * d, ryp + math.sin(q) * d)
                p1 = (rxp + math.cos(q) * (d + 70), ryp + math.sin(q) * (d + 70))
                fade_a = clamp(1.4 - u) * kb
                c.drawLine(p0[0], p0[1], p1[0], p1[1], paint("red", 0.9 * fade_a, stroke=5))
            # radar + receiver icons
            for (x, y, col, name, sub, side) in ((rxp, ryp, "red", "SOVIET RADAR", "SARY SHAGAN", 1),
                                                 (sxp, syp, "cyan", "U.S. LISTENING POST", "", -1)):
                c.drawCircle(x, y, 11 * k_in, paint(col))
                ring_pulse(c, x, y, t, col, 12, 50, 1.6, k_in * 0.7)
                T.text(c, name, x + side * 26, y + 62, F("mono_b", 26), "white", k_in, align="left" if side > 0 else "right",
                       track=0.08)
                if sub:
                    T.text(c, sub, x + side * 26, y + 94, F("mono_r", 21), col, k_in * 0.8,
                           align="left" if side > 0 else "right", track=0.08)
            # "out of reach" X at US site once beam shown
            kx = clamp((t - self.t_deep - 0.6) / 0.4) * (1 - clamp((t - self.t_cloud) / 0.3))
            if kx > 0:
                for s_ in (-1, 1):
                    c.drawLine(sxp - 16, syp - 64 - 16 * s_, sxp + 16, syp - 64 + 16 * s_, paint("red", kx, stroke=5))
            # 1962: ionized cloud of a nuclear test
            kc = clamp((t - self.t_cloud + 0.4) / 0.5) * (1 - clamp((t - self.t_needed - 0.4) / 0.8))
            if kc > 0:
                cx_, cy_ = ex - 150, ey - R - 400
                for i in range(7):
                    rr_ = 120 + 50 * math.sin(i * 1.7 + lt * 0.8)
                    ox = 70 * math.cos(i * 2.1 + lt * 0.3)
                    oy_ = 40 * math.sin(i * 1.3 + lt * 0.4)
                    c.drawCircle(cx_ + ox, cy_ + oy_, rr_, paint(shader=rad_grad((cx_ + ox, cy_ + oy_), rr_,
                                                                                  [["#C9A6FF", 0.35 * kc], ["#7A5CFF", 0.12 * kc],
                                                                                   ["#7A5CFF", 0.0]])))
                label(c, "IONIZED CLOUD", cx_, cy_ + 200, 24, "#D9C6FF", kc, align="center")
                label(c, "SOVIET NUCLEAR TEST \u00b7 1962", cx_, cy_ + 230, 20, "#B9A6EF", kc * 0.8, align="center")
                # brief scattered intercept: flicker
                fl = (0.5 + 0.5 * math.sin(lt * 31)) * (0.5 + 0.5 * math.sin(lt * 13.3))
                kf = clamp((t - self.t_cloud - 0.3) / 0.3) * (1 - clamp((t - self.t_cloud - 2.4) / 0.4))
                if kf > 0:
                    c.drawLine(rxp, ryp, cx_, cy_, paint("red", 0.5 * kf, stroke=3))
                    c.drawLine(cx_, cy_, sxp, syp, paint("cyan", (0.3 + 0.7 * fl) * kf, stroke=3, effect=dash(18, 10, lt * 80)))
                    tag(c, "BRIEF, CRUDE INTERCEPT", sxp - 20, syp - 120, 22, "night", "cyan", kf, align="right")
            # moon coming in above when we tilt up for "a steadier mirror"
            km = clamp((t - self.t_needed) / 1.5)
            if km > 0:
                draw_moon(c, 540, ey - R - 1960, 150, light=(-0.3, 0.2, 1.0), glow_a=0.4 * km)
        vignette_band(c, True, 560, 0.75)
        self.chrome(c, t)

    def post(self, t):
        return self.base_post(bloom=0.3)


# ------------------------------------------------------------------------------------------- 3. "The Moon."
class MoonReveal(NightShot):
    cap_y = 1500

    def draw(self, c, t):
        lt = self.lt(t)
        bg_space(c, t, seed=21)
        s = lerp(0.82, 1.0, out_expo(clamp(lt / 0.9)))
        R = 470 * s
        draw_moon(c, 540, 960, R, light=(-0.45, 0.25, 0.9), lon0=lerp(-6, 4, lt / 2), glow_a=0.55, exposure=1.25)
        f = clamp(1 - lt / 0.35)
        c.drawRect(rect(0, 0, W, H), paint("white", 0.5 * f, blend="Plus"))

    def post(self, t):
        return self.base_post(bloom=0.45, bthresh=0.5)


# ------------------------------------------------------------------------------------------- 4. geometry (and the 'practice' lock)
class Geometry(NightShot):
    EC, ER = (540, 1500), 300
    MOON, MR = (540, 700), 84
    lock = False

    def setup(self):
        v = GEO_VIEW
        ex, ey = self.EC
        self.sary = globe_xy(*SARY, v["lon0"], v["lat0"], ex, ey, self.ER, v["roll"])[:2]
        self.stan = globe_xy(*STANFORD, v["lon0"], v["lat0"], ex, ey, self.ER, v["roll"])[:2]
        if not self.lock:
            self.t_h = tok_t("geometry", "radar's")
            self.t_us = tok_t("geometry", "America")
            self.t_bounce = tok_t("geometry", "bounced")
        else:
            self.t_h = self.t_us = self.t_bounce = self.t0 - 2
            self.t_lock = tok_t("practice", "locked")

    def beam_angle(self, t):
        """Hen House sweeps a ~32 deg sector (Eliot); centred on the moon direction here."""
        sx, sy = self.sary
        mx, my = self.MOON
        to_moon = math.atan2(my - sy, mx - sx)
        if self.lock:
            k = io_cubic(clamp((t - self.t_lock + 0.2) / 0.6))
            sweep = math.radians(16) * math.sin((t - self.t0) * 2.1) * (1 - k)
        else:
            sweep = math.radians(16) * math.sin((t - self.t0) * 1.9 + 1.2)
        return to_moon + sweep, to_moon

    def draw(self, c, t):
        lt = self.lt(t)
        bg_space(c, t, seed=31, drift=(2, 0))
        v = GEO_VIEW
        ex, ey = self.EC
        k0 = out_expo(clamp(lt / 0.8))
        img = cached_image("geo_earth", lambda: earth_img(int(self.ER * 2 * 1.12), v["lon0"], v["lat0"],
                                                          light=(0.2, 0.9, 0.5), roll=v["roll"], lights=1.2))
        s = self.ER * 2 * 1.12
        draw_image(c, img, ex - s / 2, ey - s / 2, s, s, k0)
        mx, my = self.MOON
        draw_moon(c, mx, my, self.MR, light=(0.0, -0.6, 0.8), glow_a=0.3)
        sx, sy = self.sary
        ux, uy = self.stan
        ang, to_moon = self.beam_angle(t)
        kb = clamp((lt - 0.3) / 0.6)
        beam_cone(c, (sx, sy), ang, math.radians(3.2), 1200, "red", 0.38 * kb)
        hit = abs(ang - to_moon) < math.radians(3.6)
        lockk = 1.0 if (self.lock and t > self.t_lock + 0.3) else 0.0
        # reflection: stream of echoes while the beam is on the moon
        if hit and kb > 0.5:
            glow(c, lambda cc: cc.drawCircle(mx, my, self.MR * 0.5, paint("white", 0.9)), 24, 0.8)
            for i in range(3):
                u = ((t * 1.1 + i / 3) % 1.0)
                pulse_along(c, (mx, my + self.MR * 0.6), (ux, uy), u, "cyan", 5, 0.25)
            # scatter: most energy lost to space
            for j in range(10):
                q = math.radians(-160 + j * 34 + 7 * math.sin(lt + j))
                u = ((t * 0.9 + j * 0.13) % 1.0)
                p1 = (mx + math.cos(q) * 600, my + math.sin(q) * 600)
                pulse_along(c, (mx, my), p1, u, "cyan", 2.5, 0.12, 0.35)
        # sites
        for (x, y, col, name, side) in ((sx, sy, "red", "SARY SHAGAN", 1), (ux, uy, "cyan", "STANFORD, CA", -1)):
            c.drawCircle(x, y, 9, paint(col))
            ring_pulse(c, x, y, t, col, 10, 46, 1.5, 0.8)
            T.text(c, name, x + side * 22, y + 50 if side > 0 else y - 26, F("mono_b", 24), "white", k0,
                   align="left" if side > 0 else "right", track=0.08)
        # conditions checklist
        items = [("1", "MOON ON THE RADAR'S HORIZON", self.t_h, "red"), ("2", "MOON UP OVER THE U.S.", self.t_us, "cyan")]
        for i, (n, s_, tt, col) in enumerate(items):
            kk = out_expo(clamp((t - tt) / 0.5))
            if kk <= 0:
                continue
            y = 1590 + i * 58
            x = 70 + (1 - kk) * -40
            c.drawCircle(x + 18, y - 9, 18, paint(col, kk))
            T.text(c, n, x + 18, y + 0, F("mono_b", 22), "night", kk, align="center")
            T.text(c, s_, x + 50, y, F("mono_b", 24), "white", kk, track=0.06)
        # distance & delay readout (computed: mean distance 384,400 km -> 1.28 s one way)
        kd = clamp((t - self.t_bounce + 0.2) / 0.5) if not self.lock else 1.0
        if kd > 0:
            x0 = 900
            c.drawLine(x0, my + self.MR + 20, x0, ey - self.ER - 20, paint("steel", 0.6 * kd, stroke=2, effect=dash(6, 8)))
            for yy in (my + self.MR + 20, ey - self.ER - 20):
                c.drawLine(x0 - 14, yy, x0 + 14, yy, paint("steel", 0.8 * kd, stroke=2))
            T.text(c, "384,400 KM", x0 - 14, (my + ey) / 2 - 10, F("mono_b", 24), "white", kd, align="right", track=0.06)
            T.text(c, "\u2248 1.3 S EACH WAY", x0 - 14, (my + ey) / 2 + 22, F("mono_r", 20), "steel", kd, align="right",
                   track=0.06)
            T.text(c, "NOT TO SCALE", x0 - 14, (my + ey) / 2 + 50, F("mono_r", 17), "steel", kd * 0.7, align="right",
                   track=0.1)
        if self.lock:
            kl = clamp((t - self.t_lock) / 0.4)
            if kl > 0:
                tag(c, "TRACKING THE MOON \u00b7 UP TO 30 MIN", 540, 1150, 24, "night", "red", kl, align="center")
        vignette_band(c, True, 560, 0.7)
        self.chrome(c, t)

    def post(self, t):
        return self.base_post(bloom=0.32)


class Practice(Geometry):
    lock = True


# ------------------------------------------------------------------------------------------- 5. a million billion times weaker + the dish
class Faint(NightShot):
    def setup(self):
        self.t_mb = tok_t("faint", "million billion")
        self.t_ten = tok_t("faint", "ten")
        self.t_dish = tok_t("faint", "150-foot")

    def draw(self, c, t):
        lt = self.lt(t)
        bg_night(c, glow_at=(540, 1100))
        # ---- part A: two bars on a log scale; the moon echo collapses fifteen orders of magnitude
        ka = 1 - clamp((t - self.t_dish + 0.5) / 0.5)
        if ka > 0:
            with layer(c, ka):
                x0, y0, y1 = 230, 640, 1480
                c.drawLine(x0, y0, x0, y1, paint("steel", 0.6, stroke=2))
                for e in range(0, 16):
                    yy = y0 + (e / 15) * (y1 - y0)
                    major = e % 3 == 0
                    c.drawLine(x0 - (22 if major else 12), yy, x0, yy, paint("steel", 0.7, stroke=2))
                    if major:
                        T.text(c, "10", x0 - 96, yy + 12, F("mono_b", 28), "steel", 0.9)
                        T.text(c, f"\u2212{e}" if e else "0", x0 - 56, yy - 6, F("mono", 18), "steel", 0.9)
                T.text(c, "LOG SCALE", x0 - 20, y1 + 50, F("mono_r", 18), "steel", 0.7, track=0.12)
                drop = io_expo(clamp((t - self.t_mb + 0.1) / 1.6))
                bw_ = 190
                for i, (name, sub, col, lvl) in enumerate((("10 MI FROM", "THE RADAR", "amber", 0.0),
                                                         ("MOON", "ECHO", "cyan", drop))):
                    bx_ = x0 + 70 + i * 290
                    top = y0 + lvl * (y1 - y0)
                    c.drawRect(rect(bx_, y0, bw_, y1 - y0), paint("steel", 0.07))
                    if y1 - top > 1:
                        c.drawRect(rect(bx_, top, bw_, y1 - top), paint(shader=lin_grad((0, y0), (0, y1), [col, [col, 0.35]])))
                    glow(c, lambda cc: cc.drawRect(rect(bx_, top - 3, bw_, 6), paint("white", 1)), 12, 0.9)
                    T.text(c, name, bx_ + bw_ / 2, y1 + 50, F("mono_b", 24), "white", 1, align="center", track=0.06)
                    T.text(c, sub, bx_ + bw_ / 2, y1 + 80, F("mono_b", 24), col, 1, align="center", track=0.06)
                n = 10 ** (15 * drop)
                kn = clamp((t - self.t_mb) / 0.3)
                big_number(c, f"{int(n):,}\u00d7" if drop < 0.999 else "1,000,000,000,000,000\u00d7", 540, 1660,
                           64, "white", kn, track=-0.02)
                T.text(c, "WEAKER", 540, 1712, F("mono_b", 28), "red", kn, align="center", track=0.3)
        # ---- part B: 150-foot dish
        kb = clamp((t - self.t_dish + 0.3) / 0.6)
        if kb > 0:
            dk = io_cubic(clamp((t - self.t_dish + 0.3) / 1.6))
            draw_dish(c, 540, 1180, t, dk, cam_az=20 + 8 * (t - self.t_dish), scale=1.0, color="cyan2", a=kb, el=42)
            human(c, 815, 1420, 42, "amber", kb)
            T.text(c, "PERSON", 815, 1455, F("mono_r", 18), "amber", kb * 0.8, align="center", track=0.1)
            kd = clamp((t - self.t_dish - 0.4) / 0.5)
            c.drawLine(170, 1540, 910, 1540, paint("white", 0.7 * kd, stroke=2))
            for xx in (170, 910):
                c.drawLine(xx, 1525, xx, 1555, paint("white", 0.7 * kd, stroke=2))
            T.text(c, "150 FT  /  46 M", 540, 1590, F("mono_b", 30), "white", kd, align="center", track=0.08)
            T.text(c, "\u201cABOUT THE MINIMUM SIZE USABLE\u201d", 540, 1632, F("mono_r", 21), "steel", kd, align="center",
                   track=0.06)
        vignette_band(c, True, 560, 0.7)
        self.chrome(c, t)

    def post(self, t):
        return self.base_post(bloom=0.3)


# ------------------------------------------------------------------------------------------- 6. sites + the 18-hour window
class Sites(NightShot):
    def setup(self):
        self.t_ches = tok_t("sites", "Chesapeake")
        self.t_stan = tok_t("sites", "Stanford,")
        self.t_geo = tok_t("sites", "Geometry")
        self.t_18 = tok_t("sites", "18 hours")
        r = rng(19)
        # 18 lit hours: short runs on a handful of days (illustrative distribution)
        self.lit = set()
        days = sorted(r.choice(30, 7, replace=False))
        for d in days:
            h0 = int(r.integers(2, 20))
            for h in range(h0, h0 + 3):
                if len(self.lit) < 18:
                    self.lit.add((d, h))
        while len(self.lit) < 18:
            self.lit.add((int(r.integers(30)), int(r.integers(24))))
        self.order = sorted(self.lit)

    def draw(self, c, t):
        lt = self.lt(t)
        bg_space(c, t, seed=40)
        up = io_cubic(clamp((t - self.t_geo + 0.3) / 0.8))
        with xf(c, 0, -620 * up):
            R = 1250
            cx, cy = 540 - 40 * io_sine(clamp(lt / 9)), 1300
            img = cached_image("us_globe", lambda: earth_img(2048, -98, 40, light=(-0.3, 0.6, 0.75), margin=1.12, lights=1.4))
            s = R * 2 * 1.12
            draw_image(c, img, cx - s / 2, cy - s / 2, s, s)
            path = globe_path(country_rings({"United States of America"}), -98, 40, cx, cy, R)
            stroke_path(c, path, "cyan", 2, 0.7, 0, clamp(lt / 1.2))
            for (ll, tt, name, sub, side, col) in ((CHESAPEAKE, self.t_ches, "CHESAPEAKE BAY", "NAVY \u00b7 150 FT \u00b7 JAN 1964", -1, "cyan"),
                                                   (STANFORD, self.t_stan, "STANFORD", "CIA \u00b7 150 FT \u00b7 AUG 1965", 1, "amber")):
                x, y, z = globe_xy(ll[0], ll[1], -98, 40, cx, cy, R)
                pin(c, x, y, t, tt - 0.25, name, col, side=side, sub=sub, size=28, lead=70)
        # month grid
        if up > 0:
            gx, gy, cw, ch = 95, 1890 - 620 * up, 29, 26
            with layer(c, up):
                T.text(c, "ONE MONTH OF MOON-BOUNCE WINDOWS", gx, gy - 40, F("mono_b", 24), "white", 1, track=0.08)
                T.text(c, "HEN HOUSE \u2192 PALO ALTO", gx, gy - 10, F("mono_r", 20), "steel", 0.9, track=0.08)
                for d in range(30):
                    for h in range(24):
                        c.drawRect(rect(gx + d * cw, gy + 20 + h * (ch * 0.62), cw - 4, ch * 0.62 - 4),
                                   paint("steel", 0.16))
                n_on = int(18 * clamp((t - self.t_18 + 0.2) / 1.0))
                for i, (d, h) in enumerate(self.order[:n_on]):
                    r_ = rect(gx + d * cw, gy + 20 + h * (ch * 0.62), cw - 4, ch * 0.62 - 4)
                    c.drawRect(r_, paint("cyan2"))
                    glow(c, lambda cc: cc.drawRect(r_, paint("cyan", 1)), 8, 0.8)
                kk = clamp((t - self.t_18 - 0.4) / 0.4)
                big_number(c, "18", 300, gy + 520, 150, "cyan2", kk, align="right")
                T.text(c, "OF 720 HOURS", 320, gy + 470, F("mono_b", 30), "white", kk, track=0.06)
                T.text(c, "AT BEST \u2014 IF THE RADAR WAS ON", 320, gy + 510, F("mono_r", 22), "steel", kk, track=0.06)
        vignette_band(c, True, 560, 0.75)
        self.chrome(c, t)

    def post(self, t):
        return self.base_post(bloom=0.28)


# ------------------------------------------------------------------------------------------- 7. what they found
class Found(NightShot):
    def setup(self):
        self.t_scan = tok_t("found", "computer-controlled")
        self.t_ss = tok_t("found", "spread-spectrum")
        self.t_mw = tok_t("found", "25 megawatts")
        self.t_abm = tok_t("found", "anti-missile")

    def draw(self, c, t):
        lt = self.lt(t)
        bg_night(c, glow_at=(540, 1000), glow_col="night4")
        x, y, w, h = 90, 700, 900, 560
        G = "#7CFFB2"
        mode = 0 if t < self.t_ss - 0.1 else (1 if t < self.t_mw - 0.1 else 2)

        def trace(u, tt):
            if mode == 0:   # scan with dwell steps: beam azimuth vs time
                steps = [0.0, 0.18, 0.18, 0.18, 0.35, 0.55, 0.55, 0.72, 0.9, 0.9, 1.0]
                i = min(int(u * 10), 9)
                f = u * 10 - i
                a_, b_ = steps[i], steps[i + 1]
                return -0.85 + 1.7 * lerp(a_, b_, smoothstep(0, 1, f))
            if mode == 1:   # spectrum: narrow line broadening into a plateau
                kk = io_cubic(clamp((tt - self.t_ss) / 1.2))
                wd = lerp(0.012, 0.2, kk)
                base = 0.9 * math.exp(-((u - 0.5) / wd) ** 4) - 0.85 + 0.04 * fbm1(u * 80 + tt * 9)
                return base + 0.1 * (1 - kk) * math.exp(-((u - 0.5) / 0.004) ** 2)
            pulses = 0.0
            for j in range(4):
                c0 = 0.12 + j * 0.25
                pulses += math.exp(-((u - c0) / 0.02) ** 8)
            return -0.8 + 1.6 * pulses * (0.85 + 0.15 * fbm1(u * 50 + tt * 3)) + 0.03 * fbm1(u * 200 + tt * 20)

        ka = out_expo(clamp(lt / 0.6))
        sw = clamp((t - (self.t_scan if mode == 0 else self.t_ss if mode == 1 else self.t_mw) + 0.3) / 0.7)
        scope(c, x, y, w, h, t, trace, G, ka, sweep=sw, label_s=["BEAM AZIMUTH vs TIME", "SIGNAL SPECTRUM", "PULSE TRAIN"][mode])
        tag(c, "HEN HOUSE \u00b7 SARY SHAGAN", x, y - 24, 24, "night", G, ka)
        rows = [("SCAN \u2192 DWELL \u2192 SCAN", "COMPUTER CONTROL", self.t_scan),
                ("SPREAD-SPECTRUM MODE", "RANGE / SPEED RESOLUTION", self.t_ss)]
        for i, (a_, b_, tt) in enumerate(rows):
            kk = out_expo(clamp((t - tt) / 0.5))
            if kk > 0:
                yy = 1340 + i * 86
                c.drawRect(rect(x, yy - 34, 8, 60), paint(G, kk))
                T.text(c, a_, x + 30, yy, F("mono_b", 30), "white", kk, track=0.04)
                T.text(c, b_, x + 30, yy + 30, F("mono_r", 21), G, kk * 0.85, track=0.08)
        kmw = clamp((t - self.t_mw + 0.1) / 0.3)
        if kmw > 0:
            v = 25 * out_cubic(clamp((t - self.t_mw) / 1.1))
            T.odometer(c, v, x + w - 40, 1430, F("black", 150), "white", kmw, align="right")
            T.text(c, "MW", x + w - 30, 1430, F("xbold", 54), G, kmw)
            T.text(c, "PEAK POWER (EST.)", x + w - 40, 1475, F("mono_r", 22), G, kmw * 0.85, align="right", track=0.08)
        ks = clamp((t - self.t_abm) / 0.14)
        if ks > 0:
            s = lerp(1.7, 1.0, out_cubic(ks))
            with xf(c, 540, 960, s=s, rot=-7):
                with layer(c, ks):
                    f = F("stencil", 116)
                    w_ = T.width("ABM RADAR", f, 0.06)
                    c.drawRRect(rrect(-w_ / 2 - 30, -118, w_ + 60, 150, 10), paint("red", 0.92, stroke=10))
                    T.text(c, "ABM RADAR", 0, 0, f, "red", 0.95, align="center", track=0.06)
        vignette_band(c, True, 560, 0.7)
        self.chrome(c, t)

    def post(self, t):
        return self.base_post(bloom=0.35)
