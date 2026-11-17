"""'Interstellar - The Black Hole Was Realistic?' 40 s documentary Short (1080x1920).

Every black-hole shot is an original general-relativity simulation (raytrace.py + shade.py);
no film footage or stills are used.  Diagrams are drawn here from the same equations.
usage: python3 render.py timing.json mix.wav out.mp4 [--stills]
"""
import json, math, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import shade as S

W, H, FPS, DUR = 1080, 1920, 30, 40.0
TIM = json.load(open(sys.argv[1]))
C = [m["start"] for m in TIM]
MAPS = {n: S.load(n) for n in ("hero", "close", "tilt")}
MONT = "fonts/Montserrat.ttf"
GOLD, WHITE, ICE = (255, 199, 84), (246, 246, 250), (150, 200, 255)
_fc = {}


def font(size, wght=800):
    k = (size, wght)
    if k not in _fc:
        f = ImageFont.truetype(MONT, size)
        f.set_variation_by_axes([wght])
        _fc[k] = f
    return _fc[k]


ease = lambda x: 0.5 - 0.5 * math.cos(math.pi * min(max(x, 0.0), 1.0))
seg = lambda t, a, b: min(max((t - a) / (b - a), 0.0), 1.0)


# ------------------------------------------------------------------ black-hole shots
def bh(name, t, zoom=1.0, cx=0.5, cy=0.5, far_glow=0.0, spin=1.0):
    m = MAPS[name]
    mh, mw = m["shadow"].shape
    vw = int(mw / zoom)
    vh = int(vw * H / W)
    x0 = int(np.clip(cx * mw - vw / 2, 0, mw - vw))
    y0 = int(np.clip(cy * mh - vh / 2, 0, mh - vh))
    sub = {k: v[y0:y0 + vh, x0:x0 + vw] for k, v in m.items()}
    c = S.shade(sub, t * spin, far_glow=far_glow)
    c = 1 - np.exp(-c * 2.0)
    im = Image.fromarray((np.clip(c, 0, 1) ** (1 / 1.15) * 255).astype(np.uint8))
    return im.resize((W, H), Image.LANCZOS).convert("RGBA"), (x0, y0, vw / W)


def to_screen(view, mx, my):
    x0, y0, s = view
    return (mx - x0) / s, (my - y0) / s


