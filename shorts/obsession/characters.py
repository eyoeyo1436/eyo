"""Bear and Nikki: fixed designs, posable expressions.

Heads are authored in a local space (eye line y=0, ~190 units wide); `s` scales to pixels.
Expressions: smile (-1..1), open (0..1), teeth, eye (openness, 1 = neutral, 1.4 = staring),
pupil (iris size 0.4..1), brow (-1 worried .. +1 angry), look (x,y), tilt (radians), turn (radians).
Lighting: 'warm' (key from above), 'cold' (moonlight from the side), 'under' (horror under-light).
"""
import math
import skia
from ink import (smooth, poly, xf, sym, mirror, fill, stroke, ink, taper, hatch, shade, light,
                 glow, radial, linear, rgba, paint, col)

M = skia.BlendMode.kMultiply
SCR = skia.BlendMode.kScreen

TURN = [0.0]

def warp(pts):
    t = TURN[0]
    if not t:
        return pts
    R = 124.0
    out = []
    for x, y in pts:
        u = max(-0.999, min(0.999, x / R))
        z = 30.0 * math.exp(-(x / 22.0) ** 2) * (1.0 if -12 < y < 72 else 0.25)
        out.append((R * math.sin(math.asin(u) + t) + z * math.sin(t), y))
    return out

class Head:
    """Transforms local head points to canvas, with turn warp and whole-head tilt about the neck."""
    def __init__(self, cx, cy, s, tilt=0.0, turn=0.0):
        self.cx, self.cy, self.s, self.tilt = cx, cy, s, tilt
        TURN[0] = turn
        self.turn = turn

    def X(self, pts):
        pts = warp(pts)
        ct, st = math.cos(self.tilt), math.sin(self.tilt)
        out = []
        for x, y in pts:
            yy = y - 140  # pivot at the neck
            X, Y = x * ct - yy * st, x * st + yy * ct
            out.append((self.cx + X * self.s, self.cy + (Y + 140) * self.s))
        return out

    def P(self, pts, closed=True):
        return smooth(self.X(pts), closed)

    def L(self, pts):
        return smooth(self.X(pts), False)

def both(pts):
    return [pts, mirror(pts)]

# ---------------------------------------------------------------- lighting helpers
def face_light(c, h, face, mode, lit, hw):
    """Shade a face according to the light mode. Assumes face clip is active."""
    cx, cy, s = h.cx, h.cy, h.s
    off = 124 * math.sin(h.turn) * 0.6
    sh = linear((cx + (off - hw) * s, cy), (cx + (off + hw) * s, cy),
                [rgba('skin_deep', 210), rgba('skin_deep', 0), rgba('skin_deep', 0), rgba('skin_deep', 210)], [0, 0.22, 0.78, 1])
    c.drawPath(face, paint(shader=sh, blend=M))
    if mode == 'under':
        # light from below: brow, upper lids and forehead fall into shadow, chin and nose underside glow
        shade(c, h.P([(-90, -140), (90, -140), (90, -30), (40, -14), (0, -22), (-40, -14), (-90, -30)]), 'skin_deep', int(200 * lit), blur=14 * s)
        light(c, h.P([(-40, 100), (0, 92), (40, 100), (30, 150), (0, 160), (-30, 150)]), '#ffd7a8', int(110 * lit), blur=12 * s)
        light(c, h.P([(-16, 54), (16, 54), (12, 66), (-12, 66)]), '#ffd7a8', int(120 * lit), blur=5 * s)
    elif mode == 'cold':
        sd = 1 if h.turn >= 0 else -1
        fill(c, face, '#5f88a8', int(60 * lit), blend=skia.BlendMode.kColor)
        shade(c, h.P([(-sd * 130, -150), (-sd * 20, -150), (-sd * 24, 40), (-sd * 14, 170), (-sd * 130, 170)]), '#1a2630', int(150 * lit), blur=18 * s)
        light(c, h.P([(sd * 20, -110), (sd * 70, -90), (sd * 74, 40), (sd * 46, 110), (sd * 22, 40)]), '#9fd0e0', int(70 * lit), blur=18 * s, blend=SCR)
        light(c, h.P([(-5, -6), (5, -6), (8, 44), (-8, 44)]), '#cfe8f0', int(60 * lit), blur=4 * s, blend=SCR)
    else:  # warm top light
        light(c, h.P([(-44, -108), (0, -112), (44, -108), (36, -60), (0, -48), (-36, -60)]), 'gold', int(100 * lit), blur=12 * s)
        light(c, h.P([(-5, -8), (5, -8), (8, 44), (0, 50), (-8, 44)]), 'gold', int(120 * lit), blur=4 * s)
        for ch in both([(-64, 24), (-42, 22), (-36, 38), (-56, 48)]):
            light(c, h.P(ch), 'gold', int(60 * lit), blur=7 * s)

