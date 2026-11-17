"""Fixed character designs (same construction in every shot).

All heads are authored in a local space: eye line at y=0, head ~200 units wide.
`s` scales local units to pixels. Lighting is the film's top-light: eyes sink into shadow.
"""
import math
import skia
from ink import (smooth, poly, xf, sym, mirror, fill, stroke, ink, taper, hatch, shade, light,
                 glow, radial, linear, rgba, paint, col)

M = skia.BlendMode.kMultiply
SCR = skia.BlendMode.kScreen

TURN = [0.0]   # current head turn (radians); 0 = frontal, + = head turned to viewer's right

def warp(pts):
    t = TURN[0]
    if not t:
        return pts
    R = 128.0
    out = []
    for x, y in pts:
        u = max(-0.999, min(0.999, x / R))
        z = 34.0 * math.exp(-(x / 24.0) ** 2) * (1.0 if -14 < y < 80 else 0.25)  # nose protrudes
        out.append((R * math.sin(math.asin(u) + t) + z * math.sin(t), y))
    return out

def P(pts, cx, cy, s, closed=True, rot=0.0):
    return smooth(xf(warp(pts), cx, cy, s, rot=rot), closed)

def L(pts, cx, cy, s, rot=0.0):
    return smooth(xf(warp(pts), cx, cy, s, rot=rot), False)

def X(pts, cx, cy, s):
    return xf(warp(pts), cx, cy, s)

def ear_visible(e):
    """Hide the far ear when the head turns."""
    t = TURN[0]
    return not (t and (e[0][0] > 0) == (t < 0) and abs(t) > 0.18)

def sideshade(c, face, cx, cy, s, hw):
    """Darken only the outer edges of the face (it turns away from the key light)."""
    t = TURN[0]
    off = 128 * math.sin(t) * 0.6
    sh = linear((cx + (off - hw) * s, cy), (cx + (off + hw) * s, cy),
                [rgba('skin_deep', 200), rgba('skin_deep', 0), rgba('skin_deep', 0), rgba('skin_deep', 200)], [0, 0.24, 0.76, 1])
    c.drawPath(face, paint(shader=sh, blend=M))

def both(pts):
    return [pts, mirror(pts)]

def shoulders(w, half=230, drop=64, chest=1.0):
    """Shoulder line: collar -> sloping shoulder -> deltoid -> arm going off-frame (smoothed polygon points)."""
    pts = [(-52, -6), (-110 * w, 10), (-(half - 40) * w, 34), (-half * w, drop), (-(half + 18) * w, drop + 70),
           (-(half + 22) * w, 260), (-(half + 26) * w, 900)]
    out = []
    for i in range(1, len(pts)):  # densify with a smooth curve for the top part only
        out.append(pts[i - 1])
    out.append(pts[-1])
    right = [(-x, y) for x, y in reversed(out)]
    return out + right

TUX_BODY = lambda w: smooth_pts(shoulders(w, 240, 70))
SUIT_BODY = lambda w: smooth_pts(shoulders(w, 214, 62))