# feature points (map pixels) found from the ray-traced data itself
def _arc_top(m):
    far = m["far0"] | m["far1"]
    h, w = far.shape
    col = far[:, w // 2]
    ys = np.where(col)[0]
    return w // 2, int(ys.min()) if len(ys) else h // 3


HERO_ARC = _arc_top(MAPS["hero"])


def _arc_at(m, colfrac):
    far = (m["far0"] & (m["r0"] < 11)) | (m["far1"] & (m["r1"] < 11))   # bright inner part of the lensed arc
    x = int(far.shape[1] * colfrac)
    ys = np.where(far[:, x])[0]
    return x, int(ys.min())


CLOSE_RING = _arc_at(MAPS["close"], 0.62)

# ------------------------------------------------------------------ space backdrop for diagrams
_r = np.random.default_rng(7)
SPACE = Image.new("RGBA", (W, H), (3, 4, 9, 255))
_d = ImageDraw.Draw(SPACE)
for _ in range(700):
    x, y, b = _r.uniform(0, W), _r.uniform(0, H), _r.random() ** 4
    _d.ellipse([x - 1.2, y - 1.2, x + 1.2, y + 1.2], fill=(200, 210, 255, int(60 + 190 * b)))


def glow_layer(im, lay, r=10, n=1):
    g = lay.filter(ImageFilter.GaussianBlur(r))
    for _ in range(n):
        im.alpha_composite(g)
    im.alpha_composite(lay)


def geodesic(b, r0=60.0, dphi=0.004, maxphi=3 * math.pi):
    """Photon path (x, y) in the hole's plane, arriving from x = -r0 (G = c = M = 1)."""
    u, w, phi, pts = 1 / r0, math.sqrt(max(1 / b ** 2 - (1 / r0) ** 2 * (1 - 2 / r0), 0)), 0.0, []
    while phi < maxphi:
        r = 1 / u
        pts.append((-r * math.cos(phi), r * math.sin(phi)))
        a = -u + 3 * u * u
        w += a * dphi
        u += w * dphi
        phi += dphi
        if u >= 0.5:
            return pts, True
        if u <= 1 / (r0 * 1.2):
            return pts, False
    return pts, False


RAYS = [(b, *geodesic(b)) for b in np.linspace(-15, 15, 25) if abs(b) > 0.2]


def diagram_rays(t, t0):
    im = SPACE.copy()
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    sc, ox, oy = 21, W / 2, 840
    p = ease(seg(t, t0, t0 + 1.4))
    for b, pts, cap in RAYS:
        sign = 1 if b > 0 else -1
        pts = [(x, y * sign) for x, y in pts]
        n = max(2, int(len(pts) * p))
        xy = [(ox + x * sc, oy - y * sc) for x, y in pts[:n] if abs(x * sc) < 900]
        if len(xy) > 1:
            d.line(xy, fill=(255, 120, 60, 200) if cap else (255, 214, 140, 230), width=3)
    d.ellipse([ox - 3 * sc, oy - 3 * sc, ox + 3 * sc, oy + 3 * sc], outline=(150, 200, 255, 120), width=2)
    glow_layer(im, lay, 8, 1)
    d = ImageDraw.Draw(im)
    d.ellipse([ox - 2 * sc, oy - 2 * sc, ox + 2 * sc, oy + 2 * sc], fill=(0, 0, 0, 255))
    q = ease(seg(t, t0 + 0.3, t0 + 0.8))
    d.text((W / 2, 360), "LIGHT BENDS", font=font(96), fill=WHITE + (int(255 * q),), anchor="mm")
    d.text((W / 2, 470), "AROUND MASS", font=font(96), fill=GOLD + (int(255 * q),), anchor="mm")
    d.text((W / 2, 1185), "u'' + u = 3GMu²/c²", font=font(40, 500), fill=(190, 205, 235, int(200 * q)), anchor="mm")
    d.text((W / 2, 1232), "photon paths around a black hole · general relativity", font=font(28, 500),
           fill=(150, 165, 200, int(180 * q)), anchor="mm")
    return im


def diagram_spacetime(t, t0):
    im = SPACE.copy()
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rot = (t - t0) * 0.25
    deep = ease(seg(t, t0, t0 + 1.5))
    cam_h, cam_d, f = 7.0, 16.0, 900

    cam = np.array([0.0, -20.0, 11.0])
    fw = np.array([0.0, 0.0, -2.5]) - cam
    fw /= np.linalg.norm(fw)
    rt = np.cross(fw, [0, 0, 1.0]); rt /= np.linalg.norm(rt)
    upv = np.cross(rt, fw)

    def proj(x, y):
        r = math.hypot(x, y)
        z = -deep * 7 / math.sqrt(r * r + 0.6)
        xr, yr = x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)
        v = np.array([xr, yr, z]) - cam
        dz = max(v @ fw, 0.5)
        return W / 2 + 1100 * (v @ rt) / dz, 900 - 1100 * (v @ upv) / dz

    rng_ = np.linspace(-11, 11, 23)
    for a in rng_:
        d.line([proj(a, b) for b in np.linspace(-11, 11, 120)], fill=(110, 170, 255, 150), width=2)
        d.line([proj(b, a) for b in np.linspace(-11, 11, 120)], fill=(110, 170, 255, 150), width=2)
    glow_layer(im, lay, 6, 1)
    cxp, cyp = proj(0, 0)
    ImageDraw.Draw(im).ellipse([cxp - 34, cyp - 34, cxp + 34, cyp + 34], fill=(0, 0, 0, 255))
    q = ease(seg(t, t0 + 0.2, t0 + 0.7))
    d = ImageDraw.Draw(im)
    d.text((W / 2, 340), "MASS CURVES", font=font(96), fill=WHITE + (int(255 * q),), anchor="mm")
    d.text((W / 2, 450), "SPACETIME", font=font(110), fill=GOLD + (int(255 * q),), anchor="mm")
    return im


# side view: light from the far side of the disk is bent over the hole to the viewer
SIDE_B = 7.0
SIDE = geodesic(SIDE_B, r0=19.0, maxphi=math.pi)[0]


