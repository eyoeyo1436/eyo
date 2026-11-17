"""Every illustrated shot of the Obsession Short, as named parallax layers.

Drawn at 1296x2304 (1.2x the output) so camera moves stay sharp.
Each shot returns [(rgba_array, depth, name)]; render.py animates named layers (fades, snaps, shadows).
"""
import math, random
import numpy as np
import skia
from ink import (smooth, poly, xf, fill, stroke, ink, taper, hatch, shade, light, glow, radial, linear,
                 rgba, paint, col, new_surface, to_array)
from characters import (bear_head, hoodie, nikki_head, nikki_hair_back, sweater, willow_stick, fist, TURN)

W, H = 1296, 2304
M = skia.BlendMode.kMultiply
SCR = skia.BlendMode.kScreen

class Layer:
    def __init__(self, name='main', depth=1.0, blur=0.0):
        self.surface = new_surface(W, H)
        self.c = self.surface.getCanvas()
        self.depth, self.blur, self.name = depth, blur, name

    def done(self):
        arr = to_array(self.surface)
        if self.blur:
            import PIL.Image, PIL.ImageFilter
            im = PIL.Image.fromarray((arr * 255).astype(np.uint8), 'RGBA').filter(PIL.ImageFilter.GaussianBlur(self.blur))
            arr = np.asarray(im).astype(np.float32) / 255.0
        return arr, self.depth, self.name

def rect(x, y, w, h):
    return poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])

def full(c):
    return skia.Rect.MakeWH(W, H)

def vignette(c, strength=230, inner=0.42, cy=0.45):
    c.drawRect(full(c), paint(shader=radial(W / 2, H * cy, H * 0.62, [rgba('#000000', 0), rgba('#000000', 0), rgba('#000000', strength)], [0, inner, 1])))

def halftone(c, region, color='#000000', a=90, step=14, seed=1, angle=0.4):
    """Comic-print halftone dots inside a path (bigger dots toward the bottom)."""
    c.save(); c.clipPath(region, skia.ClipOp.kIntersect, True)
    b = region.computeTightBounds()
    ca, sa = math.cos(angle), math.sin(angle)
    y = b.top() - step
    while y < b.bottom() + step:
        x = b.left() - step
        while x < b.right() + step:
            k = (y - b.top()) / max(1, b.height())
            r = step * 0.18 + step * 0.32 * k
            c.drawCircle(x * ca - y * sa * 0.0 + (y % (2 * step)) * 0.5, y, r, paint(color, a))
            x += step
        y += step
    c.restore()

def fog(c, y0, y1, color='#3a4a5a', a=90, seed=3):
    rnd = random.Random(seed)
    for _ in range(14):
        x = rnd.uniform(-200, W + 200); y = rnd.uniform(y0, y1); r = rnd.uniform(220, 480)
        c.drawCircle(x, y, r, paint(shader=radial(x, y, r, [rgba(color, a), rgba(color, 0)])))

def bokeh(c, n, region, colors=('#ffcf7a', '#ff9a5a', '#fff0c8'), rmin=12, rmax=40, a=(40, 120), seed=4):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = region
    for _ in range(n):
        x, y, r = rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(rmin, rmax)
        cc = rnd.choice(colors)
        c.drawCircle(x, y, r, paint(cc, rnd.randint(*a), blend=SCR))

def silhouette(draw_fn, color='#050608', blur=0, eyes=None, alpha=255):
    """Render a figure offscreen, return a solid-colour silhouette image (optionally with glowing eyes)."""
    s = new_surface(W, H)
    draw_fn(s.getCanvas())
    img = s.makeImageSnapshot()
    out = new_surface(W, H)
    c = out.getCanvas()
    p = skia.Paint(AntiAlias=True)
    p.setColorFilter(skia.ColorFilters.Blend(col(color, alpha), skia.BlendMode.kSrcIn))
    if blur:
        p.setImageFilter(skia.ImageFilters.Blur(blur, blur))
    c.drawImage(img, 0, 0, skia.SamplingOptions(), p)
    if eyes:
        for (x, y, r) in eyes:
            glow(c, x, y, r * 5, '#ffe9c8', 120)
            c.drawCircle(x, y, r, paint('#fff8ea'))
    return out.makeImageSnapshot()

def draw_img(c, img, matrix=None, alpha=255):
    c.save()
    if matrix is not None:
        c.concat(matrix)
    p = skia.Paint(AntiAlias=True); p.setAlphaf(alpha / 255)
    c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), p)
    c.restore()

# ---------------------------------------------------------------- character placement
def sleeves(c, x0, y0, x1, y1):
    """Bear's green hoodie cuffs reaching in from the frame edges to his fists."""
    for x, y, edge in ((x0, y0, -200), (x1, y1, W + 200)):
        taper(c, [(edge, y + 260), ((x + edge) / 2, y + 120), (x, y + 40)], 190, 150, '#2c4536')
        stroke(c, smooth([(edge, y + 170), ((x + edge) / 2, y + 40), (x, y - 30)], False), 4)
        stroke(c, smooth([(edge, y + 350), ((x + edge) / 2, y + 200), (x, y + 110)], False), 4)

def bear_bust(c, x, chin, s, **kw):
    hoodie(c, x, chin, s)
    return bear_head(c, x, chin - 146 * s, s, **kw)

