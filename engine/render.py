"""Timeline, shots, transitions, caption track, and the frame renderer / encoder."""
import argparse
import importlib
import math
import os
import subprocess
import sys
import time as _time

import numpy as np
import skia

from .core import W, H, FPS, clamp, prog, ease_doc, io_cubic, out_expo, in_expo, io_expo, lerp
from .gfx import paint, layer, xf, rect, poly, C, draw_image


class Shot:
    theme = "paper"      # caption colour scheme
    cap_y = 300          # caption block top (px, 1080x1920 space)
    cap_alpha = 1.0

    def __init__(self, t0, t1, **kw):
        self.t0, self.t1 = t0, t1
        self.tin = kw.pop("tin", None)       # (kind, duration, opts)
        self.__dict__.update(kw)
        self.setup()

    def setup(self):
        pass

    def lt(self, t):
        return t - self.t0

    def draw(self, c, t):
        raise NotImplementedError

    def post(self, t):
        return self.base_post()

    def base_post(self, **kw):
        if self.theme == "paper":
            d = {"vig": 0.42, "grainAmt": 0.06, "bloom": 0.0, "hal": 0.0, "ca": 0.8}
        else:
            d = {"vig": 0.6, "grainAmt": 0.085, "bloom": 0.28, "bthresh": 0.55, "hal": 0.12, "ca": 1.4}
        d.update(kw)
        return d

    def cues(self):
        return []

    def caption(self, t):
        return self.cap_y, self.cap_alpha, self.theme


class Timeline:
    def __init__(self, shots, cards=(), duration=None, fps=FPS):
        self.shots = sorted(shots, key=lambda s: s.t0)
        self.cards = list(cards)
        self.duration = duration or max(s.t1 for s in self.shots)
        self.fps = fps

    def at(self, t):
        cur = None
        for s in self.shots:
            if s.t0 <= t + 1e-9:
                cur = s
        return cur

    def prev_of(self, s):
        i = self.shots.index(s)
        return self.shots[i - 1] if i > 0 else None

    def card_at(self, t):
        cur = None
        for cd in self.cards:
            if cd.t_in - 0.06 <= t < cd.t_out + 0.25:
                cur = cd
        return cur


# --- transitions ------------------------------------------------------------------------
def _snap(surf):
    return surf.makeImageSnapshot()


def transition(kind, c, imgA, imgB, k, opts):
    """Composite outgoing imgA and incoming imgB at progress k in [0,1]."""
    full = rect(0, 0, W, H)
    if kind == "fade":
        draw_image(c, imgA, 0, 0, W, H)
        draw_image(c, imgB, 0, 0, W, H, io_cubic(k))
    elif kind == "redact":
        # a black redaction bar sweeps across: covers A, then uncovers B
        e = io_expo(k)
        ang = opts.get("angle", -8)
        bw = W * 2.6
        x = lerp(-bw * 1.05, W * 1.4, e)
        draw_image(c, imgA if x + bw * 0.5 < W * 0.5 else imgB, 0, 0, W, H)
        with xf(c, W / 2, H / 2, rot=ang):
            c.translate(-W / 2, -H / 2)
            c.drawRect(rect(x, -H, bw * 0.6, H * 3), paint(opts.get("color", "ink")))
            c.drawRect(rect(x + bw * 0.6 + 26, -H, 18, H * 3), paint("red"))
    elif kind == "iris":
        cx, cy = opts.get("at", (W / 2, H / 2))
        draw_image(c, imgA, 0, 0, W, H)
        r = io_expo(k) * math.hypot(W, H)
        path = skia.Path()
        path.addCircle(cx, cy, max(r, 0.1))
        c.save()
        c.clipPath(path, doAntiAlias=True)
        draw_image(c, imgB, 0, 0, W, H)
        c.restore()
        c.drawCircle(cx, cy, r, paint(opts.get("ring", "red"), 1 - k, stroke=10))
    elif kind == "push":
        e = io_expo(k)
        dy = opts.get("dir", 1)
        draw_image(c, imgA, 0, -H * e * dy, W, H)
        draw_image(c, imgB, 0, H * (1 - e) * dy, W, H)
    elif kind == "zoom":
        e = io_cubic(k)
        s = 1 + 0.35 * e
        with xf(c, W / 2, H / 2, s=s):
            c.translate(-W / 2, -H / 2)
            draw_image(c, imgA, 0, 0, W, H, 1 - e)
        s2 = 0.86 + 0.14 * ease_doc(k)
        with xf(c, W / 2, H / 2, s=s2):
            c.translate(-W / 2, -H / 2)
            draw_image(c, imgB, 0, 0, W, H, clamp(e * 1.4))
    elif kind == "shutter":
        n = opts.get("n", 7)
        close = k < 0.5
        e = io_expo(k * 2) if close else 1 - io_expo((k - 0.5) * 2)
        draw_image(c, imgA if close else imgB, 0, 0, W, H)
        bh = H / n
        for i in range(n):
            y = i * bh
            c.drawRect(rect(0, y, W, bh * e + 1), paint(opts.get("color", "ink")))
    elif kind == "slide":
        e = io_expo(k)
        draw_image(c, imgA, -W * e, 0, W, H)
        draw_image(c, imgB, W * (1 - e), 0, W, H)
    else:  # cut / glitch / flash fall back to hard switch at mid-point
        draw_image(c, imgA if k < 0.5 else imgB, 0, 0, W, H)