def diagram_side(t, t0):
    im = SPACE.copy()
    d = ImageDraw.Draw(im)
    sc, ox, oy = 26, 440, 880
    # disk edge-on, far side (left, behind the hole) highlighted
    d.line([ox - 13 * sc, oy, ox - 6 * sc, oy], fill=GOLD, width=10)
    d.line([ox + 6 * sc, oy, ox + 13 * sc, oy], fill=(255, 150, 70), width=10)
    eye = (ox + 19 * sc, oy)
    d.ellipse([eye[0] - 30, oy - 18, eye[0] + 30, oy + 18], outline=WHITE, width=4)
    d.ellipse([eye[0] - 10, oy - 10, eye[0] + 10, oy + 10], fill=WHITE)
    # the straight line from the far side to the eye is blocked by the hole
    p = ease(seg(t, t0 + 0.2, t0 + 0.9))
    if p > 0:
        x1 = ox - 10 * sc + (8 * sc) * p
        d.line([ox - 10 * sc, oy - 4, x1, oy - 4], fill=(255, 90, 80), width=4)
    if t > t0 + 0.9:
        d.text((ox, oy + 120), "BLOCKED", font=font(40), fill=(255, 110, 100), anchor="mm")
    # the real, bent path (computed): mirror so it starts at the camera on the right
    pts = [(ox - x * sc, oy - y * sc) for x, y in SIDE][::-1]   # mirrored: viewer on the right
    q = ease(seg(t, t0 + 0.8, t0 + 1.9))
    n = max(2, int(len(pts) * q))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    seg_pts = pts[:n]
    if len(seg_pts) > 1:
        ld.line(seg_pts, fill=GOLD + (255,), width=6)
        hx, hy = seg_pts[-1]
        ld.ellipse([hx - 12, hy - 12, hx + 12, hy + 12], fill=(255, 240, 200, 255))
    glow_layer(im, lay, 10, 2)
    d = ImageDraw.Draw(im)
    d.ellipse([ox - 2 * sc, oy - 2 * sc, ox + 2 * sc, oy + 2 * sc], fill=(0, 0, 0, 255), outline=(90, 110, 150), width=2)
    d.text((ox - 10 * sc, oy + 60), "FAR SIDE", font=font(36), fill=GOLD, anchor="mm")
    d.text((eye[0], oy + 60), "YOU", font=font(36), fill=WHITE, anchor="mm")
    a = ease(seg(t, t0 + 0.1, t0 + 0.6))
    d.text((W / 2, 330), "LIGHT FROM BEHIND", font=font(84), fill=WHITE + (int(255 * a),), anchor="mm")
    d.text((W / 2, 430), "BENDS AROUND IT", font=font(84), fill=GOLD + (int(255 * a),), anchor="mm")
    return im


# ------------------------------------------------------------------ text helpers
def title(im, lines, t, t0, y=360, size=88, gap=105):
    d = ImageDraw.Draw(im)
    for i, (s, col) in enumerate(lines):
        a = ease(seg(t, t0 + 0.12 * i, t0 + 0.12 * i + 0.45))
        if a <= 0:
            continue
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((W / 2, y + i * gap + 18 * (1 - a)), s, font=font(size), fill=(0, 0, 0, int(150 * a)), anchor="mm")
        im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(10)))
        d.text((W / 2, y + i * gap + 18 * (1 - a)), s, font=font(size), fill=col + (int(255 * a),), anchor="mm")


def lower_third(im, t, t0, big, small):
    a = ease(seg(t, t0, t0 + 0.5))
    d = ImageDraw.Draw(im)
    x = 90
    d.rectangle([x, 1030, x + 8, 1150], fill=GOLD + (int(255 * a),))
    d.text((x + 34 - 30 * (1 - a), 1065), big, font=font(64), fill=WHITE + (int(255 * a),), anchor="lm")
    d.text((x + 34 - 30 * (1 - a), 1125), small, font=font(36, 500), fill=(220, 220, 230, int(230 * a)), anchor="lm")


def callout(im, t, t0, tx, ty, label, lx, ly, col=GOLD):
    a = ease(seg(t, t0, t0 + 0.4))
    if a <= 0:
        return
    d = ImageDraw.Draw(im)
    ex, ey = lx + (tx - lx) * a, ly + (ty - ly) * a
    d.line([lx, ly, ex, ey], fill=col + (230,), width=4)
    d.ellipse([tx - 16, ty - 16, tx + 16, ty + 16], outline=col + (int(255 * a),), width=4)
    d.text((lx, ly - 36), label, font=font(52), fill=col + (int(255 * a),), anchor="mm", stroke_width=2,
           stroke_fill=(0, 0, 0))


