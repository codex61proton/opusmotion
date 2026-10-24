import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.render import render_video

if __name__ == "__main__":
    for name, a, b in [("r_sites_end", 1308, None), ("r_u2", 255, 420), ("r_moon", 810, 885)]:
        render_video("film.main", f"build/render/{name}.mp4", scale=1.0, workers=2, start=a / 30,
                     end=None if b is None else b / 30, crf=14)
        print("DONE", name, flush=True)
