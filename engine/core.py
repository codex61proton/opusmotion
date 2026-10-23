"""Timing, easing, springs and deterministic noise shared by every scene."""
import math
import numpy as np

W, H, FPS = 1080, 1920, 30


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def lerp2(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def prog(t, a, b):
    """Normalised progress of t through [a, b], clamped."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return clamp((t - a) / (b - a))


def remap(x, a, b, c, d):
    return c + (d - c) * clamp((x - a) / (b - a)) if b != a else d


def smoothstep(a, b, x):
    t = clamp((x - a) / (b - a)) if b != a else float(x >= b)
    return t * t * (3 - 2 * t)


# --- easing -----------------------------------------------------------------
def linear(t): return t
def in_quad(t): return t * t
def out_quad(t): return 1 - (1 - t) ** 2
def io_quad(t): return 2 * t * t if t < .5 else 1 - (-2 * t + 2) ** 2 / 2
def in_cubic(t): return t ** 3
def out_cubic(t): return 1 - (1 - t) ** 3
def io_cubic(t): return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def out_quart(t): return 1 - (1 - t) ** 4
def io_quart(t): return 8 * t ** 4 if t < .5 else 1 - (-2 * t + 2) ** 4 / 2
def out_quint(t): return 1 - (1 - t) ** 5
def io_quint(t): return 16 * t ** 5 if t < .5 else 1 - (-2 * t + 2) ** 5 / 2
def in_expo(t): return 0.0 if t <= 0 else 2 ** (10 * t - 10)
def out_expo(t): return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def io_expo(t):
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    return 2 ** (20 * t - 10) / 2 if t < .5 else (2 - 2 ** (-20 * t + 10)) / 2


def out_circ(t): return math.sqrt(1 - (t - 1) ** 2)
def io_sine(t): return -(math.cos(math.pi * t) - 1) / 2


def out_back(t, s=1.70158):
    t -= 1
    return 1 + (s + 1) * t ** 3 + s * t ** 2


def in_back(t, s=1.70158):
    return (s + 1) * t ** 3 - s * t ** 2


def bezier(x1, y1, x2, y2):
    """CSS-style cubic-bezier easing."""
    def f(x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        t = x
        for _ in range(8):
            cx = 3 * x1 * t * (1 - t) ** 2 + 3 * x2 * t * t * (1 - t) + t ** 3 - x
            d = 3 * x1 * (1 - t) ** 2 + 6 * (x2 - x1) * t * (1 - t) + 3 * (1 - x2) * t * t
            if abs(d) < 1e-6: break
            t = clamp(t - cx / d)
        return 3 * y1 * t * (1 - t) ** 2 + 3 * y2 * t * t * (1 - t) + t ** 3
    return f


# Signature curves of the piece: a fast-settling "documentary" ease and a snap.
ease_doc = bezier(0.22, 1.0, 0.36, 1.0)
ease_snap = bezier(0.7, 0.0, 0.2, 1.0)
ease_cam = bezier(0.45, 0.0, 0.25, 1.0)


def spring(t, freq=2.2, damp=0.42):
    """Damped spring step response (0 -> 1 with overshoot). t in seconds."""
    if t <= 0: return 0.0
    w = 2 * math.pi * freq
    if damp >= 1:
        return 1 - (1 + w * t) * math.exp(-w * t)
    wd = w * math.sqrt(1 - damp * damp)
    return 1 - math.exp(-damp * w * t) * (math.cos(wd * t) + damp * w / wd * math.sin(wd * t))


def ease_in(t, a, b, fn=ease_doc):
    return fn(prog(t, a, b))


def env(t, a, b, c, d, fn_in=out_cubic, fn_out=in_cubic):
    """Trapezoid envelope: rises over [a,b], holds, falls over [c,d]."""
    if t < a or t > d: return 0.0
    if t < b: return fn_in(prog(t, a, b))
    if t <= c: return 1.0
    return 1 - fn_out(prog(t, c, d))


# --- deterministic noise ------------------------------------------------------
def _hash(i, seed=0):
    x = (i * 374761393 + seed * 668265263) & 0xFFFFFFFF
    x = ((x ^ (x >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((x ^ (x >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def noise1(x, seed=0):
    """Smooth value noise in [-1, 1]."""
    i = math.floor(x)
    f = x - i
    u = f * f * (3 - 2 * f)
    return (lerp(_hash(i, seed), _hash(i + 1, seed), u)) * 2 - 1


def fbm1(x, seed=0, oct=3):
    v, a, s = 0.0, 0.5, 1.0
    for o in range(oct):
        v += a * noise1(x * s, seed + o * 17)
        a *= 0.5
        s *= 2.03
    return v


def shake(t, amp=4.0, freq=1.3, seed=1):
    return (amp * fbm1(t * freq, seed), amp * fbm1(t * freq, seed + 99))


def rng(seed):
    return np.random.default_rng(seed)
