"""Procedural sound-effects library (48 kHz stereo float32). No music: every element is a physical-style effect."""
import math

import numpy as np
from scipy import signal

SR = 48000


def _rng(seed):
    return np.random.default_rng(seed)


def secs(n):
    return int(round(n * SR))


def t_axis(dur):
    return np.arange(secs(dur)) / SR


# ---------------------------------------------------------------- generators / filters
def white(dur, seed=0):
    return _rng(seed).standard_normal(secs(dur)).astype(np.float32)


def pink(dur, seed=0):
    n = secs(dur)
    X = np.fft.rfft(_rng(seed).standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    X /= np.sqrt(np.maximum(f, 20.0))
    y = np.fft.irfft(X, n)
    return (y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def brown(dur, seed=0):
    y = np.cumsum(_rng(seed).standard_normal(secs(dur)))
    y = signal.sosfilt(signal.butter(2, 15, "hp", fs=SR, output="sos"), y)
    return (y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def bp(x, lo, hi, order=2):
    hi = min(hi, SR / 2 * 0.95)
    return signal.sosfilt(signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x).astype(np.float32)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, min(f, SR / 2 * 0.95), "lowpass", fs=SR, output="sos"), x).astype(np.float32)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "highpass", fs=SR, output="sos"), x).astype(np.float32)


def sweep_bp(x, f0, f1, q=2.0, curve=1.0, block=128):
    """Band-pass whose centre frequency glides f0 -> f1 (RBJ biquad, coefficients updated per block, state carried)."""
    y = np.zeros_like(x, dtype=np.float32)
    n = len(x)
    zi = np.zeros(2)
    for i in range(0, n, block):
        k = (i / max(n - 1, 1)) ** curve
        fc = min(f0 * (f1 / f0) ** k, SR * 0.45)
        w0 = 2 * math.pi * fc / SR
        al = math.sin(w0) / (2 * q)
        b = np.array([al, 0.0, -al])
        a = np.array([1 + al, -2 * math.cos(w0), 1 - al])
        seg, zi = signal.lfilter(b / a[0], a / a[0], x[i:i + block], zi=zi)
        y[i:i + block] = seg
    return y


def env_ad(n, a, d, curve=4.0):
    """Attack (s) then exponential decay to silence over the remaining samples."""
    na = max(1, secs(a))
    e = np.ones(n, np.float32)
    e[:na] = np.linspace(0, 1, na) ** 2
    rest = n - na
    if rest > 0:
        e[na:] = np.exp(-curve * np.arange(rest) / max(secs(d), 1))
    return e


def fade(x, fi=0.005, fo=0.02):
    x = x.copy()
    a, b = secs(fi), secs(fo)
    if a:
        x[:a] *= np.linspace(0, 1, a)[:, None] if x.ndim == 2 else np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)[:, None] if x.ndim == 2 else np.linspace(1, 0, b)
    return x


def stereo(x, pan=0.0, width=0.0, seed=0):
    """Mono -> stereo with constant-power pan (-1..1) and optional decorrelated width."""
    if x.ndim == 2:
        return x
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    out = np.stack([x * l, x * r], 1)
    if width > 0:
        d = secs(0.0007 + 0.0006 * _rng(seed).random())
        out[d:, 1] = out[d:, 1] * (1 - width) + x[:-d] * r * width
    return out.astype(np.float32)


def pan_move(x, p0, p1):
    n = len(x)
    p = np.linspace(p0, p1, n)
    a = (p + 1) * math.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1).astype(np.float32)


def norm(x, peak=0.9):
    return (x * (peak / (np.abs(x).max() + 1e-9))).astype(np.float32)


# ---------------------------------------------------------------- space: reverb
_IR = {}


def ir(decay=1.6, pre=0.012, bright=6000, seed=3):
    key = (decay, pre, bright, seed)
    if key in _IR:
        return _IR[key]
    n = secs(decay * 1.3)
    r = _rng(seed)
    t = np.arange(n) / SR
    e = np.exp(-6.9 * t / decay)
    chans = []
    for ch in range(2):
        nz = r.standard_normal(n) * e
        nz = lp(nz, bright * (1 - 0.45 * np.clip(t[-1], 0, 1)))
        # darker tail: blend in a low-passed copy toward the end
        dark = lp(nz, bright * 0.25)
        k = np.clip(t / decay, 0, 1)
        nz = nz * (1 - k) + dark * k
        z = np.zeros(secs(pre))
        chans.append(np.concatenate([z, nz]))
    out = np.stack(chans, 1).astype(np.float32)
    out /= np.sqrt((out ** 2).sum(0, keepdims=True)) + 1e-9
    _IR[key] = out
    return out


