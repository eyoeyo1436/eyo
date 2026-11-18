"""Overlay frames for the GTA 6 Short: hook caption (0-2.5 s) and the Twitch logo + name badge that animates in when the clip starts."""
import sys, os, math, numpy as np, skia
from PIL import Image, ImageDraw
S, LOGO_SRC, AVATAR, OUT_A, OUT_B = sys.argv[1:6]
W, H, FPS = 1080, 1920, 60
VO = 0.1                                    # voice delay in the mix
WORDS = [('GTA', 0.03, 0), ('6', 0.62, 0), ('HEISTS', 0.87, 1), ('HAVE', 1.30, 1), ('BEGUN!', 1.48, 2)]
HOOK_OUT = 2.25                            # caption leaves, clip un-blurs
CLIP_START = 2.35                          # credit animation starts
END = 3.6                                  # after this the credit is static
END_T0, TOTAL = 19.9, 24.0                 # end card window
for d in (OUT_A, OUT_B):
    os.makedirs(d, exist_ok=True)

def font(name, size):
    return skia.Font(skia.Typeface.MakeFromFile(os.path.join(S, 'fonts', name)), size)

def ease_out(u):
    u = min(1, max(0, u)); return 1 - (1 - u) ** 3
def back_out(u, k=2.2):
    u = min(1, max(0, u)); u -= 1; return 1 + (k + 1) * u ** 3 + k * u ** 2

# logo: crop the purple tile from the supplied image and give it its rounded corners back
src = Image.open(LOGO_SRC).convert('RGB').crop((85, 34, 195, 144)).resize((440, 440), Image.LANCZOS)
mask = Image.new('L', (1760, 1760), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, 1759, 1759), radius=380, fill=255)
src.putalpha(mask.resize((440, 440), Image.LANCZOS))
LOGO = skia.Image.fromarray(np.ascontiguousarray(np.asarray(src)), colorType=skia.kRGBA_8888_ColorType)

CAP = {0: (font('Anton-Regular.ttf', 190), 760), 1: (font('Anton-Regular.ttf', 150), 935), 2: (font('Anton-Regular.ttf', 200), 1145)}
YEL = skia.Color(255, 214, 0); WHT = skia.ColorWHITE

def text_w(f, s):
    return f.measureText(s)

def caption(c, t):
    if t > HOOK_OUT + 0.25:
        return
    out = 1 - ease_out((t - HOOK_OUT) / 0.2)
    lines = {}
    for w, t0, ln in WORDS:
        lines.setdefault(ln, []).append((w, t0 + VO))
    for ln, words in lines.items():
        f, y = CAP[ln]
        sp = f.getSize() * 0.22
        total = sum(text_w(f, w) for w, _ in words) + sp * (len(words) - 1)
        x = (W - total) / 2
        for w, t0 in words:
            ww = text_w(f, w)
            u = (t - t0) / 0.16
            if u > 0:
                a = min(1, u * 2) * out
                sc = back_out(u) * (0.92 + 0.08 * out)
                cx, cy = x + ww / 2, y - f.getSize() * 0.35
                c.save(); c.translate(cx, cy); c.scale(sc, sc); c.translate(-cx, -cy)
                blob = skia.TextBlob(w, f)
                sh = skia.Paint(Color=skia.Color(0, 0, 0, int(150 * a)), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14), AntiAlias=True)
                c.drawTextBlob(blob, x + 6, y + 10, sh)
                st = skia.Paint(Color=skia.Color(0, 0, 0, int(255 * a)), Style=skia.Paint.kStroke_Style, StrokeWidth=f.getSize() * 0.09,
                                StrokeJoin=skia.Paint.kRound_Join, AntiAlias=True)
                c.drawTextBlob(blob, x, y, st)
                col = YEL if ln == 2 or w == '6' else WHT
                c.drawTextBlob(blob, x, y, skia.Paint(Color=skia.Color4f.FromColor(col).makeOpaque().toColor() & 0x00FFFFFF | (int(255 * a) << 24), AntiAlias=True))
                c.restore()
            x += ww + sp


NAME = 'jasontheween'
def oswald(size, wght):
    f = font('Oswald[wght].ttf', size)
    f.setTypeface(skia.Typeface.MakeFromFile(os.path.join(S, 'fonts', 'Oswald[wght].ttf')).makeClone(
        skia.FontArguments().setVariationDesignPosition(skia.FontArguments.VariationPosition(
            skia.FontArguments.VariationPosition.Coordinates([skia.FontArguments.VariationPosition.Coordinate(0x77676874, wght)])))))
    return f
NF = oswald(50, 600)
LS = 86                                   # logo size
CY = 1640                                 # badge centre line: bottom centre, above the game's own subtitles/prompts
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)

