"""Graphic-novel drawing toolkit on top of skia: smooth shapes, ink lines, hatching, light."""
import math, random
import numpy as np
import skia

# ---- palette (warm, low-key, inspired by the film's amber grade) ----
def C(hexstr, a=255):
    h = hexstr.lstrip('#')
    return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

INK = '#0d0806'
PAL = dict(
    ink=INK, black='#0b0705', umber='#2a170c', brown='#4a2a16', amber='#c8873a', gold='#e7b45a',
    skin_hi='#e2ab74', skin='#b8774a', skin_mid='#97582f', skin_lo='#4b2513', skin_deep='#1f0d06',
    shirt_hi='#f2e4c6', shirt='#cdb791', shirt_lo='#6e5940', tux='#15100d', tux_hi='#3b332d',
    rose='#b5141f', rose_hi='#e0414a', rose_lo='#4f0609', grey_hair='#8c8277', grey_hi='#cfc6b8',
    hair_dark='#1a120d', hair_dk_hi='#4a3a2e', olive='#5a5a3a', olive_hi='#8e8a5c', olive_lo='#26261a',
)

def col(name_or_hex, a=255):
    return C(PAL.get(name_or_hex, name_or_hex), a)

# ---- geometry ----
def smooth(pts, closed=True, t=0.5):
    """Catmull-Rom spline through points -> skia.Path of cubics."""
    p = skia.Path()
    n = len(pts)
    if n < 2:
        return p
    P = [skia.Point(*q) for q in pts]
    p.moveTo(P[0])
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if (closed or i > 0) else P[i]
        p1 = P[i]
        p2 = P[(i + 1) % n]
        p3 = P[(i + 2) % n] if (closed or i + 2 < n) else P[(i + 1) % n]
        c1 = skia.Point(p1.x() + (p2.x() - p0.x()) * t / 3, p1.y() + (p2.y() - p0.y()) * t / 3)
        c2 = skia.Point(p2.x() - (p3.x() - p1.x()) * t / 3, p2.y() - (p3.y() - p1.y()) * t / 3)
        p.cubicTo(c1, c2, p2)
    if closed:
        p.close()
    return p

def poly(pts, closed=True):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if closed:
        p.close()
    return p

def xf(pts, cx, cy, s, sx=None, rot=0.0):
    """Transform local points (head space) to canvas."""
    sx = s if sx is None else sx
    cr, sr = math.cos(rot), math.sin(rot)
    out = []
    for x, y in pts:
        X, Y = x * sx, y * s
        out.append((cx + X * cr - Y * sr, cy + X * sr + Y * cr))
    return out

def mirror(pts):
    return [(-x, y) for x, y in pts]

def sym(half):
    """half: points from top-centre down the LEFT side to bottom-centre; returns full closed loop."""
    right = [(-x, y) for x, y in reversed(half[1:-1])]
    return half + right

# ---- painting ----
def paint(color=None, a=None, shader=None, blend=None, aa=True, blur=0):
    p = skia.Paint(AntiAlias=aa)
    if color is not None:
        c = col(color) if isinstance(color, str) else color
        if a is not None:
            c = skia.ColorSetA(c, int(a))
        p.setColor(c)
    if shader is not None:
        p.setShader(shader)
    if blend is not None:
        p.setBlendMode(blend)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p

def fill(c, path, color, a=None, blend=None, blur=0, shader=None):
    c.drawPath(path, paint(color, a, shader=shader, blend=blend, blur=blur))