def reverb(x, mix=0.3, decay=1.6, pre=0.012, bright=6000, seed=3):
    xs = stereo(x) if x.ndim == 1 else x
    h = ir(decay, pre, bright, seed)
    wet = np.stack([signal.fftconvolve(xs[:, c], h[:, c]) for c in range(2)], 1)
    dry = np.zeros_like(wet)
    dry[:len(xs)] = xs
    return ((1 - mix) * dry + mix * wet * 0.9).astype(np.float32)


def echo(x, delay, fb=0.35, n=4, lp_f=3000):
    xs = stereo(x) if x.ndim == 1 else x
    d = secs(delay)
    out = np.zeros((len(xs) + d * n, 2), np.float32)
    out[:len(xs)] += xs
    cur = xs
    for i in range(1, n + 1):
        cur = np.stack([lp(cur[:, 0], lp_f), lp(cur[:, 1], lp_f)], 1) * fb
        cur = cur[:, ::-1]  # ping-pong
        out[d * i:d * i + len(cur)] += cur
    return out


# ---------------------------------------------------------------- effects
def whoosh(dur=0.9, f0=300, f1=4000, pan0=-0.7, pan1=0.7, seed=1, peak_at=0.6, q=1.6):
    x = pink(dur, seed) * 0.8 + white(dur, seed + 1) * 0.2
    n = len(x)
    pk = int(n * peak_at)
    e = np.concatenate([np.linspace(0, 1, pk) ** 2.2, np.linspace(1, 0, n - pk) ** 1.6])
    y = sweep_bp(x * e, f0, f1, q=q)
    y = y + 0.25 * lp(x * e, 260)
    return fade(pan_move(norm(y), pan0, pan1), 0.002, 0.03)


def swish(dur=0.35, seed=2, pan0=0.4, pan1=-0.4):
    return whoosh(dur, 1200, 7000, pan0, pan1, seed, peak_at=0.45, q=1.2)


def sub_boom(dur=2.2, f0=58, f1=28, seed=4, click=0.5):
    t = t_axis(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 5)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 2.2)
    trans = lp(white(0.06, seed), 1800) * np.exp(-np.arange(secs(0.06)) / secs(0.012))
    body[:len(trans)] += trans * click
    body = np.tanh(body * 1.6) / np.tanh(1.6)
    return reverb(norm(body), 0.18, 2.0, bright=2500)


def hit(dur=1.4, seed=5, tone=90, bright=3200):
    """Cinematic low impact with a metallic-ish transient (not tonal music: inharmonic, decaying)."""
    t = t_axis(dur)
    x = np.sin(2 * np.pi * np.cumsum(tone * (1 + 0.8 * np.exp(-t * 18))) / SR) * np.exp(-t * 4)
    nz = bp(white(dur, seed), 300, bright) * np.exp(-t * 22)
    modes = sum(np.sin(2 * np.pi * f * t + p) * np.exp(-t * d) * a for f, p, d, a in
                [(431, 0.3, 14, 0.15), (977, 1.1, 20, 0.08), (1721, 2.0, 28, 0.05)])
    y = x + nz * 0.7 + modes
    return reverb(norm(y), 0.25, 1.8, bright=5000, seed=seed)


def riser(dur=2.5, seed=6, f0=200, f1=6000):
    """Tension swell: filtered noise with accelerating flutter (no pitch content)."""
    x = pink(dur, seed)
    n = len(x)
    e = np.linspace(0, 1, n) ** 2.5
    t = np.arange(n) / SR
    rate = 4 + 26 * (t / dur) ** 2
    flutter = 0.75 + 0.25 * np.sin(2 * np.pi * np.cumsum(rate) / SR)
    y = sweep_bp(x * e * flutter, f0, f1, q=1.3, curve=1.8)
    return fade(stereo(norm(y), 0, 0.6, seed), 0.01, 0.01)


