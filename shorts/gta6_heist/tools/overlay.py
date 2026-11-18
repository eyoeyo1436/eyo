"""Overlay frames for the GTA 6 Short: hook caption (0-2.5 s) and the Twitch logo + name badge that animates in when the clip starts."""
import sys, os, math, numpy as np, skia
from PIL import Image, ImageDraw
S, LOGO_SRC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
W, H, FPS = 1080, 1920, 60
VO = 0.1                                    # voice delay in the mix
WORDS = [('GTA', 0.03, 0), ('6', 0.62, 0), ('HEISTS', 0.87, 1), ('HAVE', 1.30, 1), ('BEGUN!', 1.48, 2)]
HOOK_OUT = 2.25                            # caption leaves, clip un-blurs
CLIP_START = 2.35                          # credit animation starts
END = 3.6                                  # after this the credit is static
os.makedirs(OUT, exist_ok=True)

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
NF = font('Oswald[wght].ttf', 33)
NF.setTypeface(skia.Typeface.MakeFromFile(os.path.join(S, 'fonts', 'Oswald[wght].ttf')).makeClone(
    skia.FontArguments().setVariationDesignPosition(skia.FontArguments.VariationPosition(
        skia.FontArguments.VariationPosition.Coordinates([skia.FontArguments.VariationPosition.Coordinate(0x77676874, 600)])))))
LS, LX, MARGIN = 58, 18, 22             # logo size, left x, bottom margin
LY = H - MARGIN - LS

def credit(c, t):
    u = t - CLIP_START
    if u <= 0:
        return
    # 1) logo pops in with a little spin
    p = back_out(u / 0.32, 2.6)
    a = min(1, u / 0.12)
    nw = text_w(NF, NAME)
    # 2) name pill unrolls from behind the logo, text slides in
    r = ease_out((u - 0.22) / 0.45)
    pill_w = (LS * 0.5 + 10 + nw + 16) * r
    if r > 0:
        py = LY + LS / 2
        rect = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(LX + LS * 0.5, py - 27, LS * 0.5 + pill_w - LS * 0.5 if pill_w > LS * 0.5 else pill_w, 54), 27, 27)
        rect = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(LX + LS * 0.5, py - 23, pill_w, 46), 23, 23)
        c.drawRRect(rect, skia.Paint(Color=skia.Color(12, 12, 16, int(185 * min(1, r * 1.5))), AntiAlias=True))
        c.save(); c.clipRect(skia.Rect.MakeXYWH(LX + LS * 0.5, py - 30, pill_w, 60))
        ta = ease_out((u - 0.38) / 0.35)
        tx = LX + LS + 9 - (1 - ta) * 40
        c.drawString(NAME, tx, py + NF.getSize() * 0.36, NF, skia.Paint(Color=skia.Color(255, 255, 255, int(255 * ta)), AntiAlias=True))
        c.restore()
    c.save()
    cx, cy = LX + LS / 2, LY + LS / 2
    c.translate(cx, cy); c.rotate((1 - min(1, u / 0.32)) * -25); c.scale(p, p); c.translate(-cx, -cy)
    c.drawImageRect(LOGO, skia.Rect.MakeXYWH(LX, LY, LS, LS), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear),
                    skia.Paint(Alpha=int(255 * a), AntiAlias=True))
    c.restore()

n = int(END * FPS) + 1
for fi in range(n):
    t = fi / FPS
    surf = skia.Surface(W, H); c = surf.getCanvas(); c.clear(skia.ColorTRANSPARENT)
    caption(c, t); credit(c, t)
    surf.makeImageSnapshot().save(os.path.join(OUT, f'o_{fi:04d}.png'), skia.kPNG)
print('frames', n)