def nikki_bust(c, x, chin, s, wild=0.0, shoulders=0.0, **kw):
    hy = chin - 142 * s
    nikki_hair_back(c, x, hy, s, tilt=kw.get('tilt', 0.0), turn=kw.get('turn', 0.0), wild=wild)
    sweater(c, x, chin, s, shoulders=shoulders)
    return nikki_head(c, x, hy, s, **kw)

def arm(c, sx, sy, ex, ey, wx, wy, s, color, hi, tone='#c58a5e', bend_hand=0.0, seed=1):
    """Sleeve from shoulder through elbow to wrist, plus a hanging hand."""
    pts = [(sx, sy), (ex, ey), (wx, wy)]
    taper(c, pts, 74 * s, 52 * s, color)
    taper(c, pts, 30 * s, 20 * s, hi, 90)
    stroke(c, smooth([(sx - 30 * s, sy), (ex - 26 * s, ey), (wx - 22 * s, wy)], False), 3 * s, a=200)
    stroke(c, smooth([(sx + 30 * s, sy), (ex + 26 * s, ey), (wx + 22 * s, wy)], False), 3 * s, a=200)
    ang = math.atan2(wy - ey, wx - ex) + bend_hand
    hx, hy = wx + math.cos(ang) * 40 * s, wy + math.sin(ang) * 40 * s
    hand = smooth([(wx - 20 * s, wy), (wx + 20 * s, wy), (hx + 20 * s, hy), (hx + math.cos(ang) * 36 * s, hy + math.sin(ang) * 36 * s), (hx - 20 * s, hy)])
    fill(c, hand, tone); shade(c, hand, 'skin_deep', 90, blur=4 * s); ink(c, hand, 3 * s, seed=seed)
    for k in (-1, 0, 1):
        stroke(c, smooth([(hx + k * 9 * s, hy), (hx + k * 9 * s + math.cos(ang) * 30 * s, hy + math.sin(ang) * 30 * s)], False), 1.5 * s, a=140)

def legs(c, x, hip, s, color='#1d2430', spread=1.0, pigeon=0.0, seed=7):
    for side in (-1, 1):
        lg = poly([(x + side * 8 * s, hip), (x + side * 92 * s, hip), (x + side * (78 + 10 * spread) * s, hip + 400 * s),
                   (x + side * (70 + 14 * spread) * s, hip + 780 * s), (x + side * (22 + 10 * spread) * s, hip + 780 * s),
                   (x + side * 16 * s, hip + 400 * s)])
        fill(c, lg, color); light(c, lg, '#6a7a90', 40, blur=10 * s); ink(c, lg, 4 * s, seed=seed + side)
        fx = x + side * (46 + 12 * spread) * s
        shoe = smooth([(fx - 40 * s - pigeon * side * 30 * s, hip + 770 * s), (fx + 40 * s - pigeon * side * 30 * s, hip + 770 * s),
                       (fx + (60 - pigeon * side * 60) * s, hip + 820 * s), (fx - (60 + pigeon * side * 60) * s, hip + 820 * s)])
        fill(c, shoe, '#e8e2d6' if color == '#1d2430' else '#2a2420'); ink(c, shoe, 3.4 * s, seed=seed)

def nikki_full(c, x, chin, s, contort=0.0, **kw):
    """Standing Nikki. contort adds the unnatural tilt, uneven shoulders and dangling arms."""
    hip = chin + 420 * s
    legs(c, x, hip, s, color='#2a2c36', spread=0.6 - contort * 0.6, pigeon=contort)
    c.save(); c.clipRect(skia.Rect.MakeLTRB(0, 0, W, hip + 20 * s))
    hy = chin - 142 * s
    nikki_hair_back(c, x, hy, s, tilt=kw.get('tilt', 0.0), turn=kw.get('turn', 0.0), wild=contort)
    sweater(c, x, chin, s, shoulders=contort * 0.8)
    c.restore()
    hem = smooth([(x - 162 * s, hip), (x, hip + 18 * s), (x + 162 * s, hip)], False)
    stroke(c, hem, 6 * s)
    for side in (-1, 1):
        sh_y = chin + (90 + side * contort * 50) * s
        arm(c, x + side * 150 * s, sh_y, x + side * (176 + contort * 20) * s, chin + (330 + side * contort * 40) * s,
            x + side * (182 + contort * 10) * s, chin + (560 + contort * 90) * s, s, '#8f1c22', '#c9434a', bend_hand=side * contort * 0.8)
    nikki_head(c, x, hy, s, **kw)

def bear_full(c, x, chin, s, **kw):
    hip = chin + 430 * s
    legs(c, x, hip, s, color='#1d2430')
    c.save(); c.clipRect(skia.Rect.MakeLTRB(0, 0, W, hip + 30 * s))
    hoodie(c, x, chin, s)
    c.restore()
    stroke(c, smooth([(x - 176 * s, hip), (x, hip + 20 * s), (x + 176 * s, hip)], False), 6 * s)
    for side in (-1, 1):
        arm(c, x + side * 166 * s, chin + 90 * s, x + side * 184 * s, chin + 330 * s, x + side * 172 * s, chin + 540 * s,
            s, '#2c4536', '#557a62', tone='#dba57e')
    bear_head(c, x, chin - 146 * s, s, **kw)

# ---------------------------------------------------------------- environments
def void_bg(c, top='#0b0e16', bottom='#020203', rim='#7a1420', rim2='#1f4a5a'):
    c.drawRect(full(c), paint(shader=linear((0, 0), (0, H), [rgba(top, 255), rgba(bottom, 255)])))
    glow(c, W * 0.15, H * 0.35, 700, rim, 110, blend=skia.BlendMode.kSrcOver)
    glow(c, W * 0.9, H * 0.25, 650, rim2, 120, blend=skia.BlendMode.kSrcOver)
    fog(c, H * 0.4, H * 0.9, '#2a3444', 70)

