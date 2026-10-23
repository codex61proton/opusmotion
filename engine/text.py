"""Typography: font registry, tracked text, word-by-word caption cards, counters."""
import os
import re

import skia

from .core import clamp, prog, ease_doc, out_cubic, out_expo, lerp
from .gfx import C, paint, layer, xf, ROOT

FONT_DIR = os.path.join(ROOT, "assets", "fonts")
FILES = {
    "serif_i": "InstrumentSerif-Italic.ttf",
    "serif": "InstrumentSerif-Regular.ttf",
    "black": "InterDisplay-Black.ttf",
    "xbold": "InterDisplay-ExtraBold.ttf",
    "bold": "InterDisplay-Bold.ttf",
    "semi": "InterDisplay-SemiBold.ttf",
    "med": "InterDisplay-Medium.ttf",
    "light_i": "InterDisplay-LightItalic.ttf",
    "ital": "InterDisplay-Italic.ttf",
    "mono": "IBMPlexMono-Medium.ttf",
    "mono_r": "IBMPlexMono-Regular.ttf",
    "mono_l": "IBMPlexMono-Light.ttf",
    "mono_b": "IBMPlexMono-SemiBold.ttf",
    "type": "CourierPrime-Regular.ttf",
    "type_b": "CourierPrime-Bold.ttf",
    "stencil": ("BigShouldersStencil-VF.ttf", {"wght": 800, "opsz": 72}),
    "stencil_l": ("BigShouldersStencil-VF.ttf", {"wght": 500, "opsz": 72}),
}
_TF, _FONT = {}, {}


def _tag(s):
    return (ord(s[0]) << 24) | (ord(s[1]) << 16) | (ord(s[2]) << 8) | ord(s[3])


def typeface(name):
    if name in _TF:
        return _TF[name]
    spec = FILES[name]
    if isinstance(spec, tuple):
        fname, axes = spec
        base = skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, fname))
        coords = [skia.FontArguments.VariationPosition.Coordinate(_tag(k), v) for k, v in axes.items()]
        vp = skia.FontArguments.VariationPosition(skia.FontArguments.VariationPosition.Coordinates(coords))
        fa = skia.FontArguments()
        fa.setVariationDesignPosition(vp)
        tf = base.makeClone(fa)
    else:
        tf = skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, spec))
    _TF[name] = tf
    return tf


def font(name, size):
    key = (name, round(size, 2))
    f = _FONT.get(key)
    if f is None:
        f = skia.Font(typeface(name), size)
        f.setSubpixel(True)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        f.setLinearMetrics(True)
        f.setHinting(skia.FontHinting.kNone)
        _FONT[key] = f
    return f


def width(text, f, track=0.0):
    if not text:
        return 0.0
    return f.measureText(text) + track * f.getSize() * (len(text) - 1)


def blob(text, f, track=0.0):
    """TextBlob with tracking (letter-spacing as fraction of em)."""
    if track == 0:
        return skia.TextBlob.MakeFromString(text, f)
    glyphs = f.textToGlyphs(text)
    ws = f.getWidths(glyphs)
    xs, x = [], 0.0
    for wv in ws:
        xs.append(x)
        x += wv + track * f.getSize()
    return skia.TextBlob.MakeFromPosTextH(text, xs, 0.0, f)


def text(c, s, x, y, f, color="ink", a=1.0, align="left", track=0.0, p=None):
    if a <= 0.002 or not s:
        return 0.0
    w = width(s, f, track)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    b = blob(s, f, track)
    if b is not None:
        c.drawTextBlob(b, x, y, p if p is not None else paint(color, a))
    return w


def text_path(s, f, x=0.0, y=0.0):
    return skia.TextUtils.GetPath(s, x, y, f) if hasattr(skia, "TextUtils") else f.getPath(f.textToGlyphs(s)[0])


def cap_height(f):
    m = f.getMetrics()
    return -m.fAscent * 0.72 if not m.fCapHeight else m.fCapHeight


