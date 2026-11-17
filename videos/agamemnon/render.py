"""'Agamemnon' - 60 s animated YouTube video (1920x1080, 30 fps), cartoon style in a pale-blue palette.

Agamemnon is an original cartoon design based on Bronze Age (Mycenaean) archaeology: Dendra-style bronze
plate armour and a boar's-tusk helmet. No film costume, actor likeness or footage is used.
usage: python3 render.py timing.json mix.wav out.mp4 [--stills t1,t2,...]
"""
import json, math, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR, SS = 1920, 1080, 30, 60.0, 2
TIM = json.load(open(sys.argv[1]))
LS = {}
for m in TIM:
    LS.setdefault(m["line"], m["start"])
LS[9] = DUR
FONT = "fonts/Montserrat.ttf"

SKY1, SKY2 = (200, 216, 228), (150, 176, 196)
SEA1, SEA2, DEEP = (104, 134, 158), (66, 94, 120), (30, 46, 66)
STONE, SAND, INK = (206, 200, 188), (214, 204, 180), (30, 38, 52)
BRONZE, BRONZE_D, BRONZE_L = (186, 142, 74), (126, 90, 44), (226, 190, 120)
CLOAK, SKIN, BEARD = (150, 60, 54), (214, 170, 132), (52, 40, 34)
PALE, GOLD = (236, 241, 245), (230, 194, 116)
_fc = {}


def font(size, w=800):
    if (size, w) not in _fc:
        f = ImageFont.truetype(FONT, int(size * SS))
        f.set_variation_by_axes([w])
        _fc[(size, w)] = f
    return _fc[(size, w)]


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def eout(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


seg = lambda t, a, b: min(max((t - a) / (b - a), 0.0), 1.0)


class C:
    def __init__(self, bg=SKY1):
        self.im = Image.new("RGB", (W * SS, H * SS), bg)
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def S(self, pts):
        return [v * SS for p in pts for v in p]

    def poly(self, pts, fill, outline=None, w=0):
        self.d.polygon(self.S(pts), fill=fill)
        if outline:
            self.d.line(self.S(pts + [pts[0]]), fill=outline, width=int(w * SS), joint="curve")

    def rect(self, x0, y0, x1, y1, fill, r=0, outline=None, w=0):
        self.d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], r * SS, fill=fill, outline=outline, width=int(w * SS))

    def ell(self, x, y, rx, ry, fill=None, outline=None, w=0):
        self.d.ellipse([(x - rx) * SS, (y - ry) * SS, (x + rx) * SS, (y + ry) * SS], fill=fill, outline=outline, width=int(w * SS))

    def line(self, pts, fill, w):
        self.d.line(self.S(pts), fill=fill, width=int(w * SS), joint="curve")

    def text(self, x, y, s, size, fill, w=800, anchor="mm", stroke=0):
        self.d.text((x * SS, y * SS), s, font=font(size, w), fill=fill, anchor=anchor, stroke_width=int(stroke * SS),
                    stroke_fill=(20, 28, 40))

    def out(self):
        return self.im.resize((W, H), Image.LANCZOS)


def grad(c, top, bot, y0=0, y1=H):
    for y in range(int(y0), int(y1), 4):
        u = (y - y0) / max(y1 - y0, 1)
        col = tuple(int(top[i] + (bot[i] - top[i]) * u) for i in range(3))
        c.rect(0, y, W, y + 4, col)


def sea(c, t, y0, col1=SEA1, col2=SEA2, calm=False):
    grad(c, col1, col2, y0, H)
    amp = 3 if calm else 10
    for k in range(9):
        y = y0 + 20 + k * (H - y0) / 9
        pts = [(x, y + amp * math.sin(x / 90 + t * (1.4 + k * 0.1) + k)) for x in range(0, W + 40, 40)]
        c.line(pts, (225, 235, 242, 70 - k * 4), 3)


def clouds(c, t, y=180, col=(236, 242, 246, 200), n=5, speed=12):
    for k in range(n):
        x = (k * 470 + t * speed) % (W + 600) - 300
        for dx, dy, r in ((0, 0, 70), (70, -20, 90), (150, 0, 70), (80, 25, 70)):
            c.ell(x + dx, y + k % 2 * 60 + dy, r * 1.4, r * 0.8, fill=col)


