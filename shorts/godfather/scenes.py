"""Every illustrated shot of the Short. Each shot returns layers (bg -> fg) for parallax camera moves.

Shots are drawn at 1296x2304 (1.2x the 1080x1920 output) so slow zooms stay sharp.
"""
import math, random
import numpy as np
import skia
from ink import (smooth, poly, xf, fill, stroke, ink, taper, hatch, shade, light, glow, radial, linear,
                 rgba, paint, col, new_surface, to_array)
from characters import (vito_head, tuxedo, michael_head, suit, marine_uniform, generic_head, draw_rose, TURN)

W, H = 1296, 2304
M = skia.BlendMode.kMultiply
SCR = skia.BlendMode.kScreen
ADD = skia.BlendMode.kPlus

class Layer:
    def __init__(self, depth=1.0, blur=0.0):
        self.surface = new_surface(W, H)
        self.c = self.surface.getCanvas()
        self.depth = depth
        self.blur = blur

    def done(self):
        arr = to_array(self.surface)
        if self.blur:
            import PIL.Image, PIL.ImageFilter
            im = PIL.Image.fromarray((arr * 255).astype(np.uint8), 'RGBA')
            im = im.filter(PIL.ImageFilter.GaussianBlur(self.blur))
            arr = np.asarray(im).astype(np.float32) / 255.0
        return arr, self.depth

# ------------------------------------------------------------------ props
def rect(x, y, w, h):
    return poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])

def wood_wall(c, x0, y0, x1, y1, base='#2b170c', seed=1):
    fill(c, rect(x0, y0, x1 - x0, y1 - y0), base)
    rnd = random.Random(seed)
    pw = 150
    x = x0
    while x < x1:  # panels
        p = rect(x + 10, y0 + 40, pw - 20, (y1 - y0) - 80)
        fill(c, p, '#3a2112', 160)
        stroke(c, p, 3, '#120904', 220, wobble=0.8, seed=rnd.randint(0, 99))
        for k in range(6):
            yy = y0 + rnd.uniform(0.05, 0.95) * (y1 - y0)
            stroke(c, smooth([(x + 16, yy), (x + pw / 2, yy + rnd.uniform(-8, 8)), (x + pw - 16, yy + rnd.uniform(-6, 6))], False), 1.2, '#1a0d06', 110)
        x += pw

def blinds_window(c, x, y, w, h, bright='#ffd38a', slats=14, open_=0.55, seed=2):
    """Venetian-blind window glowing from outside."""
    fill(c, rect(x, y, w, h), bright)
    glow(c, x + w / 2, y + h / 2, max(w, h) * 0.8, 'gold', 140)
    sh = h / slats
    for i in range(slats):
        yy = y + i * sh
        fill(c, rect(x, yy + sh * open_, w, sh * (1 - open_)), '#5a3517')
        stroke(c, smooth([(x, yy + sh * open_), (x + w, yy + sh * open_)], False), 2, '#2a1406', 220)
    for k in range(3):  # cords
        stroke(c, smooth([(x + w * (0.2 + 0.3 * k), y), (x + w * (0.2 + 0.3 * k), y + h)], False), 2, '#3a2010', 200)
    frame = rect(x - 14, y - 14, w + 28, h + 28)
    stroke(c, frame, 28, '#1c0e06')
    ink(c, frame, 4, seed=seed)

def light_shafts(c, x, y, w, h, angle_dx=500, angle_dy=1300, slats=10, a=45, color='gold', open_=0.55):
    """Volumetric slatted beams falling from a window into the room."""
    sh = h / slats
    for i in range(slats):
        y0 = y + i * sh
        y1 = y0 + sh * open_
        p = poly([(x, y0), (x + w, y0), (x + w + angle_dx, y0 + angle_dy), (x + angle_dx, y1 + angle_dy), (x, y1)])
        sp = linear((x, y0), (x + angle_dx, y0 + angle_dy), [rgba(color, a), rgba(color, 0)])
        c.drawPath(p, paint(shader=sp, blend=SCR))