# --- caption cards ---------------------------------------------------------------------
STYLE = {
    # name: (font key, size, tracking)
    "lead": ("serif_i", 74, 0.0),
    "punch": ("xbold", 92, -0.025),
    "huge": ("black", 150, -0.035),
    "mono": ("mono", 46, 0.06),
}
TOKEN_RE = re.compile(r"(?P<pre>[!#^~%*]*)\[(?P<disp>[^\]=]+)=(?P<spk>[^\]]+)\](?P<punct>[^\s]*)|(?P<word>\S+)")


def parse_card(src):
    """Card markup -> lines of tokens.

    `/` breaks a line.  `*w*` punch, `^w^` red accent, `~w~` redacted-reveal,
    `#w#` mono, `[shown=spoken words]` overrides speech.  A line beginning with
    `!` is entirely punch.
    """
    lines, cur, force = [], [], False
    toks = []
    for m in TOKEN_RE.finditer(src):
        if m.group("disp"):
            pre, punct = m.group("pre") or "", m.group("punct") or ""
            # markers may wrap the override: #[a=b]# -> "#a#" ; trailing marker sits in punct
            toks.append((pre + m.group("disp") + punct, m.group("spk")))
        else:
            toks.append((m.group("word"), None))
    for raw, spoken in toks:
        if raw == "/":
            lines.append(cur)
            cur, force = [], False
            continue
        style, accent = ("punch" if force else "lead"), None
        if raw.startswith("!") and not cur:
            force, style, raw = True, "punch", raw[1:]
            if not raw:
                continue
        for mark, kind in (("*", "punch"), ("^", "red"), ("~", "redact"), ("#", "mono"), ("%", "huge")):
            if raw.startswith(mark) and raw.rstrip(".,;:?!'\"").endswith(mark) and len(raw) > 1:
                core = raw.rstrip(".,;:?!'\"")
                tail = raw[len(core):]
                raw = core[1:-1] + tail
                if kind in ("punch",):
                    style = "punch"
                elif kind == "mono":
                    style = "mono"
                elif kind == "huge":
                    style = "huge"
                else:
                    style, accent = "punch", kind
        disp = raw.replace("_", " ")
        spk = spoken if spoken is not None else disp
        cur.append({"text": disp, "style": style, "accent": accent, "spoken": spk})
    if cur:
        lines.append(cur)
    return lines


class Card:
    """A caption card: tokens with absolute reveal times (seconds)."""

    def __init__(self, lines, t_in, t_out, scale=1.0):
        self.lines, self.t_in, self.t_out, self.scale = lines, t_in, t_out, scale

    def layout(self, cx, top, maxw=960):
        rows, y = [], top
        for ln in self.lines:
            sizes = []
            for tok in ln:
                fk, sz, tr = STYLE[tok["style"]]
                f = font(fk, sz * self.scale)
                sizes.append((f, tr))
            sp = [width(" ", f) * (0.9 if tok["style"] == "lead" else 0.75) for tok, (f, tr) in zip(ln, sizes)]
            ws = [width(tok["text"], f, tr) for tok, (f, tr) in zip(ln, sizes)]
            total = sum(ws) + sum(sp[:-1])
            k = min(1.0, maxw / total) if total > 0 else 1.0
            asc = max(-f.getMetrics().fAscent for f, _ in sizes) * k
            desc = max(f.getMetrics().fDescent for f, _ in sizes) * k
            x = cx - total * k / 2
            y += asc
            row = []
            for tok, (f, tr), wv, s in zip(ln, sizes, ws, sp):
                ff = f if k == 1 else font(STYLE[tok["style"]][0], f.getSize() * k)
                row.append((tok, ff, tr, x, y, wv * k))
                x += (wv + s) * k
            rows.append(row)
            y += desc + 6 * self.scale
        return rows, y

    def draw(self, c, t, cx, top, theme="paper", alpha=1.0, maxw=960):
        if t < self.t_in - 0.5 or t > self.t_out + 0.4:
            return
        rows, _ = self.layout(cx, top, maxw)
        ink = "ink" if theme == "paper" else "paper_hi"
        soft = "ink2" if theme == "paper" else "paper"
        out = 1.0 - out_cubic(prog(t, self.t_out, self.t_out + 0.22))
        for row in rows:
            for tok, f, tr, x, y, wv in row:
                ts = tok["t"]
                k = prog(t, ts - 0.04, ts + 0.30)
                if k <= 0:
                    continue
                e = ease_doc(k)
                a = clamp(out_cubic(prog(t, ts - 0.04, ts + 0.16))) * out * alpha
                dy = (1 - e) * 26 * self.scale - (1 - out) * 14
                sig = (1 - out_expo(k)) * 9
                col = ink if tok["style"] != "lead" else soft
                if tok["accent"] == "red":
                    col = "red"
                with layer(c, a, filt=skia.ImageFilters.Blur(sig, sig * 0.6) if sig > 0.3 else None):
                    if tok["accent"] == "redact":
                        _redact_word(c, tok, f, tr, x, y + dy, wv, t - ts, theme)
                    else:
                        text(c, tok["text"], x, y + dy, f, col, 1.0, track=tr)
                if tok["accent"] == "red":
                    u = out_expo(prog(t, ts + 0.18, ts + 0.62))
                    if u > 0:
                        yy = y + f.getSize() * 0.16
                        c.drawRect(skia.Rect.MakeLTRB(x, yy, x + wv * u, yy + 7 * self.scale),
                                   paint("red", a * 0.95))