# ------------------------------------------------------------------ characters
def agamemnon(c, x, y, s=1.0, t=0.0, point=0.0, angry=0.0, crown=False, ghost=False, cloak=True):
    """Feet at (x, y). Original cartoon design: Dendra-style bronze plates, boar's-tusk helmet, red cloak."""
    a = 120 if ghost else 255
    tint = (lambda col: (170, 205, 230, a)) if ghost else (lambda col: col + (255,))
    ol = (60, 90, 120, a) if ghost else INK + (255,)
    lw = 5
    wave = math.sin(t * 2.2)
    if cloak:
        c.poly([(x - 70 * s, y - 330 * s), (x + 70 * s, y - 330 * s), (x + 120 * s + 25 * s * wave, y - 40 * s),
                (x - 130 * s + 20 * s * wave, y - 30 * s)], tint(CLOAK), ol, lw)
    for dx in (-34, 34):  # legs with bronze greaves
        c.rect(x + dx * s - 18 * s, y - 120 * s, x + dx * s + 18 * s, y - 70 * s, tint(SKIN), 8 * s, ol, lw)
        c.rect(x + dx * s - 22 * s, y - 80 * s, x + dx * s + 22 * s, y - 8 * s, tint(BRONZE), 10 * s, ol, lw)
        c.rect(x + dx * s - 30 * s, y - 14 * s, x + dx * s + 30 * s, y + 4 * s, tint(BRONZE_D), 6 * s, ol, lw)
    # kilt with pteruges strips
    c.poly([(x - 80 * s, y - 200 * s), (x + 80 * s, y - 200 * s), (x + 95 * s, y - 110 * s), (x - 95 * s, y - 110 * s)], tint((176, 196, 212)), ol, lw)
    for k in range(7):
        xx = x - 84 * s + k * 28 * s
        c.rect(xx, y - 150 * s, xx + 22 * s, y - 104 * s, tint((140, 164, 184)), 4 * s, ol, 3)
    # Dendra cuirass: torso shell, three girdle bands, high neck guard, curved shoulder plates
    c.rect(x - 92 * s, y - 360 * s, x + 92 * s, y - 220 * s, tint(BRONZE), 30 * s, ol, lw)
    for k in range(3):
        yy = y - 225 * s + k * 26 * s
        c.rect(x - 96 * s + k * 4 * s, yy, x + 96 * s - k * 4 * s, yy + 30 * s, tint(BRONZE_D if k % 2 else BRONZE), 10 * s, ol, lw)
    c.line([(x - 50 * s, y - 330 * s), (x - 40 * s, y - 250 * s)], tint(BRONZE_L), 6 * s)
    for side in (-1, 1):
        c.poly([(x + side * 60 * s, y - 372 * s), (x + side * 128 * s, y - 350 * s), (x + side * 132 * s, y - 296 * s),
                (x + side * 80 * s, y - 300 * s)], tint(BRONZE_L), ol, lw)
    c.rect(x - 52 * s, y - 392 * s, x + 52 * s, y - 356 * s, tint(BRONZE_D), 12 * s, ol, lw)  # neck guard
    # arms: left on hip / pointing, right holds sceptre
    pa = math.radians(-100 + 60 * (1 - point)) if point else math.radians(-20)
    sx, sy = x - 112 * s, y - 330 * s
    ex, ey = sx + math.sin(pa) * 120 * s, sy + math.cos(pa) * 120 * s * (0.4 if point else 1)
    if point:
        ex, ey = sx - 150 * s, sy - 40 * s * point
    c.line([(sx, sy), (ex, ey)], tint(SKIN), 30 * s)
    c.ell(ex, ey, 18 * s, 18 * s, fill=tint(SKIN), outline=ol, w=3)
    c.rect(sx - 20 * s + (ex - sx) * 0.45, sy - 16 * s + (ey - sy) * 0.45, sx + 20 * s + (ex - sx) * 0.45, sy + 16 * s + (ey - sy) * 0.45, tint(BRONZE), 6 * s)
    rx, ry = x + 112 * s, y - 330 * s
    c.line([(rx, ry), (rx + 40 * s, ry + 100 * s)], tint(SKIN), 30 * s)
    c.line([(rx + 50 * s, y - 470 * s), (rx + 40 * s, y)], tint((110, 80, 50)), 10 * s)  # sceptre
    c.ell(rx + 50 * s, y - 478 * s, 18 * s, 18 * s, fill=tint(GOLD), outline=ol, w=3)
    c.ell(rx + 42 * s, ry + 104 * s, 18 * s, 18 * s, fill=tint(SKIN), outline=ol, w=3)
    # head: heavy brow, big nose, curly dark beard
    hx, hy = x, y - 450 * s
    c.ell(hx, hy, 52 * s, 60 * s, fill=tint(SKIN), outline=ol, w=lw)
    for bx, by in ((-40, 20), (-22, 42), (0, 52), (22, 42), (40, 20), (-30, 60), (0, 74), (30, 60)):
        c.ell(hx + bx * s, hy + by * s, 20 * s, 18 * s, fill=tint(BEARD))
    c.ell(hx, hy + 8 * s, 14 * s, 10 * s, fill=tint((190, 140, 110)))
    brow = 6 * angry
    for side in (-1, 1):
        c.line([(hx + side * 34 * s, hy - 22 * s - brow * side * -1), (hx + side * 8 * s, hy - 16 * s + brow)], tint(BEARD), 7 * s)
        c.ell(hx + side * 20 * s, hy - 5 * s, 6 * s, 6 * s, fill=ol)
    # boar's-tusk helmet: dome with rows of curved tusk plates, cheek guards, knob and plume
    c.d.chord([(hx - 62 * s) * SS, (hy - 120 * s) * SS, (hx + 62 * s) * SS, (hy - 4 * s) * SS], 180, 360, fill=tint((222, 214, 196)), outline=ol, width=int(lw * SS))
    for row in range(3):
        yy = hy - 34 * s - row * 18 * s
        half = (58 - row * 12) * s
        n = 7 - row
        for k in range(n):
            xx = hx - half + (k + 0.5) * 2 * half / n
            c.d.arc([(xx - 9 * s) * SS, (yy - 8 * s) * SS, (xx + 9 * s) * SS, (yy + 8 * s) * SS], 200, 340, fill=ol, width=int(3 * SS))
    for side in (-1, 1):
        c.poly([(hx + side * 58 * s, hy - 60 * s), (hx + side * 66 * s, hy + 6 * s), (hx + side * 44 * s, hy + 18 * s), (hx + side * 48 * s, hy - 40 * s)], tint(BRONZE), ol, 4)
    c.ell(hx, hy - 120 * s, 12 * s, 12 * s, fill=tint(BRONZE), outline=ol, w=3)
    pw = math.sin(t * 3) * 10 * s
    c.poly([(hx - 6 * s, hy - 126 * s), (hx + 6 * s, hy - 126 * s), (hx + 70 * s + pw, hy - 60 * s), (hx + 40 * s + pw, hy - 54 * s)], tint((40, 36, 40)))
    if crown:
        for k in range(5):
            xx = hx - 50 * s + k * 25 * s
            c.poly([(xx - 10 * s, hy - 112 * s), (xx + 10 * s, hy - 112 * s), (xx, hy - 140 * s)], tint(GOLD), ol, 2)


