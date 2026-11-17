"""'Crystal Lake - the story' animated Short (30 s, 1080x1920), Super 8 horror look.

Everything is drawn here: no footage, no franchise mask or costume, no actor likenesses.
Characters appear only as faceless silhouettes.
usage: python3 render.py lines.json mix.wav out.mp4 [--stills]
"""
import json, math, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 30.0
LINES = json.load(open(sys.argv[1]))
L = [m["start"] for m in LINES] + [DUR]
BEBAS, OSW = "fonts/BebasNeue-Regular.ttf", "fonts/Oswald.ttf"
RED, PALE, MIST, WHITE = (200, 28, 30), (214, 226, 220), (150, 175, 175), (240, 240, 236)
_fc = {}


def font(p, s):
    if (p, s) not in _fc:
        f = ImageFont.truetype(p, s)
        if p == OSW:
            f.set_variation_by_axes([600])
        _fc[(p, s)] = f
    return _fc[(p, s)]


ease = lambda x: 1 - (1 - min(max(x, 0.0), 1.0)) ** 3
seg = lambda t, a, b: min(max((t - a) / (b - a), 0.0), 1.0)


def text(im, y, s, f, fill, a=1.0, glow=0):
    if a <= 0:
        return
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((W // 2, y), s, font=f, fill=fill + (int(255 * a),), anchor="mm",
                             stroke_width=4, stroke_fill=(0, 0, 0, int(200 * a)))
    if glow:
        g = lay.filter(ImageFilter.GaussianBlur(glow))
        im.alpha_composite(g)
        im.alpha_composite(g)
    im.alpha_composite(lay)


# ------------------------------------------------------------------ static scenery
R = np.random.default_rng(13)


def sky_grad(top, bot, horizon=1000):
    y = np.clip(np.arange(H) / horizon, 0, 1)[:, None, None]
    g = np.array(top) + (np.array(bot) - np.array(top)) * y ** 1.5
    return np.repeat(g, W, 1)


def treeline(d, base, h0, h1, col, seed, step=34):
    r = np.random.default_rng(seed)
    x = -40
    while x < W + 40:
        th = r.uniform(h0, h1)
        w = r.uniform(50, 90)
        d.polygon([(x - w, base), (x, base - th), (x + w, base)], fill=col)
        x += r.uniform(step * 0.6, step * 1.4)
    d.rectangle([0, base - 4, W, base + 6], fill=col)


def lake_scene():
    g = sky_grad([4, 8, 14], [26, 44, 50])
    yy, xx = np.mgrid[0:H, 0:W]
    moon = np.exp(-(((xx - 830) ** 2 + (yy - 700) ** 2) / 2 / 170 ** 2))[..., None]
    g += moon * np.array([70, 90, 95])
    im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    d.ellipse([780, 650, 880, 750], fill=(232, 238, 228))
    treeline(d, 1010, 120, 300, (10, 18, 20), 1, 40)
    treeline(d, 1030, 60, 170, (5, 10, 12), 2, 30)
    # water
    wy = np.linspace(0, 1, H - 1030)[:, None, None]
    water = np.array([18, 30, 36]) * (1 - wy) + np.array([4, 7, 9]) * wy
    im.paste(Image.fromarray(np.repeat(water, W, 1).astype(np.uint8)), (0, 1030))
    return im


LAKE = lake_scene()


def moon_glint(d, t):
    for k in range(26):
        y = 1050 + k * 22
        w = 60 - k * 1.4 + 16 * math.sin(t * 2 + k * 0.9)
        x = 830 + 14 * math.sin(t * 1.3 + k * 0.5)
        d.line([x - w, y, x + w, y], fill=(200, 215, 205, max(12, 90 - k * 3)), width=2)


MIST_TEX = Image.fromarray((np.random.default_rng(5).random((40, 90)) * 255).astype(np.uint8)).resize(
    (W * 2, 600), Image.BICUBIC).filter(ImageFilter.GaussianBlur(28))
_ma = np.asarray(MIST_TEX, np.float32) * np.sin(np.linspace(0, np.pi, 600))[:, None] * 0.55
MIST_A = Image.fromarray(_ma.astype(np.uint8))


def mist(im, t, y=820, speed=18, a=1.0):
    lay = Image.new("RGBA", MIST_A.size, MIST + (0,))
    lay.putalpha(MIST_A.point(lambda v: int(v * a)))
    x = int(-(t * speed) % W) - W
    im.alpha_composite(lay, (x, y))
    im.alpha_composite(lay, (x + W * 2 - 2, y)) if x + W * 2 < W else None


def rowboat(im, t, cx, cy):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    bob = 6 * math.sin(t * 1.6)
    ang = 3 * math.sin(t * 1.1)
    hull = [(-170, 0), (170, 0), (130, 42), (-130, 42)]
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    pts = [(cx + x * ca - y * sa, cy + bob + x * sa + y * ca) for x, y in hull]
    d.polygon(pts, fill=(58, 44, 34, 255), outline=(150, 160, 150, 255))
    d.line([(cx - 60, cy + bob - 4), (cx + 180, cy + bob - 70)], fill=(70, 54, 40, 255), width=8)  # oar
    for k in range(4):  # ripples
        r = ((t * 60 + k * 70) % 280)
        d.ellipse([cx - r * 1.6, cy + 40 - r * 0.18, cx + r * 1.6, cy + 40 + r * 0.18],
                  outline=(170, 190, 185, int(120 * (1 - r / 280))), width=3)
    im.alpha_composite(lay)


def mother(d, x, base, s=1.0, col=(3, 5, 6, 255)):
    """Faceless silhouette of a woman in a 1950s-style dress, seen from behind."""
    d.ellipse([x - 26 * s, base - 400 * s, x + 26 * s, base - 340 * s], fill=col)
    d.ellipse([x - 34 * s, base - 410 * s, x + 34 * s, base - 360 * s], fill=col)  # hair
    d.polygon([(x - 38 * s, base - 340 * s), (x + 38 * s, base - 340 * s), (x + 30 * s, base - 230 * s),
               (x + 90 * s, base), (x - 90 * s, base), (x - 30 * s, base - 230 * s)], fill=col)


def dock(d):
    d.polygon([(380, 1240), (700, 1240), (900, H), (180, H)], fill=(20, 16, 14))
    for k in range(9):
        y = 1240 + k * 80
        d.line([(380 - k * 25, y), (700 + k * 25, y)], fill=(10, 8, 8), width=4)


def cabin(t, red):
    im = Image.fromarray(np.clip(sky_grad([3, 6, 10], [12, 18, 22]), 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    treeline(d, 1250, 300, 700, (6, 10, 12), 7, 70)
    wall = (24, 18, 15)
    d.rectangle([140, 700, 940, 1400], fill=wall)
    for y in range(700, 1400, 46):
        d.line([140, y, 940, y], fill=(14, 10, 9), width=4)
    d.polygon([(100, 710), (540, 420), (980, 710)], fill=(12, 9, 8))
    flick = 0.8 + 0.2 * math.sin(t * 19) * math.sin(t * 5.3)
    lamp = (int(255 * flick), int((190 - 150 * red) * flick), int((110 - 90 * red) * flick))
    d.rectangle([330, 820, 750, 1180], fill=lamp)
    mother(d, 560 + 40 * math.sin(t * 0.7), 1180, 0.85, (20, 6, 6, 255))
    d.rectangle([330, 820, 750, 1180], outline=(10, 8, 8), width=18)
    d.line([540, 820, 540, 1180], fill=(10, 8, 8), width=12)
    d.line([330, 1000, 750, 1000], fill=(10, 8, 8), width=12)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse([150, 650, 930, 1350], fill=lamp + (int(70 * flick),))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 1400, W, H], fill=(8, 10, 8))
    return im


def road(t, t0):
    im = Image.fromarray(np.clip(sky_grad([2, 4, 6], [8, 12, 14]), 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    treeline(d, 1200, 400, 900, (5, 8, 8), 11, 60)
    d.polygon([(470, 1150), (610, 1150), (1300, H), (-220, H)], fill=(16, 16, 16))
    p = seg(t, t0, t0 + 2.0)
    s = 0.25 + 1.1 * p ** 2
    cy = 1150 + 420 * p ** 2
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for dx in (-90, 90):
        x = W / 2 + dx * s
        ld.polygon([(x, cy), (x - 500 * s, cy + 900), (x + 500 * s, cy + 900)], fill=(255, 240, 200, 60))
        ld.ellipse([x - 34 * s, cy - 22 * s, x + 34 * s, cy + 22 * s], fill=(255, 250, 230, 255))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(18)))
    im.alpha_composite(lay)
    return im


def porch(t):
    im = cabin(t, 0.3)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 1380, W, H], fill=(6, 8, 7))
    for x, s in ((330, 1.25), (760, 1.3)):  # two strangers, backs to us
        c = (0, 0, 0, 255)
        d.ellipse([x - 34 * s, 1560 - 470 * s, x + 34 * s, 1560 - 395 * s], fill=c)
        d.polygon([(x - 70 * s, 1560 - 390 * s), (x + 70 * s, 1560 - 390 * s), (x + 80 * s, 1560 - 120 * s),
                   (x + 60 * s, 1560), (x - 60 * s, 1560), (x - 80 * s, 1560 - 120 * s)], fill=c)
    return im


