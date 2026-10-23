from engine.core import *
from engine.gfx import *
from engine import text as T
from engine.render import Shot, Timeline
from engine.text import Card, parse_card
import skia

class Paper(Shot):
    theme = "paper"; cap_y = 330
    def draw(self, c, t):
        bg_paper(c)
        lt = self.lt(t)
        # a document card with a stamp to test layering
        r = rrect(140, 760, 800, 900, 6)
        shadow(c, r, 0, 24, 30, .25)
        c.drawRRect(r, paint("paper_hi"))
        f = T.font("type", 34)
        for i in range(14):
            T.text(c, "THE QUICK BROWN FOX JUMPS 0123456789"[: 10 + (i*7)%26], 200, 860 + i*52, f, "ink2", .85)
        c.drawRect(rect(200, 860+5*52-34, 420, 44), paint("ink"))
        T.text(c, "TOP SECRET", 540, 1500, T.font("stencil", 140), "red", .85, align="center", track=0.04)
        T.text(c, "TOP", 0, 1900, T.font("mono", 40), "red")   # bottom-left marker for orientation

class Night(Shot):
    theme = "night"; cap_y = 330
    def draw(self, c, t):
        bg_night(c, glow_at=(540, 1200))
        lt = self.lt(t)
        p = smooth([(100, 1300), (300, 1100), (540, 1250), (780, 1050), (980, 1200)])
        stroke_path(c, p, "cyan", 6, 1, 0, clamp(lt/1.5))
        glow(c, lambda cc: stroke_path(cc, p, "cyan", 10, 1, 0, clamp(lt/1.5)), 16, .9)
        c.drawCircle(540, 900, 120, paint("amber"))
        T.odometer(c, 1956 + lt*3.3, 540, 1600, T.font("mono", 120), "paper_hi", align="center")
    def post(self, t):
        return {"bloom": .5}

def build():
    lines1 = parse_card("In [1956=nineteen fifty-six], / !British intelligence ^broke^ a ~cipher~")
    ts = [0.2, 0.5, 0.9, 1.3, 1.6, 1.9, 2.2]
    i = 0
    for ln in lines1:
        for tok in ln:
            tok["t"] = ts[i]; i += 1
    lines2 = parse_card("They never touched / !the code.")
    for j, ln in enumerate(lines2):
        for k, tok in enumerate(ln):
            tok["t"] = 3.2 + 0.25*(j*3+k)
    cards = [Card(lines1, 0.2, 3.0), Card(lines2, 3.2, 6)]
    return Timeline([Paper(0, 3.0), Night(3.0, 6.0, tin=("redact", 0.7, {}))], cards)
