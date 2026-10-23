"""GPU (Mesa llvmpipe via EGL) post-processing: lens, bloom/halation, grade, grain, glitch."""
import numpy as np
import moderngl

VS = """#version 330
in vec2 p; out vec2 uv;
void main(){ uv = p*0.5+0.5; gl_Position = vec4(p,0.0,1.0); }"""

FS = """#version 330
uniform sampler2D scene;
uniform sampler2D grain;
uniform vec2 res;
uniform float t, grainAmt, vig, ca, bloom, bthresh, distort, flash, fade, glitch, scan, sat, contrast, seed, hal, lift, gofs;
uniform vec3 halCol, tint;
uniform float tintAmt;
in vec2 uv; out vec4 o;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453123); }
void main(){
  vec2 p = uv;
  vec2 cc = p - 0.5; cc.x *= res.x/res.y;
  float r2 = dot(cc,cc);
  p = 0.5 + (p-0.5)*(1.0 + distort*r2);
  float fr = floor(t*24.0);
  if (glitch > 0.0) {
    float band = floor(p.y*36.0 + hash(vec2(fr, 3.0))*36.0);
    float h = hash(vec2(band, fr + seed));
    if (h > 1.0 - glitch*0.55) p.x += (hash(vec2(band, fr + 7.0)) - 0.5) * 0.16 * glitch;
    float band2 = floor(p.y*7.0 + fr);
    if (hash(vec2(band2, fr*1.3)) > 1.0 - glitch*0.25) p.x += 0.02*glitch;
  }
  vec2 dir = p - 0.5;
  float cak = (ca + glitch*14.0) / res.x;
  vec3 col;
  col.r = texture(scene, p + dir*cak*2.0).r;
  col.g = texture(scene, p).g;
  col.b = texture(scene, p - dir*cak*2.0).b;
  vec3 b = textureLod(scene,p,2.5).rgb*0.25 + textureLod(scene,p,4.0).rgb*0.35 + textureLod(scene,p,5.5).rgb*0.4;
  vec3 bb = max(b - bthresh, 0.0) / max(1.0 - bthresh, 0.05);
  col += bb * bloom;
  col += halCol * dot(bb, vec3(0.3333)) * hal;
  float l = dot(col, vec3(0.2126,0.7152,0.0722));
  col = mix(vec3(l), col, sat);
  col = (col - 0.5)*contrast + 0.5 + lift;
  col = mix(col, col*tint, tintAmt);
  if (scan > 0.0) {
    float s = 0.5 + 0.5*cos(uv.y*res.y*3.14159265*0.5);
    col *= 1.0 - scan*0.35*s;
    col += scan*0.03*hash(vec2(fr, floor(uv.y*res.y*0.25)));
  }
  vec2 vv = uv - 0.5; vv.x *= res.x/res.y;
  float vg = smoothstep(1.05, 0.25, length(vv)*1.35);
  col *= mix(1.0, vg, vig);
  vec2 go = vec2(hash(vec2(fr, 1.0+gofs)), hash(vec2(fr, 2.0+gofs)));
  float g = texture(grain, uv*res/2048.0 + go).r - 0.5;
  float lw = clamp(l, 0.0, 1.0);
  col += g * grainAmt * (0.55 + 1.6*lw*(1.0-lw));
  col = mix(col, vec3(1.0), flash);
  col *= 1.0 - fade;
  col += (hash(uv*res + fract(t)*91.0) - 0.5) / 255.0;
  o = vec4(clamp(col, 0.0, 1.0), 1.0);
}"""

DEFAULT = dict(grainAmt=0.07, vig=0.5, ca=1.0, bloom=0.0, bthresh=0.75, distort=0.0, flash=0.0,
               fade=0.0, glitch=0.0, scan=0.0, sat=1.0, contrast=1.0, seed=0.0, hal=0.0, lift=0.0,
               halCol=(1.0, 0.45, 0.25), tint=(1.0, 1.0, 1.0), tintAmt=0.0, gofs=0.0)


def _grain_tex(n=2048, seed=11):
    from scipy.ndimage import gaussian_filter, zoom
    r = np.random.default_rng(seed)
    fine = gaussian_filter(r.standard_normal((n, n)).astype(np.float32), 0.65, mode="wrap")
    clump = zoom(r.standard_normal((n // 4, n // 4)).astype(np.float32), 4, order=1, mode="grid-wrap")[:n, :n]
    g = fine * 0.75 + gaussian_filter(clump, 0.8, mode="wrap") * 0.45
    g = g / (g.std() * 6) + 0.5
    return (np.clip(g, 0, 1) * 255).astype(np.uint8)


class Post:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.ctx = moderngl.create_context(standalone=True, backend="egl")
        self.prog = self.ctx.program(vertex_shader=VS, fragment_shader=FS)
        vbo = self.ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4").tobytes())
        self.vao = self.ctx.vertex_array(self.prog, [(vbo, "2f", "p")])
        self.scene = self.ctx.texture((w, h), 4)
        self.scene.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        self.scene.repeat_x = self.scene.repeat_y = False
        g = _grain_tex()
        self.grain = self.ctx.texture((g.shape[1], g.shape[0]), 1, g.tobytes())
        self.grain.repeat_x = self.grain.repeat_y = True
        self.grain.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.fbo = self.ctx.simple_framebuffer((w, h), 4)
        self.prog["scene"].value = 0
        self.prog["grain"].value = 1
        self.prog["res"].value = (float(w), float(h))

    def run(self, rgba, t, params):
        self.scene.write(rgba.tobytes() if isinstance(rgba, np.ndarray) else rgba)
        self.scene.build_mipmaps()
        self.scene.use(0)
        self.grain.use(1)
        q = dict(DEFAULT)
        q.update(params or {})
        self.prog["t"].value = float(t)
        for k, v in q.items():
            if k in self.prog:
                self.prog[k].value = tuple(float(x) for x in v) if isinstance(v, (tuple, list)) else float(v)
        self.fbo.use()
        self.vao.render(moderngl.TRIANGLE_STRIP)
        return self.fbo.read(components=3)