def eyes(c, h, ex0, eye=1.0, pupil=1.0, look=(0, 0), lash=False, brow=0.0, brow_col='#1a100b', mode='warm',
         sclera='#ece2d2', iris='#3a2014', lit=1.0, catch=True, lid_shadow=0):
    s = h.s
    K = 1.28
    for side in (1, -1):
        cxp = side * ex0
        hw = 18 * K
        top = -9 * eye * K
        bot = 6 * (0.6 + 0.4 * eye) * K
        shape = [(cxp - side * hw * 1.05, 2), (cxp - side * hw * 0.4, top), (cxp + side * hw * 0.35, top * 0.95),
                 (cxp + side * hw, 0), (cxp + side * hw * 0.3, bot), (cxp - side * hw * 0.5, bot * 0.9)]
        ep = h.P(shape)
        fill(c, ep, sclera)
        c.save(); c.clipPath(ep, skia.ClipOp.kIntersect, True)
        r = (8.5 * pupil + (1.5 if eye > 1.2 else 0)) * K
        ix, iy = cxp + look[0] * 6, look[1] * 4 - 1
        (px, py), = h.X([(ix, iy)])
        c.drawCircle(px, py, r * s, paint(iris))
        c.drawCircle(px, py, r * 0.5 * s, paint('#050302'))
        if catch:
            c.drawCircle(px - 2.5 * s, py - 3 * s, 2.0 * s, paint('#fff6e8', int(235 * lit)))
        # upper lid shadow on the eyeball
        shade(c, h.P([(cxp - 24, -30), (cxp + 24, -30), (cxp + 24, top + 4), (cxp - 24, top + 4)]), '#000000', 90 + lid_shadow, blur=3 * s)
        c.restore()
        stroke(c, h.L([shape[0], shape[1], shape[2], shape[3]]), (4.2 if lash else 3.2) * s)
        if lash:
            (lx, ly), = h.X([shape[3]])
            (lx2, ly2), = h.X([(cxp + side * (hw + 7), -6 - 2 * eye)])
            stroke(c, smooth([(lx, ly), (lx2, ly2)], False), 3.2 * s)
        stroke(c, h.L([shape[3], shape[4], shape[5], shape[0]]), 1.6 * s, a=170)
        if eye > 1.15:  # visible white under the iris reads as a stare
            stroke(c, h.L([(cxp - side * 10, bot + 6), (cxp + side * 6, bot + 7)]), 1.2 * s, a=120)
        # brows: brow<0 lifts the inner end (worry), brow>0 pulls it down (anger)
        inner_y = -30 + brow * 9 - (eye - 1) * 12
        outer_y = -32 - (eye - 1) * 9 - brow * 2
        taper(c, h.X([(cxp + side * 34, outer_y + 4), (cxp + side * 16, outer_y - 4), (cxp - side * 8, inner_y - 2), (cxp - side * 20, inner_y + 2)]),
              (6 if lash else 9) * s, (5 if lash else 7) * s, brow_col)
        stroke(c, h.L([(cxp - side * 18, -10 - 8 * eye), (cxp, -14 - 9 * eye), (cxp + side * 16, -10 - 8 * eye)]), 1.4 * s, a=110)

