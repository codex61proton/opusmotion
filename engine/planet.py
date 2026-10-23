"""GLSL sphere renderer (Earth / Moon) with normal-mapped relief, terminator, atmosphere."""
import math
import os

import numpy as np
import skia

from .gfx import CACHE, hexrgb

_CTX = None


def ctx():
    global _CTX
    if _CTX is None:
        import moderngl
        _CTX = moderngl.create_context(standalone=True, backend="egl")
    return _CTX


VS = """#version 330
in vec2 p; out vec2 q;
void main(){ q = p; gl_Position = vec4(p,0.0,1.0); }"""

FS = """#version 330
uniform sampler2D albedo;
uniform sampler2D height;
uniform mat3 R;            // view -> planet
uniform vec3 L;            // light dir (view space)
uniform float margin, bump, amb, atm, atmW, spec, grid, gridA, terminator, nightLift, rimDark;
uniform vec3 atmCol, gridCol, nightCol;
uniform vec2 texel;
in vec2 q; out vec4 o;
const float PI = 3.14159265;
vec2 uvOf(vec3 p){ float lat = asin(clamp(p.y,-1.,1.)); float lon = atan(p.x, p.z);
  return vec2((lon + PI)/(2.0*PI), (PI*0.5 - lat)/PI); }
void main(){
  vec2 xy = q * margin;  // xy in planet radii
  float r2 = dot(xy, xy);
  vec4 col = vec4(0.0);
  if (r2 <= 1.0) {
    vec3 n = vec3(xy, sqrt(1.0 - r2));
    vec3 p = R * n;
    vec2 uv = uvOf(p);
    vec3 a = texture(albedo, uv).rgb;
    float lat = asin(clamp(p.y,-1.,1.)); float lon = atan(p.x, p.z);
    vec3 east = vec3(cos(lon), 0.0, -sin(lon));
    vec3 north = vec3(-sin(lat)*sin(lon), cos(lat), -sin(lat)*cos(lon));
    float h0 = texture(height, uv).r;
    float hx = texture(height, uv + vec2(texel.x, 0.0)).r - texture(height, uv - vec2(texel.x, 0.0)).r;
    float hy = texture(height, uv - vec2(0.0, texel.y)).r - texture(height, uv + vec2(0.0, texel.y)).r;
    vec3 pn = normalize(p - bump * (hx / max(cos(lat), 0.08) * east + hy * north));
    vec3 nv = transpose(R) * pn;
    float d = dot(nv, normalize(L));
    float lit = smoothstep(-terminator, terminator, d) * max(d, 0.0) * 0.85 + smoothstep(-terminator, terminator, d) * 0.15;
    vec3 c = a * (amb + lit) + nightCol * nightLift * (1.0 - smoothstep(-0.1, 0.2, d));
    vec3 hv = normalize(normalize(L) + vec3(0.0, 0.0, 1.0));
    c += spec * pow(max(dot(nv, hv), 0.0), 40.0) * (1.0 - texture(albedo, uv).a);
    if (grid > 0.0) {
      float gl = abs(fract(degrees(lat) / grid + 0.5) - 0.5) * grid;
      float gn = abs(fract(degrees(lon) / grid + 0.5) - 0.5) * grid * cos(lat);
      float w = 0.18;
      float g = 1.0 - smoothstep(0.0, w, min(gl, gn));
      c = mix(c, gridCol, g * gridA);
    }
    float rim = pow(1.0 - n.z, 3.0);
    c *= 1.0 - rimDark * rim;
    c += atmCol * atm * rim * smoothstep(-0.3, 0.6, dot(normalize(vec3(xy, 0.0)), normalize(L)) + 0.4);
    float edge = smoothstep(1.0, 0.996, r2);
    col = vec4(c * edge, edge);
  }
  float r = sqrt(r2);
  if (atm > 0.0 && r > 0.98) {
    float g = exp(-(r - 1.0) / atmW) * atm * 0.9;
    vec2 dir = normalize(xy);
    float side = smoothstep(-0.5, 0.8, dot(dir, normalize(L.xy + 1e-4)));
    g *= mix(0.25, 1.0, side) * step(1.0, r);
    col.rgb += atmCol * g;
    col.a = max(col.a, clamp(g, 0.0, 1.0));
  }
  o = col;
}"""