def person(c, x, y, s=1.0, body=(120, 140, 160), head=SKIN, hat=None, veil=None, cross=False, alpha=255, t=0.0):
    """Generic cartoon figure (secondary characters), feet at (x, y)."""
    a = lambda col: col + (alpha,)
    ol = INK + (alpha,)
    c.poly([(x - 50 * s, y - 250 * s), (x + 50 * s, y - 250 * s), (x + 70 * s, y), (x - 70 * s, y)], a(body), ol, 4)
    if veil:
        c.poly([(x - 50 * s, y - 330 * s), (x + 50 * s, y - 330 * s), (x + 64 * s, y - 120 * s), (x - 64 * s, y - 120 * s)], a(veil), ol, 3)
    c.ell(x, y - 290 * s, 40 * s, 46 * s, fill=a(head), outline=ol, w=4)
    c.ell(x - 14 * s, y - 296 * s, 5 * s, 5 * s, fill=ol)
    c.ell(x + 14 * s, y - 296 * s, 5 * s, 5 * s, fill=ol)
    if hat == "phrygian":
        c.poly([(x - 44 * s, y - 300 * s), (x + 44 * s, y - 300 * s), (x + 30 * s, y - 360 * s), (x - 20 * s, y - 370 * s)], a((170, 70, 60)), ol, 3)
    if hat == "pilos":
        c.poly([(x - 42 * s, y - 312 * s), (x + 42 * s, y - 312 * s), (x, y - 376 * s)], a((140, 120, 90)), ol, 3)
    if hat == "crest":
        c.d.chord([(x - 46 * s) * SS, (y - 360 * s) * SS, (x + 46 * s) * SS, (y - 280 * s) * SS], 180, 360, fill=a(BRONZE), outline=ol, width=int(3 * SS))
        c.poly([(x - 40 * s, y - 330 * s), (x + 40 * s, y - 330 * s), (x + 10 * s, y - 390 * s), (x - 30 * s, y - 380 * s)], a((60, 50, 60)))
    if cross:
        c.line([(x - 50 * s, y - 180 * s), (x + 50 * s, y - 160 * s)], a(head), 24 * s)
        c.line([(x + 50 * s, y - 180 * s), (x - 50 * s, y - 160 * s)], a(head), 24 * s)