def dust(c, cx, cy, r, n=90, seed=3, a=150):
    rnd = random.Random(seed)
    for _ in range(n):
        ang = rnd.uniform(0, 2 * math.pi); d = r * math.sqrt(rnd.random())
        c.drawCircle(cx + d * math.cos(ang), cy + d * math.sin(ang), rnd.uniform(0.8, 2.6), paint('#ffe2a8', rnd.randint(a // 3, a)))

def bokeh(c, n, region, colors=('gold', 'amber', '#fff0c8'), rmin=14, rmax=48, a=(40, 120), seed=4):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = region
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        r = rnd.uniform(rmin, rmax)
        cc = rnd.choice(colors)
        c.drawCircle(x, y, r, paint(cc, rnd.randint(*a), blend=SCR))
        p = paint(cc, 90); p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(1.5)
        c.drawCircle(x, y, r, p)

def hand(c, x, y, s, rot=0.0, flip=False, ring=False, curl=0.6, seed=5, tone='skin'):
    """Simple ink-drawn hand (back of hand facing camera), wrist at (x,y), fingers point along rot."""
    f = -1 if flip else 1
    def T(pts):
        return xf([(f * px, py) for px, py in pts], x, y, s, rot=rot)
    palm = smooth(T([(-34, 0), (-40, -50), (-36, -96), (36, -96), (42, -50), (34, 0)]))
    fill(c, palm, tone); shade(c, palm, 'skin_deep', 90, blur=6 * s)
    fingers = []
    for i, fx in enumerate((-27, -9, 9, 27)):
        ln = (62, 72, 68, 54)[i] * (1 - 0.45 * curl)
        fp = smooth(T([(fx - 9, -92), (fx - 10, -92 - ln), (fx, -98 - ln - 6), (fx + 10, -92 - ln), (fx + 9, -92)]))
        fill(c, fp, tone); shade(c, fp, 'skin_deep', 70, blur=3 * s)
        ink(c, fp, 3 * s, seed=seed + i)
        for k in (0.4, 0.75):
            stroke(c, smooth(T([(fx - 6, -92 - ln * k), (fx + 6, -92 - ln * k)]), False), 1.4 * s, a=140)
        fingers.append(fp)
    th = smooth(T([(-34, -30), (-62, -58), (-78, -92), (-66, -100), (-46, -78), (-30, -60)]))
    fill(c, th, tone); shade(c, th, 'skin_deep', 80, blur=3 * s); ink(c, th, 3 * s, seed=seed + 9)
    light(c, smooth(T([(-20, -20), (20, -20), (24, -80), (-24, -80)])), 'gold', 60, blur=10 * s)
    ink(c, palm, 3.4 * s, seed=seed + 7)
    if ring:
        rr = smooth(T([(1, -110), (17, -110), (17, -122), (1, -122)]))
        fill(c, rr, '#d9a441'); ink(c, rr, 2 * s, seed=seed)
        glow(c, *T([(9, -116)])[0], 18 * s, 'gold', 170)

def cat(c, x, y, s, seed=7):
    """Grey tabby curled in the Don's arms."""
    body = smooth(xf([(-130, 10), (-110, -50), (-30, -78), (70, -70), (130, -30), (130, 30), (40, 60), (-80, 56)], x, y, s))
    fill(c, body, '#6d655c')
    fill(c, body, None, shader=linear((x, y - 80 * s), (x, y + 60 * s), [rgba('#9b9286', 255), rgba('#3c3530', 255)]))
    for k in range(9):
        xx = -100 + k * 26
        taper(c, xf([(xx, -60), (xx + 6, -20), (xx - 2, 20)], x, y, s), 6 * s, 2 * s, '#2b2520', 190)
    hd = smooth(xf([(90, -60), (106, -112), (124, -92), (150, -96), (172, -116), (178, -66), (170, -26), (136, -10), (100, -24)], x, y, s))
    fill(c, hd, '#857c71'); shade(c, hd, '#000000', 60, blur=8 * s)
    for k in range(3):
        taper(c, xf([(124 + k * 12, -96), (128 + k * 12, -78)], x, y, s), 4 * s, 1.5 * s, '#2b2520')
    for ex in (124, 156):
        e = smooth(xf([(ex - 9, -64), (ex, -70), (ex + 9, -64), (ex, -59)], x, y, s))
        fill(c, e, '#c9a43c'); stroke(c, smooth(xf([(ex, -69), (ex, -60)], x, y, s), False), 2.4 * s)
        ink(c, e, 1.6 * s, seed=seed)
    fill(c, smooth(xf([(136, -46), (144, -46), (140, -40)], x, y, s)), '#3a2420')
    for side in (-1, 1):
        for k in range(2):
            stroke(c, smooth(xf([(140 + side * 14, -42 + k * 5), (140 + side * 48, -48 + k * 9)], x, y, s), False), 1.2 * s, '#e8dccb', 170)
    ink(c, hd, 3.4 * s, seed=seed + 1)
    ink(c, body, 4 * s, seed=seed + 2)

def leather_chair(c, cx, top, s, color='#3a1a10'):
    back = smooth(xf([(-190, 40), (-170, -40), (0, -70), (170, -40), (190, 40), (200, 900), (-200, 900)], cx, top, s))
    fill(c, back, color)
    fill(c, back, None, shader=radial(cx - 60 * s, top + 40 * s, 260 * s, [rgba('#7a3a20', 200), rgba(color, 0)]))
    for k in range(-2, 3):  # tufting
        for j in range(4):
            c.drawCircle(cx + k * 64 * s, top + (20 + j * 70) * s, 5 * s, paint('#1a0a05', 200))
    ink(c, back, 6 * s)

def desk(c, y, s=1.0, lamp=True, seed=8):
    top = poly([(-200, y), (W + 200, y), (W + 200, y + 60 * s), (-200, y + 60 * s)])
    fill(c, top, '#3b200f')
    fill(c, top, None, shader=linear((0, y), (0, y + 60 * s), [rgba('#8a5a2e', 255), rgba('#3b200f', 255)]))
    front = rect(-200, y + 60 * s, W + 400, H)
    fill(c, front, '#1d0f07')
    for k in range(6):
        stroke(c, smooth([(-100, y + (90 + k * 60) * s), (W / 2, y + (96 + k * 60) * s), (W + 100, y + (88 + k * 60) * s)], False), 2, '#0d0603', 160)
    ink(c, top, 5, seed=seed)

def desk_lamp(c, x, y, s=1.0, on=True):
    shade_p = smooth(xf([(-90, 0), (-60, -80), (60, -80), (90, 0)], x, y, s))
    stem = rect(x - 6 * s, y, 12 * s, 150 * s)
    fill(c, stem, '#6b4a1e'); ink(c, stem, 3 * s)
    base = smooth(xf([(-60, 150), (60, 150), (50, 170), (-50, 170)], x, y, s))
    fill(c, base, '#4a3314'); ink(c, base, 3 * s)
    fill(c, shade_p, '#2c4a2a')
    fill(c, shade_p, None, shader=linear((x, y - 80 * s), (x, y), [rgba('#4f7a46', 255), rgba('#1c301a', 255)]))
    ink(c, shade_p, 4 * s)
    if on:
        cone = poly(xf([(-90, 0), (90, 0), (220, 260), (-220, 260)], x, y, s))
        c.drawPath(cone, paint(shader=linear((x, y), (x, y + 260 * s), [rgba('gold', 120), rgba('gold', 0)]), blend=SCR))
        glow(c, x, y + 6 * s, 140 * s, 'gold', 160)

def person_silhouette(c, x, y, s, color='#120a06', a=255, hat=False, seed=9, dance=0.0):
    """Background figure: head + shoulders + body, kept simple and dark."""
    hd = smooth(xf([(-40, -60), (0, -78), (40, -60), (44, -10), (24, 22), (-24, 22), (-44, -10)], x, y, s))
    bd = smooth(xf([(-30, 26), (-110, 60), (-130 - dance * 30, 200), (-120, 520), (120, 520), (130 + dance * 30, 200), (110, 60), (30, 26)], x, y, s))
    fill(c, bd, color, a); fill(c, hd, color, a)
    if hat:
        hp = smooth(xf([(-80, -50), (-50, -60), (-44, -110), (44, -110), (50, -60), (80, -50), (0, -40)], x, y, s))
        fill(c, hp, color, a)

def wine_glass(c, x, y, s, fill_col='#5a0a10'):
    bowl = smooth(xf([(-30, -120), (30, -120), (26, -70), (0, -52), (-26, -70)], x, y, s))
    fill(c, bowl, '#fff1d0', 50)
    fill(c, smooth(xf([(-24, -92), (24, -92), (22, -72), (0, -56), (-22, -72)], x, y, s)), fill_col)
    stroke(c, smooth(xf([(0, -52), (0, 0)], x, y, s), False), 3 * s, '#e8d9b8', 160)
    stroke(c, smooth(xf([(-24, 0), (24, 0)], x, y, s), False), 3 * s, '#e8d9b8', 160)
    ink(c, bowl, 2.4 * s)
    light(c, smooth(xf([(-20, -114), (-14, -114), (-16, -80), (-22, -84)], x, y, s)), '#ffffff', 160)

def wine_bottle(c, x, y, s):
    b = smooth(xf([(-36, 0), (-38, -160), (-30, -200), (-12, -230), (-12, -300), (12, -300), (12, -230), (30, -200), (38, -160), (36, 0)], x, y, s))
    fill(c, b, '#16210f'); light(c, smooth(xf([(-26, -20), (-20, -20), (-22, -170), (-28, -150)], x, y, s)), '#9fbf7a', 120, blur=3 * s)
    lab = rect(x - 34 * s, y - 120 * s, 68 * s, 60 * s)
    fill(c, lab, '#d7c49a'); ink(c, lab, 2 * s)
    ink(c, b, 3.4 * s)

def checker_cloth(c, y, s=1.0, x0=-100, x1=W + 100, rows=7, tilt=0.35):
    """Red-and-white checked tablecloth in perspective."""
    top_w = x1 - x0
    for r in range(rows):
        t0 = r / rows; t1 = (r + 1) / rows
        ya = y + (t0 ** 1.3) * 520 * s; yb = y + (t1 ** 1.3) * 520 * s
        cols = 12
        for k in range(cols):
            spread0 = 1 + tilt * t0; spread1 = 1 + tilt * t1
            def X(u, sp):
                return W / 2 + (x0 + u * top_w - W / 2) * sp
            q = poly([(X(k / cols, spread0), ya), (X((k + 1) / cols, spread0), ya), (X((k + 1) / cols, spread1), yb), (X(k / cols, spread1), yb)])
            fill(c, q, '#9e1b1b' if (r + k) % 2 else '#e6d6b4')
    fill(c, rect(-200, y, W + 400, 600 * s), None, shader=linear((0, y), (0, y + 600 * s), [rgba('#000000', 0), rgba('#000000', 200)]))
    stroke(c, smooth([(-100, y), (W + 100, y)], False), 5)

def orange(c, x, y, r, seed=11):
    o = smooth([(x + r * math.cos(a) * (1 + 0.03 * math.sin(5 * a)), y + r * math.sin(a) * 0.96) for a in [i * math.pi / 8 for i in range(16)]])
    fill(c, o, None, shader=radial(x - r * 0.35, y - r * 0.4, r * 1.5, [rgba('#ffb43c', 255), rgba('#e0701a', 255), rgba('#6a2a06', 255)], [0, 0.5, 1]))
    rnd = random.Random(seed)
    for _ in range(40):
        a = rnd.uniform(0, 2 * math.pi); d = r * math.sqrt(rnd.random()) * 0.9
        c.drawCircle(x + d * math.cos(a), y + d * math.sin(a), r * 0.025, paint('#7a3006', 90))
    light(c, smooth([(x - r * 0.55, y - r * 0.45), (x - r * 0.2, y - r * 0.62), (x - r * 0.3, y - r * 0.3)]), '#fff1c8', 170, blur=r * 0.08)
    fill(c, smooth([(x - r * 0.08, y - r * 0.92), (x + r * 0.08, y - r * 0.92), (x, y - r * 0.82)]), '#3a4a18')
    ink(c, o, max(2.5, r * 0.05), seed=seed)

def vignette_layer(c, strength=230, inner=0.45):
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=radial(W / 2, H * 0.45, H * 0.62,
               [rgba('#000000', 0), rgba('#000000', 0), rgba('#000000', strength)], [0, inner, 1])))

# ------------------------------------------------------------------ shots
def shot_vito_close():
    bg = Layer(0.3)
    c = bg.c
    c.clear(col('#070403'))
    glow(c, W * 0.5, H * 0.32, 900, 'amber', 70, blend=skia.BlendMode.kSrcOver)
    light_shafts(c, -300, 200, 260, 700, angle_dx=900, angle_dy=1400, slats=8, a=22)
    fg = Layer(1.0)
    c = fg.c
    s = 3.25
    tuxedo(c, W * 0.5, 1110 + 172 * s, s * 0.9, width=1.05)
    vito_head(c, W * 0.5, 1110, s, turn=0.12, look=0.3)
    # top light pooling: everything below the chin falls off into black
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((0, 1750), (0, H), [rgba('#000000', 0), rgba('#000000', 200)])))
    vignette_layer(c, 200, 0.4)
    return [bg.done(), fg.done()]