def mouth(c, h, y0, w, smile=0.0, open_=0.0, teeth=False, lip='#9a4a3c', full=1.0):
    s = h.s
    cy_corner = y0 - smile * 9
    cl, cr = (-w, cy_corner), (w, cy_corner)
    upper = [cl, (-w * 0.5, y0 - 3 - smile * 2), (0, y0 - 1), (w * 0.5, y0 - 3 - smile * 2), cr]
    drop = open_ * 30 + max(0, smile) * 4
    lower = [cr, (w * 0.5, y0 + 3 + drop * 0.85 + smile * 3), (0, y0 + 4 + drop + smile * 3), (-w * 0.5, y0 + 3 + drop * 0.85 + smile * 3), cl]
    if open_ > 0.05 or teeth:
        mp = h.P(upper + lower[1:-1])
        fill(c, mp, '#1a0505')
        if teeth:
            c.save(); c.clipPath(mp, skia.ClipOp.kIntersect, True)
            tb = h.P([(-w, y0 - 14), (w, y0 - 14), (w, y0 + 5 + drop * 0.35), (-w, y0 + 5 + drop * 0.35)])
            fill(c, tb, '#efe6d2')
            for k in range(-4, 5):
                stroke(c, h.L([(k * w / 5, y0 - 10), (k * w / 5, y0 + 4 + drop * 0.3)]), 1.0 * s, a=120)
            if open_ > 0.3:
                fill(c, h.P([(-w * 0.8, y0 + drop * 0.7), (w * 0.8, y0 + drop * 0.7), (w * 0.6, y0 + drop + 6), (-w * 0.6, y0 + drop + 6)]), '#d8cfbd')
            c.restore()
        ink(c, mp, 2.6 * s)
    # lips
    ul = h.P([cl, (-w * 0.45, y0 - 7 * full - smile * 2), (0, y0 - 4 * full), (w * 0.45, y0 - 7 * full - smile * 2), cr,
              (w * 0.5, y0 - 2 - smile * 2), (0, y0 - 1), (-w * 0.5, y0 - 2 - smile * 2)])
    fill(c, ul, lip)
    ll = [cr] + lower[1:-1] + [cl]
    ll_out = [cr, (w * 0.5, y0 + 9 * full + drop * 0.85 + smile * 3), (0, y0 + 11 * full + drop + smile * 3),
              (-w * 0.5, y0 + 9 * full + drop * 0.85 + smile * 3), cl]
    lp = h.P(ll_out + ll[::-1][1:-1])
    fill(c, lp, lip)
    light(c, h.P([(-w * 0.3, y0 + 4 + drop + smile * 3), (w * 0.3, y0 + 4 + drop + smile * 3), (0, y0 + 9 + drop + smile * 3)]), '#ffe0c8', 70, blur=2 * s)
    taper(c, h.X(upper), 3.0 * s, 3.0 * s)
    if smile > 0.4:  # cheek creases deepen the grin
        for side in (1, -1):
            stroke(c, h.L([(side * (w + 4), cy_corner - 16), (side * (w + 10), cy_corner - 2), (side * (w + 6), cy_corner + 8)]), 1.8 * s, a=150)
    if smile < -0.2:
        for side in (1, -1):
            stroke(c, h.L([(side * w, cy_corner), (side * (w + 6), cy_corner + 10)]), 1.8 * s, a=140)

# ---------------------------------------------------------------- BEAR
BEAR_FACE = sym([(0, -118), (-46, -114), (-70, -98), (-78, -66), (-80, -28), (-79, 10), (-75, 48),
                 (-66, 86), (-50, 116), (-28, 138), (0, 146)])
