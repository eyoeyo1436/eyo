"""'Why Halloween (1978) Worked' - 70s VHS horror motion-graphics Short (30 s, 1080x1920).

All visuals are drawn here: no film footage, stills, the film's mask or its characters.
usage: python3 render.py lines.json mix.wav out.mp4 [--stills]
"""
import json, math, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 30.0
rng = np.random.default_rng(31)
LINES = json.load(open(sys.argv[1]))
L = [m["start"] for m in LINES] + [DUR]
BEBAS, OSW = "fonts/BebasNeue-Regular.ttf", "fonts/Oswald.ttf"
ORANGE, AMBER, WHITE, BONE = (255, 122, 24), (255, 184, 76), (244, 238, 228), (226, 214, 190)
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


def text(d, y, s, f, fill, x=W // 2, stroke=0):
    d.text((x, y), s, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=(0, 0, 0))


def glow(im, y, s, f, fill, r=18, n=2, x=W // 2):
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((x, y), s, font=f, fill=fill, anchor="mm")
    g = lay.filter(ImageFilter.GaussianBlur(r))
    for _ in range(n):
        im.alpha_composite(g)
    im.alpha_composite(lay)


# ------------------------------------------------------------ the street (static)
def street():
    y = np.linspace(0, 1, H)[:, None, None]
    g = np.array([10, 6, 22]) + np.array([150, 60, 26]) * np.clip(y / 0.58, 0, 1) ** 2.4
    g = np.repeat(g, W, 1)
    yy, xx = np.mgrid[0:H, 0:W]
    moon = np.exp(-(((xx - 820) ** 2 + (yy - 330) ** 2) / 2 / 150 ** 2))[..., None]
    g = g + moon * np.array([120, 90, 60])
    im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    d.ellipse([760, 270, 880, 390], fill=(250, 226, 180))
    r = np.random.default_rng(4)
    x = -40
    while x < W:  # gabled suburban houses
        bw = int(r.integers(230, 330))
        top = int(r.integers(1020, 1120))
        roof = top - int(r.integers(110, 170))
        ink = (8, 6, 10)
        d.rectangle([x, top, x + bw, 1400], fill=ink)
        d.polygon([(x - 20, top), (x + bw // 2, roof), (x + bw + 20, top)], fill=ink)
        d.rectangle([x + bw - 70, roof + 20, x + bw - 40, top - 30], fill=ink)  # chimney
        for wx in (x + 40, x + bw - 110):
            if r.random() < 0.6:
                d.rectangle([wx, top + 60, wx + 60, top + 140], fill=(255, 170, 70))
                d.line([wx + 30, top + 60, wx + 30, top + 140], fill=ink, width=5)
        x += bw + int(r.integers(30, 80))
    for tx in (120, 640, 980):  # bare trees
        d.line([tx, 1400, tx + 10, 860], fill=(4, 3, 6), width=26)
        for k in range(7):
            a = -math.pi / 2 + r.uniform(-1.1, 1.1)
            y0 = 860 + k * 50
            d.line([tx + 8, y0, tx + 8 + math.cos(a) * 240, y0 + math.sin(a) * 240], fill=(4, 3, 6), width=10)
    lamp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lamp).polygon([(560, 1150), (380, 1420), (740, 1420)], fill=(255, 190, 110, 90))
    im.alpha_composite(lamp.filter(ImageFilter.GaussianBlur(40)))
    d.line([600, 1400, 600, 1130], fill=(4, 3, 6), width=12)
    d.line([600, 1135, 560, 1135], fill=(4, 3, 6), width=10)
    d.ellipse([548, 1135, 572, 1160], fill=(255, 220, 150))
    d.rectangle([0, 1400, W, H], fill=(14, 10, 12))  # road
    d.polygon([(300, 1400), (780, 1400), (1200, H), (-120, H)], fill=(24, 18, 20))
    return im


STREET = street()
yy, xx = np.mgrid[0:H, 0:W]
VIGN = (1 - 0.8 * np.clip(((xx - W / 2) / (W * 0.72)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2, 0, 1))[..., None]
SCAN = (0.9 + 0.1 * (np.arange(H) % 4 < 2))[:, None, None]
LEAVES = [(rng.uniform(0, W), rng.uniform(-H, H), rng.uniform(0.6, 1.4), rng.uniform(0, 6.28),
           [ORANGE, AMBER, (190, 60, 20), (150, 90, 30)][rng.integers(4)]) for _ in range(90)]


def leaves(d, t, count):
    for i, (x, y, s, ph, c) in enumerate(LEAVES[:count]):
        yy_ = (y + t * 160 * s) % (H + 200) - 100
        xx_ = (x + 60 * math.sin(t * 1.3 * s + ph) + t * 30) % W
        a = t * 3 * s + ph
        r = 22 * s
        pts = [(xx_ + r * math.cos(a + k * math.pi / 2) * (1 if k % 2 == 0 else 0.45),
                yy_ + r * math.sin(a + k * math.pi / 2) * (1 if k % 2 == 0 else 0.45)) for k in range(4)]
        d.polygon(pts, fill=c)


def figure(d, x, base, s, alpha):
    """A distant, featureless dark figure standing at the end of the street."""
    c = (0, 0, 0, alpha)
    d.ellipse([x - 16 * s, base - 190 * s, x + 16 * s, base - 150 * s], fill=c)
    d.polygon([(x - 30 * s, base - 150 * s), (x + 30 * s, base - 150 * s), (x + 36 * s, base - 60 * s),
               (x + 22 * s, base), (x - 22 * s, base), (x - 36 * s, base - 60 * s)], fill=c)


def pumpkin(im, cx, cy, t):
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    flick = 0.85 + 0.15 * math.sin(t * 23) * math.sin(t * 7.3)
    gl = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse([cx - 420, cy - 380, cx + 420, cy + 380], fill=(255, 120, 20, int(120 * flick)))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(110)))
    for dx, w in ((-150, 230), (150, 230), (-60, 240), (60, 240)):
        d.ellipse([cx + dx - w, cy - 230, cx + dx + w, cy + 230], fill=(214, 92, 14), outline=(120, 40, 6), width=8)
    d.rectangle([cx - 22, cy - 300, cx + 22, cy - 210], fill=(60, 70, 30))
    lit = (255, int(200 * flick), 60)
    d.polygon([(cx - 190, cy - 40), (cx - 90, cy - 150), (cx - 40, cy - 30)], fill=lit)
    d.polygon([(cx + 190, cy - 40), (cx + 90, cy - 150), (cx + 40, cy - 30)], fill=lit)
    d.polygon([(cx, cy - 10), (cx - 35, cy + 50), (cx + 35, cy + 50)], fill=lit)
    mouth = [(cx - 230, cy + 70)]
    for k in range(9):
        x = cx - 230 + k * 460 / 8
        mouth.append((x, cy + (130 if k % 2 else 90) + 40 * math.sin(k / 8 * math.pi)))
    mouth += [(cx + 230, cy + 70), (cx, cy + 240)]
    d.polygon(mouth, fill=lit)
    im.alpha_composite(lay)


def price_tag(im, t, t0):
    ang = 14 * math.sin((t - t0) * 3.2) * math.exp(-(t - t0) * 0.6)
    tag = Image.new("RGBA", (520, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(tag)
    d.polygon([(0, 150), (90, 0), (520, 0), (520, 300), (90, 300)], fill=BONE + (255,))
    d.ellipse([60, 130, 100, 170], fill=(20, 14, 12, 255))
    d.text((310, 150), "$1.98", font=font(BEBAS, 190), fill=(150, 30, 12, 255), anchor="mm")
    tag = tag.rotate(-ang - 8, Image.BICUBIC, expand=True)
    d2 = ImageDraw.Draw(im)
    d2.line([W // 2 - 160, 160, W // 2 - 150, 520], fill=BONE, width=4)
    im.alpha_composite(tag, (W // 2 - tag.width // 2 + 30, 470))


def keyboard(d, t, t0):
    y0, kw = 980, W / 14
    lit = int((t - t0) * 6) % 14
    for k in range(14):
        on = k in (lit, (lit * 5) % 14)
        d.rectangle([k * kw + 3, y0, (k + 1) * kw - 3, y0 + 360], fill=ORANGE if on else BONE)
    for k in range(14):
        if k % 7 not in (2, 6):
            d.rectangle([(k + 0.65) * kw, y0, (k + 1.35) * kw, y0 + 220], fill=(12, 10, 10))


def check(d, x, y, p, col=ORANGE):
    if p <= 0:
        return
    pts = [(x, y), (x + 26, y + 30), (x + 76, y - 40)]
    a = min(p * 2, 1)
    d.line([pts[0], (pts[0][0] + (pts[1][0] - pts[0][0]) * a, pts[0][1] + (pts[1][1] - pts[0][1]) * a)], fill=col, width=14)
    if p > 0.5:
        b = (p - 0.5) * 2
        d.line([pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * b, pts[1][1] + (pts[2][1] - pts[1][1]) * b)], fill=col, width=14)


# ------------------------------------------------------------ captions
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
KEY = {"1978,", "SEVENTY", "MILLION.", "MASK?", "WHITE.", "THREE", "DAYS.", "PAPER,", "SLASHER", "SCARIEST"}


def caption(im, t):
    for a, b, words in CAPS:
        if a <= t < b:
            d = ImageDraw.Draw(im)
            f = font(OSW, int(90 * (1 + 0.12 * (1 - ease(seg(t, a, a + 0.12))))))
            ws = [d.textlength(w.upper() + " ", font=f) for w in words]
            x = W / 2 - sum(ws) / 2 + d.textlength(" ", font=f) / 2
            for w, wd in zip(words, ws):
                d.text((x, 1560), w.upper(), font=f, fill=ORANGE if w.upper() in KEY else WHITE, anchor="lm",
                       stroke_width=9, stroke_fill=(0, 0, 0))
                x += wd
            return


def vhs_ui(d, t):
    if int(t * 2) % 2 == 0:
        d.polygon([(70, 90), (70, 140), (112, 115)], fill=WHITE)
    d.text((130, 115), "PLAY", font=font(OSW, 54), fill=WHITE, anchor="lm")
    d.text((W - 70, 1830), "OCT. 31  1978", font=font(OSW, 48), fill=WHITE, anchor="rm")


# ------------------------------------------------------------ frame
def frame(t):
    im = STREET.copy()
    zoom = 1 + 0.02 * t
    if zoom > 1:
        cw, ch = int(W / zoom), int(H / zoom)
        im = im.crop(((W - cw) // 2, (H - ch) // 2, (W + cw) // 2, (H + ch) // 2)).resize((W, H), Image.BILINEAR)
    d = ImageDraw.Draw(im)
    dim = lambda a: im.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, a)))

    if t < L[1]:  # hook
        figure(d, 520, 1395, 1.1, int(255 * seg(t, 1.5, 3.0)))
        p = ease(seg(t, 0.2, 1.2))
        glow(im, 360, "HALLOWEEN", font(BEBAS, 250), ORANGE + (int(255 * p),), 26, 2)
        text(ImageDraw.Draw(im), 540, "1978", font(BEBAS, 140), WHITE + (int(255 * p),))
        text(ImageDraw.Draw(im), 680, "WHY DID IT WORK SO WELL?", font(OSW, 62), BONE + (int(255 * ease(seg(t, 1.0, 1.6))),))
    elif t < L[2]:  # money
        dim(150)
        dd = ImageDraw.Draw(im)
        text(dd, 420, "BUDGET", font(OSW, 60), BONE)
        glow(im, 560, "$300,000", font(BEBAS, 200), WHITE + (255,), 14, 1)
        if t > L[1] + 1.8:
            p = ease(seg(t, L[1] + 1.8, L[1] + 3.6))
            text(ImageDraw.Draw(im), 800, "BOX OFFICE", font(OSW, 60), BONE + (int(255 * min(p * 3, 1)),))
            glow(im, 960, f"${int(70_000_000 * p):,}", font(BEBAS, 200), ORANGE + (255,), 22, 2)
    elif t < L[3]:  # mask
        dim(150)
        price_tag(im, t, L[2])
        dd = ImageDraw.Draw(im)
        for k in range(60):  # spray-paint mist
            a = rng.uniform(0, 6.28)
            r = rng.uniform(0, 160)
            x, y = 820 + r * math.cos(a), 350 + r * math.sin(a) * 0.6
            dd.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 255, 255, 140))
        text(dd, 900, "THE MASK?", font(BEBAS, 170), WHITE)
        text(dd, 1030, "STORE-BOUGHT. SPRAY-PAINTED WHITE.", font(OSW, 50), AMBER)
    elif t < L[4]:  # music
        dim(160)
        dd = ImageDraw.Draw(im)
        keyboard(dd, t, L[3])
        text(dd, 430, "THE MUSIC?", font(OSW, 70), BONE)
        glow(im, 610, "3 DAYS", font(BEBAS, 260), ORANGE + (255,), 24, 2)
        text(ImageDraw.Draw(im), 790, "WRITTEN BY THE DIRECTOR HIMSELF", font(OSW, 48), WHITE)
    elif t < L[5]:  # leaves
        dim(90)
        leaves(ImageDraw.Draw(im), t, 90)
        p = ease(seg(t, L[4] + 1.6, L[4] + 2.1))
        glow(im, 520, "FAKE LEAVES", font(BEBAS, 200), ORANGE + (255,), 22, 2)
        text(ImageDraw.Draw(im), 690, "PAINTED PAPER", font(BEBAS, 120), WHITE + (int(255 * p),))
        text(ImageDraw.Draw(im), 800, "SHOT IN SPRING, IN CALIFORNIA", font(OSW, 50), AMBER + (int(255 * p),))
    elif t < L[6]:  # rulebook
        dim(170)
        dd = ImageDraw.Draw(im)
        text(dd, 400, "THE SLASHER RULEBOOK", font(BEBAS, 130), ORANGE)
        dd.line([170, 480, 910, 480], fill=ORANGE, width=6)
        for k, s in enumerate(("ONE TERRIFYING NIGHT", "A SILENT, MASKED KILLER", "THE FINAL GIRL")):
            st = L[5] + 0.4 + k * 0.7
            a = int(255 * seg(t, st, st + 0.2))
            dd.rounded_rectangle([170, 560 + k * 150, 260, 650 + k * 150], 10, outline=BONE + (a,), width=6)
            check(dd, 188, 605 + k * 150, seg(t, st + 0.15, st + 0.45))
            dd.text((300, 605 + k * 150), s, font=font(OSW, 60), fill=WHITE + (a,), anchor="lm")
    else:  # outro
        dim(185)
        pumpkin(im, W // 2, 1000, t)
        p = ease(seg(t, L[6], L[6] + 0.5))
        text(ImageDraw.Draw(im), 380, "STILL THE", font(BEBAS, 150), WHITE + (int(255 * p),))
        glow(im, 540, "SCARIEST?", font(BEBAS, 230), ORANGE + (int(255 * p),), 24, 2)

    d = ImageDraw.Draw(im)
    if L[4] > t or t >= L[5]:
        leaves(d, t, 14)
    caption(im, t)
    vhs_ui(ImageDraw.Draw(im), t)

    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    a[..., 0] = np.roll(a[..., 0], 4, 1)  # VHS chroma shift
    a[..., 2] = np.roll(a[..., 2], -4, 1)
    a *= VIGN * SCAN
    a = a * np.array([1.06, 0.98, 0.88])  # warm faded film grade
    a += rng.normal(0, 10, (H // 3, W // 3, 1)).repeat(3, 0).repeat(3, 1)
    for s in L[1:-1]:  # glitch on cuts
        if 0 <= t - s < 0.2:
            for _ in range(6):
                y = int(rng.integers(0, H - 60))
                a[y:y + 60] = np.roll(a[y:y + 60], int(rng.integers(-80, 80)), 1)
            a += 60 * (1 - (t - s) / 0.2)
    a *= min(1, t / 0.4) * min(1, (DUR - t) / 0.5)
    return np.clip(a, 0, 255).astype(np.uint8)


if __name__ == "__main__":
    if "--stills" in sys.argv:
        for i, ts in enumerate([2.5, 8.5, 12.0, 16.0, 21.0, 25.5, 28.5]):
            Image.fromarray(frame(ts)).save(f"still_{i}.png")
        sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", sys.argv[2], "-c:v", "libx264", "-preset", "slow",
                           "-crf", "21", "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p", "-c:a", "aac",
                           "-b:a", "192k", "-shortest", "-movflags", "+faststart", sys.argv[3]], stdin=subprocess.PIPE)
    for n in range(int(DUR * FPS)):
        ff.stdin.write(frame(n / FPS).tobytes())
    ff.stdin.close()
    ff.wait()