def shot_michael_reveal():
    bg = Layer(0.3)
    c = bg.c
    c.clear(col('#050302'))
    glow(c, W * 0.62, H * 0.3, 800, '#7a4a20', 90, blend=skia.BlendMode.kSrcOver)
    fg = Layer(1.0)
    c = fg.c
    s = 3.1
    suit(c, W * 0.52, 1090 + 156 * s, s * 0.9)
    michael_head(c, W * 0.52, 1090, s, late=True, turn=-0.32, look=0.6, stubble=0.3)
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((0, 1700), (0, H), [rgba('#000000', 0), rgba('#000000', 210)])))
    # hard side light: half the face falls into darkness
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((W * 0.2, 0), (W * 0.55, 0), [rgba('#000000', 150), rgba('#000000', 0)]), blend=M))
    vignette_layer(c, 210, 0.4)
    return [bg.done(), fg.done()]

def office_bg(c, window=True, warm=1.0):
    wood_wall(c, 0, 0, W, H)
    if window:
        blinds_window(c, 90, 330, 520, 760)
    # bookshelf right
    sh = rect(860, 260, 440, 1200)
    fill(c, sh, '#1a0d06')
    rnd = random.Random(5)
    for r in range(6):
        y = 300 + r * 190
        stroke(c, smooth([(860, y + 170), (1300, y + 170)], False), 10, '#2e180b')
        x = 880
        while x < 1290:
            bw = rnd.uniform(22, 44); bh = rnd.uniform(120, 165)
            b = rect(x, y + 170 - bh, bw, bh)
            fill(c, b, rnd.choice(['#4a1f12', '#2b2a1a', '#3d2a14', '#5a3a1a', '#22160e']))
            ink(c, b, 2, seed=rnd.randint(0, 99))
            x += bw + 3
    shade(c, sh, '#000000', 120)
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((0, 0), (0, H), [rgba('#000000', 60), rgba('#000000', 0), rgba('#000000', 180)], [0, 0.35, 1])))
    if window:
        light_shafts(c, 90, 330, 520, 760, angle_dx=700, angle_dy=1200, slats=12, a=int(36 * warm))
        dust(c, 700, 1000, 420, n=120)