def trans_post(kind, k, opts):
    if kind == "flash":
        return {"flash": max(0.0, 1 - abs(k - 0.5) * 2) ** 1.6 * opts.get("amt", 0.85)}
    if kind == "glitch":
        return {"glitch": max(0.0, 1 - abs(k - 0.5) * 2) * opts.get("amt", 1.0)}
    if kind in ("push", "slide", "zoom"):
        return {"ca": 1.2 + 10 * math.sin(math.pi * k)}
    return {}


# --- frame rendering -----------------------------------------------------------------------
class Renderer:
    def __init__(self, tl, scale=1.0, post=True):
        self.tl, self.scale = tl, scale
        self.w, self.h = int(W * scale), int(H * scale)
        info = skia.ImageInfo.Make(self.w, self.h, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
        self.surf = skia.Surface.MakeRaster(info)
        self.tmpA = skia.Surface.MakeRaster(info)
        self.tmpB = skia.Surface.MakeRaster(info)
        self.post = None
        if post:
            from .glfx import Post
            self.post = Post(self.w, self.h)

    def _draw_shot(self, surf, shot, t):
        c = surf.getCanvas()
        c.save()
        c.scale(self.scale, self.scale)
        c.clear(skia.ColorBLACK)
        shot.draw(c, t)
        c.restore()

    def frame(self, t):
        tl = self.tl
        shot = tl.at(t)
        pp = {}
        c = self.surf.getCanvas()
        prev = tl.prev_of(shot)
        tin = shot.tin
        if tin and prev is not None and t < shot.t0 + tin[1]:
            kind, dur = tin[0], tin[1]
            opts = tin[2] if len(tin) > 2 else {}
            k = prog(t, shot.t0, shot.t0 + dur)
            if kind in ("flash", "glitch", "cut"):
                tm = shot.t0 + dur / 2
                active = prev if t < tm else shot
                self._draw_shot(self.surf, active, t)
                pp.update(active.post(t))
            else:
                self._draw_shot(self.tmpA, prev, t)
                self._draw_shot(self.tmpB, shot, t)
                a, b = _snap(self.tmpA), _snap(self.tmpB)
                c.save()
                c.clear(skia.ColorBLACK)
                c.scale(self.scale, self.scale)
                transition(kind, c, a, b, k, opts)
                c.restore()
                pp.update(shot.post(t))
            pp.update(trans_post(kind, k, opts))
        else:
            self._draw_shot(self.surf, shot, t)
            pp.update(shot.post(t))
        # captions on top
        card = tl.card_at(t)
        if card is not None:
            ref = tl.at(card.t_in + 0.01) if card.t_in > t else shot
            y, a, theme = shot.caption(t)
            c.save()
            c.scale(self.scale, self.scale)
            card.draw(c, t, W / 2, y, theme, a)
            c.restore()
        arr = self.surf.makeImageSnapshot().toarray()
        if self.post is None:
            return arr[..., :3].tobytes(), pp
        return self.post.run(arr, t, pp), pp


def encoder(path, w, h, fps, crf=12, preset="medium", extra=()):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", *extra, path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def _worker(args):
    modname, f0, f1, out, scale, crf = args
    mod = importlib.import_module(modname)
    tl = mod.build()
    r = Renderer(tl, scale)
    enc = encoder(out, r.w, r.h, tl.fps, crf=crf, preset="fast")
    t0 = _time.time()
    for f in range(f0, f1):
        data, _ = r.frame(f / tl.fps)
        enc.stdin.write(data)
        if (f - f0) % 60 == 0:
            el = _time.time() - t0
            done = f - f0 + 1
            print(f"[{out[-12:]}] {done}/{f1 - f0}  {el / done:.2f}s/f", flush=True)
    enc.stdin.close()
    enc.wait()
    return out


def render_video(modname, out, scale=1.0, workers=2, start=0.0, end=None, crf=12):
    import multiprocessing as mp
    mod = importlib.import_module(modname)
    tl = mod.build()
    end = tl.duration if end is None else min(end, tl.duration)
    f0, f1 = int(round(start * tl.fps)), int(round(end * tl.fps))
    n = max(1, workers)
    step = math.ceil((f1 - f0) / n)
    jobs = []
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    for i in range(n):
        a, b = f0 + i * step, min(f1, f0 + (i + 1) * step)
        if a < b:
            jobs.append((modname, a, b, f"{out}.part{i}.mp4", scale, crf))
    ctx = mp.get_context("spawn")
    with ctx.Pool(len(jobs)) as pool:
        parts = pool.map(_worker, jobs)
    lst = out + ".txt"
    with open(lst, "w") as fh:
        for p in parts:
            fh.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], check=True)
    for p in parts:
        os.remove(p)
    os.remove(lst)
    return out