def credit(c, t):
    u = t - CLIP_START
    if u <= 0:
        return
    fade = 1 - ease_out((t - END_T0) / 0.35)
    if fade <= 0:
        return
    nw = NF.measureText(NAME)
    gap, padr = 16, 30
    full = LS + gap + nw + padr
    r = ease_out((u - 0.25) / 0.5)                      # unroll progress
    x_logo = W / 2 - LS / 2 + (((W - full) / 2) - (W / 2 - LS / 2)) * r
    ly = CY - LS / 2
    if r > 0:
        pw = (full - LS / 2) * r
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x_logo + LS / 2, CY - 34, pw, 68), 34, 34)
        sh = skia.Paint(Color=skia.Color(0, 0, 0, int(110 * fade * min(1, r * 1.5))), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10), AntiAlias=True)
        c.drawRRect(rr, sh)
        c.drawRRect(rr, skia.Paint(Color=skia.Color(14, 12, 20, int(200 * fade * min(1, r * 1.5))), AntiAlias=True))
        c.drawRRect(rr, skia.Paint(Color=skia.Color(145, 70, 255, int(230 * fade * min(1, r * 1.5))), Style=skia.Paint.kStroke_Style, StrokeWidth=3, AntiAlias=True))
        c.save(); c.clipRRect(rr, True)
        ta = ease_out((u - 0.45) / 0.4)
        tx = x_logo + LS + gap - (1 - ta) * 50
        c.drawString(NAME, tx, CY + NF.getSize() * 0.36, NF, skia.Paint(Color=skia.Color(255, 255, 255, int(255 * ta * fade)), AntiAlias=True))
        c.restore()
    p = back_out(u / 0.34, 2.6)
    a = min(1, u / 0.12) * fade
    c.save(); cx, cy = x_logo + LS / 2, CY
    c.translate(cx, cy); c.rotate((1 - min(1, u / 0.34)) * -30); c.scale(p, p); c.translate(-cx, -cy)
    c.drawImageRect(LOGO, skia.Rect.MakeXYWH(x_logo, ly, LS, LS), SAMP, skia.Paint(Alpha=int(255 * a), AntiAlias=True))
    c.restore()

# ------------------------------------------------------------------ end card
AV = skia.Image.open(AVATAR)
AV_D, AV_Y = 440, 700
TF = font('Anton-Regular.ttf', 118)
BF = oswald(64, 700)
RED = skia.Color(230, 33, 23)

def bell(c, x, y, s, ang, col):
    c.save(); c.translate(x, y); c.rotate(ang); c.scale(s, s)
    p = skia.Path(); p.moveTo(0, -30); p.cubicTo(20, -30, 24, -12, 24, 4); p.lineTo(30, 18); p.lineTo(-30, 18); p.lineTo(-24, 4)
    p.cubicTo(-24, -12, -20, -30, 0, -30); p.close()
    paint = skia.Paint(Color=col, AntiAlias=True)
    c.drawPath(p, paint); c.drawCircle(0, 25, 7, paint); c.drawCircle(0, -32, 5, paint)
    c.restore()

def cursor(c, x, y, s):
    p = skia.Path(); pts = [(0, 0), (0, 52), (13, 40), (22, 62), (31, 58), (22, 37), (40, 37)]
    p.moveTo(*pts[0]);  [p.lineTo(*q) for q in pts[1:]]; p.close()
    c.save(); c.translate(x, y); c.scale(s, s)
    c.drawPath(p, skia.Paint(Color=skia.Color(0, 0, 0, 120), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4), AntiAlias=True))
    c.drawPath(p, skia.Paint(Color=skia.ColorWHITE, AntiAlias=True))
    c.drawPath(p, skia.Paint(Color=skia.ColorBLACK, Style=skia.Paint.kStroke_Style, StrokeWidth=3, StrokeJoin=skia.Paint.kRound_Join, AntiAlias=True))
    c.restore()

def outlined(c, txt, x, y, f, col, a, stroke=0.08):
    blob = skia.TextBlob(txt, f)
    c.drawTextBlob(blob, x + 5, y + 8, skia.Paint(Color=skia.Color(0, 0, 0, int(140 * a)), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 12), AntiAlias=True))
    c.drawTextBlob(blob, x, y, skia.Paint(Color=skia.Color(0, 0, 0, int(255 * a)), Style=skia.Paint.kStroke_Style, StrokeWidth=f.getSize() * stroke, StrokeJoin=skia.Paint.kRound_Join, AntiAlias=True))
    c.drawTextBlob(blob, x, y, skia.Paint(Color=(col & 0x00FFFFFF) | (int(255 * a) << 24), AntiAlias=True))

