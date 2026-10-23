import sys, time, numpy as np, skia
sys.path.insert(0, '.')
from engine import planet as PL
from engine.gfx import bg_night, draw_image
t=time.time(); alb, hgt = PL.moon_photo_maps(); print('maps', time.time()-t)
em = PL.earth_lights(); ea = PL.earth_maps("night")
surf = skia.Surface(1080, 1920); c = surf.getCanvas(); c.clear(skia.ColorBLACK)
for i,(L,b) in enumerate([((-0.3,0.1,1.0),0.0),((-1.0,0.15,0.25),2.5),((-0.95,0.2,-0.15),3.0)]):
    t=time.time()
    img = PL.render(720, "moonp", alb, "moonp_h", hgt, lon0=0, lat0=0, light=L, margin=1.02, bump=b, amb=0.0, lunar=1.0, terminator=0.03, rim_dark=0.0)
    print('render', time.time()-t)
    c.drawImageRect(img, skia.Rect.MakeXYWH([0,360,0][i], [0,0,560][i]+ (0 if i<2 else 0), 720 if i==0 else 720, 720), skia.SamplingOptions(skia.FilterMode.kLinear))
img = PL.render(900, "earthn", ea, light=(1.0,0.3,0.4), lon0=60, lat0=35, margin=1.1, amb=0.02, atm=0.8, atm_w=0.05, emit_key="lights", emit=em, emit_amt=1.4, spec=0.2)
c.drawImage(img, 90, 1020)
surf.makeImageSnapshot().save('scratch/moon_test.jpg', skia.kJPEG)