def ship(c, x, y, s=1.0, sail=1.0, col=(90, 70, 50), sailcol=(230, 226, 214), t=0.0):
    bob = 4 * s * math.sin(t * 2 + x * 0.01)
    y = y + bob
    c.poly([(x - 120 * s, y - 30 * s), (x + 120 * s, y - 30 * s), (x + 90 * s, y + 10 * s), (x - 100 * s, y + 10 * s)], col, INK, 3)
    c.line([(x + 120 * s, y - 30 * s), (x + 150 * s, y - 70 * s)], col, 8 * s)
    c.line([(x, y - 30 * s), (x, y - 190 * s)], (80, 60, 40), 6 * s)
    bulge = 30 * s * sail
    c.poly([(x - 70 * s, y - 180 * s), (x + 70 * s, y - 180 * s), (x + 70 * s + bulge, y - 110 * s), (x + 70 * s, y - 50 * s),
            (x - 70 * s, y - 50 * s), (x - 70 * s + bulge, y - 110 * s)] if sail > 0.2 else
           [(x - 60 * s, y - 180 * s), (x + 60 * s, y - 180 * s), (x + 50 * s, y - 70 * s), (x - 50 * s, y - 70 * s)], sailcol, INK, 2)
    c.line([(x - 70 * s, y - 120 * s), (x + 70 * s, y - 120 * s)], (150, 70, 60, 200), 5 * s)


def lion_gate(c, x, y, s=1.0):
    c.rect(x - 260 * s, y - 380 * s, x + 260 * s, y, STONE, 0, INK, 4)
    for k in range(6):
        c.line([(x - 260 * s, y - 380 * s + k * 63 * s), (x + 260 * s, y - 380 * s + k * 63 * s)], (176, 168, 154), 3)
    c.rect(x - 100 * s, y - 250 * s, x + 100 * s, y, (60, 70, 84), 0, INK, 4)
    c.rect(x - 130 * s, y - 280 * s, x + 130 * s, y - 250 * s, (190, 182, 166), 0, INK, 4)  # lintel
    c.poly([(x - 120 * s, y - 280 * s), (x + 120 * s, y - 280 * s), (x, y - 420 * s)], (196, 188, 172), INK, 4)
    c.rect(x - 10 * s, y - 400 * s, x + 10 * s, y - 290 * s, (170, 162, 148))  # column
    for side in (-1, 1):  # two stylised lions facing the column
        lx = x + side * 55 * s
        c.ell(lx, y - 330 * s, 32 * s, 40 * s, fill=(176, 168, 154), outline=INK, w=3)
        c.ell(lx + side * 8 * s, y - 386 * s, 20 * s, 20 * s, fill=(176, 168, 154), outline=INK, w=3)


def troy(c, x, y, s=1.0, fire=0.0, t=0.0):
    c.rect(x - 520 * s, y - 220 * s, x + 520 * s, y, STONE, 0, INK, 4)
    for k in range(-5, 6):
        c.rect(x + k * 95 * s - 30 * s, y - 250 * s, x + k * 95 * s + 30 * s, y - 220 * s, STONE, 0, INK, 3)
    for tx in (-420, 0, 420):
        c.rect(x + tx * s - 70 * s, y - 360 * s, x + tx * s + 70 * s, y, (196, 190, 178), 0, INK, 4)
        c.rect(x + tx * s - 18 * s, y - 300 * s, x + tx * s + 18 * s, y - 260 * s, (60, 70, 84))
    c.rect(x - 70 * s, y - 160 * s, x + 70 * s, y, (90, 70, 50), 0, INK, 4)  # Scaean gate
    if fire > 0:
        for k in range(28):
            fx = x - 500 * s + k * 37 * s
            fh = (80 + 60 * math.sin(t * 9 + k * 1.7)) * s * fire
            c.poly([(fx - 22 * s, y - 220 * s), (fx + 22 * s, y - 220 * s), (fx + 5 * s * math.sin(t * 7 + k), y - 220 * s - fh)], (240, 140, 60, 220))
            c.poly([(fx - 10 * s, y - 220 * s), (fx + 10 * s, y - 220 * s), (fx, y - 220 * s - fh * 0.6)], (255, 214, 120, 230))


def horse(c, x, y, s=1.0):
    wood = (150, 110, 70)
    c.rect(x - 160 * s, y - 230 * s, x + 120 * s, y - 120 * s, wood, 30 * s, INK, 4)
    c.poly([(x + 90 * s, y - 220 * s), (x + 150 * s, y - 360 * s), (x + 200 * s, y - 340 * s), (x + 140 * s, y - 200 * s)], wood, INK, 4)
    c.poly([(x + 150 * s, y - 360 * s), (x + 240 * s, y - 330 * s), (x + 220 * s, y - 300 * s), (x + 170 * s, y - 310 * s)], wood, INK, 4)
    for lx in (-130, -60, 40, 100):
        c.rect(x + lx * s, y - 130 * s, x + lx * s + 22 * s, y - 30 * s, wood, 4, INK, 3)
    c.rect(x - 180 * s, y - 34 * s, x + 150 * s, y, (110, 80, 50), 6, INK, 3)
    for wx in (-140, 110):
        c.ell(x + wx * s, y + 6 * s, 26 * s, 26 * s, fill=(90, 70, 50), outline=INK, w=3)