def smooth_pts(pts, n=6):
    """Densify a polyline with Catmull-Rom so it can be drawn with poly() (keeps hard bottom corners)."""
    out = []
    N = len(pts)
    for i in range(N - 1):
        p0 = pts[max(0, i - 1)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(N - 1, i + 2)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                   + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    out.append(pts[-1])
    return out

# ------------------------------------------------------------------ VITO
VITO_FACE = sym([(0, -122), (-48, -119), (-76, -106), (-88, -80), (-92, -44), (-95, -8), (-100, 26),
                 (-108, 58), (-111, 90), (-102, 122), (-80, 148), (-46, 165), (0, 172)])
VITO_HAIR = sym([(0, -182), (-52, -178), (-92, -156), (-112, -116), (-117, -70), (-113, -36),
                 (-104, -20), (-96, -60), (-90, -96), (-70, -116), (-36, -124), (0, -126)])
VITO_EAR = [(-95, -30), (-111, -36), (-121, -12), (-118, 20), (-109, 44), (-97, 42)]

def vito_head(c, cx, cy, s, look=0.0, lit=1.0, seed=10, turn=0.0):
    """Don Vito Corleone: broad jowly face, swept-back grey hair, pencil moustache, heavy lids."""
    TURN[0] = turn
    # neck + collar shadow
    # hair (behind)
    hair = P(VITO_HAIR, cx, cy, s)
    fill(c, hair, '#3f362f')
    fill(c, hair, None, shader=linear((cx, cy - 185 * s), (cx, cy - 60 * s), [rgba('#6f655a', 255), rgba('#2a231e', 255)]))
    for side in (1, -1):  # grey at the temples
        light(c, P([(side * 72, -118), (side * 104, -104), (side * 114, -60), (side * 106, -30), (side * 94, -50), (side * 86, -96)], cx, cy, s), 'grey_hi', 150, blur=6 * s, blend=skia.BlendMode.kSrcOver)
    for k in range(-5, 6):  # combed-back strands
        x0 = k * 17
        stroke(c, L([(x0 * 0.6, -124), (x0 * 0.9, -150), (x0 * 1.05, -176)], cx, cy, s), 2.2 * s, '#2a221c', 170, wobble=0.6)
    for side in (1, -1):
        for k in range(4):
            pts = [(side * (-80 - k * 7), -112 + k * 6), (side * (-100 - k * 4), -80 + k * 8), (side * (-104 - k * 3), -40)]
            stroke(c, L(pts, cx, cy, s), 2.0 * s, '#2a221c', 150, wobble=0.5)
    ink(c, hair, 4.5 * s, seed=seed)
    # ears
    for e in [e for e in both(VITO_EAR) if ear_visible(e)]:
        ep = P(e, cx, cy, s)
        fill(c, ep, 'skin_mid'); shade(c, ep, 'skin_deep', 120)
        ink(c, ep, 3.5 * s, seed=seed + 1)
    # face base with vertical light falloff
    face = P(VITO_FACE, cx, cy, s)
    fill(c, face, 'skin')
    fill(c, face, None, shader=linear((cx, cy - 120 * s), (cx, cy + 175 * s),
                                      [rgba('skin_hi', 255), rgba('skin', 255), rgba('skin', 255), rgba('skin_mid', 255)],
                                      [0.0, 0.35, 0.75, 1.0]))
    c.save(); c.clipPath(face, skia.ClipOp.kIntersect, True)
    # side falloff (face turns away from the top light)
    sideshade(c, face, cx, cy, s, 112)
    # eye sockets in deep shadow (the famous Gordon Willis look)
    for sock in both([(-74, -26), (-54, -38), (-24, -34), (-10, -18), (-14, 2), (-38, 8), (-64, 6), (-78, -8)]):
        shade(c, P(sock, cx, cy, s), 'skin_deep', int(215 * lit), blur=7 * s)
    for sock in both([(-62, 4), (-40, 10), (-20, 6), (-26, 18), (-44, 24), (-60, 16)]):
        shade(c, P(sock, cx, cy, s), 'skin_lo', int(120 * lit), blur=6 * s)
    if TURN[0]:
        sd = -1 if TURN[0] > 0 else 1
        far = P([(sd * 130, -140), (sd * 30, -140), (sd * 52, 0), (sd * 40, 180), (sd * 130, 180)], cx, cy, s)
        shade(c, far, 'skin_deep', 150, blur=24 * s)
        hatch(c, far, angle=-60, spacing=7 * s, w=1.2 * s, color='skin_deep', a=70, seed=seed + 9)
    # under-nose / upper lip
    shade(c, P([(-30, 70), (0, 80), (30, 70), (26, 96), (0, 100), (-26, 96)], cx, cy, s), 'skin_deep', 150, blur=6 * s)
    # under lower lip, jowl underside, neck line
    shade(c, P([(-26, 118), (0, 130), (26, 118), (20, 140), (0, 146), (-20, 140)], cx, cy, s), 'skin_deep', 170, blur=6 * s)
    shade(c, P([(-112, 110), (-80, 150), (-40, 166), (0, 172), (40, 166), (80, 150), (112, 110), (112, 190), (-112, 190)], cx, cy, s), 'skin_deep', 130, blur=9 * s)
    # cheek shadow planes (hatched)
    for cheek in both([(-98, 10), (-76, 26), (-70, 60), (-78, 100), (-98, 96), (-104, 50)]):
        cp = P(cheek, cx, cy, s)
        shade(c, cp, 'skin_lo', 60, blur=5 * s)
        hatch(c, cp, angle=-55, spacing=6.5 * s, w=1.2 * s, color='skin_deep', a=70, seed=seed + 2)
    # highlights: forehead, nose ridge, cheek tops, chin
    light(c, P([(-50, -112), (0, -116), (50, -112), (42, -60), (0, -48), (-42, -60)], cx, cy, s), 'gold', int(110 * lit), blur=12 * s)
    light(c, P([(-7, -10), (7, -10), (10, 50), (0, 58), (-10, 50)], cx, cy, s), 'gold', int(130 * lit), blur=5 * s)
    for ch in both([(-74, 30), (-52, 26), (-44, 44), (-64, 54)]):
        light(c, P(ch, cx, cy, s), 'gold', int(70 * lit), blur=8 * s)
    light(c, P([(-18, 150), (0, 146), (18, 150), (0, 162)], cx, cy, s), 'gold', int(60 * lit), blur=5 * s)
    c.restore()
    # --- features
    # eyes (deep in shadow but alive: small warm catch-lights)
    for side in (1, -1):
        ex = side * 40 + look * 5
        eye = P([(side * 60, 3), (side * 48, -6), (side * 34, -8), (side * 22, -2), (side * 34, 5), (side * 50, 6)], cx, cy, s)
        fill(c, eye, '#2a160c')
        fill(c, P([(ex - 6, -4), (ex + 6, -4), (ex + 6, 4), (ex - 6, 4)], cx, cy, s), '#070302')
        (gx, gy), = X([(ex - side * 2, -2)], cx, cy, s)
        c.drawCircle(gx, gy, 1.8 * s, paint('gold', int(220 * lit)))
        stroke(c, L([(side * 64, 0), (side * 50, -10), (side * 32, -12), (side * 18, -4)], cx, cy, s), 3.6 * s)  # heavy upper lid
        stroke(c, L([(side * 66, -6), (side * 48, -19), (side * 28, -19), (side * 14, -10)], cx, cy, s), 2.4 * s, a=200)  # lid fold
        stroke(c, L([(side * 58, 14), (side * 42, 21), (side * 24, 15)], cx, cy, s), 2.0 * s, a=170)  # bag
        stroke(c, L([(side * 62, 24), (side * 44, 31), (side * 28, 27)], cx, cy, s), 1.6 * s, a=120)
        # brow: grey, low and heavy
        taper(c, X([(side * 74, -24), (side * 58, -36), (side * 36, -38), (side * 16, -30)], cx, cy, s), 9 * s, 6 * s, '#3b322a')
        taper(c, X([(side * 70, -27), (side * 54, -37), (side * 32, -37)], cx, cy, s), 3 * s, 2 * s, '#a59a8b', 160)
    # forehead creases
    for k, y in enumerate((-70, -84, -98)):
        stroke(c, L([(-46 + k * 4, y + 4), (-20, y - 2), (8, y), (40 - k * 4, y + 5)], cx, cy, s), 1.8 * s, a=110, wobble=1)
    # nose
    stroke(c, L([(-12, -10), (-15, 20), (-18, 46)], cx, cy, s), 2.2 * s, a=150)
    nose_tip = P([(-14, 50), (0, 44), (14, 50), (16, 64), (0, 70), (-16, 64)], cx, cy, s)
    light(c, nose_tip, 'gold', int(90 * lit), blur=3 * s)
    for side in (1, -1):
        stroke(c, L([(side * 14, 52), (side * 28, 60), (side * 26, 72), (side * 12, 74)], cx, cy, s), 3.6 * s)
        fill(c, P([(side * 10, 70), (side * 20, 68), (side * 18, 75), (side * 9, 75)], cx, cy, s), '#100604')
    stroke(c, L([(-10, 76), (0, 72), (10, 76)], cx, cy, s), 2.4 * s)
    # nasolabial folds and jowls (the heavy, weary face)
    for side in (1, -1):
        taper(c, X([(side * 28, 70), (side * 44, 92), (side * 50, 116), (side * 48, 134)], cx, cy, s), 5 * s, 2 * s)
        taper(c, X([(side * 52, 128), (side * 64, 144), (side * 72, 152)], cx, cy, s), 4 * s, 1.5 * s, a=200)
        stroke(c, L([(side * 74, 40), (side * 70, 70), (side * 74, 92)], cx, cy, s), 1.6 * s, a=110)
    # pencil moustache
    taper(c, X([(-36, 89), (-18, 84), (0, 86)], cx, cy, s), 2 * s, 6 * s, '#2d241e')
    taper(c, X([(0, 86), (18, 84), (36, 89)], cx, cy, s), 6 * s, 2 * s, '#2d241e')
    # mouth: downturned, lower lip pushed out
    lip = P([(-30, 107), (0, 104), (30, 107), (22, 118), (0, 123), (-22, 118)], cx, cy, s)
    fill(c, lip, '#7a3a24'); light(c, P([(-14, 110), (14, 110), (8, 116), (-8, 116)], cx, cy, s), 'gold', 60, blur=2 * s)
    taper(c, X([(-42, 112), (-30, 106), (-12, 103), (0, 105), (12, 103), (30, 106), (42, 112)], cx, cy, s), 3 * s, 3 * s)
    stroke(c, L([(-20, 124), (0, 128), (20, 124)], cx, cy, s), 2.0 * s, a=140)
    # chin dimple
    stroke(c, L([(-2, 148), (0, 156), (2, 162)], cx, cy, s), 1.8 * s, a=120)
    ink(c, face, 5.5 * s, seed=seed + 4)

def tuxedo(c, cx, cy, s, rose=True, seed=20, width=1.0, neck_w=66):
    """Black dinner jacket, white shirt, bow tie, red rose on the lapel. cy = chin position."""
    w = width
    TURN[0] = 0.0
    neck = P([(-neck_w * 0.9, -50), (-neck_w, 30), (neck_w, 30), (neck_w * 0.9, -50)], cx, cy, s)
    fill(c, neck, 'skin_mid'); shade(c, neck, 'skin_deep', 190)
    body = poly(xf(TUX_BODY(w), cx, cy, s))
    fill(c, body, 'tux')
    fill(c, body, None, shader=radial(cx - 60 * s, cy + 40 * s, 300 * s, [rgba('tux_hi', 200), rgba('tux', 0)]))
    shirt = P([(-60, -6), (0, 6), (60, -6), (40, 240), (0, 280), (-40, 240)], cx, cy, s)
    fill(c, shirt, 'shirt')
    fill(c, shirt, None, shader=linear((cx, cy), (cx, cy + 270 * s), [rgba('shirt_hi', 255), rgba('shirt_lo', 255)]))
    for k in range(3):
        c.drawCircle(cx, cy + (90 + k * 50) * s, 4 * s, paint('#1a1210'))
    # lapels (satin, catching the light)
    for side in (1, -1):
        lap = P([(side * 56, -4), (side * 130, 30), (side * 120, 120), (side * 44, 250), (side * 30, 220), (side * 66, 120), (side * 40, 20)], cx, cy, s)
        fill(c, lap, '#1d1714')
        light(c, P([(side * 70, 20), (side * 118, 40), (side * 108, 110), (side * 80, 100)], cx, cy, s), 'amber', 70, blur=10 * s)
        ink(c, lap, 3.5 * s, seed=seed + side)
    # bow tie
    for side in (1, -1):
        bt = P([(0, 10), (side * 40, -6), (side * 46, 22), (0, 22)], cx, cy, s)
        fill(c, bt, '#0f0a08'); ink(c, bt, 3 * s, seed=seed + 3)
    fill(c, P([(-8, 6), (8, 6), (8, 24), (-8, 24)], cx, cy, s), '#0f0a08')
    if rose:
        rx, ry = cx + 104 * s, cy + 92 * s  # on his left lapel (viewer's right)
        draw_rose(c, rx, ry, 30 * s, seed=seed + 5)
    ink(c, body, 6 * s, seed=seed + 6)

def draw_rose(c, x, y, r, seed=5):
    """Red rose boutonniere: layered cupped petals with a tight spiral heart."""
    def petal(ang, dist, size, squash=0.75, tone=('rose_lo', 'rose', 'rose_hi')):
        px, py = x + dist * r * math.cos(ang), y + dist * r * math.sin(ang) * 0.85
        pts = [(px + size * r * math.cos(a) * (1 + 0.12 * math.cos(2 * a)), py + size * r * squash * math.sin(a))
               for a in [ang + i * math.pi / 6 for i in range(12)]]
        pp = smooth(pts)
        fill(c, pp, None, shader=radial(px - 0.2 * size * r, py - 0.35 * size * r, size * r * 1.3,
                                         [rgba(tone[2], 255), rgba(tone[1], 255), rgba(tone[0], 255)], [0, 0.45, 1]))
        ink(c, pp, max(1.4, r * 0.05), seed=seed)
        return pp
    leaf = smooth([(x - r * 0.3, y + r * 0.7), (x - r * 1.4, y + r * 1.15), (x - r * 0.5, y + r * 1.45)])
    fill(c, leaf, None, shader=linear((x - r, y + r), (x, y + r * 1.4), [rgba('#4a6a2a', 255), rgba('#1c2a10', 255)]))
    ink(c, leaf, max(1.2, r * 0.05), seed=seed)
    stroke(c, smooth([(x - r * 1.2, y + r * 1.18), (x - r * 0.45, y + r * 1.1)], False), max(1, r * 0.03), '#0d1406', 180)
    for k in range(6):  # outer petals
        petal(-math.pi / 2 + k * math.pi / 3 + 0.3, 0.55, 0.62)
    for k in range(4):  # middle cup
        petal(-math.pi / 2 + k * math.pi / 2, 0.28, 0.5, 0.7)
    heart = smooth([(x + r * 0.32 * math.cos(a), y - r * 0.08 + r * 0.26 * math.sin(a)) for a in [i * math.pi / 6 for i in range(12)]])
    fill(c, heart, 'rose_lo'); ink(c, heart, max(1.4, r * 0.05), seed=seed)
    sp = [(x + r * 0.03 * k * math.cos(k * 0.9), y - r * 0.08 + r * 0.025 * k * math.sin(k * 0.9)) for k in range(1, 11)]
    stroke(c, smooth(sp, False), max(1.4, r * 0.05), '#2a0204')
    light(c, smooth([(x - r * 0.55, y - r * 0.55), (x - r * 0.1, y - r * 0.72), (x - r * 0.25, y - r * 0.4)]), 'rose_hi', 120, blur=r * 0.1)

# ------------------------------------------------------------------ MICHAEL
MIKE_FACE = sym([(0, -120), (-48, -116), (-72, -98), (-81, -66), (-83, -30), (-83, 6), (-80, 42),
                 (-74, 80), (-62, 112), (-42, 138), (-20, 152), (0, 156)])
MIKE_HAIR_LATE = sym([(0, -176), (-46, -172), (-80, -152), (-96, -112), (-99, -66), (-94, -30),
                      (-84, -36), (-80, -76), (-70, -104), (-40, -122), (0, -126)])
MIKE_HAIR_EARLY = [(4, -176), (-46, -170), (-82, -148), (-98, -108), (-99, -62), (-93, -30), (-84, -40),
                   (-80, -84), (-62, -100), (-38, -108), (-20, -102), (10, -114), (40, -118), (70, -104),
                   (82, -80), (86, -40), (94, -30), (99, -66), (96, -112), (80, -152), (46, -172)]
MIKE_EAR = [(-80, -26), (-95, -30), (-102, -6), (-99, 22), (-90, 40), (-80, 36)]

def michael_head(c, cx, cy, s, late=True, look=0.0, lit=1.0, stubble=0.0, seed=40, sweat=0.0, cold=None, turn=0.0):
    """Michael Corleone. late=False: the young war hero (softer, side-parted hair);
    late=True: the Don (slicked-back hair, hollow cheeks, eyes lost in shadow)."""
    TURN[0] = turn
    cold = late if cold is None else cold
    hair = P(MIKE_HAIR_LATE if late else MIKE_HAIR_EARLY, cx, cy, s)
    fill(c, hair, 'hair_dark')
    fill(c, hair, None, shader=radial(cx - 20 * s, cy - 160 * s, 90 * s, [rgba('hair_dk_hi', 230), rgba('hair_dark', 0)]))
    for k in range(-4, 5):
        x0 = k * 16
        pts = [(x0 * 0.6, -122), (x0 * 0.9, -150), (x0 * 1.1, -172)] if late else [(x0 * 0.8 - 30, -110), (x0 - 20, -145), (x0 * 1.1, -172)]
        stroke(c, L(pts, cx, cy, s), 2.0 * s, '#5c4a3c', 120, wobble=0.6)
    ink(c, hair, 4.5 * s, seed=seed)
    for e in [e for e in both(MIKE_EAR) if ear_visible(e)]:
        ep = P(e, cx, cy, s)
        fill(c, ep, 'skin_mid'); shade(c, ep, 'skin_deep', 110); ink(c, ep, 3.2 * s, seed=seed + 1)
    face = P(MIKE_FACE, cx, cy, s)
    top = 'skin_hi'
    fill(c, face, None, shader=linear((cx, cy - 120 * s), (cx, cy + 160 * s),
         [rgba(top, 255), rgba('skin', 255), rgba('skin', 255), rgba('skin_mid', 255)], [0, 0.35, 0.75, 1]))
    c.save(); c.clipPath(face, skia.ClipOp.kIntersect, True)
    sideshade(c, face, cx, cy, s, 86)
    sock_a = int((245 if cold else 175) * lit)
    if TURN[0]:
        sd = -1 if TURN[0] > 0 else 1
        far = P([(sd * 130, -140), (sd * 26, -140), (sd * 44, 0), (sd * 34, 180), (sd * 130, 180)], cx, cy, s)
        shade(c, far, 'skin_deep', 160, blur=22 * s)
        hatch(c, far, angle=-60, spacing=7 * s, w=1.2 * s, color='skin_deep', a=70, seed=seed + 9)
    for sock in both([(-66, -24), (-46, -36), (-18, -32), (-6, -16), (-10, 2), (-34, 8), (-58, 6), (-70, -8)]):
        shade(c, P(sock, cx, cy, s), 'skin_deep', sock_a, blur=7 * s)
    for sock in both([(-54, 4), (-34, 10), (-16, 6), (-22, 18), (-38, 22), (-52, 14)]):
        shade(c, P(sock, cx, cy, s), 'skin_lo', int(sock_a * 0.5), blur=5 * s)
    shade(c, P([(-24, 66), (0, 74), (24, 66), (20, 84), (0, 88), (-20, 84)], cx, cy, s), 'skin_deep', 140, blur=5 * s)
    shade(c, P([(-20, 104), (0, 112), (20, 104), (16, 124), (0, 128), (-16, 124)], cx, cy, s), 'skin_deep', 150, blur=6 * s)
    shade(c, P([(-86, 100), (-62, 132), (-30, 150), (0, 156), (30, 150), (62, 132), (86, 100), (86, 180), (-86, 180)], cx, cy, s), 'skin_deep', 120, blur=8 * s)
    for cheek in both([(-82, 20), (-62, 40), (-56, 74), (-66, 104), (-82, 92)]):
        cp = P(cheek, cx, cy, s)
        shade(c, cp, 'skin_lo', 130 if late else 80, blur=4 * s)
        hatch(c, cp, angle=-58, spacing=6 * s, w=1.2 * s, color='skin_deep', a=80 if late else 45, seed=seed + 2)
    if stubble:
        jaw = P([(-74, 70), (-56, 112), (-30, 140), (0, 150), (30, 140), (56, 112), (74, 70), (40, 96), (0, 92), (-40, 96)], cx, cy, s)
        shade(c, jaw, '#3a2c24', int(90 * stubble), blur=6 * s)
    light(c, P([(-44, -110), (0, -114), (44, -110), (36, -60), (0, -46), (-36, -60)], cx, cy, s), 'gold', int(115 * lit), blur=12 * s)
    light(c, P([(-6, -8), (6, -8), (9, 46), (0, 54), (-9, 46)], cx, cy, s), 'gold', int(135 * lit), blur=4 * s)
    for ch in both([(-66, 24), (-44, 22), (-38, 38), (-58, 48)]):
        light(c, P(ch, cx, cy, s), 'gold', int((55 if late else 85) * lit), blur=7 * s)
    if sweat:
        for k, (x, y) in enumerate([(-30, -70), (22, -80), (-52, -40), (48, -44), (6, -94)]):
            (gx, gy), = X([(x, y)], cx, cy, s)
            c.drawCircle(gx, gy, 2.2 * s, paint('#fff3d6', int(200 * sweat)))
    c.restore()
    for side in (1, -1):
        ex = side * 34 + look * 6
        eye = P([(side * 52, 2), (side * 42, -6), (side * 28, -7), (side * 17, -1), (side * 28, 5), (side * 44, 5)], cx, cy, s)
        fill(c, eye, '#c9b49a' if not cold else '#3a2214')
        iris = P([(ex - 6, -6), (ex + 6, -6), (ex + 6, 5), (ex - 6, 5)], cx, cy, s)
        fill(c, iris, '#1a0d07')
        (gx, gy), = X([(ex - 2 * side, -2)], cx, cy, s)
        c.drawCircle(gx, gy, 1.7 * s, paint('#ffe8c0', int((150 if cold else 230) * lit)))
        stroke(c, L([(side * 56, 0), (side * 44, -9), (side * 26, -10), (side * 14, -3)], cx, cy, s), 3.4 * s)
        stroke(c, L([(side * 56, -8), (side * 42, -17), (side * 24, -17), (side * 12, -9)], cx, cy, s), 1.8 * s, a=170)
        stroke(c, L([(side * 50, 12), (side * 36, 17), (side * 20, 12)], cx, cy, s), 1.8 * s, a=150 if late else 90)
        # thick dark brows, low over the eyes
        taper(c, X([(side * 66, -22), (side * 50, -31), (side * 30, -33), (side * 10, -27)], cx, cy, s), 11 * s, 8 * s, '#160e09')
    # nose: long, strong bridge with a slight bump
    stroke(c, L([(-10, -8), (-13, 18), (-15, 44)], cx, cy, s), 2.0 * s, a=150)
    for side in (1, -1):
        stroke(c, L([(side * 11, 48), (side * 22, 56), (side * 21, 66), (side * 9, 68)], cx, cy, s), 3.2 * s)
        fill(c, P([(side * 8, 64), (side * 17, 62), (side * 15, 69), (side * 7, 69)], cx, cy, s), '#100604')
    stroke(c, L([(-8, 70), (0, 66), (8, 70)], cx, cy, s), 2.2 * s)
    for side in (1, -1):  # philtrum
        stroke(c, L([(side * 5, 72), (side * 6, 84)], cx, cy, s), 1.4 * s, a=100)
    # mouth: firm and closed
    lip = P([(-26, 94), (0, 92), (26, 94), (18, 104), (0, 108), (-18, 104)], cx, cy, s)
    fill(c, lip, '#83432c')
    taper(c, X([(-30, 96), (-14, 92), (0, 94), (14, 92), (30, 96)], cx, cy, s), 3 * s, 3 * s)
    stroke(c, L([(-14, 110), (0, 114), (14, 110)], cx, cy, s), 1.8 * s, a=130)
    stroke(c, L([(-2, 136), (0, 144)], cx, cy, s), 1.6 * s, a=110)
    for side in (1, -1):
        stroke(c, L([(side * 22, 66), (side * 34, 86), (side * 36, 102)], cx, cy, s), 2.0 * s, a=130 if late else 80)
        if late:
            stroke(c, L([(side * 66, 40), (side * 58, 70), (side * 60, 96)], cx, cy, s), 1.6 * s, a=110)
    ink(c, face, 5 * s, seed=seed + 4)

def suit(c, cx, cy, s, seed=60, tie='#2a1712', width=1.0, neck_w=42):
    """Michael's dark suit: charcoal jacket, white shirt, dark tie. cy = chin."""
    w = width
    TURN[0] = 0.0
    neck = P([(-neck_w * 0.9, -50), (-neck_w, 30), (neck_w, 30), (neck_w * 0.9, -50)], cx, cy, s)
    fill(c, neck, 'skin_mid'); shade(c, neck, 'skin_deep', 190)
    body = poly(xf(SUIT_BODY(w), cx, cy, s))
    fill(c, body, '#1a1614')
    fill(c, body, None, shader=radial(cx - 50 * s, cy + 30 * s, 280 * s, [rgba('#4a403a', 190), rgba('#1a1614', 0)]))
    shirt = P([(-48, -4), (0, 8), (48, -4), (30, 220), (0, 250), (-30, 220)], cx, cy, s)
    fill(c, shirt, None, shader=linear((cx, cy), (cx, cy + 240 * s), [rgba('shirt_hi', 255), rgba('shirt_lo', 255)]))
    tiep = P([(-11, 14), (11, 14), (18, 160), (0, 200), (-18, 160)], cx, cy, s)
    fill(c, tiep, tie); ink(c, tiep, 2.6 * s, seed=seed)
    knot = P([(-14, 2), (14, 2), (10, 18), (-10, 18)], cx, cy, s)
    fill(c, knot, tie); ink(c, knot, 2.6 * s, seed=seed)
    for side in (1, -1):
        col_ = P([(side * 6, 4), (side * 46, -6), (side * 40, 30)], cx, cy, s)
        fill(c, col_, 'shirt_hi'); ink(c, col_, 2.6 * s, seed=seed + 1)
        lap = P([(side * 48, -2), (side * 118, 26), (side * 104, 110), (side * 36, 230), (side * 26, 200), (side * 58, 110), (side * 36, 16)], cx, cy, s)
        fill(c, lap, '#221d1a')
        light(c, P([(side * 62, 20), (side * 104, 36), (side * 96, 96), (side * 70, 90)], cx, cy, s), 'amber', 45, blur=10 * s)
        ink(c, lap, 3.2 * s, seed=seed + 2)
    ink(c, body, 6 * s, seed=seed + 3)

def marine_uniform(c, cx, cy, s, seed=70, neck_w=42):
    """Michael's Marine Corps service uniform from the wedding: olive coat, khaki shirt and tie, ribbons."""
    TURN[0] = 0.0
    neck = P([(-neck_w * 0.9, -50), (-neck_w, 30), (neck_w, 30), (neck_w * 0.9, -50)], cx, cy, s)
    fill(c, neck, 'skin_mid'); shade(c, neck, 'skin_deep', 190)
    body = poly(xf(SUIT_BODY(1.0), cx, cy, s))
    fill(c, body, 'olive')
    fill(c, body, None, shader=radial(cx - 40 * s, cy + 20 * s, 280 * s, [rgba('olive_hi', 220), rgba('olive', 0)]))
    shade(c, P([(-256, 200), (-200, 420), (-256, 420)], cx, cy, s), 'olive_lo', 160, blur=20 * s)
    shirt = P([(-46, -4), (0, 8), (46, -4), (24, 120), (0, 150), (-24, 120)], cx, cy, s)
    fill(c, shirt, '#b9a57a')
    tiep = P([(-10, 14), (10, 14), (14, 120), (0, 146), (-14, 120)], cx, cy, s)
    fill(c, tiep, '#9c8a60'); ink(c, tiep, 2.4 * s, seed=seed)
    for side in (1, -1):
        col_ = P([(side * 6, 4), (side * 44, -6), (side * 38, 28)], cx, cy, s)
        fill(c, col_, '#cdb98c'); ink(c, col_, 2.4 * s, seed=seed + 1)
        lap = P([(side * 48, -2), (side * 116, 26), (side * 100, 100), (side * 30, 160), (side * 22, 140), (side * 56, 96), (side * 36, 16)], cx, cy, s)
        fill(c, lap, '#4c4c30'); ink(c, lap, 3 * s, seed=seed + 2)
        # pocket flaps
        pk = P([(side * 70, 170), (side * 150, 170), (side * 146, 196), (side * 74, 196)], cx, cy, s)
        fill(c, pk, '#4c4c30'); ink(c, pk, 2.6 * s, seed=seed + 3)
        c.drawCircle(cx + side * 110 * s, cy + 188 * s, 5 * s, paint('#c9a24a'))
    # ribbon bar on his left chest
    cols_ = ['#7a1b1b', '#c9a24a', '#2a4a7a', '#7a1b1b', '#3a6a3a', '#c9a24a']
    for i, cc in enumerate(cols_):
        x = cx + (78 + (i % 3) * 22) * s; y = cy + (130 + (i // 3) * 12) * s
        c.drawRect(skia.Rect.MakeXYWH(x, y, 21 * s, 10 * s), paint(cc))
    for k in range(4):
        c.drawCircle(cx, cy + (190 + k * 56) * s, 6 * s, paint('#c9a24a'))
        stroke(c, smooth([(cx - 6 * s, cy + (190 + k * 56) * s), (cx + 6 * s, cy + (190 + k * 56) * s)], False), 1.2 * s, a=160)
    ink(c, body, 6 * s, seed=seed + 4)

def generic_head(c, cx, cy, s, hair='#1a120d', curly=False, recede=False, mustache=False, seed=90, lit=1.0, narrow=1.0, turn=0.0):
    TURN[0] = turn
    """Supporting family members (smaller in frame): simpler build, same ink/light treatment."""
    face_half = [(0, -118), (-46, -114), (-72, -96), (-80 * narrow, -60), (-82 * narrow, -20), (-82 * narrow, 20),
                 (-76 * narrow, 70), (-60, 110), (-36, 140), (0, 152)]
    face = P(sym(face_half), cx, cy, s)
    hy = -100 if recede else -112
    if curly:
        for k in range(16):
            a = math.pi * (1.05 + k / 15 * 0.9)
            hx, hyy = 92 * math.cos(a), -60 + 110 * math.sin(a)
            cp = smooth([(cx + (hx + 22 * math.cos(t)) * s, cy + (hyy + 20 * math.sin(t)) * s) for t in [i * math.pi / 4 for i in range(8)]])
            fill(c, cp, hair); ink(c, cp, 2.6 * s, seed=seed + k)
    else:
        hp = P(sym([(0, -172), (-48, -168), (-84, -146), (-96, -100), (-96, -50), (-88, -30), (-80, -70), (-64, hy), (0, hy - 10)]), cx, cy, s)
        fill(c, hp, hair); ink(c, hp, 4 * s, seed=seed)
    fill(c, face, None, shader=linear((cx, cy - 120 * s), (cx, cy + 150 * s),
         [rgba('skin_hi', 255), rgba('skin', 255), rgba('skin_mid', 255)], [0, 0.4, 1]))
    c.save(); c.clipPath(face, skia.ClipOp.kIntersect, True)
    sideshade(c, face, cx, cy, s, 84)
    for sock in both([(-62, -16), (-44, -28), (-16, -24), (-8, -8), (-12, 12), (-34, 20), (-58, 14)]):
        shade(c, P(sock, cx, cy, s), 'skin_deep', int(200 * lit), blur=5 * s)
    shade(c, P([(-80, 110), (0, 152), (80, 110), (80, 180), (-80, 180)], cx, cy, s), 'skin_deep', 110, blur=8 * s)
    light(c, P([(-6, -6), (6, -6), (8, 44), (-8, 44)], cx, cy, s), 'gold', int(120 * lit), blur=4 * s)
    c.restore()
    if curly:  # front curls over the forehead
        for k in range(7):
            x = -66 + k * 22
            cp = smooth([(cx + (x + 16 * math.cos(t)) * s, cy + (-112 + 14 * math.sin(t)) * s) for t in [i * math.pi / 4 for i in range(8)]])
            fill(c, cp, hair); ink(c, cp, 2.4 * s, seed=seed + 30 + k)
    for side in (1, -1):
        ex = side * 34
        (gx, gy), = X([(ex, 0)], cx, cy, s)
        c.drawCircle(gx, gy, 5 * s, paint('#120804'))
        stroke(c, L([(side * 50, 0), (side * 38, -8), (side * 22, -8), (side * 14, -2)], cx, cy, s), 3 * s)
        taper(c, X([(side * 62, -22), (side * 44, -30), (side * 14, -26)], cx, cy, s), 8 * s, 6 * s, hair if not recede else '#4a3a2c')
        stroke(c, L([(side * 10, 46), (side * 20, 56), (side * 10, 64)], cx, cy, s), 3 * s)
    if mustache:
        taper(c, X([(-28, 78), (0, 74), (28, 78)], cx, cy, s), 4 * s, 4 * s, hair)
    fill(c, P([(-22, 90), (0, 88), (22, 90), (14, 98), (0, 101), (-14, 98)], cx, cy, s), '#7e4029')
    taper(c, X([(-26, 92), (0, 90), (26, 92)], cx, cy, s), 2.6 * s, 2.6 * s)
    ink(c, face, 4.6 * s, seed=seed + 2)
