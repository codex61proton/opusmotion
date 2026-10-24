import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.render import Renderer
import film.main as M
tl = M.build()
r = Renderer(tl, 1.0)
r.frame(1.0)
tot = 0
for s in tl.shots:
    ts = [s.t0 + (s.t1 - s.t0) * f for f in (0.3, 0.7)]
    t0 = time.time()
    for t in ts:
        r.frame(t)
    dt = (time.time() - t0) / len(ts)
    tot += dt * (s.t1 - s.t0) * 30
    print(f"{type(s).__name__:12s} {dt*1000:7.0f} ms/frame  ({(s.t1-s.t0):5.1f}s)", flush=True)
print("est single-process total min", round(tot / 60, 1))