# ------------------------------------------------------------------ scenes
def headline(c, t, t0, s1, s2=None, y=150, col=PALE, col2=GOLD, size=86):
    p = eout(seg(t, t0, t0 + 0.5))
    if p <= 0:
        return
    c.text(W / 2, y + 30 * (1 - p), s1, size, col + (int(255 * p),), stroke=3)
    if s2:
        q = eout(seg(t, t0 + 0.15, t0 + 0.65))
        c.text(W / 2, y + size + 20 + 30 * (1 - q), s2, int(size * 0.62), col2 + (int(255 * q),), 700, stroke=3)


def sc0(t):
    if t < 4.2:  # stormy sea, a lone ship trying to get home
        c = C((120, 140, 160))
        grad(c, (110, 130, 150), (170, 190, 205), 0, 560)
        clouds(c, t, 160, (90, 108, 126, 230), 6, 40)
        sea(c, t, 560, (82, 110, 134), (40, 62, 84))
        ship(c, 1100 - t * 30, 700, 0.9, 1.0, t=t * 2)
        for k in range(60):  # rain
            rx = (k * 97 + t * 900) % W
            ry = (k * 53 + t * 1400) % H
            c.line([(rx, ry), (rx - 14, ry + 50)], (220, 230, 240, 90), 2)
        headline(c, t, 0.4, "BEFORE ODYSSEUS COULD GET HOME…", None, 150, PALE, GOLD, 64)
        return c
    c = C()  # reveal: low angle on a hill, cloak in the wind
    grad(c, (176, 198, 214), SKY1, 0, 760)
    clouds(c, t, 200)
    c.poly([(0, 1080), (0, 860), (700, 760), (1300, 780), (1920, 880), (1920, 1080)], (150, 166, 150), INK, 4)
    agamemnon(c, 960, 960, 1.35, t)
    p = eout(seg(t, LS[0] + 3.9, LS[0] + 4.4))
    c.text(W / 2 - 520, 360 + 30 * (1 - p), "AGAMEMNON", 110, PALE + (int(255 * p),), stroke=4)
    c.text(W / 2 - 520, 470 + 30 * (1 - p), "KING OF KINGS", 54, GOLD + (int(255 * p),), 700, stroke=3)
    return c


def sc1(t):
    c = C()
    grad(c, (186, 204, 218), SKY1, 0, 700)
    clouds(c, t, 160)
    c.poly([(0, 1080), (0, 760), (900, 640), (1920, 760), (1920, 1080)], (170, 170, 150), INK, 4)
    lion_gate(c, 1250, 860, 1.0)
    for k in range(6):  # gold glints: "richest city"
        q = (t * 1.4 + k * 0.37) % 1
        gx, gy = 1050 + k * 80, 520 + (k % 3) * 60
        c.ell(gx, gy, 10 * (1 - q), 10 * (1 - q), fill=GOLD + (int(255 * (1 - q)),))
    agamemnon(c, 560, 1000, 1.1, t)
    if t > LS[1] + 2.6:
        q = eout(seg(t, LS[1] + 2.6, LS[1] + 3.1))
        person(c, 330 - 80 * (1 - q), 1000, 0.95, body=(130, 150, 172), hat="crest", alpha=int(255 * q))
        c.text(330, 600, "MENELAUS", 40, PALE + (int(255 * q),), 700, stroke=3)
    headline(c, t, LS[1] + 0.1, "KING OF MYCENAE", "THE RICHEST CITY IN GREECE", 150)
    return c


def sc2(t):
    c = C()
    grad(c, (186, 204, 218), SKY1, 0, 600)
    clouds(c, t, 150)
    sea(c, t, 600)
    if t < LS[2] + 3.0:  # Paris sails away with Helen toward Troy
        u = seg(t, LS[2], LS[2] + 3.0)
        c.poly([(1500, 600), (1920, 560), (1920, 600)], (170, 160, 140))
        c.text(1740, 520, "TROY", 40, PALE, 800, stroke=3)
        sx = 500 + 800 * ease(u)
        ship(c, sx, 760, 1.0, 1.0, t=t)
        person(c, sx - 40, 700, 0.35, body=(170, 80, 70), hat="phrygian")
        person(c, sx + 30, 700, 0.35, body=(220, 216, 230), veil=(240, 236, 244))
        headline(c, t, LS[2] + 0.1, "PARIS TOOK HELEN", "MENELAUS'S WIFE", 150)
        return c
    # the fleet multiplies
    u = seg(t, LS[2] + 3.0, LS[3] - 0.5)
    n = int(4 + 60 * ease(u))
    r = np.random.default_rng(3)
    for k in range(n):
        x, y = r.uniform(80, 1840), r.uniform(640, 1040)
        ship(c, x, y, 0.25 + (y - 640) / 900, 1.0, t=t + k)
    agamemnon(c, 380, 1080, 0.9, t, point=ease(seg(t, LS[2] + 3.2, LS[2] + 3.8)))
    cnt = int(1000 * ease(u))
    c.text(W / 2 + 200, 170, f"{cnt:,}+ SHIPS", 92, GOLD + (255,), stroke=4)
    c.text(W / 2 + 200, 270, "THE KINGS OF GREECE GO TO WAR", 44, PALE + (255,), 700, stroke=3)
    return c