def police(t):
    im = Image.fromarray(np.clip(sky_grad([3, 5, 8], [10, 14, 16]), 0, 255).astype(np.uint8)).convert("RGBA")
    ph = int(t * 4) % 2
    col = (230, 30, 40) if ph else (40, 80, 255)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse([200 if ph else 500, 900, 700 if ph else 1000, 1500], fill=col + (150,))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(140)))
    d = ImageDraw.Draw(im)
    for k, x in enumerate(range(-30, W + 60, 110)):  # foreground trunks
        w = 26 + (k * 37) % 30
        d.rectangle([x, 0, x + w, H], fill=(3, 4, 4))
    d.rectangle([0, 1450, W, 1520], fill=(220, 190, 40))  # tape
    for x in range(-40, W, 160):
        d.polygon([(x, 1450), (x + 60, 1450), (x + 100, 1520), (x + 40, 1520)], fill=(20, 20, 20))
    return im


def woods(t):
    im = Image.fromarray(np.clip(sky_grad([2, 4, 4], [14, 20, 20]), 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    for layer, (col, n, seed) in enumerate((((16, 22, 22), 14, 3), ((9, 13, 13), 10, 4))):
        r = np.random.default_rng(seed)
        for _ in range(n):
            x, w = r.uniform(0, W), r.uniform(20, 60) * (1 + layer)
            d.rectangle([x, 0, x + w, H], fill=col)
    mist(im, t, 1000, 30, 1.2)
    # a shape moving between the trees: just a darker shadow, no features
    x = -200 + (t - L[5]) * 520
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([x - 70, 900, x + 70, 1500], fill=(0, 0, 0, 230))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(5)
    for _ in range(6):
        x2, w = r.uniform(0, W), r.uniform(70, 130)
        d.rectangle([x2, 0, x2 + w, H], fill=(2, 3, 3))
    return im


def camp_sign(im, t):
    sway = 2.5 * math.sin(t * 1.4)
    s = Image.new("RGBA", (820, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rectangle([0, 0, 819, 299], fill=(70, 46, 28, 255), outline=(36, 22, 14, 255), width=10)
    for y in (75, 150, 225):
        d.line([10, y, 810, y], fill=(52, 34, 20, 255), width=4)
    d.text((410, 100), "CAMP", font=font(BEBAS, 110), fill=(226, 214, 186, 255), anchor="mm")
    d.text((410, 210), "CRYSTAL LAKE", font=font(BEBAS, 130), fill=(226, 214, 186, 255), anchor="mm")
    s = s.rotate(sway, Image.BICUBIC, expand=True)
    dd = ImageDraw.Draw(im)
    dd.rectangle([200, 940, 240, 1500], fill=(30, 20, 12))
    dd.rectangle([840, 940, 880, 1500], fill=(30, 20, 12))
    im.alpha_composite(s, (W // 2 - s.width // 2, 760))


# ------------------------------------------------------------------ captions
def chunks():
    out = []
    for m in LINES:
        gs, g = [], []
        for w in m["text"].split():
            g.append(w)
            if len(" ".join(g)) > 15 or w.endswith((",", ".", "?")):
                gs.append(g)
                g = []
        if g:
            gs.append(g)
        tot = sum(len(" ".join(x)) + 2 for x in gs)
        t = m["start"]
        for g in gs:
            dt = (m["end"] - m["start"]) * (len(" ".join(g)) + 2) / tot
            out.append((t, t + dt, g))
            t += dt
    return out


CAPS = chunks()
KEY = {"JASON,", "JASON", "MOTHER.", "CRYSTAL", "LAKE", "PREQUEL", "DROWNED", "OBSESSION,", "KILLER", "STRANGERS",
       "BODIES", "DANGER", "PEACOCK."}


def caption(im, t):
    for a, b, words in CAPS:
        if a <= t < b:
            d = ImageDraw.Draw(im)
            f = font(OSW, int(88 * (1 + 0.1 * (1 - ease(seg(t, a, a + 0.1))))))
            ws = [d.textlength(w.upper() + " ", font=f) for w in words]
            x = W / 2 - (sum(ws) - d.textlength(" ", font=f)) / 2
            for w, wd in zip(words, ws):
                d.text((x, 1600), w.upper(), font=f, fill=RED if w.upper() in KEY else WHITE, anchor="lm",
                       stroke_width=9, stroke_fill=(0, 0, 0))
                x += wd
            return


# ------------------------------------------------------------------ frame
def scene(t):
    if t < L[1]:
        im = LAKE.copy()
        moon_glint(ImageDraw.Draw(im), t)
        mist(im, t, 820)
        text(im, 420, "BEFORE JASON…", font(BEBAS, 150), PALE, ease(seg(t, 0.2, 0.7)))
        text(im, 570, "THERE WAS HIS MOTHER.", font(BEBAS, 120), RED, ease(seg(t, 1.2, 1.6)), 16)
    elif t < L[2]:
        im = LAKE.copy()
        moon_glint(ImageDraw.Draw(im), t)
        camp_sign(im, t)
        mist(im, t, 1100, 26, 1.3)
        text(im, 330, "A FRIDAY THE 13TH", font(OSW, 64), PALE, ease(seg(t, L[1] + 0.3, L[1] + 0.8)))
        text(im, 420, "PREQUEL SERIES", font(OSW, 64), RED, ease(seg(t, L[1] + 0.5, L[1] + 1.0)))
    elif t < L[2] + 3.0:
        im = LAKE.copy()
        moon_glint(ImageDraw.Draw(im), t)
        rowboat(im, t, 640, 1250)
        mist(im, t, 900)
        text(im, 420, "AN EMPTY BOAT", font(BEBAS, 140), PALE, ease(seg(t, L[2] + 0.3, L[2] + 0.8)))
    elif t < L[3]:
        im = LAKE.copy()
        moon_glint(ImageDraw.Draw(im), t)
        d = ImageDraw.Draw(im)
        dock(d)
        halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse([300, 640, 780, 1360], fill=(150, 175, 170, 90))
        im.alpha_composite(halo.filter(ImageFilter.GaussianBlur(90)))
        d = ImageDraw.Draw(im)
        mother(d, 540, 1300, 1.3)
        mist(im, t, 950, 14, 0.8)
        text(im, 400, "A MOTHER'S", font(BEBAS, 140), PALE, ease(seg(t, L[2] + 3.2, L[2] + 3.6)))
        text(im, 540, "GRIEF", font(BEBAS, 190), RED, ease(seg(t, L[2] + 3.4, L[2] + 3.8)), 16)
    elif t < L[4]:
        red = seg(t, L[3] + 1.0, L[4] - 0.5)
        im = cabin(t, red)
        d = ImageDraw.Draw(im)
        text(im, 360, "GRIEF", font(BEBAS, 150), PALE, ease(seg(t, L[3] + 0.2, L[3] + 0.6)))
        if t > L[3] + 1.4:
            p = ease(seg(t, L[3] + 1.4, L[3] + 1.8))
            d = ImageDraw.Draw(im)
            d.line([370, 360, 370 + 340 * p, 350], fill=RED, width=12)
            text(im, 520, "OBSESSION", font(BEBAS, 190), RED, p, 18)
    elif t < L[4] + 1.8:
        im = road(t, L[4])
        text(im, 380, "TWO STRANGERS", font(BEBAS, 150), PALE, ease(seg(t, L[4] + 0.2, L[4] + 0.6)))
    elif t < L[4] + 3.7:
        im = porch(t)
        text(im, 380, "DIGGING INTO", font(BEBAS, 130), PALE, ease(seg(t, L[4] + 1.9, L[4] + 2.3)))
        text(im, 510, "HER PAST", font(BEBAS, 170), RED, ease(seg(t, L[4] + 2.1, L[4] + 2.5)), 14)
    elif t < L[5]:
        im = police(t)
        text(im, 380, "BODIES START", font(BEBAS, 140), PALE, ease(seg(t, L[4] + 3.8, L[4] + 4.2)))
        text(im, 520, "TURNING UP", font(BEBAS, 170), RED, ease(seg(t, L[4] + 4.0, L[4] + 4.4)), 14)
    elif t < L[6]:
        im = woods(t)
        text(im, 380, "SHE MAY NOT BE", font(BEBAS, 130), PALE, ease(seg(t, L[5] + 0.3, L[5] + 0.7)))
        text(im, 510, "THE ONLY DANGER", font(BEBAS, 150), RED, ease(seg(t, L[5] + 0.6, L[5] + 1.0)), 16)
    else:
        im = LAKE.copy()
        moon_glint(ImageDraw.Draw(im), t)
        mist(im, t, 820, 14, 1.2)
        im.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 90)))
        text(im, 560, "CRYSTAL LAKE", font(BEBAS, 210), PALE, ease(seg(t, L[6] + 0.1, L[6] + 0.6)), 22)
        text(im, 720, "ALL 8 EPISODES", font(OSW, 66), WHITE, ease(seg(t, L[6] + 0.8, L[6] + 1.2)))
        text(im, 810, "NOW STREAMING ON PEACOCK", font(OSW, 54), RED, ease(seg(t, L[6] + 1.0, L[6] + 1.4)))
    return im


CUTS = [L[1], L[2], L[2] + 3.0, L[3], L[4], L[4] + 1.8, L[4] + 3.7, L[5], L[6]]
yy, xx = np.mgrid[0:H, 0:W]
VIGN = (1 - 0.85 * np.clip(((xx - W / 2) / (W * 0.62)) ** 4 + ((yy - H / 2) / (H * 0.56)) ** 4, 0, 1) ** 0.5)[..., None].astype(np.float32)


def frame(n):
    t = n / FPS
    rng = np.random.default_rng(n)
    im = scene(t)
    caption(im, t)
    d = ImageDraw.Draw(im)
    for _ in range(int(rng.integers(0, 4))):  # dust and scratches
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        d.ellipse([x, y, x + rng.uniform(2, 7), y + rng.uniform(2, 7)], fill=(220, 220, 210, 160))
    if rng.random() < 0.15:
        x = rng.uniform(0, W)
        d.line([x, 0, x + rng.uniform(-20, 20), H], fill=(200, 200, 190, 60), width=2)
    a = np.asarray(im.convert("RGB"), np.float32)
    dx, dy = int(rng.integers(-3, 4)), int(rng.integers(-3, 4))  # gate weave
    a = np.roll(a, (dy, dx), (0, 1))
    a *= VIGN * (0.94 + 0.06 * rng.random())  # flicker
    a = a * np.array([1.02, 1.0, 0.95]) + np.array([6, 4, 0])
    a += rng.normal(0, 9, (H // 3, W // 3, 1)).astype(np.float32).repeat(3, 0).repeat(3, 1)
    for c in CUTS:
        if 0 <= t - c < 0.12:
            a *= (t - c) / 0.12
    a *= min(1, t / 0.4) * min(1, (DUR - t) / 0.5)
    return np.clip(a, 0, 255).astype(np.uint8).tobytes()


if __name__ == "__main__":
    if "--stills" in sys.argv:
        for i, ts in enumerate([1.8, 4.5, 8.0, 11.0, 15.8, 18.8, 20.5, 22.8, 25.5, 28.5]):
            Image.frombytes("RGB", (W, H), frame(int(ts * FPS))).save(f"still_{i}.png")
        sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", sys.argv[2], "-c:v", "libx264", "-preset", "slow",
                           "-crf", "21", "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p", "-c:a", "aac",
                           "-b:a", "192k", "-shortest", "-movflags", "+faststart", sys.argv[3]], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for buf in pool.imap(frame, range(int(DUR * FPS)), chunksize=4):
            ff.stdin.write(buf)
    ff.stdin.close()
    ff.wait()