def shot_vito_office():
    bg = Layer(0.35, blur=2.5)
    office_bg(bg.c)
    mid = Layer(0.8)
    c = mid.c
    leather_chair(c, W * 0.56, 820, 1.55)
    s = 1.55
    tuxedo(c, W * 0.56, 1235, s)
    vito_head(c, W * 0.56, 1235 - 172 * s, s, turn=-0.22, look=-0.4)
    cat(c, W * 0.56 - 40, 1660, 1.5)
    hand(c, W * 0.56 + 140, 1730, 1.4, rot=-1.9, ring=True, curl=0.3)
    shade(c, rect(0, 0, W, H), '#000000', 0)
    fg = Layer(1.0)
    c = fg.c
    desk(c, 1840)
    desk_lamp(c, 1080, 1610, 1.1)
    # papers + glass on desk
    pp = poly([(240, 1850), (520, 1838), (540, 1880), (250, 1894)])
    fill(c, pp, '#d8c8a2'); ink(c, pp, 2.5)
    vignette_layer(c, 230, 0.42)
    return [bg.done(), mid.done(), fg.done()]

def wedding_bg(c, crowd=True, seed=21):
    """Sunny garden wedding at the Long Island estate: warm, bright, soft focus."""
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((0, 0), (0, H), [rgba('#f7d79a', 255), rgba('#d79a52', 255), rgba('#7a4a22', 255)], [0, 0.5, 1])))
    rnd = random.Random(seed)
    for k in range(9):  # tree canopy
        x = rnd.uniform(-100, W + 100); y = rnd.uniform(-60, 500); r = rnd.uniform(200, 340)
        tp = smooth([(x + r * math.cos(a) * rnd.uniform(0.8, 1.1), y + r * math.sin(a) * rnd.uniform(0.7, 1.0)) for a in [i * math.pi / 7 for i in range(14)]])
        fill(c, tp, rnd.choice(['#5c6a2c', '#4a5a24', '#6f7a34']))
        light(c, tp, '#ffe39a', 60, blur=30)
    # house facade / striped tent
    tent = poly([(-50, 620), (W + 50, 560), (W + 50, 760), (-50, 800)])
    fill(c, tent, '#efe3c6')
    for k in range(14):
        x = -50 + k * 100
        stripe = poly([(x, 620 - k * 4.6), (x + 50, 620 - (k + 0.5) * 4.6), (x + 50, 800 - (k + 0.5) * 2.9), (x, 800 - k * 2.9)])
        fill(c, stripe, '#c9a26a', 160)
    # string lights
    for row in range(2):
        pts = [(x, 560 + row * 90 + 40 * math.sin(x / 260 + row)) for x in range(-40, W + 80, 60)]
        stroke(c, smooth(pts, False), 2, '#3a2412', 200)
        for x, y in pts[::2]:
            glow(c, x, y + 8, 26, '#fff0c0', 200)
    # tables with white cloths
    for k in range(4):
        x = 120 + k * 330; y = 1050 + (k % 2) * 40
        t = smooth([(x - 150, y), (x + 150, y), (x + 170, y + 160), (x - 170, y + 160)])
        fill(c, t, '#f4ead4'); shade(c, t, '#7a5a3a', 70)
    if crowd:
        for k in range(10):
            x = rnd.uniform(0, W); y = rnd.uniform(930, 1150)
            person_silhouette(c, x, y, rnd.uniform(0.75, 1.05), color=rnd.choice(['#2a1a10', '#3a2416', '#4a2c1a', '#1a100a']),
                              a=230, dance=rnd.uniform(0, 1), hat=rnd.random() < 0.2)
    bokeh(c, 40, (0, 300, W, 1000), seed=seed)