def warm_room_bg(c, seed=11):
    """Warm, lived-in interior at night: string lights, shelves, a lamp. Soft focus."""
    c.drawRect(full(c), paint(shader=linear((0, 0), (0, H), [rgba('#3a2216', 255), rgba('#1a0e08', 255)])))
    rnd = random.Random(seed)
    for k in range(4):  # shelves with books and plants
        y = 500 + k * 240
        stroke(c, smooth([(700, y), (W, y)], False), 12, '#2a160c')
        x = 720
        while x < W:
            bw, bh = rnd.uniform(24, 44), rnd.uniform(110, 170)
            fill(c, rect(x, y - bh, bw, bh), rnd.choice(['#6a2a1a', '#2a4a3a', '#7a5a2a', '#3a2a4a', '#8a6a4a']), 220)
            x += bw + 4
    pts = [(x, 300 + 60 * math.sin(x / 200)) for x in range(-50, W + 100, 50)]
    stroke(c, smooth(pts, False), 2, '#1a0a04')
    for x, y in pts:
        glow(c, x, y + 10, 34, '#ffd27a', 200)
    lamp = smooth([(180, 980), (360, 980), (320, 860), (220, 860)])
    fill(c, lamp, '#f6d8a0'); glow(c, 270, 930, 420, '#ffb85a', 150)
    bokeh(c, 50, (0, 200, W, 1400), seed=seed)

def bedroom_bg(c, door_open=True, seed=21):
    """Bear's bedroom at night: moonlit window, frame shadows bent across the wall, a dark doorway."""
    c.drawRect(full(c), paint(shader=linear((0, 0), (0, H), [rgba('#151b26', 255), rgba('#07090d', 255)])))
    # window (right) with moon glow
    win = rect(820, 380, 380, 620)
    fill(c, win, '#9fc3d6'); glow(c, 1010, 600, 520, '#7fb0c8', 120)
    for k in range(1, 3):
        c.drawRect(skia.Rect.MakeXYWH(820, 380 + k * 206, 380, 14), paint('#0b0f16'))
    c.drawRect(skia.Rect.MakeXYWH(1003, 380, 14, 620), paint('#0b0f16'))
    stroke(c, win, 22, '#0b0f16'); ink(c, win, 4)
    # distorted window-frame shadow stretched across the wall (cold light)
    for i in range(3):
        for j in range(2):
            x0 = 120 + j * 260; y0 = 700 + i * 300
            q = poly([(x0, y0), (x0 + 240, y0 - 60), (x0 + 300, y0 + 220), (x0 + 40, y0 + 290)])
            fill(c, q, '#5f8aa0', 50, blend=SCR)
    # dark doorway (left)
    door = rect(110, 520, 330, 900)
    fill(c, door, '#020203')
    stroke(c, door, 24, '#1c2330'); ink(c, door, 4)
    if not door_open:
        fill(c, door, '#1a2028')
    # posters / shelf silhouettes
    fill(c, rect(520, 560, 200, 280), '#2a3240', 200); ink(c, rect(520, 560, 200, 280), 3)
    # bed
    bed = smooth([(-100, 1600), (W + 100, 1560), (W + 100, H), (-100, H)])
    fill(c, bed, '#3a4a5c')
    fill(c, bed, None, shader=linear((0, 1560), (0, H), [rgba('#7d98ae', 160), rgba('#0a0d12', 255)]))
    for k in range(6):
        stroke(c, smooth([(-50, 1640 + k * 90), (W * 0.4, 1600 + k * 100 + 30 * math.sin(k)), (W + 50, 1620 + k * 90)], False), 3, '#121820', 160)
    ink(c, bed, 5)
    hatch(c, rect(0, 0, W, H), angle=-30, spacing=16, w=1.2, color='#000000', a=55, seed=seed)

def hallway_bg(c, seed=31):
    """Narrow hallway, one bare bulb, doors receding, long shadows."""
    c.drawRect(full(c), paint('#0c0b0d'))
    vx, vy = W / 2, 860
    # walls / floor in one-point perspective
    for pts, colr in ((([(0, 0), (vx - 160, vy - 300), (vx - 160, vy + 300), (0, H)]), '#2a2422'),
                      (([(W, 0), (vx + 160, vy - 300), (vx + 160, vy + 300), (W, H)]), '#221c1a'),
                      (([(0, H), (vx - 160, vy + 300), (vx + 160, vy + 300), (W, H)]), '#1a1412'),
                      (([(0, 0), (vx - 160, vy - 300), (vx + 160, vy - 300), (W, 0)]), '#141110')):
        p = poly(pts); fill(c, p, colr); ink(c, p, 3)
    fill(c, rect(vx - 160, vy - 300, 320, 600), '#050405')
    for k, d in enumerate((0.25, 0.55)):  # door frames on the walls
        for side in (-1, 1):
            x0 = vx + side * (160 + (W / 2 - 160) * (1 - d)) ; x1 = vx + side * (160 + (W / 2 - 160) * (1 - d - 0.12))
            y0t = vy - 300 - (vy - 300) * (1 - d) * 0.8; y0b = vy + 300 + (H - vy - 300) * (1 - d) * 0.5
            dp = poly([(x0, y0t), (x1, y0t + 30), (x1, y0b - 20), (x0, y0b)])
            fill(c, dp, '#0e0b0a'); ink(c, dp, 3)
    stroke(c, smooth([(vx, 0), (vx, 340)], False), 3, '#0a0806')
    glow(c, vx, 360, 700, '#e8c890', 120)
    c.drawCircle(vx, 360, 22, paint('#fff4d8'))
    hatch(c, rect(0, 0, W, H), angle=40, spacing=12, w=1.3, color='#000000', a=70, seed=seed)