def _redact_word(c, tok, f, tr, x, y, wv, dt, theme):
    """Word starts under a black redaction bar that slides off to the right."""
    ink = "ink" if theme == "paper" else "paper_hi"
    text(c, tok["text"], x, y, f, "red" if theme == "paper" else "red", 1.0, track=tr)
    k = out_expo(prog(dt, 0.25, 0.75))
    m = f.getMetrics()
    top, bot = y + m.fAscent * 0.86, y + m.fDescent * 0.6
    pad = 10
    x0 = x - pad + (wv + 2 * pad) * k
    if k < 1:
        c.drawRect(skia.Rect.MakeLTRB(x0, top, x + wv + pad, bot), paint("ink" if theme == "paper" else "black", 1.0))


def caption_cards(spec, timings):
    """spec: list of card markup strings; timings: list of per-spoken-word (start, end) flat
    across the spec. Returns Card list with token times filled in."""
    cards, wi = [], 0
    for src in spec:
        lines = parse_card(src)
        for ln in lines:
            for tok in ln:
                n = max(1, len(tok["spoken"].split()))
                tok["t"] = timings[wi][0]
                tok["t_end"] = timings[min(wi + n - 1, len(timings) - 1)][1]
                wi += n
        cards.append(lines)
    return cards


def odometer(c, value, x, y, f, color="ink", a=1.0, digits=None, align="left", t_roll=None, track=0.0):
    """Draw integer with per-digit vertical rolling (value may be fractional)."""
    v = max(0.0, value)
    iv = int(v)
    s = f"{iv:,}" if digits is None else f"{iv:0{digits}d}"
    frac = v - iv
    cw = max(width(str(d), f) for d in range(10)) + track * f.getSize()
    total = sum(cw if ch.isdigit() else width(ch, f) for ch in s)
    if align == "center":
        x -= total / 2
    elif align == "right":
        x -= total
    m = f.getMetrics()
    lh = (m.fDescent - m.fAscent) * 1.02
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(x - 10, y + m.fAscent * 1.02, x + total + 10, y + m.fDescent * 1.1))
    ndig = sum(ch.isdigit() for ch in s)
    di = 0
    for ch in s:
        if ch.isdigit():
            # the last digit rolls with fractional part; carries roll when lower digits are 9
            place = ndig - 1 - di
            roll = 0.0
            if place == 0:
                roll = frac
            else:
                lower = iv % (10 ** place)
                if lower == 10 ** place - 1:
                    roll = frac
            d = int(ch)
            text(c, str(d), x + (cw - width(str(d), f)) / 2, y - roll * lh, f, color, a)
            text(c, str((d + 1) % 10), x + (cw - width(str((d + 1) % 10), f)) / 2, y + (1 - roll) * lh, f, color, a)
            x += cw
            di += 1
        else:
            text(c, ch, x, y, f, color, a)
            x += width(ch, f)
    c.restore()
    return total