def shot_family():
    bg = Layer(0.3, blur=6)
    wedding_bg(bg.c)
    mid = Layer(0.9)
    c = mid.c
    # back row: Tom Hagen, Sonny, Fredo; front: Connie (bride), Vito, Michael (uniform), Mama
    s = 0.72
    def body_simple(x, y, s, color='#16110e', shirt=True, dress=None):
        if dress:
            d = smooth(xf([(-46, -6), (-150, 40), (-230, 600), (230, 600), (150, 40), (46, -6)], x, y, s))
            fill(c, d, dress); ink(c, d, 5 * s)
            return
        tuxedo(c, x, y, s, rose=False) if shirt else suit(c, x, y, s)
    row_back = [(W * 0.22, 1235, dict(hair='#6a4a2c', recede=True, seed=101)),   # Tom
                (W * 0.50, 1205, dict(hair='#1a120d', curly=True, seed=102)),    # Sonny
                (W * 0.78, 1235, dict(hair='#5a4a3a', recede=True, mustache=True, seed=103, narrow=0.9))]  # Fredo
    for x, y, kw in row_back:
        body_simple(x, y, s)
        generic_head(c, x, y - 152 * s, s, **kw)
    # front row
    s2 = 0.8
    # Connie: bride with veil
    xC, yC = W * 0.16, 1420
    veil = smooth(xf([(0, -330), (-120, -280), (-200, 200), (-160, 700), (160, 700), (200, 200), (120, -280)], xC, yC, s2))
    fill(c, veil, '#fff6e6', 170)
    body_simple(xC, yC, s2, dress='#f6eedd')
    generic_head(c, xC, yC - 152 * s2, s2 * 0.92, hair='#2a1a10', seed=104, narrow=0.9)
    ink(c, veil, 3, a=120)
    # Mama
    xM, yM = W * 0.84, 1420
    body_simple(xM, yM, s2, dress='#2a1a22')
    generic_head(c, xM, yM - 152 * s2, s2 * 0.92, hair='#4a4038', seed=105, narrow=0.92)
    # Vito centre, Michael at his side
    sv = 0.95
    tuxedo(c, W * 0.40, 1400, sv)
    vito_head(c, W * 0.40, 1400 - 172 * sv, sv, turn=0.1)
    sm = 0.92
    marine_uniform(c, W * 0.64, 1420, sm)
    michael_head(c, W * 0.64, 1420 - 156 * sm, sm, late=False, turn=-0.15)
    # sun from top-left, warm wash
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((0, 1500), (0, H), [rgba('#000000', 0), rgba('#000000', 190)])))
    fg = Layer(1.25, blur=10)
    c = fg.c
    for k in range(5):  # out-of-focus foreground flowers
        x = 80 + k * 300; y = 2150 + (k % 2) * 70
        for j in range(5):
            a = j * 2 * math.pi / 5
            p = smooth([(x + 60 * math.cos(a) + 40 * math.cos(t), y + 60 * math.sin(a) + 30 * math.sin(t)) for t in [i * math.pi / 4 for i in range(8)]])
            fill(c, p, '#f2e2c4' if k % 2 else '#c8323a', 220)
    vignette_layer(c, 170, 0.5)
    return [bg.done(), mid.done(), fg.done()]