def empty_room_bg(c, seed=41):
    c.drawRect(full(c), paint(shader=linear((0, 0), (0, H), [rgba('#0a0b10', 255), rgba('#020203', 255)])))
    wall_pool = radial(W / 2, 1150, 1000, [rgba('#b09670', 255), rgba('#5a4a38', 255), rgba('#0a0b10', 0)], [0, 0.55, 1])
    c.drawRect(skia.Rect.MakeWH(W, 1700), paint(shader=wall_pool))
    floor = poly([(0, 1700), (W, 1700), (W, H), (0, H)])
    fill(c, floor, '#0e0f14'); ink(c, floor, 3)
    stroke(c, smooth([(W / 2, 0), (W / 2, 520)], False), 3, '#1a1a1a')
    shade_p = smooth([(W / 2 - 70, 560), (W / 2 + 70, 560), (W / 2 + 40, 510), (W / 2 - 40, 510)])
    fill(c, shade_p, '#2a2a2a'); ink(c, shade_p, 3)
    cone = poly([(W / 2 - 70, 560), (W / 2 + 70, 560), (W / 2 + 520, 2000), (W / 2 - 520, 2000)])
    c.drawPath(cone, paint(shader=linear((0, 560), (0, 2000), [rgba('#d9c7a0', 70), rgba('#d9c7a0', 0)]), blend=SCR))
    pool = smooth([(W / 2 - 420, 1880), (W / 2 + 420, 1880), (W / 2 + 380, 1980), (W / 2 - 380, 1980)])
    fill(c, pool, '#d9c7a0', 40, blur=30, blend=SCR)
    hatch(c, rect(0, 0, W, 1700), angle=-35, spacing=14, w=1.2, color='#000000', a=60, seed=seed)

def red_splash_bg(c, seed=51):
    """Comic-panel red burst: violence suggested, never shown."""
    c.clear(col('#140204'))
    rnd = random.Random(seed)
    for k in range(40):
        a = rnd.uniform(0, 2 * math.pi)
        r0, r1 = rnd.uniform(80, 200), rnd.uniform(800, 1500)
        w = rnd.uniform(0.03, 0.09)
        p = poly([(W / 2 + r0 * math.cos(a - w), 900 + r0 * math.sin(a - w)), (W / 2 + r1 * math.cos(a), 900 + r1 * math.sin(a)),
                  (W / 2 + r0 * math.cos(a + w), 900 + r0 * math.sin(a + w))])
        fill(c, p, rnd.choice(['#7a0a12', '#a3101c', '#4a0408']), 220)
    for k in range(26):  # splatter blobs
        x, y, r = rnd.uniform(0, W), rnd.uniform(200, 1800), rnd.uniform(14, 70)
        b = smooth([(x + r * math.cos(t) * rnd.uniform(0.7, 1.3), y + r * math.sin(t) * rnd.uniform(0.7, 1.3)) for t in [i * math.pi / 5 for i in range(10)]])
        fill(c, b, '#b0121e', 230); ink(c, b, 2.5, a=150)
    halftone(c, rect(0, 0, W, H), '#000000', 110, step=16)

# ---------------------------------------------------------------- shots
def shot_hook_a():
    bg = Layer('bg', 0.3); void_bg(bg.c)
    nk = Layer('nikki', 0.6, blur=1.5)
    nikki_bust(nk.c, W * 0.62, 1080, 1.35, smile=0.75, eye=0.9, blush=0.6, turn=-0.2, look=(-0.5, 0.2), mode='warm', lit=0.9)
    shade(nk.c, rect(0, 0, W, H), '#000000', 40)
    fg = Layer('bear', 1.0)
    c = fg.c
    bear_bust(c, W * 0.38, 1560, 1.75, smile=-0.1, eye=1.05, brow=-0.7, look=(0.3, 0.6), turn=0.2, mode='cold', lit=0.9)
    # broken wish stick held in both hands at chest height
    willow_stick(c, W * 0.38, 2000, 1.9, rot=-0.05, broken=1.0, glow_a=150)
    fist(c, W * 0.38 - 230, 2010, 1.4, rot=-0.2, tone='#dba57e')
    fist(c, W * 0.38 + 230, 2000, 1.4, rot=0.2, flip=True, tone='#dba57e')
    c.drawRect(full(c), paint(shader=linear((0, 2150), (0, H), [rgba('#000000', 0), rgba('#000000', 200)])))
    vignette(c, 200, 0.45)
    return [bg.done(), nk.done(), fg.done()]