def reverse_swell(dur=1.6, seed=7):
    y = hit(dur, seed)
    return fade(y[::-1][-secs(dur):], 0.05, 0.004)


def radar_ping(freq=1400, dur=1.8, seed=8, sweep=0.04, verb=0.45):
    t = t_axis(0.12)
    f = freq * (1 + sweep * (1 - t / 0.12))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(len(t), 0.002, 0.11, 3.0)
    tone += 0.25 * np.sin(2 * np.pi * np.cumsum(f * 2.01) / SR) * env_ad(len(t), 0.001, 0.05, 5.0)
    pad = np.zeros(secs(dur))
    pad[:len(tone)] = tone
    return reverb(norm(pad) * 0.9, verb, 2.4, pre=0.02, bright=5000, seed=seed)


def pulse_train(n=6, gap=0.11, freq=2400, seed=9):
    """Radar pulse burst as heard through a receiver: short clipped tone bursts."""
    out = np.zeros(secs(gap * n + 0.3))
    for i in range(n):
        t = t_axis(0.012)
        b = np.sign(np.sin(2 * np.pi * freq * t)) * 0.5 + np.sin(2 * np.pi * freq * t) * 0.5
        b *= np.hanning(len(t))
        s = secs(i * gap)
        out[s:s + len(b)] += b
    out = bp(out, 600, 6000)
    return stereo(norm(out), 0, 0.3, seed)


def static(dur=3.0, seed=10, crackle=12.0, fade_rate=0.4, band=(300, 4200)):
    """Shortwave-style receiver hiss with crackle and slow fading."""
    r = _rng(seed)
    x = bp(white(dur, seed), *band) * 0.35 + bp(pink(dur, seed + 1), 200, 2500) * 0.4
    n = len(x)
    k = r.random(n) < crackle / SR
    imp = np.zeros(n)
    imp[k] = r.standard_normal(k.sum()) * 3
    imp = bp(signal.lfilter([1], [1, -0.97], imp), 500, 7000)
    t = np.arange(n) / SR
    am = 0.65 + 0.35 * np.sin(2 * np.pi * fade_rate * t + r.random() * 6) * np.sin(2 * np.pi * fade_rate * 0.37 * t + 1)
    return stereo(norm((x + imp * 0.6) * am) * 0.8, 0, 0.5, seed)


def tuning(dur=1.6, seed=11, f0=3200, f1=600):
    """Receiver tuning sweep: heterodyne whistle gliding through static."""
    t = t_axis(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    w = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.3 + 0.2 * np.sin(2 * np.pi * 7 * t))
    w *= np.sin(np.pi * t / dur) ** 1.5
    s = static(dur, seed)[:, 0]
    return stereo(norm(bp(w * 0.6 + s * 0.7, 250, 5000)), 0, 0.4, seed)


def beep(freq=1850, dur=0.07, seed=12):
    t = t_axis(dur)
    y = np.sin(2 * np.pi * freq * t) * np.hanning(len(t)) ** 0.3
    return stereo(fade(y.astype(np.float32), 0.002, 0.01), 0, 0.2, seed)


def data_chirps(dur=0.6, seed=13, rate=28):
    """Fast telemetry-like blips (random, inharmonic)."""
    r = _rng(seed)
    out = np.zeros(secs(dur))
    i = 0.0
    while i < dur - 0.03:
        f = r.choice([1650, 2120, 2730, 3310, 1980])
        b = np.sin(2 * np.pi * f * t_axis(0.018)) * np.hanning(secs(0.018))
        s = secs(i)
        out[s:s + len(b)] += b * (0.5 + 0.5 * r.random())
        i += (1 + r.random()) / rate
    return stereo(norm(out) * 0.7, 0, 0.5, seed)


def click(seed=14, bright=4500, dur=0.04, body=0.5):
    r = _rng(seed)
    t = t_axis(dur)
    nz = bp(white(dur, seed), 800, bright) * np.exp(-t * 300)
    modes = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) * a for f, d, a in
                [(r.uniform(1400, 2400), 180, 0.6), (r.uniform(3000, 5200), 260, 0.4), (r.uniform(500, 900), 120, body)])
    return norm(nz + modes * 0.6)