_PROG = {}


def _prog():
    c = ctx()
    if "p" not in _PROG:
        prog = c.program(vertex_shader=VS, fragment_shader=FS)
        vbo = c.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4").tobytes())
        _PROG["p"] = prog
        _PROG["vao"] = c.vertex_array(prog, [(vbo, "2f", "p")])
    return _PROG["p"], _PROG["vao"]


_TEX = {}


def texture(key, arr, components):
    if key in _TEX:
        return _TEX[key]
    import moderngl
    c = ctx()
    t = c.texture((arr.shape[1], arr.shape[0]), components, np.ascontiguousarray(arr).tobytes())
    t.build_mipmaps()
    t.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
    t.repeat_x, t.repeat_y = True, False
    t.anisotropy = 8.0
    _TEX[key] = t
    return t


def rot(lon0, lat0, roll=0.0):
    a, b, r = math.radians(-lat0), math.radians(lon0), math.radians(roll)
    Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    Rz = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def project(lon, lat, lon0, lat0, roll=0.0):
    """Planet (lon,lat) -> view-space unit vector (x right, y up, z toward viewer)."""
    la, lo = math.radians(lat), math.radians(lon)
    p = np.array([math.cos(la) * math.sin(lo), math.sin(la), math.cos(la) * math.cos(lo)])
    return rot(lon0, lat0, roll).T @ p


_FBO = {}


def render(size, albedo_key, albedo, height_key=None, height=None, lon0=0.0, lat0=0.0, roll=0.0,
           light=(-0.6, 0.4, 0.7), margin=1.25, bump=0.0, amb=0.04, atm=0.0, atm_w=0.06,
           atm_col=(0.55, 0.78, 1.0), spec=0.0, grid=0.0, grid_a=0.0, grid_col=(0.5, 0.6, 0.7),
           terminator=0.08, night_col=(0.0, 0.0, 0.0), night_lift=0.0, rim_dark=0.25):
    """Render sphere to a premultiplied RGBA skia.Image of size x size.
    The planet radius in the image is size / (2*margin)."""
    import moderngl
    c = ctx()
    prog, vao = _prog()
    size = int(size)
    if size not in _FBO:
        tex = c.texture((size, size), 4)
        _FBO[size] = c.framebuffer(color_attachments=[tex])
    fbo = _FBO[size]
    ta = texture(albedo_key, albedo, albedo.shape[2])
    if height is None:
        height_key, height = "flat", np.zeros((8, 16), np.uint8)
    th = texture(height_key, height, 1)
    ta.use(0)
    th.use(1)
    prog["albedo"].value = 0
    prog["height"].value = 1
    R = rot(lon0, lat0, roll)
    prog["R"].write(R.T.astype("f4").tobytes())  # GLSL is column-major
    L = np.array(light, float)
    prog["L"].value = tuple((L / np.linalg.norm(L)).tolist())
    vals = dict(margin=margin, bump=bump, amb=amb, atm=atm, atmW=atm_w, spec=spec, grid=grid, gridA=grid_a,
                terminator=terminator, nightLift=night_lift, rimDark=rim_dark)
    for k, v in vals.items():
        if k in prog:
            prog[k].value = float(v)
    for k, v in dict(atmCol=atm_col, gridCol=grid_col, nightCol=night_col).items():
        if k in prog:
            prog[k].value = tuple(float(x) for x in v)
    if "texel" in prog:
        prog["texel"].value = (1.0 / height.shape[1], 1.0 / height.shape[0])
    fbo.use()
    c.viewport = (0, 0, size, size)
    fbo.clear(0, 0, 0, 0)
    vao.render(moderngl.TRIANGLE_STRIP)
    data = np.frombuffer(fbo.read(components=4, alignment=1), np.uint8).reshape(size, size, 4)
    data = np.ascontiguousarray(data[::-1])  # GL rows bottom-up -> image rows top-down
    return skia.Image.fromarray(data, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)


