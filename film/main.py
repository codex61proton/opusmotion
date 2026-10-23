"""Film assembly: shot list keyed to the narration segments."""
from engine.render import Timeline
from film.common import S, layout
from film import part1 as P1


def build():
    segs, cards, total = layout()
    b = lambda sid, d=-0.1: S(sid)["t0"] + d
    shots = [
        P1.Open(0.0, S("open")["t1"] + 0.3),
        P1.FileCard(S("open")["t1"] + 0.3, b("u2", -0.05), tin=("flash", 0.3, {"amt": 0.6})),
        P1.U2(b("u2", -0.05), b("horizon"), tin=("zoom", 0.45, {})),
        P1.Horizon(b("horizon"), b("moon", -0.05), tin=("push", 0.45, {"dir": 1})),
        P1.MoonReveal(b("moon", -0.05), b("geometry"), tin=("flash", 0.25, {"amt": 0.5})),
        P1.Geometry(b("geometry"), b("faint"), tin=("zoom", 0.5, {})),
        P1.Faint(b("faint"), b("sites"), tin=("slide", 0.45, {})),
        P1.Sites(b("sites"), b("found"), tin=("push", 0.45, {"dir": 1})),
        P1.Found(b("found"), b("practice"), tin=("glitch", 0.25, {})),
        P1.Practice(b("practice"), S("practice")["t1"] + 0.4, tin=("zoom", 0.45, {})),
    ]
    try:
        from film import part2 as P2
        shots += P2.shots(b)
    except ImportError:
        pass
    end = max(s.t1 for s in shots)
    return Timeline(shots, [c for c in cards if c.t_in < end], duration=min(total, end))