def sim_tag(im):
    ImageDraw.Draw(im).text((W - 60, 120), "ORIGINAL GR SIMULATION", font=font(26, 600), fill=(220, 220, 235, 120), anchor="rm")


# ------------------------------------------------------------------ subtitles (synced per clause, words by syllables)
KEY = {"REALISTIC", "BLACK", "HOLES", "HOLE", "INTERSTELLAR,", "INTERSTELLAR", "SCIENTIFICALLY", "ACCURATE.", "LIGHT",
       "BEND", "BENDS", "SPINNING", "GARGANTUA.", "RING", "GRAVITATIONAL", "LENSING.", "ACCRETION", "DISK",
       "SCIENTIFIC", "STUDIES.", "VISUALIZE", "SCIENTISTS"}


def syl(w):
    w = w.lower().strip(".,:'?")
    v = sum(1 for i, ch in enumerate(w) if ch in "aeiouy" and (i == 0 or w[i - 1] not in "aeiouy"))
    return max(1, v - (1 if w.endswith("e") and v > 1 else 0))


def build_caps():
    caps = []
    for m in TIM:
        words = m["text"].replace("...", "…").split()
        groups, g = [], []
        for wd in words:
            g.append(wd)
            if len(" ".join(g)) >= 14 or wd.endswith((",", ".", ":", "…")):
                groups.append(g)
                g = []
        if g:
            groups.append(g)
        tot = sum(sum(syl(x) for x in gr) + 0.6 for gr in groups)
        t = m["start"]
        for gr in groups:
            dt = (m["end"] - m["start"]) * (sum(syl(x) for x in gr) + 0.6) / tot
            caps.append((t, t + dt, gr))
            t += dt
    return caps


CAPS = build_caps()


def subtitle(im, t):
    for a, b, words in CAPS:
        if a - 0.02 <= t < b + 0.12:
            d = ImageDraw.Draw(im)
            pop = 1 + 0.08 * (1 - ease(seg(t, a, a + 0.1)))
            f = font(int(74 * pop))
            ups = [w.upper() for w in words]
            ws = [d.textlength(u + " ", font=f) for u in ups]
            if sum(ws) > 860:
                f = font(int(74 * pop * 860 / sum(ws)))
                ws = [d.textlength(u + " ", font=f) for u in ups]
            x = W / 2 - (sum(ws) - d.textlength(" ", font=f)) / 2
            for u, wdt in zip(ups, ws):
                col = GOLD if u in KEY else WHITE
                d.text((x, 1330), u, font=f, fill=col, anchor="lm", stroke_width=7, stroke_fill=(0, 0, 0))
                x += wdt
            return


# ------------------------------------------------------------------ shot list
def hook_text(im, t):
    title(im, [("THIS BLACK HOLE WAS", WHITE), ("SCIENTIFICALLY", GOLD), ("ACCURATE.", GOLD)], t, 0.05, y=330, size=70, gap=86)


def s_hero_in(t):
    im, _ = bh("hero", t, zoom=1.0 + 0.22 * ease(seg(t, 0, 2.3)), cy=0.52)
    hook_text(im, t)
    sim_tag(im)
    return im


def s_close_hook(t):
    im, _ = bh("close", t, zoom=1.05 + 0.08 * seg(t, 2.1, 4.2), cx=0.5 - 0.03 * seg(t, 2.1, 4.2))
    hook_text(im, t + 10)
    sim_tag(im)
    return im


def s_tilt_intro(t):
    im, _ = bh("tilt", t, zoom=1.0 + 0.08 * seg(t, C[1], C[1] + 2.6), cy=0.5)
    lower_third(im, t, C[1] + 0.1, "INTERSTELLAR (2014)", "Directed by Christopher Nolan")
    sim_tag(im)
    return im


