import sys, time, numpy as np, soundfile as sf
sys.path.insert(0,'.')
from engine import sfx as S
t=time.time()
clips=[S.whoosh(), S.swish(), S.sub_boom(), S.hit(), S.riser(2.0), S.radar_ping(), S.pulse_train(), S.static(2), S.tuning(), S.data_chirps(), S.typewriter(), S.teletype(1.5), S.stamp(), S.paper(), S.shutter(), S.clock(2), S.ratchet(), S.clank(), S.engine_rumble(2), S.air_brake(), S.door(), S.glitch(), S.crickets(3), S.flashbulb(), S.space_air(3)]
print('gen', time.time()-t)
out=[]
for c in clips:
    c = S.stereo(c) if c.ndim==1 else c
    out.append(c); out.append(np.zeros((S.secs(0.4),2),np.float32))
y=np.concatenate(out); print(y.shape, np.abs(y).max())
sf.write('scratch/sfx_demo.wav', y/np.abs(y).max()*0.9, S.SR)