def sc3(t):
    dark = ease(seg(t, LS[3] + 3.2, LS[3] + 4.2)) * (1 - ease(seg(t, LS[3] + 5.6, LS[4])))
    c = C()
    top = tuple(int(a + (b - a) * dark) for a, b in zip((196, 210, 220), (120, 96, 100)))
    grad(c, top, SKY1, 0, 640)
    sea(c, t, 640, calm=True)
    wind = ease(seg(t, LS[3] + 5.3, LS[3] + 6.0))
    for k in range(9):
        ship(c, 120 + k * 210, 800 + (k % 2) * 90, 0.55, sail=0.1 + 0.9 * wind, t=t * (0.2 + wind))
    if dark > 0:  # altar on the cliff: a small silhouette, nothing graphic
        c.poly([(1400, 640), (1920, 520), (1920, 640)], (120, 110, 100, int(255 * dark)))
        c.rect(1620, 470, 1700, 530, (90, 80, 76, int(255 * dark)))
        person(c, 1660, 470, 0.28, body=(240, 236, 240), veil=(250, 248, 250), alpha=int(255 * dark))
    if wind > 0:
        for k in range(14):
            yy = 300 + k * 40
            xx = (t * 900 + k * 260) % (W + 400) - 200
            c.line([(xx, yy), (xx + 160, yy - 10)], (240, 246, 250, int(160 * wind)), 4)
    headline(c, t, LS[3] + 0.1, "AT AULIS, THE WINDS DIED", None, 150, PALE, GOLD, 74)
    if t > LS[3] + 3.4:
        q = eout(seg(t, LS[3] + 3.4, LS[3] + 3.9))
        c.text(W / 2, 270, "HE SACRIFICED HIS OWN DAUGHTER", 50, (230, 200, 196, int(255 * q)), 700, stroke=3)
    return c


def sc4(t):
    c = C()
    grad(c, (190, 206, 218), SKY1, 0, 700)
    c.rect(0, 700, W, H, SAND)
    troy(c, 1300, 760, 0.9)
    for k in range(7):  # Greek tents
        tx = 120 + k * 150
        c.poly([(tx - 60, 900 + (k % 2) * 60), (tx + 60, 900 + (k % 2) * 60), (tx, 810 + (k % 2) * 60)], (226, 220, 204), INK, 3)
    yr = 1 + int(9 * ease(seg(t, LS[4], LS[4] + 2.2)))
    c.text(W / 2, 150, f"YEAR {yr}", 96, PALE + (255,), stroke=4)
    c.text(W / 2, 250, "THE SIEGE OF TROY", 46, GOLD + (255,), 700, stroke=3)
    if t > LS[4] + 2.4:  # the quarrel with Achilles
        q = eout(seg(t, LS[4] + 2.4, LS[4] + 2.9))
        c.rect(0, 0, W, H, (20, 30, 44, int(110 * q)))
        agamemnon(c, 520, 1060, 0.95, t, angry=q, point=q)
        c.poly([(1180, 1060), (1560, 1060), (1370, 720)], (226, 220, 204, int(255 * q)), INK + (int(255 * q),), 4)
        person(c, 1370, 1060, 0.8, body=(110, 130, 150), hat="crest", cross=True, alpha=int(255 * q))
        c.text(1370, 640, "ACHILLES REFUSES TO FIGHT", 40, PALE + (int(255 * q),), 700, stroke=3)
        if t > LS[4] + 4.1:
            r = eout(seg(t, LS[4] + 4.1, LS[4] + 4.5))
            c.text(520, 560, "PRIDE", 70, (230, 120, 100, int(255 * r)), 900, stroke=4)
    return c