BEAR_EAR = [(-77, -24), (-97, -32), (-104, -4), (-99, 24), (-87, 42), (-77, 34)]

def bear_head(c, cx, cy, s, smile=0.1, open_=0.0, teeth=False, eye=1.0, pupil=1.0, brow=-0.3, look=(0, 0),
              tilt=0.0, turn=0.0, mode='warm', lit=1.0, sweat=0.0, seed=200):
    """Bear: lean young face, messy dark fringe, light stubble, anxious brows."""
    h = Head(cx, cy, s, tilt, turn)
    hair_col, hair_hi = '#2b1b12', '#6a4a30'
    back = h.P([(0, -186), (-58, -180), (-96, -154), (-108, -108), (-104, -54), (-92, -22), (-80, -60),
                (-74, -96), (0, -110), (74, -96), (80, -60), (92, -22), (104, -54), (108, -108), (96, -154), (58, -180)])
    fill(c, back, hair_col); ink(c, back, 4.5 * s, seed=seed)
    for e in both(BEAR_EAR):
        if TURN[0] and (e[0][0] > 0) == (TURN[0] < 0) and abs(TURN[0]) > 0.2:
            continue
        ep = h.P(e)
        fill(c, ep, '#cf9a74'); shade(c, ep, 'skin_deep', 70); ink(c, ep, 3.2 * s, seed=seed + 1)
        stroke(c, h.L([(e[1][0] * 0.95 + 4 * (1 if e[1][0] < 0 else -1), -18), (e[2][0] * 0.92, 4), (e[3][0] * 0.95, 22)]), 1.6 * s, a=140)
    face = h.P(BEAR_FACE)
    fill(c, face, None, shader=linear((cx, cy - 120 * s), (cx, cy + 150 * s), [rgba('#f2cba6', 255), rgba('#dba57e', 255), rgba('#b9845f', 255)], [0, 0.45, 1]))
    c.save(); c.clipPath(face, skia.ClipOp.kIntersect, True)
    face_light(c, h, face, mode, lit * 0.8, 84)
    for sock in both([(-62, -24), (-44, -34), (-16, -30), (-6, -14), (-10, 4), (-32, 10), (-56, 8), (-66, -8)]):
        shade(c, h.P(sock), 'skin_lo', int(110 * lit), blur=6 * s)
    shade(c, h.P([(-60, 12), (-36, 20), (-18, 14), (-30, 26), (-50, 24)]), 'skin_lo', 70, blur=5 * s)
    shade(c, h.P([(18, 14), (36, 20), (60, 12), (50, 24), (30, 26)]), 'skin_lo', 70, blur=5 * s)
    stub = h.P([(-76, 50), (-62, 96), (-30, 132), (0, 144), (30, 132), (62, 96), (76, 50), (40, 70), (24, 104), (0, 116), (-24, 104), (-40, 70)])
    shade(c, stub, '#4a3a30', 80, blur=6 * s)
    hatch(c, stub, angle=80, spacing=4 * s, w=0.9 * s, color='#2a1e18', a=60, seed=seed + 3)
    shade(c, h.P([(-80, 100), (-50, 128), (0, 150), (50, 128), (80, 100), (80, 180), (-80, 180)]), 'skin_deep', 110, blur=8 * s)
    if sweat:
        for x, y in [(-40, -70), (30, -84), (-58, -30), (54, -40), (8, -96), (-62, 30)]:
            (gx, gy), = h.X([(x, y)])
            drop = smooth([(gx, gy - 6 * s), (gx + 3 * s, gy + 2 * s), (gx, gy + 5 * s), (gx - 3 * s, gy + 2 * s)])
            fill(c, drop, '#f4fbff', int(220 * sweat)); stroke(c, drop, 1.0 * s, a=int(160 * sweat))
    c.restore()
    eyes(c, h, 32, eye, pupil, look, lash=False, brow=brow, brow_col='#21140c', mode=mode, lit=lit, iris='#4a3020')
    stroke(c, h.L([(-9, -6), (-11, 22), (-13, 42)]), 1.8 * s, a=130)
    for side in (1, -1):
        stroke(c, h.L([(side * 10, 46), (side * 19, 54), (side * 18, 62), (side * 8, 64)]), 3.0 * s)
        fill(c, h.P([(side * 7, 60), (side * 15, 58), (side * 13, 64), (side * 6, 64)]), '#120604')
    stroke(c, h.L([(-7, 66), (0, 62), (7, 66)]), 2.0 * s)
    mouth(c, h, 92, 25, smile, open_, teeth, lip='#a05a48', full=0.8)
    stroke(c, h.L([(-2, 128), (0, 136)]), 1.6 * s, a=110)
    ink(c, face, 5 * s, seed=seed + 4)
    # messy fringe: pointed clumps swept toward his right, uneven lengths
    clumps = [(-84, -128, -96, -60), (-62, -140, -70, -44), (-38, -146, -50, -34), (-12, -150, -24, -42),
              (14, -150, 2, -52), (40, -146, 30, -64), (64, -138, 62, -76), (86, -124, 92, -70)]
    for k, (rx, ry, tx, ty) in enumerate(clumps):
        cp = h.P([(rx - 22, ry + 4), (rx + 20, ry - 6), (tx + 12, ty - 22), (tx + 2, ty), (tx - 10, ty - 18)])
        fill(c, cp, hair_col)
        stroke(c, h.L([(rx, ry), ((rx + tx) / 2 + 3, (ry + ty) / 2), (tx + 3, ty - 8)]), 2 * s, hair_hi, 170)
        ink(c, cp, 3.0 * s, seed=seed + 10 + k)
    light(c, h.P([(-60, -168), (0, -184), (60, -168), (40, -150), (-40, -150)]), hair_hi, 140, blur=10 * s)
    return h

