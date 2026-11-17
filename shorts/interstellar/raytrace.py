"""Physically based black-hole renderer (geometry pass).

Light rays are traced through Schwarzschild spacetime (G = c = M = 1) with the exact
photon-orbit equation  u'' + u = 3u^2  (u = 1/r, ' = d/dphi).  Every ray stays in the
plane through the black hole, so one integration per impact parameter b serves all
pixels with that b.  For every pixel we store where its ray crosses a thin accretion
disk (up to three crossings: direct image, image bent over/under the hole, photon ring),
plus the Doppler/gravitational shift there and, for escaping rays, the sky direction.

usage: python3 raytrace.py   -> maps/<name>.npz
"""
import os
import numpy as np

R_IN, R_OUT = 6.0, 22.0          # disk from the innermost stable orbit outward
os.makedirs("maps", exist_ok=True)


def integrate(bs, r0, dphi=0.003, phimax=4 * np.pi):
    """RK4 for u'' = -u + 3u^2 for all b at once. Returns u, w(=u') tables, end phi, captured flag."""
    n = int(phimax / dphi)
    u = np.full(len(bs), 1 / r0)
    w = np.sqrt(np.maximum(1 / bs ** 2 - u ** 2 * (1 - 2 * u), 0))
    U = np.full((len(bs), n), np.nan, np.float32)
    Wt = np.full((len(bs), n), np.nan, np.float32)
    alive = np.ones(len(bs), bool)
    end = np.full(len(bs), phimax)
    capt = np.zeros(len(bs), bool)
    f = lambda u, w: (w, -u + 3 * u * u)
    for i in range(n):
        U[alive, i], Wt[alive, i] = u[alive], w[alive]
        k1 = f(u, w)
        k2 = f(u + dphi / 2 * k1[0], w + dphi / 2 * k1[1])
        k3 = f(u + dphi / 2 * k2[0], w + dphi / 2 * k2[1])
        k4 = f(u + dphi * k3[0], w + dphi * k3[1])
        u = u + dphi / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        w = w + dphi / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        cap = alive & (u >= 0.5)
        esc = alive & (u <= 0)
        end[cap | esc] = (i + 1) * dphi
        capt |= cap
        alive &= ~(cap | esc)
        u = np.where(alive, u, 0.01)
        if not alive.any():
            break
    return U, Wt, end, capt


def render_map(name, elev_deg, r0, hfov_deg, w, h, shift=(0.0, 0.0)):
    e = np.radians(elev_deg)
    c = np.array([0.0, -np.cos(e), np.sin(e)])           # unit vector BH -> camera
    fwd = -c
    up = np.array([0, 0, 1.0]) - fwd[2] * fwd
    up /= np.linalg.norm(up)
    right = np.cross(fwd, up)
    th = np.tan(np.radians(hfov_deg))
    sx = (np.linspace(-1, 1, w)[None, :] + shift[0]) * th
    sy = (np.linspace(1, -1, h)[:, None] * h / w + shift[1]) * th
    d = fwd[None, None] + sx[..., None] * right + sy[..., None] * up
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    cosa = np.clip(d @ fwd, -1, 1)
    sina = np.sqrt(1 - cosa ** 2) + 1e-9
    ehat = (d - cosa[..., None] * fwd) / sina[..., None]   # in-plane direction perpendicular to camera axis
    b = r0 * sina / np.sqrt(1 - 2 / r0)

    bs = np.linspace(1e-3, b.max() * 1.001, 5000)
    U, Wt, end, capt = integrate(bs, r0)
    dphi = 0.003
    bi = np.clip(np.round((b - bs[0]) / (bs[1] - bs[0])).astype(int), 0, len(bs) - 1)
    pend = end[bi]

    A, B = c[2], ehat[..., 2]
    phi1 = np.mod(np.arctan2(-A, B), np.pi)
    out = {}
    for k in range(3):
        pc = phi1 + k * np.pi
        j = np.clip((pc / dphi).astype(int), 0, U.shape[1] - 2)
        fr = pc / dphi - j
        u = U[bi, j] * (1 - fr) + U[bi, j + 1] * fr
        wv = Wt[bi, j] * (1 - fr) + Wt[bi, j + 1] * fr
        r = 1 / np.where(np.isfinite(u) & (u > 0), u, 1e-6)
        hit = (pc < pend) & np.isfinite(u) & (r >= R_IN) & (r <= R_OUT)
        P = r[..., None] * (np.cos(pc)[..., None] * c + np.sin(pc)[..., None] * ehat)
        psi = np.arctan2(P[..., 1], P[..., 0])
        # photon direction at emission (towards the camera) = -dP/dphi
        rp = -wv / np.where(np.abs(u) > 1e-6, u ** 2, 1e-6)
        dP = (rp[..., None] * (np.cos(pc)[..., None] * c + np.sin(pc)[..., None] * ehat)
              + r[..., None] * (-np.sin(pc)[..., None] * c + np.cos(pc)[..., None] * ehat))
        kdir = -dP / (np.linalg.norm(dP, axis=-1, keepdims=True) + 1e-9)
        vhat = np.stack([-np.sin(psi), np.cos(psi), np.zeros_like(psi)], -1)
        v = np.sqrt(1 / np.maximum(r - 2, 1e-3))                # orbital speed seen by a static observer
        gam = 1 / np.sqrt(np.maximum(1 - v ** 2, 1e-3))
        dop = 1 / (gam * (1 - v * np.sum(kdir * vhat, -1)))
        g = dop * np.sqrt(np.maximum(1 - 2 / r, 0)) / np.sqrt(1 - 2 / r0)
        far = np.sum(P * c, -1) < 0                              # point lies behind the hole
        out[f"r{k}"] = np.where(hit, r, 0).astype(np.float16)
        out[f"psi{k}"] = psi.astype(np.float16)
        out[f"g{k}"] = np.where(hit, g, 0).astype(np.float16)
        out[f"far{k}"] = (hit & far)
    # escaping rays: asymptotic sky direction
    pe = np.minimum(pend, 4 * np.pi)
    sky = np.cos(pe)[..., None] * c + np.sin(pe)[..., None] * ehat
    out["sky_lon"] = np.arctan2(sky[..., 1], sky[..., 0]).astype(np.float16)
    out["sky_lat"] = np.arcsin(np.clip(sky[..., 2], -1, 1)).astype(np.float16)
    out["shadow"] = capt[bi]
    np.savez_compressed(f"maps/{name}.npz", **out)
    print(name, "ok")


if __name__ == "__main__":
    render_map("hero", 5.0, 40.0, 23.0, 1404, 2496)
    render_map("close", 3.5, 40.0, 11.0, 1080, 1920, shift=(-0.55, 0.35))
    render_map("tilt", 20.0, 36.0, 36.0, 1080, 1920)
