"""Render stills at given times (or N evenly spaced per shot) into a contact sheet."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.render import stills
import film.main as M
args = sys.argv[1:]
out = args[0]
if args[1] == "shots":
    tl = M.build()
    per = int(args[2]) if len(args) > 2 else 2
    times = []
    for s in tl.shots:
        for i in range(per):
            times.append(round(s.t0 + (s.t1 - s.t0) * (i + 1) / (per + 1), 2))
    times = [t for t in times if len(args) < 5 or float(args[3]) <= t <= float(args[4])]
else:
    times = [float(x) for x in args[1:]]
t0 = time.time()
print(stills("film.main", times, out, scale=0.5, sheet=6), len(times), "frames", round(time.time() - t0, 1), "s")