def hoodie(c, cx, cy, s, seed=230, hood=True, color='#2c4536', hi='#557a62'):
    """Bear's dark-green pullover hoodie with drawstrings over a grey tee. cy = chin."""
    TURN[0] = 0.0
    neck = smooth(xf([(-40, -60), (-44, 30), (44, 30), (40, -60)], cx, cy, s))
    fill(c, neck, 'skin_mid'); shade(c, neck, 'skin_deep', 170)
    body = poly(xf([(-50, -2), (-100, 10), (-150, 34), (-178, 74), (-184, 150), (-172, 320), (-176, 900),
                    (176, 900), (172, 320), (184, 150), (178, 74), (150, 34), (100, 10), (50, -2)], cx, cy, s))
    fill(c, body, color)
    fill(c, body, None, shader=radial(cx - 40 * s, cy + 40 * s, 260 * s, [rgba(hi, 200), rgba(color, 0)]))
    hatch(c, poly(xf([(100, 60), (176, 120), (176, 900), (80, 900)], cx, cy, s)), angle=-60, spacing=8 * s, w=1.4 * s, color='#0c1610', a=90, seed=seed)
    tee = smooth(xf([(-40, -2), (0, 22), (40, -2), (34, 30), (0, 46), (-34, 30)], cx, cy, s))
    fill(c, tee, '#8f8f8a'); ink(c, tee, 2.6 * s, seed=seed + 1)
    if hood:
        hp = smooth(xf([(-46, -4), (-104, -10), (-128, 24), (-96, 52), (-40, 40), (0, 56), (40, 40), (96, 52), (128, 24), (104, -10), (46, -4), (0, 36)], cx, cy, s))
        fill(c, hp, color); fill(c, hp, None, shader=linear((cx, cy - 10 * s), (cx, cy + 60 * s), [rgba(hi, 160), rgba(color, 0)]))
        ink(c, hp, 3.6 * s, seed=seed + 2)
    for side in (1, -1):
        stroke(c, smooth(xf([(side * 22, 40), (side * 26, 120), (side * 20, 190)], cx, cy, s), False), 4 * s, '#d9d4c4')
        c.drawCircle(cx + side * 20 * s, cy + 194 * s, 5 * s, paint('#b8b2a2'))
    ink(c, body, 6 * s, seed=seed + 3)