def shot_hook_b():
    bg = Layer('bg', 0.3); void_bg(bg.c, rim='#a0101c')
    nk = Layer('nikki', 0.6, blur=1.5)
    nikki_bust(nk.c, W * 0.62, 1080, 1.35, smile=0.75, eye=0.9, blush=0.6, turn=-0.2, look=(-0.5, 0.2), mode='warm', lit=0.9)
    shade(nk.c, rect(0, 0, W, H), '#000000', 40)
    sil = Layer('nikki_shadow', 0.6)
    def fig(cc):
        nikki_bust(cc, W * 0.62, 1080, 1.35, wild=1.2, smile=0.0, tilt=0.25, turn=-0.2)
    img = silhouette(fig, '#040306', eyes=[(W * 0.62 - 40, 900, 9), (W * 0.62 + 50, 910, 9)])
    m = skia.Matrix.Translate(W * 0.62, 1500).preScale(1.12, 1.35).preTranslate(-W * 0.62, -1500)
    draw_img(sil.c, img, m)
    fg = Layer('bear', 1.0)
    c = fg.c
    bear_bust(c, W * 0.38, 1560, 1.75, smile=-0.3, eye=1.2, brow=-0.9, look=(0.9, 0.0), turn=0.35, mode='cold', lit=0.9)
    willow_stick(c, W * 0.38, 2000, 1.9, rot=-0.05, broken=1.0, glow_a=60)
    fist(c, W * 0.38 - 230, 2010, 1.4, rot=-0.2, tone='#dba57e')
    fist(c, W * 0.38 + 230, 2000, 1.4, rot=0.2, flip=True, tone='#dba57e')
    c.drawRect(full(c), paint(shader=linear((0, 2150), (0, H), [rgba('#000000', 0), rgba('#000000', 200)])))
    vignette(c, 210, 0.42)
    return [bg.done(), nk.done(), sil.done(), fg.done()]

def shot_watch():
    bg = Layer('bg', 0.3, blur=5); warm_room_bg(bg.c)
    mid = Layer('nikki', 0.6, blur=2)
    nikki_bust(mid.c, W * 0.66, 1300, 1.0, smile=0.9, teeth=True, open_=0.25, eye=0.8, blush=0.7, turn=-0.3, look=(-0.6, 0), mode='warm', lit=1.1)
    fg = Layer('bear', 1.0)
    c = fg.c
    # doorframe Bear hides behind
    fr = rect(-40, 0, 330, H)
    fill(c, fr, '#120a06'); ink(c, fr, 5)
    bear_bust(c, W * 0.2, 1500, 1.9, smile=0.15, eye=1.0, brow=-0.6, look=(1.0, 0.1), turn=0.5, mode='cold', lit=0.8)
    edge = rect(-40, 0, 170, H)
    fill(c, edge, '#0a0604'); ink(c, edge, 5)
    c.drawRect(full(c), paint(shader=linear((0, 0), (W * 0.55, 0), [rgba('#000000', 150), rgba('#000000', 0)])))
    vignette(c, 200, 0.45)
    return [bg.done(), mid.done(), fg.done()]

def shot_bear_longing():
    bg = Layer('bg', 0.3, blur=8); warm_room_bg(bg.c, seed=12)
    shade(bg.c, rect(0, 0, W, H), '#000000', 90)
    fg = Layer('bear', 1.0)
    c = fg.c
    bear_bust(c, W * 0.5, 1640, 3.0, smile=0.2, eye=1.05, brow=-0.8, look=(0.8, -0.1), turn=0.25, mode='warm', lit=0.9)
    c.drawRect(full(c), paint(shader=linear((0, 1800), (0, H), [rgba('#000000', 0), rgba('#000000', 210)])))
    vignette(c, 210, 0.4)
    return [bg.done(), fg.done()]

def shot_wish():
    bg = Layer('bg', 0.3); void_bg(bg.c, top='#08100c', rim='#2a6a3a', rim2='#5a4a1a')
    whole = Layer('stick_whole', 1.0)
    c = whole.c
    willow_stick(c, W / 2, 1150, 3.6, rot=0.0, broken=0.0)
    sleeves(c, W / 2 - 330, 1170, W / 2 + 330, 1170)
    fist(c, W / 2 - 330, 1170, 2.4, rot=-0.15, tone='#dba57e')
    fist(c, W / 2 + 330, 1170, 2.4, rot=0.15, flip=True, tone='#dba57e')
    broken = Layer('stick_broken', 1.0)
    c = broken.c
    willow_stick(c, W / 2, 1150, 3.6, rot=0.0, broken=1.0, glow_a=220)
    sleeves(c, W / 2 - 400, 1120, W / 2 + 400, 1120)
    fist(c, W / 2 - 400, 1120, 2.4, rot=-0.5, tone='#dba57e')
    fist(c, W / 2 + 400, 1120, 2.4, rot=0.5, flip=True, tone='#dba57e')
    rnd = random.Random(4)
    for _ in range(70):  # sparks
        a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(60, 600)
        c.drawCircle(W / 2 + d * math.cos(a), 1150 + d * math.sin(a) * 0.8, rnd.uniform(2, 7), paint('#e8ffd0', rnd.randint(120, 255)))
    for L_ in (whole, broken):
        vignette(L_.c, 180, 0.4)
    return [bg.done(), whole.done(), broken.done()]

def shot_nikki_sweet():
    bg = Layer('bg', 0.3, blur=7); warm_room_bg(bg.c, seed=13)
    fg = Layer('nikki', 1.0)
    c = fg.c
    nikki_bust(c, W * 0.5, 1700, 3.0, smile=0.8, eye=0.92, blush=0.8, turn=-0.15, look=(0.1, 0.0), mode='warm', lit=1.1)
    c.drawRect(full(c), paint(shader=linear((0, 1850), (0, H), [rgba('#000000', 0), rgba('#000000', 200)])))
    vignette(c, 190, 0.45)
    return [bg.done(), fg.done()]