def sc5(t):
    c = C()
    fire = ease(seg(t, LS[5], LS[5] + 0.8))
    if t < LS[5] + 1.9:
        grad(c, (150, 120, 120), (200, 170, 150), 0, 700)
        c.rect(0, 700, W, H, SAND)
        troy(c, 1150, 780, 0.95, fire, t)
        horse(c, 600, 900, 0.9)
        headline(c, t, LS[5] + 0.1, "TROY FELL", None, 150, PALE, GOLD, 100)
        return c
    grad(c, (196, 206, 214), SKY1, 0, 620)  # sailing home a conqueror
    clouds(c, t, 150)
    sea(c, t, 620)
    sx = 400 + (t - LS[5] - 1.9) * 120
    ship(c, sx, 860, 1.6, 1.0, t=t)
    agamemnon(c, sx - 40, 800, 0.42, t, crown=True)
    c.text(W / 2 + 250, 170, "HOME, A CONQUEROR", 82, GOLD + (255,), stroke=4)
    return c


def sc6(t):
    c = C((26, 34, 50))
    out = ease(seg(t, LS[6] + 5.6, LS[6] + 6.3))
    # palace hall with columns, a lit doorway
    for k in range(6):
        cx = 180 + k * 312
        c.rect(cx - 36, 160, cx + 36, 940, (60, 72, 92), 0, (16, 22, 34), 4)
    c.rect(0, 940, W, H, (44, 54, 70))
    c.rect(840, 300, 1080, 940, (220, 180, 120))
    person(c, 960, 940, 1.15, body=(30, 30, 40), head=(30, 30, 40), veil=(30, 30, 40))  # Clytemnestra in the doorway
    c.poly([(960, 940), (1100, 940), (1600, 1080), (900, 1080)], (20, 24, 34, 180))  # her long shadow
    if t > LS[6] + 3.4:
        q = eout(seg(t, LS[6] + 3.4, LS[6] + 3.9))
        person(c, 1420, 940, 1.0, body=(14, 18, 28), head=(14, 18, 28), alpha=int(220 * q))  # Aegisthus behind a column
        c.text(1420, 520, "AEGISTHUS", 36, (200, 200, 210, int(255 * q)), 700, stroke=3)
    agamemnon(c, 420 + 100 * ease(seg(t, LS[6], LS[6] + 4)), 1000, 0.95, t, crown=True)
    c.text(960, 240, "CLYTEMNESTRA", 40, (230, 200, 160, 255), 700, stroke=3)
    if out > 0:
        c.rect(0, 0, W, H, (6, 8, 12, int(255 * out)))
        if t > LS[6] + 6.0:  # the crown falls and rolls
            u = seg(t, LS[6] + 6.0, LS[6] + 7.2)
            cx, cy = 900 + 300 * u, 640 + 260 * min(1, u * 2.2) - 60 * abs(math.sin(u * 9)) * (1 - u)
            for k in range(5):
                xx = cx - 50 + k * 25
                c.poly([(xx - 12, cy), (xx + 12, cy), (xx, cy - 36)], GOLD)
            c.rect(cx - 62, cy, cx + 62, cy + 20, GOLD)
    return c


def sc7(t):
    c = C((22, 32, 48))
    grad(c, (24, 34, 52), (54, 74, 96), 0, H)
    for k in range(12):  # drifting mist
        x = (k * 220 + t * 30) % (W + 400) - 200
        c.ell(x, 900 + (k % 3) * 40, 260, 60, fill=(150, 180, 200, 40))
    agamemnon(c, 1250, 980, 1.15, t, ghost=True)
    person(c, 520, 1000, 1.0, body=(110, 120, 120), hat="pilos")
    c.text(520, 560, "ODYSSEUS", 40, PALE + (255,), 700, stroke=3)
    if t > LS[7] + 4.1:
        q = eout(seg(t, LS[7] + 4.1, LS[7] + 4.6))
        c.text(W / 2, 200, "“TRUST NO ONE.”", 110, (210, 232, 246, int(255 * q)), 800, stroke=4)
    else:
        headline(c, t, LS[7] + 0.1, "HIS GHOST WARNS ODYSSEUS", None, 160, PALE, GOLD, 64)
    return c


def sc8(t):
    c = C((30, 44, 62))
    grad(c, (60, 84, 108), (150, 176, 196), 0, 620)
    sea(c, t, 620, (90, 120, 146), (36, 54, 74))
    # the dark mirror: the king above, his reflection below the waterline
    agamemnon(c, 1380, 620, 0.9, t, crown=True)
    refl = c.im.crop((0, int(160 * SS), W * SS, int(620 * SS))).transpose(Image.FLIP_TOP_BOTTOM)
    refl = Image.blend(refl, Image.new("RGB", refl.size, (36, 54, 74)), 0.6)
    c.im.paste(refl, (0, int(620 * SS)))
    p = eout(seg(t, LS[8], LS[8] + 0.6))
    c.text(560, 300, "AGAMEMNON", 110, PALE + (int(255 * p),), stroke=4)
    q = eout(seg(t, LS[8] + 1.4, LS[8] + 2.0))
    c.text(560, 410, "in Christopher Nolan's THE ODYSSEY", 42, GOLD + (int(255 * q),), 700, stroke=3)
    r = eout(seg(t, LS[8] + 2.0, LS[8] + 2.6))
    c.text(560, 475, "played by Benny Safdie", 36, PALE + (int(255 * r),), 600, stroke=3)
    return c