def shot_michael_quiet():
    bg = Layer(0.3, blur=9)
    wedding_bg(bg.c, seed=33)
    shade(bg.c, rect(0, 0, W, H), '#000000', 50)
    mid = Layer(0.9)
    c = mid.c
    s = 1.75
    marine_uniform(c, W * 0.58, 1300, s)
    michael_head(c, W * 0.58, 1300 - 156 * s, s, late=False, turn=-0.42, look=-0.8)
    hand(c, W * 0.42, 1820, 1.4, rot=-1.4, curl=0.8)
    fg = Layer(1.0)
    c = fg.c
    t = poly([(-100, 1840), (W + 100, 1840), (W + 100, H), (-100, H)])
    fill(c, t, '#efe2c4'); shade(c, t, '#5a3a1a', 80)
    fill(c, t, None, shader=linear((0, 1840), (0, H), [rgba('#000000', 0), rgba('#000000', 200)]))
    ink(c, t, 5)
    wine_glass(c, W * 0.8, 1940, 1.5)
    vignette_layer(c, 200, 0.45)
    return [bg.done(), mid.done(), fg.done()]

def shot_diptych():
    """Vertical split: the war hero in sunlight above, the Don in shadow below."""
    top = Layer(0.6)
    c = top.c
    c.save(); c.clipRect(skia.Rect.MakeXYWH(0, 0, W, H / 2))
    wedding_bg(c, crowd=False, seed=41)
    c.drawRect(skia.Rect.MakeWH(W, H), paint('#f2c886', 60))
    s = 1.55
    marine_uniform(c, W * 0.5, 900, s)
    michael_head(c, W * 0.5, 900 - 156 * s, s, late=False, turn=0.2, look=0.3, lit=1.15)
    c.restore()
    bot = Layer(1.0)
    c = bot.c
    c.save(); c.clipRect(skia.Rect.MakeXYWH(0, H / 2, W, H / 2))
    c.clear(col('#060302'))
    office_bg(c, window=False)
    shade(c, rect(0, 0, W, H), '#000000', 90)
    glow(c, W * 0.5, H / 2 + 420, 520, 'amber', 70)
    s = 1.55
    suit(c, W * 0.5, H / 2 + 800, s)
    michael_head(c, W * 0.5, H / 2 + 800 - 156 * s, s, late=True, turn=-0.2, look=-0.2, stubble=0.4)
    c.drawRect(skia.Rect.MakeXYWH(0, H / 2, W, H / 2), paint(shader=linear((0, H / 2), (0, H), [rgba('#000000', 40), rgba('#000000', 0), rgba('#000000', 180)], [0, 0.3, 1])))
    c.restore()
    # gold divider
    c.drawRect(skia.Rect.MakeXYWH(0, H / 2 - 5, W, 10), paint('gold'))
    c.drawRect(skia.Rect.MakeXYWH(0, H / 2 - 9, W, 4), paint(INK_C()))
    c.drawRect(skia.Rect.MakeXYWH(0, H / 2 + 5, W, 4), paint(INK_C()))
    vignette_layer(c, 150, 0.55)
    return [top.done(), bot.done()]

def INK_C():
    return col('ink')

def shot_michael_outsider():
    bg = Layer(0.3, blur=7)
    wedding_bg(bg.c, seed=55)
    mid = Layer(0.6, blur=3)
    c = mid.c
    rnd = random.Random(9)
    for k in range(7):  # the celebration he stands apart from
        x = 80 + k * 170 + rnd.uniform(-30, 30)
        person_silhouette(c, x, 1250 + rnd.uniform(-40, 40), 1.2, color='#2a170c', a=235, dance=rnd.uniform(0.3, 1))
    fg = Layer(1.0)
    c = fg.c
    s = 2.0
    marine_uniform(c, W * 0.72, 1560, s)
    michael_head(c, W * 0.72, 1560 - 156 * s, s, late=False, turn=0.48, look=1.0)
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((0, 1700), (0, H), [rgba('#000000', 0), rgba('#000000', 200)])))
    vignette_layer(c, 190, 0.45)
    return [bg.done(), mid.done(), fg.done()]

def shot_michael_cold():
    bg = Layer(0.3)
    c = bg.c
    c.clear(col('#040202'))
    glow(c, W * 0.5, H * 0.35, 700, '#5a3416', 120, blend=skia.BlendMode.kSrcOver)
    fg = Layer(1.0)
    c = fg.c
    s = 4.6
    suit(c, W * 0.5, 830 + 156 * s, s * 0.85)
    michael_head(c, W * 0.5, 830, s, late=True, turn=0.05, look=0.0, stubble=0.5, lit=0.85)
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((0, 0), (0, H), [rgba('#000000', 160), rgba('#000000', 0), rgba('#000000', 0), rgba('#000000', 230)], [0, 0.2, 0.55, 0.8])))
    # slatted shadow across the face
    for i in range(5):
        y = 420 + i * 230
        c.drawRect(skia.Rect.MakeXYWH(0, y, W, 95), paint('#000000', 110, blend=M))
    vignette_layer(c, 220, 0.35)
    return [bg.done(), fg.done()]

