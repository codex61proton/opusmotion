import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.render import render_video

if __name__ == "__main__":
    render_video("film.main", "build/render/r_end.mp4", scale=1.0, workers=2, start=3510 / 30, crf=14)
    print("DONE r_end", flush=True)