SCENES = [(0.0, sc0), (LS[1] - 0.2, sc1), (LS[2] - 0.2, sc2), (LS[3] - 0.2, sc3), (LS[4] - 0.2, sc4),
          (LS[5] - 0.2, sc5), (LS[6] - 0.2, sc6), (LS[7] - 0.2, sc7), (LS[8] - 0.2, sc8)]
XF = 0.35


def zoomed(img, z):
    if z <= 1.0001:
        return img
    cw, ch = int(W / z), int(H / z)
    return img.crop(((W - cw) // 2, (H - ch) // 2, (W + cw) // 2, (H + ch) // 2)).resize((W, H), Image.BILINEAR)


def shot(i, t):
    s0 = SCENES[i][0]
    s1 = SCENES[i + 1][0] if i + 1 < len(SCENES) else DUR
    return zoomed(SCENES[i][1](t).out(), 1 + 0.05 * seg(t, s0, s1))


def scene(t):
    i = max(k for k, (s, _) in enumerate(SCENES) if s <= t)
    im = shot(i, t)
    if i + 1 < len(SCENES) and t > SCENES[i + 1][0] - XF:
        im = Image.blend(im, shot(i + 1, t), (t - (SCENES[i + 1][0] - XF)) / XF)
    return im


# ------------------------------------------------------------------ subtitles
KEY = {"ODYSSEUS", "AGAMEMNON.", "AGAMEMNON", "MYCENAE,", "MENELAUS.", "HELEN,", "TROY", "TROY.", "SHIPS,", "AULIS,",
       "IPHIGENIA.", "ACHILLES'", "CLYTEMNESTRA,", "AEGISTHUS,", "GHOST", "NOLAN'S", "SAFDIE", "ODYSSEUS:", "ODYSSEUS'S", "FELL,", "MIRROR"}


def caps():
    out = []
    for m in TIM:
        words = m["text"].split()
        gs, g = [], []
        for w in words:
            g.append(w)
            if len(" ".join(g)) >= 26:
                gs.append(g)
                g = []
        if g:
            gs.append(g)
        tot = sum(len(" ".join(x)) + 2 for x in gs)
        tt = m["start"]
        for gr in gs:
            dt = (m["end"] - m["start"]) * (len(" ".join(gr)) + 2) / tot
            out.append((tt, tt + dt, gr))
            tt += dt
    return out


CAPS = caps()
SF = ImageFont.truetype(FONT, 50)
SF.set_variation_by_axes([800])


def subtitle(im, t):
    for a, b, words in CAPS:
        if a - 0.03 <= t < b + 0.1:
            d = ImageDraw.Draw(im)
            ups = [w.upper() for w in words]
            ws = [d.textlength(u + " ", font=SF) for u in ups]
            x = W / 2 - (sum(ws) - d.textlength(" ", font=SF)) / 2
            for u, wd in zip(ups, ws):
                d.text((x, 1000), u, font=SF, fill=GOLD if u in KEY else (250, 250, 252), anchor="lm", stroke_width=6,
                       stroke_fill=(18, 26, 38))
                x += wd
            return


_yy, _xx = np.mgrid[0:H, 0:W]
VIGN = (1 - 0.35 * np.clip(((_xx - W / 2) / (W * 0.7)) ** 2 + ((_yy - H / 2) / (H * 0.75)) ** 2, 0, 1))[..., None].astype(np.float32)


def frame(n):
    t = n / FPS
    im = scene(t)
    subtitle(im, t)
    a = np.asarray(im, np.float32) * VIGN
    a = a * 0.92 + np.array([150, 170, 190]) * 0.08          # soft pale-blue film wash
    a += np.random.default_rng(n).normal(0, 3, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    a *= min(1, t / 0.5) * min(1, (DUR - t) / 1.2)
    return np.clip(a, 0, 255).astype(np.uint8).tobytes()


if __name__ == "__main__":
    if "--stills" in sys.argv:
        for ts in [float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")]:
            Image.frombytes("RGB", (W, H), frame(int(ts * FPS))).save(f"still_{ts:05.1f}.png")
        sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", sys.argv[2], "-c:v", "libx264", "-preset", "slow",
                           "-crf", "22", "-maxrate", "9M", "-bufsize", "18M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", sys.argv[3]], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for buf in pool.imap(frame, range(int(DUR * FPS)), chunksize=4):
            ff.stdin.write(buf)
    ff.stdin.close()
    ff.wait()