def shot_office_shadows():
    bg = Layer(0.5)
    office_bg(bg.c, warm=1.4)
    shade(bg.c, rect(0, 0, W, H), '#000000', 70)
    mid = Layer(0.8)
    c = mid.c
    leather_chair(c, W * 0.5, 1000, 1.5)
    light(c, smooth([(W * 0.3, 950), (W * 0.62, 940), (W * 0.6, 1100), (W * 0.32, 1110)]), 'gold', 50, blur=40)
    fg = Layer(1.0)
    c = fg.c
    desk(c, 1700)
    desk_lamp(c, 300, 1460, 1.2)
    # smoke curling from an ashtray
    ash = smooth([(860, 1712), (1000, 1712), (990, 1740), (870, 1740)])
    fill(c, ash, '#8a7a6a'); ink(c, ash, 3)
    for k in range(4):
        pts = [(930 + 30 * math.sin(j * 0.7 + k), 1700 - j * 70) for j in range(12)]
        stroke(c, smooth(pts, False), 10 - k * 2, '#d8c8b0', 40, blur=6)
    vignette_layer(c, 220, 0.4)
    return [bg.done(), mid.done(), fg.done()]

def restaurant_bg(c):
    c.clear(col('#2a0f08'))
    for k in range(9):  # wallpaper stripes
        c.drawRect(skia.Rect.MakeXYWH(k * 150, 0, 70, H), paint('#3a160c', 200))
    for x in (230, 1060):  # sconces
        glow(c, x, 640, 260, 'gold', 150)
        sc = smooth([(x - 40, 600), (x + 40, 600), (x + 30, 680), (x - 30, 680)])
        fill(c, sc, '#f2d79a'); ink(c, sc, 3)
    for x, y in ((420, 420), (720, 470)):  # framed pictures
        fr = rect(x, y, 200, 250)
        fill(c, fr, '#3a2a1a'); fill(c, rect(x + 20, y + 20, 160, 210), '#6a5030'); ink(c, fr, 4)
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((0, 0), (0, H), [rgba('#000000', 120), rgba('#000000', 0), rgba('#000000', 200)], [0, 0.3, 1])))

def shot_restaurant():
    bg = Layer(0.3, blur=4)
    restaurant_bg(bg.c)
    mid = Layer(0.85)
    c = mid.c
    s = 1.5
    suit(c, W * 0.5, 1300, s, tie='#3a2a22')
    michael_head(c, W * 0.5, 1300 - 156 * s, s, late=True, cold=False, turn=0.1, look=0.6, sweat=0.6, lit=1.0)
    fg = Layer(1.0)
    c = fg.c
    checker_cloth(c, 1700)
    wine_bottle(c, W * 0.5, 1860, 1.2)
    wine_glass(c, W * 0.66, 1880, 1.2)
    wine_glass(c, W * 0.34, 1880, 1.2)
    # the two men across the table, backs to camera, in silhouette
    for x, sc in ((W * 0.1, 2.2), (W * 0.92, 2.3)):
        person_silhouette(c, x, 1750, sc, color='#0a0503', hat=False)
    vignette_layer(c, 220, 0.42)
    return [bg.done(), mid.done(), fg.done()]

def shot_restaurant_close():
    bg = Layer(0.3, blur=6)
    restaurant_bg(bg.c)
    fg = Layer(1.0)
    c = fg.c
    s = 3.6
    suit(c, W * 0.47, 900 + 156 * s, s * 0.9, tie='#3a2a22')
    michael_head(c, W * 0.47, 900, s, late=True, cold=False, turn=-0.18, look=-0.9, sweat=1.0)
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((0, 1500), (0, H), [rgba('#000000', 0), rgba('#000000', 220)])))
    vignette_layer(c, 230, 0.38)
    return [bg.done(), fg.done()]

def shot_silence():
    bg = Layer(1.0)
    c = bg.c
    c.clear(col('#020101'))
    s = 3.9
    vito_head(c, W * 0.5, 900, s, turn=-0.4, look=-0.6, lit=0.7)
    # only a single blade of light across the eyes survives
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((0, 0), (0, H),
               [rgba('#000000', 250), rgba('#000000', 250), rgba('#000000', 0), rgba('#000000', 0), rgba('#000000', 250), rgba('#000000', 250)],
               [0, 0.3, 0.355, 0.43, 0.49, 1]), blend=skia.BlendMode.kSrcOver))
    return [bg.done()]

def shot_oranges():
    bg = Layer(0.5, blur=3)
    c = bg.c
    c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=linear((0, 0), (0, H), [rgba('#3a2412', 255), rgba('#120904', 255)])))
    for k in range(7):  # cobblestones
        for j in range(5):
            st = smooth([(j * 300 + (k % 2) * 150 + dx, 1200 + k * 160 + dy) for dx, dy in [(-120, -50), (120, -60), (130, 50), (-110, 60)]])
            fill(c, st, '#4a3220'); ink(c, st, 3, a=180)
    fg = Layer(1.0)
    c = fg.c
    rnd = random.Random(3)
    for k, (x, y, r) in enumerate([(380, 1500, 150), (760, 1640, 130), (980, 1380, 100), (230, 1820, 120), (640, 1980, 160), (1050, 1900, 110)]):
        shade(c, smooth([(x - r * 1.1, y + r * 0.8), (x + r * 1.1, y + r * 0.8), (x + r, y + r * 1.05), (x - r, y + r * 1.05)]), '#000000', 150, blur=20)
        orange(c, x, y, r, seed=k)
    light_shafts(c, -200, -200, 400, 600, angle_dx=900, angle_dy=1800, slats=5, a=30)
    vignette_layer(c, 220, 0.4)
    return [bg.done(), fg.done()]