def typewriter(n=10, rate=11.0, seed=15, jitter=0.35, bell=False):
    r = _rng(seed)
    out = np.zeros(secs(n / rate + 0.4))
    tt = 0.0
    for i in range(n):
        k = click(seed + i, bright=r.uniform(3500, 6500), body=r.uniform(0.6, 1.2)) * r.uniform(0.55, 1.0)
        thump = lp(white(0.03, seed + 100 + i), 300) * np.exp(-t_axis(0.03) * 120) * 0.6
        s = secs(tt)
        out[s:s + len(k)] += k
        out[s:s + len(thump)] += thump
        tt += (1 + jitter * r.uniform(-1, 1)) / rate
    return reverb(stereo(norm(out) * 0.9, 0, 0.3, seed), 0.08, 0.4, bright=7000)


def teletype(dur=2.0, seed=16):
    """Clattering teleprinter: dense mechanical clicks over motor hum."""
    r = _rng(seed)
    out = np.zeros(secs(dur))
    tt = 0.0
    while tt < dur - 0.05:
        k = click(int(r.integers(1e6)), bright=r.uniform(2500, 5000), body=0.9) * r.uniform(0.4, 1.0)
        s = secs(tt)
        out[s:s + len(k)] += k[:len(out) - s]
        tt += 1 / r.uniform(9, 14) if r.random() > 0.08 else 0.15
    t = t_axis(dur)
    motor = (np.sin(2 * np.pi * 60 * t) * 0.3 + bp(pink(dur, seed), 80, 400) * 0.6) * 0.25
    return reverb(stereo(norm(out + motor) * 0.8, 0, 0.3, seed), 0.1, 0.5)


def stamp(seed=17):
    t = t_axis(0.5)
    thud = lp(white(0.5, seed), 400) * np.exp(-t * 35) * 1.4
    body = np.sin(2 * np.pi * (70 + 60 * np.exp(-t * 40)) * t) * np.exp(-t * 18)
    slap = bp(white(0.5, seed + 1), 1200, 6000) * np.exp(-t * 90) * 0.5
    return reverb(stereo(norm(thud + body + slap), 0, 0.2, seed), 0.12, 0.6, bright=4000)


def paper(dur=0.6, seed=18, intensity=1.0):
    r = _rng(seed)
    x = bp(white(dur, seed), 1500, 9000)
    n = len(x)
    grains = np.zeros(n)
    k = r.random(n) < 500 / SR
    grains[k] = r.random(k.sum())
    grains = signal.lfilter([1], [1, -0.995], grains)
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 0.7
    y = x * (0.25 + grains / (grains.max() + 1e-9)) * e
    return stereo(norm(y) * 0.6 * intensity, r.uniform(-0.3, 0.3), 0.5, seed)


def shutter(seed=19):
    """Mechanical camera shutter: first curtain, second curtain, then film advance whirr."""
    out = np.zeros(secs(0.55))
    for i, (tt, a) in enumerate([(0.0, 1.0), (0.045, 0.8)]):
        k = click(seed + i, bright=7000, body=0.3) * a
        s = secs(tt)
        out[s:s + len(k)] += k
    t = t_axis(0.22)
    whirr = bp(white(0.22, seed + 5), 1500, 5000) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 70 * t))) * np.hanning(len(t))
    s = secs(0.18)
    out[s:s + len(whirr)] += whirr * 0.35
    return reverb(stereo(norm(out) * 0.8, 0, 0.3, seed), 0.08, 0.5)


def tick(seed=20, hi=True):
    k = click(seed, bright=6000 if hi else 3500, dur=0.03, body=0.2)
    return reverb(stereo(k * (0.7 if hi else 0.55), 0, 0.2, seed), 0.15, 0.7)


def clock(dur=3.0, rate=2.0, seed=21):
    out = np.zeros((secs(dur + 0.8), 2), np.float32)
    for i in range(int(dur * rate)):
        k = tick(seed, i % 2 == 0)
        s = secs(i / rate)
        out[s:s + len(k)] += k
    return out


def ratchet(n=8, rate=16, seed=22):
    out = np.zeros(secs(n / rate + 0.3))
    for i in range(n):
        k = click(seed + i, bright=5000, body=0.8)
        s = secs(i / rate)
        out[s:s + len(k)] += k * (0.7 + 0.3 * (i % 2))
    return reverb(stereo(norm(out) * 0.8, 0.2, 0.3, seed), 0.15, 0.7)