# --- procedural / data textures ---------------------------------------------------------
def moon_maps(w=4096, h=2048, seed=42):
    """Procedural lunar albedo (RGBA) + height (R) in equirect projection."""
    pa = os.path.join(CACHE, f"moon_alb_{w}_{seed}.npy")
    ph = os.path.join(CACHE, f"moon_h_{w}_{seed}.npy")
    if os.path.exists(pa) and os.path.exists(ph):
        return np.load(pa), np.load(ph)
    from .gfx import _fbm2
    from scipy.ndimage import gaussian_filter
    r = np.random.default_rng(seed)
    lat = (0.5 - (np.arange(h) + 0.5) / h) * math.pi
    coslat = np.cos(lat)[:, None]
    # maria: approximate selenographic positions (lat, lon, radius deg) of the major basins,
    # so the near side reads as the real Moon; edges roughened with noise.
    lon = ((np.arange(w) + 0.5) / w - 0.5) * 2 * math.pi
    LAT, LON = lat[:, None], lon[None, :]
    MARIA = [(33, -16, 17), (28, 17.5, 10.5), (8.5, 31.4, 12.5), (17, 59, 8), (20, -55, 17), (5, -50, 13),
             (35, -45, 10), (-5, -40, 10), (-21, -17, 11), (-8, 51, 12), (-15, 35, 5.5), (-24, -39, 6),
             (56, -20, 5), (58, 5, 5.5), (55, 30, 5), (13, 3.6, 4), (-10, -23, 5), (0, 15, 6), (40, -5, 6),
             (-2, 25, 6), (25, -30, 8), (45, 25, 5)]
    field = np.zeros((h, w), np.float32)
    for la_, lo_, rr in MARIA:
        la0, lo0 = math.radians(la_), math.radians(lo_)
        d = np.arccos(np.clip(np.sin(LAT) * math.sin(la0) + np.cos(LAT) * math.cos(la0) * np.cos(LON - lo0), -1, 1))
        field = np.maximum(field, np.clip(1.25 - d / math.radians(rr), 0, 1))
    m = _fbm2(h, w, seed + 1, scales=(8, 24, 64), weights=(1, .6, .35))
    maria = np.clip((field + m * 0.22 - 0.3) * 3.0, 0, 1)
    maria = gaussian_filter(maria, 2.0)
    hgt = np.zeros((h, w), np.float32)
    # crater field: power-law sizes, fewer small craters inside maria
    n = 3800
    radii = np.clip(0.004 * (r.pareto(1.25, n) + 1), 0.004, 0.14)
    for i in range(n):
        rad = radii[i]
        cy = r.uniform(-0.98, 0.98)
        la = math.asin(cy)
        lo = r.uniform(-math.pi, math.pi)
        y0 = int((0.5 - la / math.pi) * h)
        x0 = int((lo / (2 * math.pi) + 0.5) * w)
        if maria[min(h - 1, max(0, y0)), x0 % w] > 0.5 and rad < 0.03 and r.random() < 0.7:
            continue
        ry = int(rad * 2.6 / math.pi * h) + 2
        rx = int(min(w / 2 - 1, rad * 2.6 / (2 * math.pi) * w / max(math.cos(la), 0.05))) + 2
        ys = np.arange(y0 - ry, y0 + ry + 1)
        ys = ys[(ys >= 0) & (ys < h)]
        if len(ys) == 0:
            continue
        xs = np.arange(x0 - rx, x0 + rx + 1) % w
        LA = lat[ys][:, None]
        LO = lon[xs][None, :]
        d = np.arccos(np.clip(np.sin(LA) * math.sin(la) + np.cos(LA) * math.cos(la) * np.cos(LO - lo), -1, 1)) / rad
        depth = rad * 9.0
        bowl = np.where(d < 1, -depth * np.clip(1 - d ** 2, 0, 1) ** 0.8, 0.0)
        rim = depth * 0.42 * np.exp(-((d - 1.0) / 0.16) ** 2)
        ejecta = depth * 0.12 * np.exp(-np.clip(d - 1, 0, None) * 2.2) * (d > 1)
        if rad > 0.05:  # central peak for large complex craters
            bowl += depth * 0.35 * np.exp(-(d / 0.18) ** 2)
        hgt[np.ix_(ys, xs)] += (bowl + rim + ejecta).astype(np.float32)
    hgt += gaussian_filter(r.standard_normal((h, w)).astype(np.float32), 1.5) * 0.0015 * (1 - maria * 0.7)
    hgt += _fbm2(h, w, seed + 7, scales=(8, 32, 128), weights=(1, .5, .25)) * 0.006
    hgt -= maria * 0.025
    hn = (hgt - hgt.min()) / (hgt.max() - hgt.min() + 1e-6)
    # albedo: highlands bright, maria dark, young craters with bright ray systems (Tycho, Copernicus, Kepler)
    base = 0.66 + _fbm2(h, w, seed + 3, scales=(4, 16, 64, 256), weights=(1, .6, .4, .3)) * 0.035
    alb = base - maria * 0.36 + gaussian_filter((hn - np.median(hn)), 1.0) * 0.5
    ang_noise = r.random(720)
    for la_, lo_, L, k in [(-43.3, -11.2, 0.75, 0.22), (9.6, -20.1, 0.35, 0.16), (8.1, -38, 0.22, 0.12),
                           (-8.9, 61.0, 0.2, 0.08), (21.9, -47.4, 0.15, 0.09)]:
        la0, lo0 = math.radians(la_), math.radians(lo_)
        d = np.arccos(np.clip(np.sin(LAT) * math.sin(la0) + np.cos(LAT) * math.cos(la0) * np.cos(LON - lo0), -1, 1))
        bear = np.arctan2(np.sin(LON - lo0) * np.cos(LAT), math.cos(la0) * np.sin(LAT) - math.sin(la0) * np.cos(LAT) * np.cos(LON - lo0))
        idx = ((bear + math.pi) / (2 * math.pi) * 720).astype(int) % 720
        rays = np.clip((ang_noise[idx] - 0.55) * 2.6, 0, 1)
        halo = np.exp(-d / 0.02)
        alb += (rays * np.exp(-d / L) * (d > 0.012) + halo * 0.8) * k
    alb = np.clip(alb, 0.06, 0.95)
    rgb = np.stack([alb * 0.985, alb * 0.97, alb * 0.94], -1)
    a = np.ones((h, w, 1), np.float32)  # alpha=1 -> no ocean specular
    albedo = (np.clip(np.concatenate([rgb, a], -1), 0, 1) * 255).astype(np.uint8)
    height = (hn * 255).astype(np.uint8)
    np.save(pa, albedo)
    np.save(ph, height)
    return albedo, height


