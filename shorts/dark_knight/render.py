"""'Why The Dark Knight Worked' - noir motion-graphics Short (40 s, 1080x1920).

All visuals are drawn here (no film footage, stills, logos or likenesses).
usage: python3 render.py lines.json mix.wav out.mp4 [--stills]
"""
import json, math, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 40.0
rng = np.random.default_rng(1436)
LINES = json.load(open(sys.argv[1]))
BEBAS = "fonts/BebasNeue-Regular.ttf"
OSW = "fonts/Oswald.ttf"
_fc = {}


def font(path, size):
    k = (path, size)
    if k not in _fc:
        f = ImageFont.truetype(path, size)
        if path == OSW:
            f.set_variation_by_axes([600])
        _fc[k] = f
    return _fc[k]


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def seg(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


RED = (214, 32, 38)
GOLD = (236, 196, 110)
ICE = (178, 205, 230)
WHITE = (240, 242, 246)

# ------------------------------------------------------------ static layers
def skyline(seed, h_min, h_max, color, width=W + 400, windows=True):
    r = np.random.default_rng(seed)
    im = Image.new("RGBA", (width, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 0
    while x < width:
        bw = int(r.integers(60, 170))
        bh = int(r.integers(h_min, h_max))
        top = H - bh
        d.rectangle([x, top, x + bw, H], fill=color)
        if r.random() < 0.3:  # spire / stepped top
            d.rectangle([x + bw // 3, top - bh // 6, x + 2 * bw // 3, top], fill=color)
            d.rectangle([x + bw // 2 - 3, top - bh // 6 - 90, x + bw // 2 + 3, top], fill=color)
        if windows:
            for wy in range(top + 20, H - 40, 34):
                for wx in range(x + 12, x + bw - 16, 26):
                    if r.random() < 0.13:
                        a = int(r.integers(90, 230))
                        d.rectangle([wx, wy, wx + 9, wy + 14], fill=(255, 205, 130, min(255, a + 25)))
        x += bw + int(r.integers(0, 14))
    return im


def sky():
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([4, 6, 12]), np.array([22, 32, 48])
    g = top + (bot - top) * (y ** 1.6)[..., None]
    g = np.repeat(g, W, 1)
    # soft moon-glow behind clouds
    yy, xx = np.mgrid[0:H, 0:W]
    glow = np.exp(-(((xx - 760) / 420) ** 2 + ((yy - 520) / 380) ** 2))
    g += glow[..., None] * np.array([40, 52, 70])
    return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")


SKY = sky()
FAR = skyline(1, 380, 900, (14, 20, 32, 255), windows=False)
MID = skyline(2, 300, 760, (9, 12, 20, 255))
NEAR = skyline(3, 120, 420, (3, 4, 8, 255), width=W + 800)

# fog band
_fog = (np.random.default_rng(5).random((60, 120)) * 255).astype(np.uint8)
FOG = Image.fromarray(_fog).resize((W * 2, 700), Image.BICUBIC).filter(ImageFilter.GaussianBlur(30))

_fa = np.asarray(FOG, np.float32) * 0.35 * np.sin(np.linspace(0, np.pi, 700))[:, None]
FOGA = Image.fromarray(_fa.astype(np.uint8))
yy, xx = np.mgrid[0:H, 0:W]
VIGN = (1 - 0.75 * np.clip(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2, 0, 1))[..., None]

RAIN = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 1.0)) for _ in range(260)]
GRAIN = [rng.normal(0, 9, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(8)]


def city(t, push=0.0):
    im = SKY.copy()
    for layer, sp, dy in ((FAR, 6, 120), (MID, 14, 60), (NEAR, 26, 0)):
        im.alpha_composite(layer, (int(-t * sp - push * sp * 3) % 200 - 200, dy))
    fog = Image.new("RGBA", FOG.size, (120, 140, 165, 0))
    fog.putalpha(FOGA)
    im.alpha_composite(fog, (int(-(t * 20) % W) - W // 2, 1050))
    return im


def rain(d, t, alpha=150):
    for x, y, s in RAIN:
        yy_ = (y + t * 2300 * s) % (H + 200) - 100
        xx_ = (x - t * 260 * s) % W
        d.line([xx_, yy_, xx_ - 14 * s, yy_ + 70 * s], fill=(190, 210, 235, int(alpha * s)), width=2)


def text_c(d, y, s, f, fill, stroke=0, sc=(0, 0, 0), x=None, anchor="mm"):
    d.text((W // 2 if x is None else x, y), s, font=f, fill=fill, anchor=anchor,
           stroke_width=stroke, stroke_fill=sc)


def glow_text(im, y, s, f, fill, radius=18, strength=1.6, x=None):
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((W // 2 if x is None else x, y), s, font=f, fill=fill, anchor="mm")
    g = lay.filter(ImageFilter.GaussianBlur(radius))
    for _ in range(int(strength)):
        im.alpha_composite(g)
    im.alpha_composite(lay)


# ------------------------------------------------------------ scene pieces
def _bez(p0, p1, p2, n=24):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]) for u in np.linspace(0, 1, n)]


def draw_jester(d, cx):
    """Classic playing-card court jester silhouette: three-point bell hat, scalloped ruff, shoulders."""
    ink, bell = (18, 18, 22, 255), (*RED, 255)
    d.ellipse([cx - 135, 455, cx + 135, 700], fill=ink)  # shoulders (clipped by card border later)
    d.rectangle([cx - 135, 560, cx + 135, 600], fill=ink)
    for i in range(9):  # scalloped ruff
        x = cx - 112 + i * 28
        d.ellipse([x - 26, 428, x + 26, 482], fill=ink, outline=(236, 232, 222, 255), width=3)
    d.ellipse([cx - 50, 300, cx + 50, 425], fill=ink)  # head
    # three curved hat points, each a tapered curve ending in a bell
    tips = []
    for (base_l, base_r, ctrl, tip) in (((cx - 55, 318), (cx - 5, 300), (cx - 120, 230), (cx - 150, 300)),
                                        ((cx + 5, 300), (cx + 55, 318), (cx + 120, 230), (cx + 150, 300)),
                                        ((cx - 30, 305), (cx + 30, 305), (cx - 10, 150), (cx + 70, 135))):
        outer = _bez(base_l, (ctrl[0] - 12, ctrl[1] - 14), tip)
        inner = _bez(tip, (ctrl[0] + 14, ctrl[1] + 22), base_r)
        d.polygon(outer + inner, fill=ink)
        tips.append(tip)
    d.chord([cx - 60, 280, cx + 60, 340], 180, 360, fill=ink)  # hat crown
    for bx, by in tips:
        d.ellipse([bx - 18, by - 18, bx + 18, by + 18], fill=bell)


def card(t0, t, jester=False):
    """A generic joker playing card spinning in, with a red wild-card mark (or a jester)."""
    cw, ch = 420, 600
    c = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], 34, fill=(236, 232, 222, 255), outline=(30, 30, 30, 255), width=5)
    d.rounded_rectangle([22, 22, cw - 23, ch - 23], 22, outline=(*RED, 255), width=4)
    for (px, py, an) in ((48, 70, "mm"), (cw - 48, ch - 70, "mm")):
        d.text((px, py), "J", font=font(BEBAS, 92), fill=(*RED, 255), anchor=an)
    if jester:
        lay = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        draw_jester(ImageDraw.Draw(lay), cw // 2)
        m = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(m).rounded_rectangle([26, 26, cw - 27, ch - 27], 20, fill=255)
        c.paste(lay, (0, 0), Image.composite(lay.getchannel("A"), m, m).point(lambda v: v))
        d.rounded_rectangle([22, 22, cw - 23, ch - 23], 22, outline=(*RED, 255), width=4)
        for (px, py) in ((48, 70), (cw - 48, ch - 70)):
            d.text((px, py), "J", font=font(BEBAS, 92), fill=(*RED, 255), anchor="mm")
    else:
        d.text((cw // 2, 250), "WILD", font=font(BEBAS, 150), fill=(20, 20, 24, 255), anchor="mm")
        d.text((cw // 2, 360), "CARD", font=font(BEBAS, 110), fill=(*RED, 255), anchor="mm")
        for i in range(5):  # scratchy red strokes
            d.arc([90 + i * 6, 410, 330 - i * 6, 520], 20 + i * 4, 160 - i * 4, fill=(*RED, 255), width=6)
    p = ease(seg(t, t0, t0 + 0.9))
    sx = max(abs(math.cos((1 - p) * math.pi * 2.5)), 0.03)
    c = c.resize((max(int(cw * sx), 2), ch), Image.BICUBIC)
    return c.rotate(-8 + 8 * p + 2 * math.sin(t * 1.7), Image.BICUBIC, expand=True)


def film_strip(d, t, y0):
    off = (t * 420) % 260
    d.rectangle([0, y0, W, y0 + 520], fill=(10, 10, 12))
    for i in range(-1, 6):
        x = i * 260 - off
        d.rectangle([x + 18, y0 + 70, x + 242, y0 + 450], fill=(40, 52, 68), outline=(80, 96, 118), width=3)
        for k in range(4):
            d.rectangle([x + 20 + k * 60, y0 + 18, x + 52 + k * 60, y0 + 46], fill=(200, 200, 205))
            d.rectangle([x + 20 + k * 60, y0 + 474, x + 52 + k * 60, y0 + 502], fill=(200, 200, 205))


def truck(angle_deg):
    tw, th = 760, 300
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body = (20, 22, 28, 255)
    d.rectangle([10, 30, 520, 230], fill=(200, 204, 210, 255))  # trailer
    d.rectangle([10, 30, 520, 52], fill=(*RED, 255))
    d.polygon([(535, 230), (535, 70), (650, 70), (740, 150), (740, 230)], fill=body)  # cab
    d.polygon([(560, 90), (640, 90), (705, 150), (560, 150)], fill=(90, 120, 150, 255))
    d.rectangle([520, 200, 540, 225], fill=body)
    for wx in (70, 150, 430, 610, 690):
        d.ellipse([wx - 36, 196, wx + 36, 268], fill=(8, 8, 10, 255))
        d.ellipse([wx - 14, 218, wx + 14, 246], fill=(120, 120, 128, 255))
    return im.rotate(angle_deg, Image.BICUBIC, expand=True)


def coin(t, t0):
    """Spinning coin: one clean face, one scorched face."""
    r = 190
    p = t - t0
    spin = math.cos(p * 9) if p < 2.2 else math.cos(2.2 * 9) * (1 - ease(seg(t, t0 + 2.2, t0 + 2.6))) + 0.0
    if p >= 2.6:
        spin = -1.0  # lands on the scarred side
    sx = max(abs(spin), 0.05)
    c = Image.new("RGBA", (2 * r + 20, 2 * r + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.ellipse([10, 10, 2 * r + 10, 2 * r + 10], fill=(150, 124, 70, 255))
    d.ellipse([28, 28, 2 * r - 8, 2 * r - 8], fill=(214, 182, 112, 255), outline=(120, 96, 50, 255), width=6)
    if spin >= 0:
        d.text((r + 10, r + 10), "2008", font=font(BEBAS, 120), fill=(110, 84, 40, 255), anchor="mm")
    else:
        burn = np.random.default_rng(7)
        for _ in range(140):
            a, rr = burn.uniform(0, 2 * math.pi), burn.uniform(0, r - 30)
            x, y = r + 10 + rr * math.cos(a), r + 10 + rr * math.sin(a)
            if x > r - 10:
                s = burn.uniform(6, 20)
                d.ellipse([x - s, y - s, x + s, y + s], fill=(40, 30, 22, 220))
        d.text((r + 10, r + 10), "2008", font=font(BEBAS, 120), fill=(60, 40, 20, 255), anchor="mm")
    c = c.resize((max(int(c.width * sx), 2), c.height), Image.BICUBIC)
    hop = -260 * math.sin(math.pi * min(p / 2.6, 1)) if p < 2.6 else 0
    return c, int(hop)


def figure(d, cx, base, s=1.0, fill=(2, 2, 4)):
    """Lone long-coat silhouette on a rooftop ledge (generic, no costume)."""
    d.ellipse([cx - 26 * s, base - 470 * s, cx + 26 * s, base - 412 * s], fill=fill)
    d.polygon([(cx - 30 * s, base - 410 * s), (cx + 30 * s, base - 410 * s), (cx + 78 * s, base - 120 * s),
               (cx + 40 * s, base), (cx - 40 * s, base), (cx - 78 * s, base - 120 * s)], fill=fill)


# ------------------------------------------------------------ captions
def caption_chunks():
    out = []
    for m in LINES:
        words = m["text"].split()
        groups, g = [], []
        for w in words:
            g.append(w)
            if len(" ".join(g)) > 15 or w.endswith((",", ".", "?")):
                groups.append(g)
                g = []
        if g:
            groups.append(g)
        total = sum(len(" ".join(x)) + 2 for x in groups)
        t, span = m["start"], m["end"] - m["start"]
        for gr in groups:
            dt = span * (len(" ".join(gr)) + 2) / total
            out.append((t, t + dt, gr))
            t += dt
    return out


CAPS = caption_chunks()
KEY = {"2008,", "BILLION", "OSCAR", "IMAX", "REAL", "TRUCK", "CRIME", "EPIC.", "BEST", "PICTURE,", "COSTS.", "BEST", "EVER"}


def draw_caption(im, t):
    for a, b, words in CAPS:
        if a <= t < b:
            d = ImageDraw.Draw(im)
            f = font(OSW, 92)
            s = " ".join(words).upper()
            pop = 1 + 0.12 * (1 - ease(seg(t, a, a + 0.12)))
            f = font(OSW, int(92 * pop))
            # word-level colouring
            widths = [d.textlength(w.upper() + " ", font=f) for w in words]
            x = W / 2 - sum(widths) / 2 + d.textlength(" ", font=f) / 2
            for w, wd in zip(words, widths):
                col = GOLD if w.upper().strip("'S") in KEY or w.upper() in KEY else WHITE
                d.text((x, 1500), w.upper(), font=f, fill=col, anchor="lm", stroke_width=9, stroke_fill=(0, 0, 0))
                x += wd
            return


# ------------------------------------------------------------ frame
L = [m["start"] for m in LINES] + [DUR]


def frame(t):
    shake = 0.0
    for s in L[1:-1]:
        if 0 <= t - s < 0.35:
            shake = 14 * (1 - (t - s) / 0.35)
    im = city(t)
    d = ImageDraw.Draw(im)

    if t < L[1]:  # hook
        p = ease(seg(t, 0.2, 1.4))
        glow_text(im, 960, "2008", font(BEBAS, int(400 + 30 * t)), (*ICE, int(255 * p)), 30, 2)
        text_c(d, 330, "WHY DID", font(BEBAS, 120), (*WHITE, int(255 * p)))
        text_c(d, 450, "THE DARK KNIGHT", font(BEBAS, 150), (*WHITE, int(255 * p)))
        glow_text(im, 580, "WORK SO WELL?", font(BEBAS, 150), (*RED, int(255 * p)), 16, 2)

    elif t < L[2]:  # billion
        p = ease(seg(t, L[1], L[1] + 1.6))
        v = int(1_000_000_000 * p)
        im.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 110)))
        glow_text(im, 700, f"${v:,}", font(BEBAS, 190), (*GOLD, 255), 24, 2)
        text_c(ImageDraw.Draw(im), 860, "WORLDWIDE BOX OFFICE", font(OSW, 54), (*WHITE, 230))

    elif t < L[3]:  # joker / oscar
        im.alpha_composite(Image.new("RGBA", (W, H), (30, 0, 0, 120)))
        c = card(L[2], t)
        im.alpha_composite(c, (W // 2 - c.width // 2, 300))
        if t > L[2] + 2.2:
            p = ease(seg(t, L[2] + 2.2, L[2] + 2.8))
            dd = ImageDraw.Draw(im)
            text_c(dd, 1050, "HEATH LEDGER", font(BEBAS, 120), (*WHITE, int(255 * p)))
            text_c(dd, 1150, "OSCAR — BEST SUPPORTING ACTOR", font(OSW, 46), (*GOLD, int(255 * p)))

    elif t < L[4]:  # IMAX + real truck
        mid = L[3] + 2.6
        if t < mid:
            film_strip(d, t, 360)
            glow_text(im, 1040, "SHOT ON IMAX", font(BEBAS, 160), (*ICE, 255), 20, 2)
        else:
            p = seg(t, mid + 0.4, mid + 1.8)
            ang = 180 * ease(p) if p < 1 else 180
            tr = truck(-ang)
            road = ImageDraw.Draw(im)
            road.rectangle([0, 1000, W, 1080], fill=(18, 18, 22))
            for k in range(6):
                road.rectangle([k * 220 - (t * 600) % 220, 1036, k * 220 - (t * 600) % 220 + 110, 1044], fill=(200, 180, 90))
            tx = int(W / 2 - tr.width / 2 + (1 - ease(seg(t, mid, mid + 0.5))) * 900)
            im.alpha_composite(tr, (tx, int(1000 - tr.height / 2 - 120 - 160 * math.sin(math.pi * min(p, 1)))))
            text_c(ImageDraw.Draw(im), 520, "A REAL TRUCK.", font(BEBAS, 150), (*WHITE, 255))
            glow_text(im, 650, "REALLY FLIPPED.", font(BEBAS, 150), (*RED, 255), 16, 2)

    elif t < L[5]:  # genre
        im.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 140)))
        dd = ImageDraw.Draw(im)
        text_c(dd, 560, "SUPERHERO MOVIE", font(BEBAS, 150), (150, 150, 158, 255))
        p = ease(seg(t, L[4] + 0.6, L[4] + 1.0))
        dd.line([120, 565, 120 + 840 * p, 545], fill=RED, width=16)
        if t > L[4] + 2.1:
            q = ease(seg(t, L[4] + 2.1, L[4] + 2.5))
            glow_text(im, 820, "CRIME EPIC", font(BEBAS, int(200 + 30 * (1 - q))), (*GOLD, int(255 * q)), 22, 2)

    elif t < L[6]:  # snub -> rule change, coin
        c, hop = coin(t, L[5])
        im.alpha_composite(c, (W // 2 - c.width // 2, 330 + hop))
        dd = ImageDraw.Draw(im)
        if t < L[5] + 3.0:
            text_c(dd, 1000, "BEST PICTURE?", font(BEBAS, 140), (*WHITE, 255))
            text_c(dd, 1120, "NOT EVEN NOMINATED.", font(OSW, 58), (*RED, 255))
        else:
            q = ease(seg(t, L[5] + 3.0, L[5] + 3.4))
            text_c(dd, 1000, "NEXT YEAR, BEST PICTURE WENT", font(OSW, 54), (*WHITE, int(255 * q)))
            glow_text(im, 1130, "FROM 5 TO 10 NOMINEES", font(BEBAS, 118), (*GOLD, int(255 * q)), 18, 2)

    elif t < L[7]:  # what a hero costs
        im = city(t, push=seg(t, L[6], L[7]))
        dd = ImageDraw.Draw(im)
        dd.rectangle([0, 1240, W, H], fill=(2, 2, 4))
        figure(dd, 540, 1250, 1.25)
        p = ease(seg(t, L[6] + 1.6, L[6] + 2.2))
        glow_text(im, 420, "WHAT DOES", font(BEBAS, 140), (*WHITE, int(255 * p)), 14, 1)
        glow_text(im, 560, "A HERO COST?", font(BEBAS, 170), (*RED, int(255 * p)), 18, 2)

    else:  # outro question
        im.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 150)))
        p = ease(seg(t, L[7], L[7] + 0.5))
        glow_text(im, 640, "STILL THE", font(BEBAS, 150), (*WHITE, int(255 * p)), 14, 1)
        glow_text(im, 820, "GREATEST?", font(BEBAS, 230), (*GOLD, int(255 * p)), 24, 2)
        if t > L[7] + 1.2:
            q = ease(seg(t, L[7] + 1.2, L[7] + 1.6))
            text_c(ImageDraw.Draw(im), 1060, "TELL ME IN THE COMMENTS", font(OSW, 56), (*WHITE, int(230 * q)))

    rain(ImageDraw.Draw(im), t, 120 if t < L[6] else 170)
    draw_caption(im, t)

    # lightning-style flash on scene cuts
    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    for s in L[1:-1]:
        if 0 <= t - s < 0.18:
            a += 120 * (1 - (t - s) / 0.18)
    a *= VIGN
    a[..., 2] *= 1.06  # cold grade
    g = GRAIN[int(t * FPS) % len(GRAIN)]
    a += np.repeat(np.repeat(g, 2, 0), 2, 1)
    a *= min(1, t / 0.4) * min(1, (DUR - t) / 0.5)
    a = np.clip(a, 0, 255).astype(np.uint8)
    if shake:
        dx, dy = rng.integers(-1, 2) * shake, rng.integers(-1, 2) * shake
        a = np.roll(a, (int(dy), int(dx)), (0, 1))
    return a


if __name__ == "__main__":
    if "--stills" in sys.argv:
        for i, ts in enumerate([1.5, 7.0, 12.0, 15.0, 18.5, 23.5, 26.0, 29.5, 33.5, 37.5]):
            Image.fromarray(frame(ts)).save(f"still_{i}.png")
        sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", sys.argv[2],
                           "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", sys.argv[3]],
                          stdin=subprocess.PIPE)
    for n in range(int(DUR * FPS)):
        ff.stdin.write(frame(n / FPS).tobytes())
    ff.stdin.close()
    ff.wait()