def shot_rose_detail():
    bg = Layer(0.4)
    c = bg.c
    c.clear(col('#0a0605'))
    lap = smooth([(-200, 0), (700, 0), (1100, 2400), (-200, 2400)])
    fill(c, lap, '#171210')
    fill(c, lap, None, shader=radial(500, 900, 900, [rgba('#4a3e36', 200), rgba('#171210', 0)]))
    sat = smooth([(560, -50), (900, -50), (1300, 2400), (980, 2400)])
    fill(c, sat, '#221b17'); light(c, sat, 'amber', 50, blur=40); ink(c, sat, 6)
    shirt = poly([(900, -50), (W + 50, -50), (W + 50, H), (1300, H)])
    fill(c, shirt, 'shirt_lo')
    fg = Layer(1.0)
    c = fg.c
    draw_rose(c, 690, 980, 260, seed=31)
    vignette_layer(c, 230, 0.35)
    return [bg.done(), fg.done()]

def shot_michael_office():
    bg = Layer(0.35, blur=3)
    office_bg(bg.c, warm=0.7)
    shade(bg.c, rect(0, 0, W, H), '#000000', 110)
    mid = Layer(0.8)
    c = mid.c
    leather_chair(c, W * 0.5, 780, 1.6)
    s = 1.6
    suit(c, W * 0.5, 1210, s)
    michael_head(c, W * 0.5, 1210 - 156 * s, s, late=True, turn=0.0, stubble=0.5)
    hand(c, W * 0.5 + 170, 1760, 1.3, rot=-1.6, ring=True, curl=0.2)
    fg = Layer(1.0)
    c = fg.c
    desk(c, 1800)
    # a caporegime bending to kiss the ring, in silhouette
    person_silhouette(c, W * 0.86, 1750, 2.6, color='#070403')
    vignette_layer(c, 230, 0.4)
    return [bg.done(), mid.done(), fg.done()]

def shot_door():
    """Kay's point of view: the office through the doorway. The door itself is a separate layer."""
    bg = Layer(0.6)
    c = bg.c
    c.clear(col('#140906'))
    # interior seen through the door: warm, Michael receiving his men
    c.save(); c.clipRect(skia.Rect.MakeXYWH(330, 300, 640, 1700))
    office_bg(c, warm=0.6)
    s = 0.95
    suit(c, W * 0.5, 1100, s)
    michael_head(c, W * 0.5, 1100 - 156 * s, s, late=True, turn=0.0, stubble=0.4)
    for x, y in ((420, 1260), (880, 1240)):
        suit(c, x, y, 0.9)
        generic_head(c, x, y - 152 * 0.9, 0.9, hair='#1a120d', seed=int(x), turn=0.6 if x < 600 else -0.6)
    c.restore()
    # dark hallway wall around the door frame
    wall = skia.Path(); wall.addRect(skia.Rect.MakeWH(W, H)); wall.addRect(skia.Rect.MakeXYWH(330, 300, 640, 1700))
    wall.setFillType(skia.PathFillType.kEvenOdd)
    fill(c, wall, '#0d0705')
    hatch(c, wall, angle=-40, spacing=14, w=1.4, color='#000000', a=170)
    frame = rect(318, 288, 664, 1724)
    stroke(c, frame, 26, '#3a2010'); ink(c, frame, 4)
    door = Layer(1.0)
    c = door.c
    d = rect(330, 300, 640, 1700)
    fill(c, d, '#2a160b')
    for k in range(3):
        pnl = rect(390, 360 + k * 540, 520, 460)
        stroke(c, pnl, 8, '#160b05'); light(c, rect(390, 360 + k * 540, 520, 30), 'amber', 30)
    c.drawCircle(370 + 560, 1150, 16, paint('#c9a24a'))
    ink(c, d, 5)
    return [bg.done(), door.done()]

SHOTS = {
    'vito_close': shot_vito_close, 'michael_reveal': shot_michael_reveal, 'vito_office': shot_vito_office,
    'family': shot_family, 'michael_quiet': shot_michael_quiet, 'diptych': shot_diptych,
    'michael_outsider': shot_michael_outsider, 'michael_cold': shot_michael_cold,
    'office_shadows': shot_office_shadows, 'restaurant': shot_restaurant, 'restaurant_close': shot_restaurant_close,
    'silence': shot_silence, 'oranges': shot_oranges, 'rose_detail': shot_rose_detail,
    'michael_office': shot_michael_office, 'door': shot_door,
}

def flatten(layers):
    out = np.zeros((H, W, 4), np.float32)
    for arr, _ in layers:
        out = arr + out * (1 - arr[..., 3:4])
    return out

if __name__ == '__main__':
    import sys, PIL.Image
    outdir = sys.argv[1]
    names = sys.argv[2:] or list(SHOTS)
    for n in names:
        img = flatten(SHOTS[n]())
        rgb = img[..., :3] + (1 - img[..., 3:4]) * 0
        PIL.Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).resize((W // 3, H // 3), PIL.Image.LANCZOS).save(f'{outdir}/{n}.png')
        print('ok', n)