CLICK = 22.05
def endcard(c, t):
    u = t - END_T0
    if u <= 0:
        return
    # darken
    dim = 0.45 * ease_out(u / 0.5)
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Color=skia.Color(0, 0, 0, int(255 * dim))))
    # avatar pops in with a purple ring and glow
    ua = u - 0.25
    if ua > 0:
        s = back_out(ua / 0.45, 1.8); a = min(1, ua / 0.15)
        cx, cy = W / 2, AV_Y
        c.save(); c.translate(cx, cy); c.scale(s, s); c.translate(-cx, -cy)
        c.drawCircle(cx, cy, AV_D / 2 + 26, skia.Paint(Color=skia.Color(145, 70, 255, int(150 * a)), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 40), AntiAlias=True))
        c.drawCircle(cx, cy, AV_D / 2 + 12, skia.Paint(Color=skia.Color(255, 255, 255, int(255 * a)), AntiAlias=True))
        c.drawCircle(cx, cy, AV_D / 2 + 6, skia.Paint(Color=skia.Color(145, 70, 255, int(255 * a)), AntiAlias=True))
        c.drawImageRect(AV, skia.Rect.MakeXYWH(cx - AV_D / 2, cy - AV_D / 2, AV_D, AV_D), SAMP, skia.Paint(Alpha=int(255 * a), AntiAlias=True))
        c.restore()
    # MORE GTA 6 VIDEOS
    ut = u - 0.55
    if ut > 0:
        a = min(1, ut / 0.2); dy = (1 - ease_out(ut / 0.4)) * 60
        parts = [('MORE ', skia.ColorWHITE), ('GTA 6', skia.Color(255, 214, 0)), (' VIDEOS', skia.ColorWHITE)]
        tw = sum(TF.measureText(p) for p, _ in parts); x = (W - tw) / 2
        for p, col in parts:
            outlined(c, p, x, 1100 + dy, TF, col, a); x += TF.measureText(p)
    # subscribe button
    ub = u - 0.9
    if ub > 0:
        clicked = t >= CLICK
        press = 1 - 0.08 * math.sin(math.pi * min(1, max(0, (t - CLICK + 0.06) / 0.18))) if t >= CLICK - 0.06 else 1
        s = back_out(ub / 0.4, 2.0) * press; a = min(1, ub / 0.15)
        label = 'SUBSCRIBED' if clicked else 'SUBSCRIBE'
        lw = BF.measureText(label)
        bw, bh = lw + 90, 118
        cx, cy = W / 2 - 50, 1290
        c.save(); c.translate(cx, cy); c.scale(s, s); c.translate(-cx, -cy)
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - bw / 2, cy - bh / 2, bw, bh), bh / 2, bh / 2)
        c.drawRRect(rr, skia.Paint(Color=skia.Color(0, 0, 0, int(120 * a)), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16), AntiAlias=True))
        col = skia.Color(72, 72, 78) if clicked else RED
        c.drawRRect(rr, skia.Paint(Color=(col & 0x00FFFFFF) | (int(255 * a) << 24), AntiAlias=True))
        c.drawString(label, cx - lw / 2, cy + BF.getSize() * 0.36, BF, skia.Paint(Color=skia.Color(255, 255, 255, int(255 * a)), AntiAlias=True))
        c.restore()
        # bell, rings after the click
        bx = cx + bw / 2 + 85
        ring = t - (CLICK + 0.15)
        ang = 22 * math.sin(ring * 28) * math.exp(-ring * 3.5) if ring > 0 else 0
        bcol = skia.Color(255, 214, 0) if ring > 0 else skia.ColorWHITE
        bell(c, bx, cy - 4, 1.35 * back_out(ub / 0.4, 2.0), ang, (bcol & 0x00FFFFFF) | (int(255 * a) << 24))
        # cursor glides in, clicks, glides off a little
        uc = t - (CLICK - 0.55)
        if uc > 0:
            k = ease_out(uc / 0.5)
            x = W + 40 + (cx + bw * 0.18 - W - 40) * k
            y = 1600 + (cy + 6 - 1600) * k
            if t > CLICK + 0.5:
                m = ease_out((t - CLICK - 0.5) / 0.4); x += 140 * m; y += 40 * m
            cursor(c, x, y, 1.5 * (0.88 if CLICK - 0.03 <= t < CLICK + 0.1 else 1.0))
    # fade to black
    fb = ease_out((t - (TOTAL - 0.75)) / 0.75)
    if fb > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Color=skia.Color(0, 0, 0, int(255 * fb))))

def frame(t):
    surf = skia.Surface(W, H); c = surf.getCanvas(); c.clear(skia.ColorTRANSPARENT)
    if t < END_T0:
        caption(c, t)
    endcard(c, t)
    credit(c, t)
    return surf.makeImageSnapshot()

for fi in range(int(END * FPS) + 1):
    frame(fi / FPS).save(os.path.join(OUT_A, f'o_{fi:04d}.png'), skia.kPNG)
nb = int(round((TOTAL - END_T0) * FPS))
for k in range(nb):
    frame(END_T0 + k / FPS).save(os.path.join(OUT_B, f'o_{k:04d}.png'), skia.kPNG)
print('frames', int(END * FPS) + 1, nb)