# ---------------------------------------------------------------- NIKKI
NIKKI_FACE = sym([(0, -116), (-46, -112), (-70, -96), (-77, -62), (-78, -24), (-76, 14), (-70, 52),
                  (-59, 88), (-41, 118), (-20, 136), (0, 142)])
HAIR_COL, HAIR_HI = '#1c110c', '#5a3a28'

def nikki_hair_back(c, cx, cy, s, tilt=0.0, turn=0.0, length=1.0, seed=300, wild=0.0):
    """Long wavy dark hair behind head and shoulders (draw before body)."""
    h = Head(cx, cy, s, tilt, turn)
    L = 360 * length
    pts = [(0, -188), (-62, -182), (-104, -150), (-122, -96), (-128, -20), (-140, 60), (-150 - wild * 30, 160),
           (-156 - wild * 40, L * 0.75), (-138 - wild * 20, L), (-96, L * 0.92), (-60, L * 0.8), (0, L * 0.6)]
    full = pts + [(-x, y) for x, y in reversed(pts[1:-1])]
    hp = h.P(full)
    fill(c, hp, HAIR_COL)
    for k in range(9):  # wavy strand lines
        x0 = -118 + k * 8
        wav = [(x0 - 10 * math.sin(j * 0.9 + k), -60 + j * 50) for j in range(int(L / 50) + 1)]
        stroke(c, h.L(wav), 1.6 * s, HAIR_HI, 110, wobble=0.8)
        stroke(c, h.L([(-x, y) for x, y in wav]), 1.6 * s, HAIR_HI, 110, wobble=0.8)
    ink(c, hp, 4.5 * s, seed=seed)
    return h

