"""Tuğba Korkmaz · Konya real-estate ad: 2D flat stick-figure animation, 1080x1920, 30 fps, 30 s.

usage: python3 render.py timing.json mix.wav out.mp4 [--stills t1,t2,...]
"""
import json, math, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR, SS, VO = 1080, 1920, 30, 30.0, 2, 0.3
TIM = json.load(open(sys.argv[1]))
S = [m["start"] + VO for m in TIM]
E = [m["end"] + VO for m in TIM]
CREAM, NAVY, ORANGE, TEAL, SAND, GREEN, INK = (247, 241, 230), (31, 42, 68), (232, 116, 59), (42, 157, 143), (233, 216, 186), (106, 168, 79), (34, 34, 40)
F = "fonts/Montserrat.ttf"
_fc = {}


def font(size, w=800):
    k = (size, w)
    if k not in _fc:
        f = ImageFont.truetype(F, size * SS)
        f.set_variation_by_axes([w])
        _fc[k] = f
    return _fc[k]


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def eout(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def back(x):
    x = min(max(x, 0.0), 1.0)
    return 1 + 2.7 * (x - 1) ** 3 + 1.7 * (x - 1) ** 2


seg = lambda t, a, b: min(max((t - a) / (b - a), 0.0), 1.0)


class C:
    """Drawing canvas in 1080x1920 units, rendered at SS x."""

    def __init__(self, bg=CREAM):
        self.im = Image.new("RGB", (W * SS, H * SS), bg)
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def p(self, *xy):
        return [v * SS for v in xy]

    def rect(self, x0, y0, x1, y1, fill, r=0, outline=None, w=0):
        if r:
            self.d.rounded_rectangle(self.p(x0, y0, x1, y1), r * SS, fill=fill, outline=outline, width=w * SS)
        else:
            self.d.rectangle(self.p(x0, y0, x1, y1), fill=fill, outline=outline, width=w * SS)

    def circle(self, x, y, r, fill=None, outline=None, w=0):
        self.d.ellipse(self.p(x - r, y - r, x + r, y + r), fill=fill, outline=outline, width=int(w * SS))

    def line(self, pts, fill=INK, w=8):
        self.d.line([v * SS for pt in pts for v in pt], fill=fill, width=int(w * SS), joint="curve")
        for x, y in (pts[0], pts[-1]):
            self.circle(x, y, w / 2, fill=fill)

    def poly(self, pts, fill):
        self.d.polygon([v * SS for pt in pts for v in pt], fill=fill)

    def text(self, x, y, s, size, fill=NAVY, w=800, anchor="mm"):
        self.d.text((x * SS, y * SS), s, font=font(size, w), fill=fill, anchor=anchor)

    def tlen(self, s, size, w=800):
        return self.d.textlength(s, font=font(size, w)) / SS

    def out(self):
        return self.im.resize((W, H), Image.LANCZOS)


# ------------------------------------------------------------------ stick figures
def stick(c, x, y, s=1.0, t=0.0, walk=0.0, arms=None, hair=False, jacket=None, hat=None, wave=0.0, col=INK):
    """x,y = feet. walk: 0..1 amount of walking cycle. arms: (left_angle, right_angle) override (degrees from down)."""
    lw = 9 * s
    ph = t * 9
    sw = math.sin(ph) * 28 * walk
    hip = (x, y - 120 * s)
    neck = (x, y - 230 * s)
    head = (x, y - 278 * s)
    for k, a in ((-1, sw), (1, -sw)):  # legs
        ang = math.radians(a + 12 * k)
        c.line([hip, (hip[0] + math.sin(ang) * 120 * s, hip[1] + math.cos(ang) * 120 * s)], col, lw)
    c.line([hip, neck], col, lw)
    if jacket:
        c.poly([(neck[0] - 30 * s, neck[1] + 6 * s), (neck[0] + 30 * s, neck[1] + 6 * s), (hip[0] + 24 * s, hip[1] + 12 * s),
                (hip[0] - 24 * s, hip[1] + 12 * s)], jacket)
    al, ar = arms if arms else (20 - sw, -20 + sw)
    if wave:
        ar = -150 + 25 * math.sin(t * 14) * wave
    for a in (al, ar):
        ang = math.radians(a)
        sh = (neck[0], neck[1] + 18 * s)
        c.line([sh, (sh[0] + math.sin(ang) * 105 * s, sh[1] + math.cos(ang) * 105 * s)], col, lw)
    if hair:
        c.circle(head[0], head[1] - 6 * s, 50 * s, fill=(70, 46, 32))
        c.circle(head[0] + 34 * s, head[1] - 40 * s, 22 * s, fill=(70, 46, 32))  # bun
        c.rect(head[0] - 52 * s, head[1] - 6 * s, head[0] - 30 * s, head[1] + 48 * s, (70, 46, 32), r=10 * s)
        c.rect(head[0] + 30 * s, head[1] - 6 * s, head[0] + 52 * s, head[1] + 48 * s, (70, 46, 32), r=10 * s)
    c.circle(head[0], head[1], 42 * s, fill=CREAM, outline=col, w=lw)
    c.circle(head[0] - 14 * s, head[1] - 4 * s, 4.5 * s, fill=col)
    c.circle(head[0] + 14 * s, head[1] - 4 * s, 4.5 * s, fill=col)
    c.d.arc([v * SS for v in (head[0] - 16 * s, head[1] + 2 * s, head[0] + 16 * s, head[1] + 22 * s)], 20, 160, fill=col, width=int(5 * s * SS))
    if hat == "hard":
        c.d.chord([v * SS for v in (head[0] - 50 * s, head[1] - 74 * s, head[0] + 50 * s, head[1] + 6 * s)], 180, 360, fill=(245, 190, 40))
        c.rect(head[0] - 60 * s, head[1] - 36 * s, head[0] + 60 * s, head[1] - 26 * s, (225, 165, 20))


def tugba(c, x, y, s=1.0, t=0.0, **kw):
    stick(c, x, y, s, t, hair=True, jacket=ORANGE, **kw)


# ------------------------------------------------------------------ buildings & Konya
def factory(c, x, y, w, h, col=NAVY, bulge=0.0, t=0.0):
    b = bulge * (6 + 4 * math.sin(t * 20))
    c.poly([(x - b, y), (x - b, y - h), (x + w + b, y - h), (x + w + b, y)], col)
    n = 4
    for k in range(n):  # sawtooth roof
        x0 = x - b + k * (w + 2 * b) / n
        c.poly([(x0, y - h), (x0 + (w + 2 * b) / n, y - h), (x0 + (w + 2 * b) / n, y - h - 46)], col)
        c.poly([(x0 + (w + 2 * b) / n - 6, y - h - 38), (x0 + (w + 2 * b) / n - 6, y - h - 4), (x0 + 30, y - h - 4)], (120, 170, 200))
    c.rect(x + w * 0.75, y - h - 120, x + w * 0.75 + 34, y - h, col)
    for k in range(3):
        c.rect(x + 20 + k * (w - 40) / 3, y - h * 0.6, x + 20 + k * (w - 40) / 3 + (w - 40) / 3 - 18, y - h * 0.3, (120, 170, 200), r=6)
    c.rect(x + w * 0.4, y - 80, x + w * 0.6, y, (90, 100, 120))


def house(c, x, y, w, col=ORANGE, roof=(150, 60, 40)):
    h = w * 0.7
    c.rect(x, y - h, x + w, y, col)
    c.poly([(x - 20, y - h), (x + w / 2, y - h - w * 0.45), (x + w + 20, y - h)], roof)
    c.rect(x + w * 0.4, y - h * 0.55, x + w * 0.6, y, (110, 70, 50))
    c.rect(x + w * 0.1, y - h * 0.75, x + w * 0.3, y - h * 0.5, (190, 225, 240))
    c.rect(x + w * 0.7, y - h * 0.75, x + w * 0.9, y - h * 0.5, (190, 225, 240))


def apartment(c, x, y, w, h, col=TEAL):
    c.rect(x, y - h, x + w, y, col)
    for r in range(int(h // 70)):
        for k in range(int(w // 60)):
            c.rect(x + 16 + k * 60, y - h + 20 + r * 70, x + 50 + k * 60, y - h + 60 + r * 70, (215, 238, 240), r=4)


def tree(c, x, y, s=1.0):
    c.rect(x - 8 * s, y - 70 * s, x + 8 * s, y, (110, 80, 50))
    c.circle(x, y - 100 * s, 50 * s, fill=GREEN)
    c.circle(x - 30 * s, y - 70 * s, 34 * s, fill=(90, 150, 65))


def mevlana(c, x, y, s=1.0, col=(46, 139, 110)):
    """Stylised green fluted conical dome on a drum, with a slim minaret (Konya landmark)."""
    c.rect(x - 70 * s, y - 120 * s, x + 70 * s, y, (220, 205, 175))
    c.rect(x - 52 * s, y - 210 * s, x + 52 * s, y - 120 * s, col)
    for k in range(5):
        xx = x - 40 * s + k * 20 * s
        c.line([(xx, y - 205 * s), (xx, y - 125 * s)], (30, 110, 85), 4 * s)
    c.poly([(x - 56 * s, y - 210 * s), (x, y - 360 * s), (x + 56 * s, y - 210 * s)], col)
    c.line([(x, y - 360 * s), (x, y - 395 * s)], (200, 170, 60), 5 * s)
    c.rect(x + 120 * s, y - 330 * s, x + 140 * s, y, (220, 205, 175))
    c.poly([(x + 116 * s, y - 330 * s), (x + 130 * s, y - 390 * s), (x + 144 * s, y - 330 * s)], (200, 185, 150))
    c.rect(x + 112 * s, y - 250 * s, x + 148 * s, y - 238 * s, (200, 185, 150))


def pin(c, x, y, p, label, col=ORANGE):
    if p <= 0:
        return
    sc = back(p)
    yy = y - (1 - eout(p)) * 120
    c.circle(x, yy - 56 * sc, 30 * sc, fill=col)
    c.poly([(x - 24 * sc, yy - 44 * sc), (x + 24 * sc, yy - 44 * sc), (x, yy)], col)
    c.circle(x, yy - 56 * sc, 12 * sc, fill=(255, 255, 255))
    if label and p > 0.5:
        a = int(255 * ease((p - 0.5) * 2))
        tw = c.tlen(label, 34)
        c.rect(x - tw / 2 - 22, yy - 160, x + tw / 2 + 22, yy - 104, (*NAVY, a), r=28)
        c.text(x, yy - 132, label, 34, (255, 255, 255, a))


def bubble(c, x, y, w, h, p, tail=(0, 1)):
    if p <= 0:
        return 0
    sc = back(p)
    ww, hh = w * sc, h * sc
    c.rect(x - ww / 2, y - hh / 2, x + ww / 2, y + hh / 2, (255, 255, 255), r=34 * sc, outline=NAVY, w=5)
    c.poly([(x - 20 * sc + tail[0] * 30, y + hh / 2 - 3), (x + 20 * sc + tail[0] * 30, y + hh / 2 - 3), (x + tail[0] * 80, y + hh / 2 + 44 * sc)], (255, 255, 255))
    return sc


def ground(c, y=1420, col=SAND):
    c.rect(0, y, W, H, col)


def headline(c, t, t0, lines, y=330, size=92):
    for i, (s, col) in enumerate(lines):
        p = eout(seg(t, t0 + 0.1 * i, t0 + 0.1 * i + 0.35))
        if p <= 0:
            continue
        c.text(W / 2, y + i * (size + 18) + 40 * (1 - p), s, size, (*col, int(255 * p)))


# ------------------------------------------------------------------ scenes
def sc_factory(t):
    c = C()
    ground(c)
    zoom = 1 + 0.05 * t
    bulge = ease(seg(t, 0.6, 1.0)) * (1 - 0.3 * seg(t, 2.0, 3.0))
    factory(c, 330, 1420, 420 * zoom, 300 * zoom, NAVY, bulge, t)
    for k in range(6):  # boxes popping out of the too-small factory
        p = seg(t, 0.8 + k * 0.17, 1.2 + k * 0.17)
        if p > 0:
            bx = 300 + k * 85 + 30 * math.sin(k * 2.1)
            by = 1110 - 160 * math.sin(math.pi * p) - 20 * k * p
            c.rect(bx, by, bx + 70, by + 60, (205, 150, 90), r=6, outline=(150, 100, 60), w=3)
    stick(c, 200, 1500, 1.0, t, arms=(30, -150 + 10 * math.sin(t * 8)), hat="hard")
    p = seg(t, 1.2, 1.6)
    if bubble(c, 820, 830, 300, 230, p):  # dream: a bigger plot
        c.rect(700, 860, 940, 900, (200, 230, 170))
        factory(c, 720, 880, 200, 90, ORANGE)
    headline(c, t, 0.25, [("FABRİKAN", NAVY), ("DAR MI GELDİ?", ORANGE)])
    return c


def sc_family(t):
    c = C()
    ground(c)
    t0 = S[1]
    apartment(c, 330, 1420, 420, 560, (150, 160, 180))
    for k, (dx, s) in enumerate(((-120, 1.0), (0, 0.95), (110, 0.6))):  # family squeezed at the door
        stick(c, 540 + dx, 1520, s, t + k, arms=(25, -25))
    p = seg(t, t0 + 0.4, t0 + 0.8)
    if bubble(c, 540, 700, 360, 280, p):
        house(c, 450, 790, 180, ORANGE)
        tree(c, 680, 790, 0.8)
    headline(c, t, t0 + 0.05, [("YA DA", NAVY), ("YENİ BİR YUVA?", ORANGE)], y=300)
    return c


def sc_konya(t):
    """Panorama: Organize Sanayi -> Meram -> Selçuklu, Mevlana dome behind."""
    c = C((220, 236, 245))
    t0 = S[2]
    pan = -1100 * ease(seg(t, S[2] + 0.4, S[4] + 1.2))
    # far: sky, sun, Mevlana silhouette
    c.circle(860, 420, 90, fill=(255, 210, 120))
    mevlana(c, 1300 + pan * 0.35, 1210, 1.4)
    c.text(1300 + pan * 0.35, 1260, "KONYA", 46, (*NAVY, 160))
    ground(c, 1300, (225, 205, 165))
    c.rect(0, 1600, W, H, (210, 185, 140))
    ox = pan
    factory(c, 120 + ox, 1600, 330, 220, NAVY)
    factory(c, 520 + ox, 1600, 260, 170, (60, 74, 104))
    pin(c, 400 + ox, 1300, seg(t, S[2] + 0.15, S[2] + 0.55), "ORGANİZE SANAYİ")
    for k in range(5):
        tree(c, 1060 + k * 95 + ox, 1600, 0.9 + 0.2 * (k % 2))
    house(c, 1170 + ox, 1600, 230)
    pin(c, 1285 + ox, 1300, seg(t, S[3], S[3] + 0.4), "MERAM", GREEN)
    apartment(c, 1820 + ox, 1600, 200, 520)
    apartment(c, 2050 + ox, 1600, 170, 380, (60, 140, 160))
    c.rect(2260 + ox, 1600 - 650, 2300 + ox, 1600, (90, 100, 120))  # tower
    c.circle(2280 + ox, 1600 - 680, 50, fill=(90, 100, 120))
    pin(c, 1960 + ox, 1030, seg(t, S[4], S[4] + 0.4), "SELÇUKLU", TEAL)
    labels = [("DOĞRU PARSEL", S[2]), ("HUZURLU BİR EV", S[3]), ("DEĞERLİ BİR DAİRE", S[4])]
    cur = [l for l in labels if t >= l[1]]
    if cur:
        s, st = cur[-1]
        p = eout(seg(t, st, st + 0.3))
        c.text(W / 2, 330 + 30 * (1 - p), s, 86, (*NAVY, int(255 * p)))
    return c


def sc_phone(t):
    c = C()
    t0 = S[5]
    ground(c, 1500)
    stick(c, 300, 1560, 1.05, t, arms=(25, -165))
    ring = math.sin(t * 60) * 6 * (1 - seg(t, t0 + 1.0, t0 + 1.2))
    # big phone
    px, py = 640 + ring, 900
    c.rect(px - 130, py - 250, px + 130, py + 250, NAVY, r=40)
    c.rect(px - 110, py - 210, px + 110, py + 200, (230, 240, 250), r=16)
    c.circle(px, py - 60, 60, fill=ORANGE)
    c.text(px, py - 60, "TK", 46, (255, 255, 255))
    c.text(px, py + 40, "Tuğba Korkmaz", 24, NAVY)
    c.text(px, py + 85, "aranıyor…", 26, (*NAVY, 180), 600)
    c.circle(px, py + 160, 30, fill=(70, 180, 90))
    for k in range(3):  # ring waves
        q = ((t - t0) * 1.5 + k / 3) % 1
        c.d.arc([v * SS for v in (px + 120, py - 230 - 60 * q, px + 200 + 120 * q, py - 150 + 60 * q)], -60, 60,
                fill=(*ORANGE, int(255 * (1 - q))), width=8 * SS)
    headline(c, t, t0 + 0.05, [("HER ŞEY", NAVY), ("TEK BİR TELEFONLA", ORANGE), ("BAŞLAR", NAVY)], y=250, size=84)
    return c


def sc_listen(t):
    c = C()
    ground(c, 1500)
    c.rect(330, 1240, 750, 1270, (150, 100, 60))  # desk
    c.rect(350, 1270, 370, 1500, (150, 100, 60))
    c.rect(710, 1270, 730, 1500, (150, 100, 60))
    c.rect(480, 1205, 600, 1240, (255, 255, 255), outline=NAVY, w=3)  # notebook
    tugba(c, 830, 1500, 1.0, t, arms=(40, -60 + 8 * math.sin(t * 6)))
    stick(c, 230, 1500, 1.0, t, arms=(-40 + 15 * math.sin(t * 5), -70))
    items = [("İHTİYAÇ", S[7], "factory"), ("BÜTÇE", S[8], "coin"), ("HEDEF", S[9], "flag")]
    for k, (lab, st, icon) in enumerate(items):
        p = seg(t, st - 0.05, st + 0.3)
        x, y = 230 + k * 0, 820 - k * 0
        bx = 80 + k * 320
        sc = bubble(c, bx + 100, 860, 270, 250, p, tail=(-0.6 if k else 0, 1))
        if sc:
            cx, cy = bx + 100, 830
            if icon == "factory":
                factory(c, cx - 70, cy + 40, 140, 70, NAVY)
            elif icon == "coin":
                for j in range(3):
                    c.circle(cx - 10 + j * 12, cy + 10 - j * 16, 42, fill=(245, 190, 40), outline=(200, 140, 20), w=4)
                c.text(cx + 14, cy - 22, "₺", 48, (150, 100, 10))
            else:
                c.line([(cx - 30, cy + 60), (cx - 30, cy - 60)], NAVY, 8)
                c.poly([(cx - 30, cy - 60), (cx + 60, cy - 35), (cx - 30, cy - 10)], ORANGE)
            c.text(cx, cy + 90, lab, 34, NAVY)
    headline(c, t, S[6] + 0.05, [("ÖNCE", NAVY), ("SENİ DİNLER", ORANGE)], y=330)
    return c


def sc_journey(t):
    c = C()
    steps = [("Uygun seçenekler", S[10]), ("Yerinde gösterim", S[11]), ("Pazarlık", S[12] + 0.1), ("Tapu", S[12] + 1.2)]
    ys = [560, 790, 1020, 1250]
    x0 = 150
    prog = seg(t, S[10], S[12] + 1.6)
    c.line([(x0, ys[0]), (x0, ys[-1])], (215, 205, 185), 14)
    c.line([(x0, ys[0]), (x0, ys[0] + (ys[-1] - ys[0]) * ease(prog))], ORANGE, 14)
    for k, (lab, st) in enumerate(steps):
        p = seg(t, st, st + 0.35)
        on = p > 0
        c.circle(x0, ys[k], 40, fill=ORANGE if on else (215, 205, 185))
        c.text(x0, ys[k], str(k + 1), 38, (255, 255, 255))
        if not on:
            continue
        a = int(255 * eout(p))
        ix, iy = 330, ys[k]
        sc = back(p)
        c.rect(ix - 95 * sc, iy - 95 * sc, ix + 95 * sc, iy + 95 * sc, (255, 255, 255), r=30, outline=(*NAVY, a), w=4)
        if k == 0:  # property cards
            for j in range(3):
                c.rect(ix - 60 + j * 14, iy - 50 - j * 10, ix + 30 + j * 14, iy + 40 - j * 10, (255, 255, 255), r=8, outline=NAVY, w=3)
            house(c, ix - 22, iy + 10, 74, ORANGE)
        elif k == 1:  # agent shows a building
            apartment(c, ix - 50, iy + 70, 100, 140, TEAL)
        elif k == 2:  # handshake
            c.line([(ix - 75, iy + 35), (ix - 12, iy)], INK, 10)
            c.line([(ix + 75, iy + 35), (ix + 12, iy)], ORANGE, 10)
            c.circle(ix, iy, 24 * sc, fill=(240, 200, 160), outline=INK, w=4)
        else:  # title deed with stamp
            c.rect(ix - 55, iy - 75, ix + 55, iy + 70, (255, 255, 255), outline=NAVY, w=4)
            for j in range(4):
                c.line([(ix - 36, iy - 48 + j * 22), (ix + 36, iy - 48 + j * 22)], (180, 190, 205), 5)
            q = seg(t, st + 0.15, st + 0.3)
            if q > 0:
                c.circle(ix + 28, iy + 38, 34 * back(q), outline=(200, 40, 40), w=6)
                c.text(ix + 28, iy + 38, "TAPU", 15, (200, 40, 40))
        c.text(470 - 30 * (1 - eout(p)), iy, lab, 50, (*NAVY, a), 800, "lm")
    # Tuğba walks the client across the bottom
    c.rect(0, 1560, W, H, SAND)
    wx = 160 + 760 * ease(prog)
    walking = 1.0 if 0.02 < prog < 0.98 else 0.0
    tugba(c, wx + 60, 1580, 0.62, t, walk=walking)
    stick(c, wx - 50, 1580, 0.62, t + 0.3, walk=walking)
    headline(c, t, S[10] + 0.05, [("ADIM ADIM", NAVY), ("YANINDA", ORANGE)], y=250, size=88)
    return c


def sc_end(t):
    c = C(NAVY)
    t0 = S[13]
    # Konya skyline at golden hour: factory + houses + dome
    c.circle(540, 1080, 260, fill=(240, 150, 80))
    c.rect(0, 1300, W, H, (24, 33, 54))
    factory(c, 60, 1300, 300, 170, (18, 26, 44))
    mevlana(c, 540, 1300, 1.1, (18, 26, 44))
    apartment(c, 760, 1300, 150, 330, (18, 26, 44))
    house(c, 930, 1300, 120, (18, 26, 44), (18, 26, 44))
    p1 = eout(seg(t, t0, t0 + 0.4))
    c.text(W / 2, 330, "SANAYİDE DE", 72, (255, 255, 255, int(255 * p1)))
    c.text(W / 2, 420, "KONUTTA DA", 72, (*ORANGE, int(255 * p1)))
    p2 = eout(seg(t, S[14], S[14] + 0.4))
    c.text(W / 2, 560, "Konya'da doğru adres", 46, (230, 230, 240, int(255 * p2)), 600)
    p3 = back(seg(t, S[15] - 0.05, S[15] + 0.45))
    if p3 > 0:
        a = int(255 * min(1, p3))
        c.rect(110, 1500, 970, 1790, (*CREAM, a), r=40)
        c.circle(240, 1645, 80 * p3, fill=ORANGE)
        c.text(240, 1645, "TK", int(64 * max(p3, 0.1)), (255, 255, 255, a))
        c.text(350, 1600, "Tuğba Korkmaz", 54, (*NAVY, a), 800, "lm")
        c.text(350, 1662, "Gayrimenkul Danışmanı", 32, (*NAVY, a), 600, "lm")
        c.text(350, 1712, "Konya · Sanayi & Konut", 30, (*ORANGE, a), 700, "lm")
    return c


SCENES = [(0.0, sc_factory), (S[1] - 0.15, sc_family), (S[2] - 0.15, sc_konya), (S[5] - 0.15, sc_phone),
          (S[6] - 0.15, sc_listen), (S[10] - 0.15, sc_journey), (S[13] - 0.15, sc_end)]
XF = 0.25


def scene_img(t):
    i = max(k for k, (s, _) in enumerate(SCENES) if s <= t)
    im = SCENES[i][1](t).out()
    if i + 1 < len(SCENES) and t > SCENES[i + 1][0] - XF:  # quick slide transition
        u = eout((t - (SCENES[i + 1][0] - XF)) / XF)
        nxt = SCENES[i + 1][1](t).out()
        frame = Image.new("RGB", (W, H))
        frame.paste(im, (int(-W * u), 0))
        frame.paste(nxt, (int(W * (1 - u)), 0))
        im = frame
    return im


# ------------------------------------------------------------------ subtitles
KEY = {"KONYA'DA", "FABRİKANI", "ARSA", "YUVA", "ORGANİZE", "SANAYİ'DE", "MERAM'DA", "SELÇUKLU'DA", "TELEFONLA", "TUĞBA",
       "KORKMAZ", "DİNLER:", "İHTİYACINI,", "BÜTÇENİ,", "HEDEFİNİ.", "YERİNDE", "TAPUYA", "SANAYİDE", "KONUTTA", "KORKMAZ.", "ADRES:"}


def tr_upper(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


def syl(w):
    return max(1, sum(ch in "aeıioöuüAEIİOÖUÜ" for ch in w))


def caps():
    out = []
    for m in TIM:
        words = m["text"].split()
        gs, g = [], []
        for w in words:
            g.append(w)
            if len(" ".join(g)) >= 16 or w.endswith((",", ".", ":", "?")):
                gs.append(g)
                g = []
        if g:
            gs.append(g)
        tot = sum(sum(syl(w) for w in gr) + 0.5 for gr in gs)
        t = m["start"] + VO
        for gr in gs:
            dt = (m["end"] - m["start"]) * (sum(syl(w) for w in gr) + 0.5) / tot
            out.append((t, t + dt, gr))
            t += dt
    return out


CAPS = caps()


def subtitle(im, t):
    if t > S[13] - 0.2:   # end card carries its own text
        return
    for a, b, words in CAPS:
        if a - 0.03 <= t < b + 0.1:
            d = ImageDraw.Draw(im)
            f = ImageFont.truetype(F, 62)
            f.set_variation_by_axes([800])
            ups = [tr_upper(w) for w in words]
            ws = [d.textlength(u + " ", font=f) for u in ups]
            x = W / 2 - (sum(ws) - d.textlength(" ", font=f)) / 2
            for u, wd in zip(ups, ws):
                d.text((x, 1700), u, font=f, fill=ORANGE if u in KEY else (255, 255, 255), anchor="lm",
                       stroke_width=8, stroke_fill=NAVY)
                x += wd
            return


def frame(n):
    t = n / FPS
    im = scene_img(t)
    subtitle(im, t)
    a = np.asarray(im, np.float32)
    a *= min(1, t / 0.2) * min(1, (DUR - t) / 0.5)
    return np.clip(a, 0, 255).astype(np.uint8).tobytes()


if __name__ == "__main__":
    if "--stills" in sys.argv:
        for ts in [float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")]:
            Image.frombytes("RGB", (W, H), frame(int(ts * FPS))).save(f"still_{ts:05.1f}.png")
        sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", sys.argv[2], "-c:v", "libx264", "-preset", "slow",
                           "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", sys.argv[3]], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for buf in pool.imap(frame, range(int(DUR * FPS)), chunksize=4):
            ff.stdin.write(buf)
    ff.stdin.close()
    ff.wait()