def shot_getting():
    """Getting exactly what you want: Nikki clings adoringly; Bear's smile wavers."""
    bg = Layer('bg', 0.3, blur=6); warm_room_bg(bg.c, seed=14)
    shade(bg.c, rect(0, 0, W, H), '#000000', 60)
    fg = Layer('pair', 1.0)
    c = fg.c
    bear_bust(c, W * 0.36, 1720, 1.9, smile=0.45, eye=1.1, brow=-0.5, look=(0.6, 0.1), turn=0.15, mode='warm', lit=0.9)
    nikki_bust(c, W * 0.7, 1820, 1.9, smile=0.9, eye=1.15, pupil=0.75, blush=0.9, turn=-0.45, look=(-1.0, -0.2), tilt=-0.18, mode='warm', lit=1.0)
    c.drawRect(full(c), paint(shader=linear((0, 1900), (0, H), [rgba('#000000', 0), rgba('#000000', 210)])))
    vignette(c, 200, 0.45)
    return [bg.done(), fg.done()]

def shot_price():
    bg = Layer('bg', 0.3); void_bg(bg.c, top='#0a0c12', rim='#5a0a12')
    fg = Layer('nikki', 1.0)
    c = fg.c
    nikki_bust(c, W * 0.5, 1700, 3.0, smile=1.0, teeth=True, eye=1.25, pupil=0.55, blush=0.2, catch=False, turn=-0.1,
               mode='cold', lit=1.0, pale=0.5)
    c.drawRect(full(c), paint(shader=linear((0, 1850), (0, H), [rgba('#000000', 0), rgba('#000000', 220)])))
    vignette(c, 220, 0.4)
    return [bg.done(), fg.done()]

def shot_perf_charming():
    bg = Layer('bg', 0.3, blur=10)
    c = bg.c
    c.drawRect(full(c), paint(shader=linear((0, 0), (0, H), [rgba('#5a3a20', 255), rgba('#1a0e08', 255)])))
    bokeh(c, 70, (0, 0, W, H), seed=21, rmin=20, rmax=70)
    fg = Layer('nikki', 1.0)
    c = fg.c
    nikki_bust(c, W * 0.5, 1560, 2.4, smile=0.65, eye=0.95, blush=0.7, turn=0.25, look=(-0.4, 0), mode='warm', lit=1.2)
    c.drawRect(full(c), paint(shader=linear((0, 1700), (0, H), [rgba('#000000', 0), rgba('#000000', 200)])))
    vignette(c, 170, 0.5)
    return [bg.done(), fg.done()]

def shot_perf_tilt():
    bg = Layer('bg', 0.3, blur=6)
    c = bg.c
    c.drawRect(full(c), paint(shader=linear((0, 0), (0, H), [rgba('#2a1a14', 255), rgba('#08060a', 255)])))
    bokeh(c, 40, (0, 0, W, H), seed=22, colors=('#c88a5a', '#7a5a8a'), a=(20, 60))
    fg = Layer('nikki', 1.0)
    c = fg.c
    nikki_bust(c, W * 0.5, 1600, 2.4, smile=0.75, eye=1.2, pupil=0.7, blush=0.3, turn=0.0, tilt=0.42, look=(0, 0),
               mode='cold', lit=0.9, pale=0.3, catch=False)
    vignette(c, 210, 0.42)
    return [bg.done(), fg.done()]

def shot_perf_eyes():
    bg = Layer('bg', 1.0)
    c = bg.c
    c.clear(col('#050406'))
    nikki_head(c, W * 0.5, 1040, 6.2, smile=0.6, eye=1.38, pupil=0.4, blush=0, catch=False, mode='under', lit=1.0, pale=0.8, strands=0.7)
    c.drawRect(full(c), paint(shader=linear((0, 0), (0, H), [rgba('#000000', 255), rgba('#000000', 255), rgba('#000000', 0), rgba('#000000', 0), rgba('#000000', 255), rgba('#000000', 255)],
                                            [0, 0.26, 0.34, 0.6, 0.68, 1]), blend=skia.BlendMode.kSrcOver))
    return [bg.done()]

def shot_perf_hall():
    bg = Layer('bg', 0.35); hallway_bg(bg.c)
    shadow = Layer('wall_shadow', 0.5)
    def fig(cc):
        nikki_full(cc, W * 0.5, 900, 1.05, contort=1.0, smile=0.0, tilt=0.7)
    img = silhouette(fig, '#000000', blur=6, alpha=200)
    m = skia.Matrix.Translate(W * 0.5, 2100).preScale(1.6, 1.25).preSkew(0.35, 0).preTranslate(-W * 0.5, -2100)
    draw_img(shadow.c, img, m, alpha=200)
    fg = Layer('nikki', 1.0)
    c = fg.c
    nikki_full(c, W * 0.5, 900, 1.05, contort=1.0, smile=0.85, teeth=True, eye=1.35, pupil=0.4, catch=False, blush=0,
               tilt=0.75, mode='under', lit=1.0, pale=0.7, strands=1.0)
    vignette(c, 220, 0.4)
    return [bg.done(), shadow.done(), fg.done()]

def shot_perf_lunge():
    bg = Layer('bg', 0.3)
    c = bg.c
    c.clear(col('#030304'))
    glow(c, W / 2, H * 0.45, 900, '#5a0a12', 140, blend=skia.BlendMode.kSrcOver)
    fg = Layer('nikki', 1.0)
    c = fg.c
    nikki_bust(c, W * 0.5, 1860, 4.4, smile=1.0, teeth=True, open_=0.45, eye=1.4, pupil=0.38, catch=False, blush=0,
               tilt=-0.22, mode='under', lit=1.0, pale=0.9, strands=1.0, wild=1.5)
    vignette(c, 200, 0.4)
    return [bg.done(), fg.done()]