def nikki_head(c, cx, cy, s, smile=0.6, open_=0.0, teeth=False, eye=1.0, pupil=1.0, brow=0.0, look=(0, 0),
               tilt=0.0, turn=0.0, mode='warm', lit=1.0, blush=0.5, catch=True, strands=0.0, seed=320, pale=0.0):
    """Nikki: soft oval face, big lashed eyes, full lips, middle-parted long wavy hair."""
    h = Head(cx, cy, s, tilt, turn)
    face = h.P(NIKKI_FACE)
    top = '#e9b98c' if not pale else '#d8c2a8'
    fill(c, face, None, shader=linear((cx, cy - 120 * s), (cx, cy + 150 * s), [rgba(top, 255), rgba('#c58a5e', 255), rgba('#a8693f', 255)], [0, 0.5, 1]))
    c.save(); c.clipPath(face, skia.ClipOp.kIntersect, True)
    face_light(c, h, face, mode, lit, 80)
    if pale:
        fill(c, face, '#9fb4b8', int(70 * pale), blend=skia.BlendMode.kColor)
    for sock in both([(-60, -22), (-44, -32), (-16, -28), (-6, -12), (-10, 4), (-32, 10), (-54, 8), (-64, -8)]):
        shade(c, h.P(sock), 'skin_lo', int((70 + 120 * pale) * lit), blur=6 * s)
    if blush:
        for side in (1, -1):
            (bx, by), = h.X([(side * 46, 42)])
            c.drawCircle(bx, by, 20 * s, paint(shader=radial(bx, by, 20 * s, [rgba('#e0606a', int(110 * blush)), rgba('#e0606a', 0)])))
    shade(c, h.P([(-78, 96), (-46, 124), (0, 146), (46, 124), (78, 96), (78, 180), (-78, 180)]), 'skin_deep', 100, blur=8 * s)
    c.restore()
    eyes(c, h, 33, eye, pupil, look, lash=True, brow=brow, brow_col='#1e120c', mode=mode, lit=lit,
         iris='#4a2414', catch=catch, sclera='#f2e9dc' if not pale else '#e4ecea', lid_shadow=int(60 * pale))
    stroke(c, h.L([(-7, -2), (-9, 22), (-11, 40)]), 1.5 * s, a=110)
    for side in (1, -1):
        stroke(c, h.L([(side * 8, 46), (side * 15, 52), (side * 14, 58), (side * 6, 60)]), 2.6 * s)
    stroke(c, h.L([(-6, 61), (0, 58), (6, 61)]), 1.8 * s)
    mouth(c, h, 88, 24 + max(0, smile) * (16 if teeth else 3), smile, open_, teeth, lip='#b0484a', full=1.15)
    ink(c, face, 4.6 * s, seed=seed + 4)
    # front hair: middle part, curtains framing the face
    for side in (1, -1):
        cur = h.P([(side * 2, -188), (side * 64, -180), (side * 110, -144), (side * 124, -70), (side * 116, -10),
                   (side * 132, 50), (side * 120, 110), (side * 140, 170), (side * 112, 230), (side * 92, 170),
                   (side * 98, 110), (side * 82, 50), (side * 86, -10), (side * 74, -70), (side * 58, -110),
                   (side * 28, -124), (side * 4, -130)])
        fill(c, cur, HAIR_COL)
        for k in range(4):
            stroke(c, h.L([(side * (12 + k * 18), -170 + k * 6), (side * (64 + k * 12), -120), (side * (90 + k * 8), -20), (side * (100 + k * 6), 120)]),
                   1.8 * s, HAIR_HI, 150, wobble=0.6)
        ink(c, cur, 4 * s, seed=seed + side)
    light(c, h.P([(-70, -160), (-20, -182), (-30, -160), (-80, -130)]), HAIR_HI, 170, blur=8 * s)
    light(c, h.P([(70, -160), (20, -182), (30, -160), (80, -130)]), HAIR_HI, 120, blur=8 * s)
    if strands:  # loose strands falling across the face
        for k, (x0, x1) in enumerate([(-20, -36), (10, 26), (-50, -30)][:max(1, int(strands * 3))]):
            stroke(c, h.L([(x0, -128), (x0 - 6, -60), (x1, 0), (x1 + 4, 60)]), 2.6 * s, HAIR_COL, 230, wobble=1.0)
    return h

def sweater(c, cx, cy, s, seed=360, color='#8f1c22', hi='#c9434a', shoulders=0.0):
    """Nikki's red knit sweater. shoulders: lift (+) / drop (-) asymmetry for unnatural poses."""
    TURN[0] = 0.0
    neck = smooth(xf([(-34, -60), (-38, 30), (38, 30), (34, -60)], cx, cy, s))
    fill(c, neck, '#b77a50'); shade(c, neck, 'skin_deep', 150)
    a = shoulders
    body = poly(xf([(-44, 6), (-92, 18 - a * 20), (-136, 40 - a * 40), (-162, 80 - a * 50), (-168, 150 - a * 30), (-156, 320), (-160, 900),
                    (160, 900), (156, 320), (168, 150 + a * 30), (162, 80 + a * 50), (136, 40 + a * 40), (92, 18 + a * 20), (44, 6)], cx, cy, s))
    fill(c, body, color)
    fill(c, body, None, shader=radial(cx - 30 * s, cy + 50 * s, 240 * s, [rgba(hi, 190), rgba(color, 0)]))
    c.save(); c.clipPath(body, skia.ClipOp.kIntersect, True)
    for k in range(-9, 10):  # rib-knit texture
        stroke(c, smooth(xf([(k * 22, 30), (k * 22 + 4, 300), (k * 22, 900)], cx, cy, s), False), 1.4 * s, '#4a080c', 90, wobble=0.8)
    c.restore()
    collar = smooth(xf([(-46, 2), (0, 30), (46, 2), (40, 18), (0, 44), (-40, 18)], cx, cy, s))
    fill(c, collar, '#7a161b'); ink(c, collar, 2.8 * s, seed=seed)
    ink(c, body, 6 * s, seed=seed + 1)