def stills(modname, times, outdir, scale=0.5, post=True, sheet=None):
    from PIL import Image
    mod = importlib.import_module(modname)
    tl = mod.build()
    r = Renderer(tl, scale, post=post)
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for t in times:
        data, _ = r.frame(t)
        img = Image.frombytes("RGB", (r.w, r.h), data)
        p = os.path.join(outdir, f"t{t:07.2f}.png")
        img.save(p)
        paths.append(p)
    if sheet:
        cols = min(len(paths), sheet)
        rows = math.ceil(len(paths) / cols)
        tw, th = r.w, r.h
        S = Image.new("RGB", (cols * tw + (cols - 1) * 6, rows * th + (rows - 1) * 6), "white")
        for i, p in enumerate(paths):
            S.paste(Image.open(p), ((i % cols) * (tw + 6), (i // cols) * (th + 6)))
        sp = os.path.join(outdir, "sheet.png")
        S.save(sp)
        return sp
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("module")
    ap.add_argument("--out", default="build/out.mp4")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--crf", type=int, default=12)
    ap.add_argument("--stills", default=None)
    ap.add_argument("--stilldir", default="/tmp/verify/stills")
    ap.add_argument("--sheet", type=int, default=0)
    a = ap.parse_args()
    if a.stills:
        ts = [float(x) for x in a.stills.split(",")]
        print(stills(a.module, ts, a.stilldir, a.scale, sheet=a.sheet or None))
    else:
        t0 = _time.time()
        render_video(a.module, a.out, a.scale, a.workers, a.start, a.end, a.crf)
        print("done", a.out, f"{_time.time() - t0:.1f}s")