def clank(seed=23):
    """Metal panel/bolt: inharmonic modal ring."""
    r = _rng(seed)
    t = t_axis(1.2)
    y = sum(np.sin(2 * np.pi * f * t + r.random() * 6) * np.exp(-t * d) * a for f, d, a in
            [(r.uniform(300, 420), 6, 0.5), (r.uniform(900, 1100), 9, 0.35), (r.uniform(1900, 2300), 14, 0.25),
             (r.uniform(3100, 3600), 20, 0.15)])
    y += bp(white(1.2, seed), 1000, 6000) * np.exp(-t * 80) * 0.6
    return reverb(stereo(norm(y) * 0.8, r.uniform(-0.4, 0.4), 0.3, seed), 0.25, 1.2)


def engine_rumble(dur=4.0, rpm=750, seed=24, load=1.0):
    """Diesel/petrol truck idle: firing pulses + chassis noise."""
    t = t_axis(dur)
    fire = rpm / 60 * 3  # 6-cyl four-stroke firing rate
    r = _rng(seed)
    jitter = 1 + 0.02 * np.cumsum(r.standard_normal(len(t))) / np.sqrt(len(t))
    ph = 2 * np.pi * np.cumsum(fire * jitter) / SR
    pulses = np.maximum(np.sin(ph), 0) ** 6
    y = lp(pulses, 300) * 1.0 + lp(brown(dur, seed), 180) * 0.6 + bp(pink(dur, seed + 1), 200, 1200) * 0.15 * load
    return stereo(norm(y) * 0.8, 0, 0.4, seed)


def air_brake(seed=25):
    t = t_axis(1.0)
    y = bp(white(1.0, seed), 2500, 9000) * (np.exp(-t * 3) * np.minimum(1, t * 60))
    return reverb(stereo(norm(y) * 0.6, 0.3, 0.4, seed), 0.2, 1.0)


def door(seed=26):
    """Heavy truck/warehouse door: latch clunk + rolling rumble."""
    t = t_axis(1.4)
    latch = click(seed, bright=2500, dur=0.08, body=1.4)
    roll = lp(brown(1.4, seed), 500) * np.sin(np.pi * np.clip(t / 1.2, 0, 1)) * 0.7
    out = roll.copy()
    out[:len(latch)] += latch
    end = clank(seed + 1)[:, 0][:secs(0.6)] * 0.5
    s = secs(1.1)
    out[s:s + len(end)] += end[:len(out) - s]
    return reverb(stereo(norm(out) * 0.8, 0, 0.3, seed), 0.25, 1.4, bright=3000)


def tape_motor(dur=3.0, seed=27):
    t = t_axis(dur)
    y = (np.sin(2 * np.pi * 50 * t) * 0.2 + np.sin(2 * np.pi * 100 * t) * 0.1 + bp(pink(dur, seed), 300, 3000) * 0.3)
    y *= 0.9 + 0.1 * np.sin(2 * np.pi * 3.1 * t)
    return stereo(norm(y) * 0.5, 0, 0.5, seed)


def room_tone(dur=10.0, seed=28, color="pink", level=0.06):
    x = pink(dur, seed) if color == "pink" else brown(dur, seed)
    x = lp(x, 1800)
    return stereo(norm(x) * level, 0, 0.9, seed)


def space_air(dur=10.0, seed=29):
    """Dark, breathing low wind for vacuum shots — filtered brown noise with slow motion."""
    t = t_axis(dur)
    x = lp(brown(dur, seed), 220) * 0.7 + bp(pink(dur, seed + 1), 300, 900) * 0.12
    x *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t + 1.3)
    return stereo(norm(x) * 0.5, 0, 0.9, seed)


def glitch(dur=0.25, seed=30):
    r = _rng(seed)
    out = np.zeros(secs(dur))
    i = 0
    while i < len(out):
        L = int(r.integers(secs(0.005), secs(0.03)))
        kind = r.integers(3)
        seg = np.arange(L) / SR
        if kind == 0:
            s = np.sign(np.sin(2 * np.pi * r.uniform(200, 3000) * seg))
        elif kind == 1:
            s = white(L / SR, int(r.integers(1e6)))[:L]
        else:
            s = np.zeros(L)
        out[i:i + L] = s[:len(out) - i] * r.uniform(0.2, 0.8)
        i += L
    return stereo(norm(bp(out, 200, 9000)) * 0.6, r.uniform(-0.5, 0.5), 0.3, seed)