# ---------------------------------------------------------------- props
def willow_stick(c, x, y, s, rot=0.0, broken=0.0, glow_a=0, seed=400):
    """The One Wish Willow: a slender pale wooden stick. broken: 0 whole .. 1 snapped apart."""
    def seg(x0, x1, ang, dx, dy):
        pts = [(x0, -5), (x1, -4), (x1, 4), (x0, 5)]
        return smooth(xf([(px, py) for px, py in pts], x + dx * s, y + dy * s, s, rot=rot + ang), True)
    if broken <= 0:
        st = seg(-150, 150, 0, 0, 0)
        fill(c, st, '#cdb58a'); fill(c, st, None, shader=linear((x, y - 6 * s), (x, y + 6 * s), [rgba('#efe0b8', 255), rgba('#8a7048', 255)]))
        for kx in (-90, -20, 60):
            (kx_, ky_), = xf([(kx, 0)], x, y, s, rot=rot)
            c.drawCircle(kx_, ky_, 3 * s, paint('#6a5030'))
        ink(c, st, 2.6 * s, seed=seed)
    else:
        g = broken * 40
        for side, ang in ((-1, -0.25 * broken), (1, 0.25 * broken)):
            st = seg(0 if side > 0 else -150, 150 if side > 0 else 0, ang, side * g, -g * 0.3)
            fill(c, st, None, shader=linear((x, y - 6 * s), (x, y + 6 * s), [rgba('#efe0b8', 255), rgba('#8a7048', 255)]))
            ink(c, st, 2.6 * s, seed=seed + side)
        for k in range(7):  # splinters
            a = -1.2 + k * 0.4
            sx, sy = x + math.cos(a) * 10 * s, y + math.sin(a) * 10 * s
            stroke(c, smooth([(sx, sy), (sx + math.cos(a) * 18 * s, sy + math.sin(a) * 18 * s)], False), 2 * s, '#efe0b8', 230)
    if glow_a:
        glow(c, x, y, 160 * s, '#bfe8c0', glow_a)
        glow(c, x, y, 60 * s, '#ffffff', min(255, glow_a + 40))

def fist(c, x, y, s, rot=0.0, flip=False, tone='skin', seed=410):
    """A hand gripping something horizontal: knuckles toward camera."""
    f = -1 if flip else 1
    def T(pts):
        return xf([(f * px, py) for px, py in pts], x, y, s, rot=rot)
    palm = smooth(T([(-40, -36), (36, -40), (46, -6), (40, 40), (0, 54), (-38, 40), (-48, 4)]))
    fill(c, palm, tone); shade(c, palm, 'skin_deep', 80, blur=6 * s)
    for i, fx in enumerate((-30, -10, 10, 30)):
        k = smooth(T([(fx - 10, -40), (fx + 10, -40), (fx + 11, -14), (fx, -8), (fx - 11, -14)]))
        fill(c, k, tone); light(c, k, 'gold', 40, blur=3 * s); ink(c, k, 2.6 * s, seed=seed + i)
    th = smooth(T([(-46, -10), (-20, -30), (10, -30), (10, -18), (-20, -12), (-44, 8)]))
    fill(c, th, tone); ink(c, th, 2.6 * s, seed=seed + 9)
    sleeve = smooth(T([(-56, 30), (56, 30), (64, 140), (-64, 140)]))
    ink(c, palm, 3.2 * s, seed=seed + 7)
    return sleeve