def shot_bedroom_wide():
    bg = Layer('bg', 0.5); bedroom_bg(bg.c)
    fg = Layer('bear', 1.0)
    c = fg.c
    bear_bust(c, W * 0.6, 1700, 1.65, smile=-0.2, eye=1.15, brow=-0.8, look=(-0.8, 0), turn=-0.3, mode='cold', lit=1.0)
    blanket = smooth([(-100, 1720), (W + 100, 1680), (W + 100, H), (-100, H)])
    fill(c, blanket, '#4a5a70'); fill(c, blanket, None, shader=linear((0, 1680), (0, H), [rgba('#8aa4ba', 150), rgba('#0a0d12', 255)]))
    for k in range(5):
        stroke(c, smooth([(-50, 1760 + k * 110), (W * 0.5, 1730 + k * 120), (W + 50, 1770 + k * 100)], False), 3, '#121820', 170)
    ink(c, blanket, 5)
    vignette(c, 220, 0.42)
    return [bg.done(), fg.done()]

def shot_bear_terror():
    bg = Layer('bg', 0.3, blur=8); bedroom_bg(bg.c, seed=22)
    fg = Layer('bear', 1.0)
    c = fg.c
    bear_bust(c, W * 0.5, 1700, 3.1, smile=-0.6, open_=0.5, eye=1.4, pupil=0.45, brow=-1.0, look=(-0.6, 0), turn=-0.2,
              mode='cold', lit=1.0, sweat=1.0)
    c.drawRect(full(c), paint(shader=linear((0, 1800), (0, H), [rgba('#000000', 0), rgba('#000000', 220)])))
    vignette(c, 220, 0.4)
    return [bg.done(), fg.done()]

def shot_doorway():
    bg = Layer('bg', 0.5); bedroom_bg(bg.c, seed=23)
    nk = Layer('nikki', 0.5)
    c = nk.c
    c.save(); c.clipRect(skia.Rect.MakeXYWH(110, 520, 330, 900))
    nikki_full(c, 275, 760, 0.5, contort=0.3, smile=0.7, teeth=True, eye=1.35, pupil=0.4, catch=False, blush=0, tilt=0.3,
               mode='cold', lit=0.5, pale=0.8)
    c.drawRect(skia.Rect.MakeXYWH(110, 520, 330, 900), paint('#000000', 120))
    c.restore()
    for ex in (258, 290):
        glow(c, ex, 680, 16, '#fff2d8', 200)
    fg = Layer('bear', 1.0)
    c = fg.c
    bear_bust(c, W * 0.74, 1880, 1.8, smile=-0.4, eye=1.3, pupil=0.6, brow=-0.9, look=(0.9, 0), turn=0.45, mode='cold', lit=0.8, sweat=0.6)
    vignette(c, 220, 0.42)
    return [bg.done(), nk.done(), fg.done()]

def shot_red_grin():
    bg = Layer('bg', 0.3); red_splash_bg(bg.c)
    fg = Layer('nikki', 1.0)
    c = fg.c
    nikki_bust(c, W * 0.5, 1720, 2.7, smile=0.95, teeth=True, eye=1.1, pupil=0.6, blush=0.6, catch=True, turn=0.2,
               tilt=0.12, mode='warm', lit=1.0, pale=0.1)
    for k in range(9):  # spatter on her face and sweater
        rnd = random.Random(k)
        x, y, r = W * 0.5 + rnd.uniform(-260, 260), rnd.uniform(1100, 2100), rnd.uniform(5, 16)
        c.drawCircle(x, y, r, paint('#8a0a12', 230))
    vignette(c, 200, 0.42)
    return [bg.done(), fg.done()]

def shot_dark_humor():
    """Uncomfortable dark humour: a too-tight hug, her bliss, his frozen grin."""
    bg = Layer('bg', 0.3, blur=6); warm_room_bg(bg.c, seed=15)
    shade(bg.c, rect(0, 0, W, H), '#000000', 70)
    fg = Layer('pair', 1.0)
    c = fg.c
    bear_bust(c, W * 0.32, 1700, 1.9, smile=0.7, teeth=True, eye=1.35, pupil=0.55, brow=-1.0, look=(0.9, 0), turn=0.1,
              mode='warm', lit=0.9, sweat=0.8)
    nikki_bust(c, W * 0.74, 1780, 1.8, smile=0.8, eye=0.75, blush=1.0, turn=-0.5, tilt=-0.3, mode='warm', lit=1.0)
    # her arm wrapped too tight across his chest, fingers digging into his hoodie
    arm_pts = [(W * 0.74, 1960), (W * 0.52, 2010), (W * 0.3, 1985)]
    taper(c, arm_pts, 92, 70, '#8f1c22')
    taper(c, arm_pts, 30, 20, '#c9434a', 90)
    stroke(c, smooth([(W * 0.74, 1916), (W * 0.52, 1966), (W * 0.3, 1950)], False), 3.5)
    stroke(c, smooth([(W * 0.74, 2004), (W * 0.52, 2054), (W * 0.3, 2020)], False), 3.5)
    hnd = smooth([(W * 0.3, 1950), (W * 0.3, 2022), (W * 0.2, 2030), (W * 0.15, 1990), (W * 0.19, 1950)])
    fill(c, hnd, '#c58a5e'); shade(c, hnd, 'skin_deep', 80, blur=4); ink(c, hnd, 4)
    for k in range(4):
        y = 1962 + k * 17
        stroke(c, smooth([(W * 0.22, y), (W * 0.15, y + 6)], False), 2.4, a=170)
    vignette(c, 200, 0.45)
    return [bg.done(), fg.done()]