def heartbeat_thump(seed=31):
    """Very low single body-thump used for emphasis on key reveals."""
    t = t_axis(0.6)
    y = np.sin(2 * np.pi * (52 + 25 * np.exp(-t * 30)) * t) * np.exp(-t * 9)
    return stereo(norm(y) * 0.9, 0, 0.0, seed)


def mains_hum(dur=3.0, seed=32):
    t = t_axis(dur)
    y = sum(np.sin(2 * np.pi * 60 * k * t) / k ** 1.4 for k in range(1, 8))
    y = bp(y, 50, 900) * (0.9 + 0.1 * np.sin(2 * np.pi * 0.3 * t))
    return stereo(norm(y) * 0.4, 0, 0.3, seed)


def crickets(dur=6.0, seed=33):
    """Night ambience: distant, irregular insect chirps (high band, sparse)."""
    r = _rng(seed)
    out = np.zeros(secs(dur))
    tt = r.uniform(0, 0.3)
    while tt < dur - 0.2:
        f = r.uniform(4200, 4800)
        nchirp = int(r.integers(2, 5))
        for j in range(nchirp):
            seg = t_axis(0.03)
            b = np.sin(2 * np.pi * f * seg) * np.hanning(len(seg))
            s = secs(tt + j * 0.045)
            if s + len(b) < len(out):
                out[s:s + len(b)] += b * r.uniform(0.3, 1.0)
        tt += r.uniform(0.4, 1.4)
    return reverb(stereo(norm(out) * 0.25, r.uniform(-0.6, 0.6), 0.8, seed), 0.5, 1.8)


def city_night(dur=6.0, seed=34):
    """Distant city wash: low traffic rumble + occasional far horn-less swells."""
    x = lp(brown(dur, seed), 400) * 0.6 + bp(pink(dur, seed + 1), 200, 1500) * 0.25
    t = t_axis(dur)
    x *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t) ** 2
    return stereo(norm(x) * 0.5, 0, 0.9, seed)


def flashbulb(seed=35):
    """Photo flash: capacitor whine-up tail is skipped; bright pop + tiny glass tick."""
    t = t_axis(0.3)
    pop = bp(white(0.3, seed), 2000, 10000) * np.exp(-t * 60)
    tk = click(seed, bright=9000, dur=0.02, body=0.1)
    y = pop.copy()
    y[:len(tk)] += tk
    return reverb(stereo(norm(y) * 0.7, 0, 0.3, seed), 0.15, 0.6)


# ---------------------------------------------------------------- mixing
class Mix:
    def __init__(self, dur):
        self.buf = {}
        self.dur = dur

    def bus(self, name):
        if name not in self.buf:
            self.buf[name] = np.zeros((secs(self.dur) + SR, 2), np.float32)
        return self.buf[name]

    def add(self, t, clip, gain_db=0.0, bus="sfx", pan=None):
        b = self.bus(bus)
        x = stereo(clip) if clip.ndim == 1 else clip
        if pan is not None:
            m = x.mean(1)
            x = stereo(m, pan)
        s = secs(t)
        if s < 0:
            x, s = x[-s:], 0
        e = min(len(b), s + len(x))
        b[s:e] += x[:e - s] * (10 ** (gain_db / 20))

    def render(self, duck_from="vo", duck_db=7.0, duck_buses=("sfx", "amb")):
        n = secs(self.dur)
        out = np.zeros((n, 2), np.float32)
        key = None
        if duck_from in self.buf:
            v = np.abs(self.buf[duck_from][:n]).mean(1)
            # envelope follower: fast attack, slow release
            env = signal.lfilter([0.02], [1, -0.98], v)
            env = np.maximum.accumulate if False else env
            env = signal.sosfiltfilt(signal.butter(1, 6, fs=SR, output="sos"), env)
            key = np.clip(env / (np.percentile(env, 95) + 1e-9), 0, 1)
        for name, b in self.buf.items():
            x = b[:n].copy()
            if key is not None and name in duck_buses:
                g = 10 ** (-duck_db * key / 20)
                x *= g[:, None]
            out += x
        return out