def s_letterbox(t):
    im, _ = bh("hero", t, zoom=1.0, cx=0.5 + 0.03 * seg(t, 6.6, 9.2), cy=0.5)
    d = ImageDraw.Draw(im)
    bar = int((H - W / 2.39 * 1.9) / 2 * ease(seg(t, 6.6, 7.1)))
    d.rectangle([0, 0, W, bar], fill=(0, 0, 0, 255))
    d.rectangle([0, H - bar, W, H], fill=(0, 0, 0, 255))
    a = ease(seg(t, 6.9, 7.4))
    d.text((W / 2, bar - 90), "VISUALLY IMPRESSIVE…", font=font(64), fill=WHITE + (int(255 * a),), anchor="mm")
    return im


def s_close_accurate(t):
    im, _ = bh("close", t, zoom=1.0 + 0.15 * ease(seg(t, 9.2, 10.7)))
    title(im, [("…BUT SCIENTIFICALLY", WHITE), ("ACCURATE", GOLD)], t, 9.25, y=360, size=84, gap=104)
    sim_tag(im)
    return im


def s_spin(t):
    im, _ = bh("tilt", t, zoom=1.12, spin=3.0)
    title(im, [("MASSIVE.", WHITE), ("SPINNING.", GOLD)], t, 14.9, y=360, size=96, gap=115)
    sim_tag(im)
    return im


def s_garg(t):
    im, _ = bh("hero", t, zoom=1.0 + 0.06 * seg(t, 16.6, 18.2))
    title(im, [("GARGANTUA", WHITE)], t, C[5] + 0.3, y=360, size=120)
    a = ease(seg(t, C[5] + 0.7, C[5] + 1.1))
    ImageDraw.Draw(im).text((W / 2, 455), "the fictional black hole of Interstellar", font=font(38, 500),
                            fill=(225, 225, 235, int(230 * a)), anchor="mm")
    sim_tag(im)
    return im


def s_ring(t):
    im, view = bh("close", t, zoom=1.1)
    # photon ring: thin bright circle just outside the shadow; point at its upper-left part
    tx, ty = to_screen(view, *CLOSE_RING)
    callout(im, t, 18.6, tx, ty, "GLOWING RING", 330, 330)
    sim_tag(im)
    return im


def s_lensing(t):
    im, view = bh("hero", t, zoom=1.18, cy=0.5)
    tx, ty = to_screen(view, *HERO_ARC)
    callout(im, t, C[7] - 0.1, tx, ty + 14, "GRAVITATIONAL LENSING", W / 2, 470)
    sim_tag(im)
    return im


def s_far(t):
    glow = 0.55 + 0.25 * math.sin((t - 25.4) * 5)
    im, view = bh("hero", t, zoom=1.18, far_glow=glow * ease(seg(t, 25.4, 25.9)))
    tx, ty = to_screen(view, *HERO_ARC)
    title(im, [("THE FAR SIDE OF THE DISK", WHITE), ("NORMALLY HIDDEN", GOLD)], t, 25.5, y=360, size=66, gap=86)
    sim_tag(im)
    return im


def s_far_close(t):
    im, _ = bh("close", t, zoom=1.0 + 0.1 * seg(t, 27.6, 29.1), far_glow=0.6)
    sim_tag(im)
    return im


def s_reveal(t):
    im, _ = bh("tilt", t, zoom=1.0 + 0.5 * ease(seg(t, 29.0, 31.0)))
    sim_tag(im)
    return im