def shot_final_alone():
    bg = Layer('bg', 0.4); empty_room_bg(bg.c)
    fg = Layer('bear', 0.9)
    bear_full(fg.c, W / 2, 1180, 0.62, smile=-0.2, eye=1.0, brow=-0.7, look=(0, 0.3), mode='warm', lit=0.8)
    vignette(fg.c, 230, 0.36)
    return [bg.done(), fg.done()]

def nikki_shadow_img(scale_y=1.5):
    def fig(cc):
        nikki_full(cc, W / 2, 1120, 0.62, contort=0.4, tilt=0.3, smile=0.0)
    return silhouette(fig, '#000000', blur=8, alpha=230)

def shot_final_shadow():
    bg = Layer('bg', 0.4); empty_room_bg(bg.c, seed=42)
    sh = Layer('shadow', 0.45)
    m = skia.Matrix.Translate(W / 2 + 120, 1700).preScale(1.9, 1.75).preTranslate(-W / 2, -1700)
    draw_img(sh.c, nikki_shadow_img(), m, alpha=235)
    fg = Layer('bear', 0.9)
    bear_full(fg.c, W / 2, 1180, 0.62, smile=-0.3, eye=1.2, brow=-0.9, look=(0.6, 0), turn=0.3, mode='warm', lit=0.8)
    vignette(fg.c, 230, 0.36)
    return [bg.done(), sh.done(), fg.done()]

def shot_final_close():
    bg = Layer('bg', 0.3)
    c = bg.c
    c.clear(col('#050507'))
    glow(c, W / 2, 900, 700, '#3a3020', 140, blend=skia.BlendMode.kSrcOver)
    fg = Layer('bear', 1.0)
    bear_bust(fg.c, W * 0.46, 1720, 3.0, smile=-0.3, eye=1.15, brow=-0.9, look=(0.8, 0.2), turn=0.3, mode='warm', lit=0.8, sweat=0.4)
    hand = Layer('shadow_hand', 1.05)
    c = hand.c
    # a long shadow hand creeping over his shoulder
    pts = [(W + 120, 2150), (W * 0.92, 2020), (W * 0.8, 1950)]
    taper(c, pts, 130, 90, '#000000', 225)
    for k, a in enumerate((-0.5, -0.2, 0.1, 0.4)):
        bx, by = W * 0.8, 1950
        taper(c, [(bx, by), (bx - 120 * math.cos(a), by - 120 * math.sin(a) - 40), (bx - 220 * math.cos(a), by - 160 * math.sin(a) - 20)], 30, 12, '#000000', 225)
    vignette(fg.c, 220, 0.4)
    return [bg.done(), fg.done(), hand.done()]

def shot_final_wide():
    bg = Layer('bg', 0.4); empty_room_bg(bg.c, seed=43)
    sh = Layer('shadow', 0.45)
    m = skia.Matrix.Translate(W / 2, 1700).preScale(2.6, 2.3).preTranslate(-W / 2, -1700)
    draw_img(sh.c, nikki_shadow_img(), m, alpha=245)
    fg = Layer('bear', 0.9)
    bear_full(fg.c, W / 2, 1330, 0.5, smile=-0.3, eye=1.1, brow=-0.8, look=(0, -0.3), mode='warm', lit=0.6)
    vignette(fg.c, 240, 0.32)
    return [bg.done(), sh.done(), fg.done()]

SHOTS = {
    'hook_a': shot_hook_a, 'hook_b': shot_hook_b, 'watch': shot_watch, 'bear_longing': shot_bear_longing,
    'wish': shot_wish, 'nikki_sweet': shot_nikki_sweet, 'getting': shot_getting, 'price': shot_price,
    'perf_charming': shot_perf_charming, 'perf_tilt': shot_perf_tilt, 'perf_eyes': shot_perf_eyes,
    'perf_hall': shot_perf_hall, 'perf_lunge': shot_perf_lunge, 'bedroom_wide': shot_bedroom_wide,
    'bear_terror': shot_bear_terror, 'doorway': shot_doorway, 'red_grin': shot_red_grin,
    'dark_humor': shot_dark_humor, 'final_alone': shot_final_alone, 'final_shadow': shot_final_shadow,
    'final_close': shot_final_close, 'final_wide': shot_final_wide,
}

def flatten(layers, skip=()):
    out = np.zeros((H, W, 4), np.float32)
    for arr, _, name in layers:
        if name in skip:
            continue
        out = arr + out * (1 - arr[..., 3:4])
    return out

if __name__ == '__main__':
    import sys, PIL.Image
    outdir = sys.argv[1]
    names = sys.argv[2:] or list(SHOTS)
    for n in names:
        skip = {'stick_whole'} if n == 'wish' else ({'nikki'} if n == 'hook_b' else set())
        img = flatten(SHOTS[n](), skip)
        PIL.Image.fromarray((np.clip(img[..., :3], 0, 1) * 255).astype(np.uint8)).resize((W // 3, H // 3), PIL.Image.LANCZOS).save(f'{outdir}/{n}.png')
        print('ok', n, flush=True)