def stroke(c, path, w=4, color=INK, a=None, wobble=0.0, seed=1, cap=True, blur=0):
    p = paint(color, a, blur=blur)
    p.setStyle(skia.Paint.kStroke_Style)
    p.setStrokeWidth(w)
    p.setStrokeCap(skia.Paint.kRound_Cap if cap else skia.Paint.kButt_Cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    if wobble:
        p.setPathEffect(skia.DiscretePathEffect.Make(max(6, w * 3), wobble, seed))
    c.drawPath(path, p)

def ink(c, path, w=5, color=INK, a=None, seed=1):
    """Ink outline: a slightly wobbly main stroke plus a thinner offset pass for a hand-drawn edge."""
    stroke(c, path, w, color, a, wobble=w * 0.18, seed=seed)
    stroke(c, path, max(1.2, w * 0.45), color, a if a is not None else 200, wobble=w * 0.35, seed=seed + 7)

def taper(c, pts, w0, w1, color=INK, a=None, closed=False):
    """Brush stroke with varying width along a polyline (filled polygon)."""
    sp = smooth(pts, closed=False)
    meas = skia.PathMeasure(sp, False)
    L = meas.getLength()
    if L <= 0:
        return
    N = max(8, int(L / 4))
    left, right = [], []
    for i in range(N + 1):
        d = L * i / N
        pos, tan = meas.getPosTan(d)
        u = i / N
        w = (w0 + (w1 - w0) * u) * (0.35 + 0.65 * math.sin(math.pi * min(1, max(0, u * 0.98 + 0.01))) ** 0.5)
        nx, ny = -tan.y(), tan.x()
        left.append((pos.x() + nx * w / 2, pos.y() + ny * w / 2))
        right.append((pos.x() - nx * w / 2, pos.y() - ny * w / 2))
    fill(c, poly(left + right[::-1]), color, a)

def hatch(c, clip, angle=-35, spacing=9, w=1.6, color=INK, a=150, seed=3, jitter=0.25, bounds=None):
    """Parallel hand-drawn hatching clipped to a path."""
    rnd = random.Random(seed)
    c.save()
    c.clipPath(clip, skia.ClipOp.kIntersect, True)
    b = bounds or clip.computeTightBounds()
    cx, cy = b.centerX(), b.centerY()
    R = math.hypot(b.width(), b.height()) / 2 + 10
    th = math.radians(angle)
    dx, dy = math.cos(th), math.sin(th)
    nx, ny = -dy, dx
    k = -R
    p = paint(color, a)
    p.setStyle(skia.Paint.kStroke_Style)
    p.setStrokeCap(skia.Paint.kRound_Cap)
    while k < R:
        off = k + rnd.uniform(-jitter, jitter) * spacing
        x0, y0 = cx + nx * off - dx * R, cy + ny * off - dy * R
        x1, y1 = cx + nx * off + dx * R, cy + ny * off + dy * R
        p.setStrokeWidth(w * rnd.uniform(0.7, 1.2))
        c.drawLine(x0, y0, x1, y1, p)
        k += spacing
    c.restore()

def radial(cx, cy, r, colors, stops=None):
    cols = [col(x) if isinstance(x, str) else x for x in colors]
    return skia.GradientShader.MakeRadial(skia.Point(cx, cy), r, cols, stops)

def linear(p0, p1, colors, stops=None):
    cols = [col(x) if isinstance(x, str) else x for x in colors]
    return skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)], cols, stops)

def rgba(colr, a):
    """skia colour from palette name / hex with alpha."""
    return col(colr, a)

def glow(c, cx, cy, r, color='gold', a=120, blend=skia.BlendMode.kScreen):
    sh = radial(cx, cy, r, [rgba(color, a), rgba(color, 0)])
    p = paint(shader=sh, blend=blend)
    c.drawCircle(cx, cy, r, p)

def shade(c, path, color='black', a=160, blur=0, blend=skia.BlendMode.kMultiply):
    fill(c, path, color, a, blend=blend, blur=blur)

def light(c, path, color='gold', a=120, blur=0, blend=skia.BlendMode.kScreen):
    fill(c, path, color, a, blend=blend, blur=blur)

def new_surface(w, h):
    s = skia.Surface(w, h)
    s.getCanvas().clear(skia.ColorTRANSPARENT)
    return s

def to_array(surface):
    """Return float32 RGBA premultiplied array in 0..1."""
    img = surface.makeImageSnapshot()
    a = img.toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
    return a.astype(np.float32) / 255.0

def paper_grain(w, h, seed=0, strength=0.06):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (h // 2 + 1, w // 2 + 1)).astype(np.float32)
    n = np.kron(n, np.ones((2, 2), np.float32))[:h, :w]
    return 1.0 + strength * n