def s_paper(t):
    im, _ = bh("hero", t, zoom=1.25)
    im.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 150)))
    a = ease(seg(t, 31.0, 31.5))
    card = Image.new("RGBA", (860, 560), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, 859, 559], 26, fill=(244, 242, 236, 245))
    d.text((50, 60), "CLASSICAL AND QUANTUM GRAVITY · 2015", font=font(30, 700), fill=(140, 110, 40), anchor="lm")
    for i, s in enumerate(["Gravitational lensing by spinning", "black holes in astrophysics, and", "in the movie Interstellar"]):
        d.text((50, 150 + i * 62), s, font=font(46, 700), fill=(20, 22, 30), anchor="lm")
    d.text((50, 360), "O. James, E. von Tunzelmann,", font=font(32, 500), fill=(70, 72, 80), anchor="lm")
    d.text((50, 405), "P. Franklin, K. S. Thorne", font=font(32, 500), fill=(70, 72, 80), anchor="lm")
    d.line([50, 470, 810, 470], fill=(200, 196, 186), width=2)
    d.text((50, 510), "Peer-reviewed research", font=font(30, 600), fill=(140, 110, 40), anchor="lm")
    card = card.rotate(-2 + 2 * a, Image.BICUBIC, expand=True)
    card.putalpha(card.getchannel("A").point(lambda v: int(v * a)))
    im.alpha_composite(card, (W // 2 - card.width // 2, 520 + int(60 * (1 - a))))
    title(im, [("FROM MOVIE", WHITE), ("TO SCIENCE", GOLD)], t, 31.0, y=300, size=80, gap=96)
    return im


def s_close_drift(t):
    im, _ = bh("close", t, zoom=1.15, cx=0.45 + 0.08 * seg(t, 33.1, 35.2))
    sim_tag(im)
    return im


def s_pullback(t):
    im, _ = bh("hero", t, zoom=1.3 - 0.3 * ease(seg(t, 35.1, 39.6)))
    title(im, [("CINEMA", WHITE), ("MEETS SCIENCE.", GOLD)], t, 37.7, y=380, size=110, gap=125)
    return im


SHOTS = [
    (0.0, s_hero_in), (2.15, s_close_hook), (C[1] - 0.05, s_tilt_intro), (6.6, s_letterbox),
    (C[3], s_close_accurate), (C[4], lambda t: diagram_spacetime(t, C[4])), (12.9, lambda t: diagram_rays(t, 12.9)),
    (14.9, s_spin), (C[5], s_garg), (18.2, s_ring), (20.2, s_lensing), (C[8], lambda t: diagram_side(t, C[8])),
    (25.4, s_far), (27.6, s_far_close), (C[10], s_reveal), (C[11] + 0.1, s_paper), (33.1, s_close_drift),
    (C[12], s_pullback),
]
XF = 0.28  # crossfade length


def raw(t):
    i = max(k for k, (s, _) in enumerate(SHOTS) if s <= t)
    im = SHOTS[i][1](t)
    if i + 1 < len(SHOTS) and t > SHOTS[i + 1][0] - XF:
        w = (t - (SHOTS[i + 1][0] - XF)) / XF
        im = Image.blend(im, SHOTS[i + 1][1](t), w)
    return im


_g = np.random.default_rng(3)
GRAIN = [(_g.normal(0, 1, (H // 2, W // 2)).astype(np.float32)) for _ in range(6)]
yy, xx = np.mgrid[0:H, 0:W]
VIGN = (1 - 0.55 * np.clip(((xx - W / 2) / (W * 0.8)) ** 2 + ((yy - H / 2) / (H * 0.66)) ** 2, 0, 1))[..., None].astype(np.float32)


def frame(n):
    t = n / FPS
    im = raw(t)
    # bloom on bright parts
    small = im.convert("RGB").resize((W // 4, H // 4), Image.BILINEAR)
    b = np.asarray(small, np.float32)
    b = np.clip(b - 150, 0, None) * 1.6
    bl = Image.fromarray(np.clip(b, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(14)).resize((W, H), Image.BILINEAR)
    subtitle(im, t)
    a = np.asarray(im.convert("RGB"), np.float32) + np.asarray(bl, np.float32) * 0.55
    a *= VIGN
    a += GRAIN[n % 6].repeat(2, 0).repeat(2, 1)[..., None] * 5
    if C[10] - 0.05 <= t < C[10] + 0.12:  # white flash on the reveal
        a += 255 * (1 - (t - C[10] + 0.05) / 0.17)
    a *= min(1, t / 0.15) * min(1, (DUR - t) / 0.45)
    return np.clip(a, 0, 255).astype(np.uint8).tobytes()


if __name__ == "__main__":
    if "--stills" in sys.argv:
        for ts in [float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")]:
            Image.frombytes("RGB", (W, H), frame(int(ts * FPS))).save(f"still_{ts:05.1f}.png")
        sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", sys.argv[2], "-c:v", "libx264", "-preset", "slow",
                           "-crf", "19", "-maxrate", "16M", "-bufsize", "32M", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", sys.argv[3]],
                          stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for buf in pool.imap(frame, range(int(DUR * FPS)), chunksize=4):
            ff.stdin.write(buf)
    ff.stdin.close()
    ff.wait()
