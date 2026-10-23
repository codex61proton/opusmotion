"""Sound design: narration + procedurally synthesized effects keyed to the film timeline. No music."""
import math
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine import sfx as X
from engine.core import clamp
from film.common import S, layout, word_t, tok_t, ROOT
from film import main as M
from film import part1 as P1
from film import part2 as P2

OUT = os.path.join(ROOT, "build", "audio")


def vo_chain(x):
    x = signal.sosfilt(signal.butter(2, 75, "hp", fs=X.SR, output="sos"), x)
    # gentle presence lift around 3.2 kHz (+2 dB peaking)
    b, a = signal.iirpeak(3200, 1.2, fs=X.SR)
    x = x + 0.26 * signal.lfilter(b, a, x)
    # soft RMS compression, 3:1 above -20 dBFS
    env = np.sqrt(signal.lfilter([0.002], [1, -0.998], x ** 2) + 1e-9)
    db = 20 * np.log10(env)
    gain_db = np.where(db > -20, -(db + 20) * (1 - 1 / 3), 0.0)
    x = x * 10 ** (gain_db / 20)
    return (x / (np.abs(x).max() + 1e-9) * 0.7).astype(np.float32)


def build_mix():
    segs, cards, total = layout()
    tl = M.build()
    mix = X.Mix(total + 1)
    add = mix.add
    sh = {type(s).__name__ + ("" if type(s).__name__ != "FileCard" else str(s.t0 > 30)): s for s in tl.shots}

    # ---------------- narration
    for sid, seg in segs.items():
        x, sr = sf.read(os.path.join(ROOT, "build", "vo", f"{sid}.wav"), dtype="float32")
        add(seg["t0"], vo_chain(x), -1.0, bus="vo")

    # ---------------- transitions
    for s in tl.shots:
        if not s.tin:
            continue
        kind, d = s.tin[0], s.tin[1]
        t = s.t0
        seed = int(t * 10)
        if kind == "zoom":
            add(t - 0.45, X.whoosh(0.9, 250, 3500, -0.5, 0.5, seed), -15, "sfx")
        elif kind in ("push", "slide"):
            add(t - 0.25, X.whoosh(0.6, 500, 6000, 0.6, -0.6, seed, peak_at=0.45), -16, "sfx")
        elif kind == "flash":
            add(t - 0.05, X.hit(1.6, seed), -14, "sfx")
            add(t - 0.02, X.flashbulb(seed), -18, "sfx")
        elif kind == "glitch":
            add(t - 0.12, X.glitch(0.3, seed), -18, "sfx")
        elif kind == "redact":
            add(t - 0.3, X.whoosh(0.7, 180, 2200, -0.8, 0.8, seed, peak_at=0.5), -14, "sfx")
            add(t, X.paper(0.5, seed), -20, "sfx")
        elif kind == "iris":
            add(t - 0.5, X.reverse_swell(0.8, seed), -18, "sfx")
        elif kind == "fade":
            add(t - 0.3, X.whoosh(1.0, 120, 900, 0, 0, seed, peak_at=0.5, q=0.8), -22, "sfx")

    # ---------------- beds (ambience), crossfaded per shot
    def bed(t0, t1, clip_fn, gain, fade_s=0.6, bus="amb"):
        d = t1 - t0 + fade_s * 2
        x = clip_fn(d)
        x = X.fade(x, fade_s, fade_s)
        add(t0 - fade_s, x, gain, bus)

    names = [type(s).__name__ for s in tl.shots]
    for s, n in zip(tl.shots, names):
        if n in ("Open", "U2", "Horizon", "MoonReveal", "Geometry", "Practice", "ICBM", "End"):
            bed(s.t0, s.t1, lambda d, k=int(s.t0): X.space_air(d, 29 + k), -27)
        elif n in ("Faint", "Sites", "Found"):
            bed(s.t0, s.t1, lambda d, k=int(s.t0): X.room_tone(d, 28 + k, "brown", 0.5), -29)
            bed(s.t0, s.t1, lambda d, k=int(s.t0): X.static(d, 10 + k, 6, 0.25), -34)
        elif n in ("FileCard", "FileCard2", "Results", "NoSign", "Real", "Borrow"):
            bed(s.t0, s.t1, lambda d, k=int(s.t0): X.room_tone(d, 50 + k, "pink", 0.4), -30)
        elif n == "Exhibit":
            bed(s.t0, s.t1, lambda d: X.room_tone(d, 61, "brown", 0.5), -24)
            bed(s.t0, s.t1, lambda d: X.mains_hum(d, 62), -36)
        elif n in ("Truck", "Yard"):
            bed(s.t0, s.t1, lambda d, k=int(s.t0): X.city_night(d, 70 + k), -24)
            bed(s.t0, s.t1, lambda d, k=int(s.t0): X.crickets(d, 80 + k), -26)
        elif n == "Dawn":
            bed(s.t0, s.t1, lambda d: X.city_night(d, 90), -22)

    # ---------------- per-shot effects
    o = sh["Open"]
    add(0.0, X.sub_boom(3.0, 48, 26), -10)
    add(o.t_launch, X.radar_ping(1150, 2.2, verb=0.5), -12)
    add(o.t_launch + 1.28, X.radar_ping(1650, 1.6, verb=0.7), -22)   # touch the moon
    add(o.t_echo, X.radar_ping(1450, 2.4, verb=0.6), -14)
    add(o.t_echo, X.heartbeat_thump(), -10)
    add(o.t_echo + 0.05, X.data_chirps(0.5), -24)
    add(1.0, X.fade(X.static(6.5, 3, 8, 0.3), 0.8, 1.0), -32)

    f1 = [s for s in tl.shots if type(s).__name__ == "FileCard"][0]
    add(f1.t0 + 0.2, X.typewriter(14, 18, 5), -22)
    add(f1.t0 + 0.35, X.stamp(17), -9)

    u = sh["U2"]
    add(u.t_sary - 0.3, X.beep(1850), -20)
    add(u.t_sary - 0.25, X.data_chirps(0.45, 3), -26)
    add(u.t_ant - 0.15, X.shutter(19), -14)
    add(u.t_ant + 0.3, X.typewriter(22, 26, 9), -28)
    add(u.t0 + 0.1, X.whoosh(3.5, 120, 700, -0.3, 0.3, 77, peak_at=0.5, q=0.7), -24)

    h = sh["Horizon"]
    tt = S("horizon")["t0"] + 0.4
    while tt < h.t_cloud - 0.6:
        add(tt, X.radar_ping(1250, 1.0, verb=0.35), -27)
        tt += 1.2
    add(h.t_space, X.whoosh(1.6, 300, 5000, 0, 0.3, 31, peak_at=0.3), -20)
    add(h.t_cloud - 0.45, X.sub_boom(3.0, 44, 24, click=0.9), -12)
    add(h.t_cloud + 0.3, X.fade(X.static(2.2, 33, 30, 3.0), 0.05, 0.4), -18)
    add(h.t_cloud + 0.35, X.pulse_train(9, 0.21, 2200, 4), -22)
    add(h.t_needed + 0.2, X.riser(S("moon")["t0"] - h.t_needed - 0.15, 6), -18)

    m = sh["MoonReveal"]
    add(m.t0 - 0.02, X.sub_boom(3.2, 56, 24, click=0.8), -6)
    add(m.t0 - 0.02, X.hit(2.4, 8, 70, 2500), -12)

    def beam_hits(shot, t0, t1):
        hits, prev = [], False
        t = t0
        while t < t1:
            ang, to_moon = shot.beam_angle(t)
            on = abs(ang - to_moon) < math.radians(3.6)
            if on and not prev:
                hits.append(t)
            prev = on
            t += 1 / 60
        return hits

    g = sh["Geometry"]
    for th in beam_hits(g, g.t0 + 0.4, g.t1):
        add(th, X.radar_ping(1500, 1.4, verb=0.55, seed=int(th)), -21)
        add(th + 0.05, X.data_chirps(0.25, int(th)), -30)
    add(g.t_h, X.beep(1500), -22)
    add(g.t_us, X.beep(1900), -22)
    add(g.t_bounce - 0.2, X.data_chirps(0.6, 12), -27)

    f = sh["Faint"]
    add(f.t_mb, X.tuning(1.7, 11, 3400, 260), -18)
    for i in range(16):
        add(f.t_mb + 0.05 + i * 0.1 * (1 + i / 20), X.tick(100 + i, i % 2 == 0), -26)
    add(f.t_dish - 0.2, X.whoosh(1.4, 200, 1800, 0.4, -0.4, 5, peak_at=0.4), -18)
    add(f.t_dish + 1.2, X.clank(23), -24)

    s_ = sh["Sites"]
    add(s_.t_ches - 0.25, X.beep(1700), -20)
    add(s_.t_ches - 0.2, X.data_chirps(0.4, 21), -26)
    add(s_.t_stan - 0.25, X.beep(2100), -20)
    add(s_.t_stan - 0.2, X.data_chirps(0.4, 22), -26)
    add(s_.t_geo - 0.3, X.whoosh(0.9, 400, 4000, 0, 0, 23, peak_at=0.5), -20)
    for i in range(18):
        add(s_.t_18 - 0.2 + i * (1.0 / 18), X.tick(200 + i, True), -27)

    fd = sh["Found"]
    for i in range(5):
        add(fd.t_scan - 0.3 + i * 0.36, X.beep(1400 + 120 * i, 0.05), -28)
    add(fd.t_ss - 0.1, X.fade(X.static(1.4, 41, 4, 1.0, (200, 7000)), 0.3, 0.4), -22)
    add(fd.t_mw - 0.1, X.pulse_train(8, 0.13, 2400, 42), -22)
    for i in range(12):
        add(fd.t_mw + i * 0.09, X.tick(300 + i, i % 2 == 0), -28)
    add(fd.t_abm - 0.02, X.stamp(43), -8)
    add(fd.t_abm - 0.02, X.hit(1.4, 44, 85), -16)

    pr = sh["Practice"]
    add(pr.t_lock + 0.1, X.beep(1850, 0.06), -18)
    add(pr.t_lock + 0.22, X.beep(1850, 0.06), -18)
    add(pr.t_lock + 0.34, X.beep(2350, 0.12), -17)
    tt = pr.t_lock + 0.5
    while tt < pr.t1 + 0.3:
        add(tt, X.radar_ping(1500, 0.8, verb=0.4, seed=int(tt * 10)), -26)
        tt += 0.28

    f2 = sh["FileCard2"]
    add(f2.t0 + 0.2, X.typewriter(14, 18, 25), -22)
    add(f2.t0 + 0.35, X.stamp(27), -9)

    ex = sh["Exhibit"]
    add(ex.t0 + 0.05, X.clank(51), -16)
    add(ex.t0 + 0.05, X.switch_click(52), -12)
    add(ex.t_lunik, X.beep(1300, 0.06), -24)
    add(ex.t_mock, X.stamp(53), -14)

    rl = sh["Real"]
    add(rl.t0 + 0.2, X.fade(X.paper(2.0, 61, 0.6), 0.2, 0.5), -24)
    add(rl.t_wasnt - 0.1, X.swish(0.3, 62), -16)
    add(rl.t_prod, X.stamp(63), -8)
    add(rl.t_prod, X.hit(1.3, 64, 95), -17)
    add(rl.t_day, X.clock(1.8, 8.0, 65), -24)
    add(rl.t_engine, X.glitch(0.2, 66), -22)

    ic = sh["ICBM"]
    add(ic.t0 + 0.1, X.paper(0.6, 71), -18)
    add(ic.t_meas + 0.2, X.swish(0.4, 72), -20)
    add(ic.t_lb - 0.1, X.riser(2.4, 73, 150, 3000), -22)
    add(ic.t_mi, X.hit(1.6, 74, 75), -14)

    bo = sh["Borrow"]
    add(bo.t0 + 0.1, X.clank(81), -20)
    add(bo.t_mark - 0.2, X.click(82, 9000, 0.03, 0.1), -20)
    add(bo.t_borrow - 0.1, X.whoosh(1.0, 120, 600, 0, 0, 83, peak_at=0.3, q=0.7), -16)
    add(bo.t_borrow + 0.2, X.clock(3.5, 2.0, 84), -18)

    tr = sh["Truck"]
    add(tr.t0, X.fade(X.engine_rumble(tr.t_turn - tr.t0 + 0.6, 900, 91), 0.5, 0.5), -16)
    add(tr.t_turn - 0.1, X.air_brake(92), -16)
    add(tr.t0 + 0.4, X.fade(X.static(0.7, 93, 25, 2, (500, 3000)), 0.02, 0.1), -22)
    add(tr.t_turn + 0.3, X.fade(X.static(0.6, 94, 25, 2, (500, 3000)), 0.02, 0.1), -22)
    add(tr.t_driver - 0.1, X.door(95), -18)
    add(tr.t_driver + 0.6, X.door(96), -20)
    add(tr.t_driver + 0.5, X.fade(X.engine_rumble(2.4, 820, 97), 0.4, 0.8), -19)
    add(tr.t_hotel, X.switch_click(98), -16)

    yd = sh["Yard"]
    add(yd.t0 + 1.0, X.switch_click(101), -16)
    add(yd.t0 + 1.0, X.fade(X.mains_hum(4.0, 102), 0.1, 1.0), -34)
    for i in range(5):
        add(yd.t_roof + i * 0.3, X.creak(0.45, 110 + i, 480 + 40 * i), -17)
    add(yd.t_roof + 1.2, X.clank(115), -26)
    for i in range(4):
        add(yd.t_base + i * 0.42, X.ratchet(5, 18, 120 + i), -20)
    add(yd.t_base + 0.9, X.clank(125), -18)
    for j in range(3):
        tf = yd.t_in + 0.3 + j * 0.55
        add(tf, X.shutter(130 + j), -16)
        add(tf, X.flashbulb(135 + j), -20)
    add(yd.t_shoes, X.footstep(140), -18)
    add(yd.t_shoes + 0.16, X.footstep(141), -19)
    add(yd.t0, X.clock(yd.t1 - yd.t0, 2.0, 142), -30)

    dw = sh["Dawn"]
    add(dw.t_seven - 0.2, X.clock(1.0, 2.0, 151), -26)
    add(dw.t_checker, X.paper(0.4, 152), -18)
    add(dw.t_no, X.click(153, 3000, 0.05, 0.6), -18)
    add(dw.t_no + 0.7, X.fade(X.engine_rumble(3.5, 420, 154), 0.6, 1.0), -18)
    add(dw.t_no + 0.8, X.rail_clacks(3.0, 155), -20)

    rs = sh["Results"]
    add(rs.t0 + 0.1, X.paper(0.6, 161), -18)
    for (_, _, _, _, tt, _) in rs.marks:
        add(tt, X.marker(0.55, int(tt * 10)), -16)
    add(rs.tf, X.stamp(162), -10)
    ns = sh["NoSign"]
    for (_, _, _, _, tt, _) in ns.marks:
        add(tt, X.marker(0.55, int(tt * 10)), -16)

    en = sh["End"]
    add(en.t0 + 0.1, X.paper(0.5, 171), -16)
    add(en.t0 + 0.6, X.stamp(174), -11)
    add(en.t0 + 0.95, X.stamp(175), -11)
    add(en.t_end + 0.15, X.reverse_swell(1.2, 176), -16)
    add(en.t_end + 0.25, X.sub_boom(4.0, 50, 24), -10)
    add(en.t_end + 0.3, X.radar_ping(1200, 3.0, verb=0.7), -24)

    out = mix.render(duck_db=6.0)
    n = int(round(total * X.SR))
    out = out[:n]
    # master: rumble filter, gentle glue compression, soft clip
    out = signal.sosfilt(signal.butter(2, 28, "hp", fs=X.SR, output="sos"), out, axis=0)
    env = np.sqrt(signal.lfilter([0.0015], [1, -0.9985], (out ** 2).mean(1)) + 1e-9)
    db = 20 * np.log10(env)
    g = np.where(db > -18, -(db + 18) * (1 - 1 / 2), 0.0)
    out = out * (10 ** (g / 20))[:, None]
    out = out / (np.abs(out).max() + 1e-9) * 0.89
    tail = int(X.SR * 1.5)
    out[-tail:] *= np.linspace(1, 0, tail)[:, None] ** 2
    os.makedirs(OUT, exist_ok=True)
    sf.write(os.path.join(OUT, "mix.wav"), out.astype(np.float32), X.SR, subtype="FLOAT")
    # stems for verification
    for name, b in mix.buf.items():
        sf.write(os.path.join(OUT, f"stem_{name}.wav"), (b[:n] / (np.abs(b).max() + 1e-9) * 0.9).astype(np.float32), X.SR)
    print("mix", round(total, 2), "s", os.path.join(OUT, "mix.wav"))


if __name__ == "__main__":
    build_mix()
