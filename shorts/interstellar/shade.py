"""Shading pass: turns ray-traced maps into images (disk emission, Doppler beaming, starfield)."""
import numpy as np

R_IN, R_OUT = 6.0, 22.0
rng = np.random.default_rng(2014)


def _noise(h, w, octaves, seed, bh=4, bw=16):
    r = np.random.default_rng(seed)
    out = np.zeros((h, w))
    for o in range(octaves):
        gh, gw = bh * 2 ** o, bw * 2 ** o
        g = r.random((gh + 1, gw + 1))
        g[:, -1] = g[:, 0]  # wrap in angle
        yi = np.linspace(0, gh, h)[:, None]
        xi = np.linspace(0, gw, w)[None, :]
        y0, x0 = np.floor(yi).astype(int).clip(0, gh - 1), np.floor(xi).astype(int).clip(0, gw - 1)
        fy, fx = yi - y0, xi - x0
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        v = (g[y0, x0] * (1 - fx) + g[y0, x0 + 1] * fx) * (1 - fy) + (g[y0 + 1, x0] * (1 - fx) + g[y0 + 1, x0 + 1] * fx) * fy
        out += v / 2 ** o
    return out / out.max()


# disk texture in (radius, angle): fine concentric streaks, stretched along the orbit
NR, NA = 600, 2048
_streak = _noise(NR, NA, 5, 3, bh=24, bw=6)      # fine rings broken up along the orbit
_clump = _noise(NR, NA, 5, 8, bh=6, bw=10)       # larger turbulent clumps
DISK_TEX = 0.25 + 0.75 * (0.6 * _streak ** 1.8 + 0.4 * _clump ** 1.4) / 1.0
# starfield (equirectangular), with a faint dusty band
SW, SH = 4096, 2048
STARS = np.zeros((SH, SW, 3), np.float32)
n = 9000
ys, xs = rng.integers(0, SH, n), rng.integers(0, SW, n)
mag = rng.random(n) ** 6
tint = np.stack([np.ones(n), 0.9 + 0.1 * rng.random(n), 0.8 + 0.25 * rng.random(n)], 1)
STARS[ys, xs] = (0.15 + 2.5 * mag)[:, None] * tint
lat = np.linspace(np.pi / 2, -np.pi / 2, SH)[:, None]
lon = np.linspace(-np.pi, np.pi, SW)[None, :]
band = np.exp(-((lat - 0.35 * np.sin(lon + 0.6)) / 0.18) ** 2) * _noise(SH // 4, SW // 4, 5, 21).repeat(4, 0).repeat(4, 1)
STARS += (band * 0.07)[..., None] * np.array([0.9, 0.75, 1.0])


def temp_color(x):
    """x in [0, ~1.6]: deep red -> orange -> warm white -> blue-white (blackbody-like)."""
    pts = np.array([0.0, 0.25, 0.5, 0.8, 1.1, 1.6])
    cols = np.array([[0.05, 0.0, 0.0], [0.6, 0.12, 0.02], [1.0, 0.45, 0.12], [1.0, 0.78, 0.5], [1.0, 0.95, 0.88], [0.8, 0.9, 1.0]])
    return np.stack([np.interp(x, pts, cols[:, i]) for i in range(3)], -1)


def load(name):
    d = np.load(f"maps/{name}.npz")
    return {k: d[k].astype(np.float32) if d[k].dtype == np.float16 else d[k] for k in d.files}


def shade(m, t, far_glow=0.0, beaming=3.4):
    """Render one frame of a map at time t (seconds). far_glow>0 tints the far side of the disk."""
    h, w = m["shadow"].shape
    li = ((np.pi / 2 - m["sky_lat"]) / np.pi * (SH - 1)).astype(int).clip(0, SH - 1)
    lo = ((m["sky_lon"] + np.pi) / (2 * np.pi) * (SW - 1)).astype(int).clip(0, SW - 1)
    col = STARS[li, lo] * (~m["shadow"])[..., None]
    for k in (2, 1, 0):  # back to front
        r, g = m[f"r{k}"], m[f"g{k}"]
        hit = r > 0
        if not hit.any():
            continue
        rr = np.where(hit, r, R_IN)
        omega = 0.78 * (rr / R_IN) ** -1.5                  # Keplerian: inner disk orbits fastest
        ang = (m[f"psi{k}"] - omega * t) / (2 * np.pi) % 1.0
        tex = DISK_TEX[((rr - R_IN) / (R_OUT - R_IN) * (NR - 1)).astype(int).clip(0, NR - 1),
                       (ang * NA).astype(int) % NA]
        x = rr / R_IN
        prof = (x ** -3 * (1 - np.sqrt(1 / x))).clip(0) ** 0.25 / 0.5    # thin-disk temperature profile
        edge = np.clip((R_OUT - rr) / 6, 0, 1)
        tempv = prof * np.clip(g, 0, 3) ** 0.7
        inten = tex * edge * np.clip(g, 0, 3) ** beaming * 0.9 * prof ** 2
        c = temp_color(tempv * 1.05) * inten[..., None]
        if far_glow:
            fg = m[f"far{k}"][..., None] * far_glow
            c = c * (1 - fg) + fg * (c.mean(-1, keepdims=True) * 1.4 + 0.25) * np.array([1.0, 0.82, 0.25])
        a = np.clip(inten * 1.6, 0, 0.97)[..., None] * hit[..., None]
        col = col * (1 - a) + c * hit[..., None]
    return col