def earth_maps(style="night", w=4096, h=2048):
    """Stylised Earth albedo from Natural Earth land mask. Alpha: 0 = ocean (specular)."""
    from .geo import equirect_mask
    p = os.path.join(CACHE, f"earth_{style}_{w}.npy")
    if os.path.exists(p):
        return np.load(p)
    from scipy.ndimage import gaussian_filter
    from .gfx import _fbm2
    m = equirect_mask("ne_50m_land", w, h).astype(np.float32) / 255.0
    # equirect_mask lon runs -180..180 left->right; shader lon=atan(x,z) also -pi..pi: matches.
    if style == "night":
        ocean, land = np.array(hexrgb("#0C1622")) / 255, np.array(hexrgb("#2B3B4E")) / 255
    elif style == "paper":
        ocean, land = np.array(hexrgb("paper2")) / 255, np.array(hexrgb("ink2")) / 255
    else:
        ocean, land = np.array(hexrgb("#10263A")) / 255, np.array(hexrgb("#C9BFA6")) / 255
    tex = _fbm2(h, w, 5, scales=(4, 16, 64), weights=(1, .5, .25))
    coast = np.clip(gaussian_filter(m, 1.2) * (1 - m) * 6, 0, 1)
    rgb = ocean[None, None] * (1 - m[..., None]) + land[None, None] * m[..., None]
    rgb = rgb * (1 + tex[..., None] * 0.04 * m[..., None])
    rgb += coast[..., None] * (land - ocean)[None, None] * 0.35
    alpha = m
    out = np.concatenate([np.clip(rgb, 0, 1), alpha[..., None]], -1)
    out = (out * 255).astype(np.uint8)
    np.save(p, out)
    return out
