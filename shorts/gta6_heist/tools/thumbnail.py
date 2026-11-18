import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
A = '/home/user/eyo/shorts/gta6_template/assets/'
game_src = Image.open('u_8.6.png').convert('RGB')
cam_src = Image.open('u_6.9.png').convert('RGB')
logo = Image.open(A + 'twitch_logo.png')
YEL, RED, PUR = (255, 214, 0), (235, 30, 30), (145, 70, 255)

def punch(im, sat=1.25, con=1.15, sharp=True):
    im = ImageEnhance.Color(im).enhance(sat); im = ImageEnhance.Contrast(im).enhance(con)
    return im.filter(ImageFilter.UnsharpMask(2.2, 90, 2)) if sharp else im

def vignette(im, k=0.55):
    w, h = im.size; y, x = np.mgrid[0:h, 0:w]
    d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    m = np.clip(1 - k * np.clip(d - 0.45, 0, None) ** 1.4, 0, 1)
    return Image.fromarray((np.asarray(im).astype(float) * m[..., None]).astype(np.uint8))

def text(d, xy, s, size, fill, anchor='mm', stroke=None):
    f = ImageFont.truetype(A + 'Anton-Regular.ttf', size)
    sw = stroke or max(4, size // 11)
    x, y = xy
    d.text((x + size * 0.04, y + size * 0.06), s, font=f, fill=(0, 0, 0), anchor=anchor, stroke_width=sw, stroke_fill=(0, 0, 0))
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=(0, 0, 0))
    return f.getbbox(s, anchor=anchor)

def rounded(im, r, border=0, bcol=PUR):
    w, h = im.size
    m = Image.new('L', (w * 4, h * 4), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 4 - 1, h * 4 - 1), radius=r * 4, fill=255)
    m = m.resize((w, h), Image.LANCZOS)
    out = Image.new('RGBA', (w + 2 * border, h + 2 * border), (0, 0, 0, 0))
    if border:
        bm = Image.new('L', ((w + 2 * border) * 4, (h + 2 * border) * 4), 0)
        ImageDraw.Draw(bm).rounded_rectangle((0, 0, (w + 2 * border) * 4 - 1, (h + 2 * border) * 4 - 1), radius=(r + border) * 4, fill=255)
        out.paste(Image.new('RGBA', out.size, bcol + (255,)), (0, 0), bm.resize(out.size, Image.LANCZOS))
    im = im.convert('RGBA'); im.putalpha(m); out.alpha_composite(im, (border, border))
    return out

def shadow(canvas, im, xy, blur=18, off=(8, 12)):
    sh = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    a = im.split()[-1].point(lambda v: v * 0.6)
    blk = Image.new('RGBA', im.size, (0, 0, 0, 255)); blk.putalpha(a)
    sh.alpha_composite(blk, (xy[0] + off[0], xy[1] + off[1]))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    canvas.alpha_composite(im, xy)

def arrow(d, tip, tail, col, w):
    tip, tail = np.array(tip, float), np.array(tail, float)
    v = tip - tail; L = np.linalg.norm(v); u = v / L; n = np.array([-u[1], u[0]])
    head = tip - u * w * 2.6
    body = [tail + n * w / 2, head + n * w / 2, head + n * w * 1.5, tip, head - n * w * 1.5, head - n * w / 2, tail - n * w / 2]
    pts = [tuple(p) for p in body]
    d.polygon(pts, fill=(0, 0, 0)); d.line(pts + [pts[0]], fill=(0, 0, 0), width=12, joint='curve')
    d.polygon(pts, fill=col)

def badge(canvas, cx, cy, scale=1.0):
    LS = int(86 * scale)
    f = ImageFont.truetype(A + 'Oswald[wght].ttf', int(50 * scale)); f.set_variation_by_axes([600])
    name = 'jasontheween'; nw = f.getlength(name)
    full = LS + 16 * scale + nw + 30 * scale; x0 = int(cx - full / 2)
    layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    h = 68 * scale
    d.rounded_rectangle((x0 + LS / 2, cy - h / 2, x0 + full, cy + h / 2), radius=h / 2, fill=(14, 12, 20, 215), outline=PUR + (255,), width=max(2, int(3 * scale)))
    d.text((x0 + LS + 16 * scale, cy), name, font=f, fill='white', anchor='lm')
    layer.alpha_composite(logo.resize((LS, LS), Image.LANCZOS), (x0, int(cy - LS / 2)))
    canvas.alpha_composite(layer)

# game: crop out the clip's own caption bar and HUD prompts
game = game_src.crop((0, 640, 954, 1560))

# ---------------- vertical 1080x1920 (Shorts cover)
Wv, Hv = 1080, 1920
g = game.resize((int(954 * Hv / 920), Hv), Image.LANCZOS)
cx = int(g.width * 0.53)
g = g.crop((cx - Wv // 2, 0, cx + Wv // 2, Hv))
g = vignette(punch(g), 0.6)
cv = Image.new('RGBA', (Wv, Hv)); cv.paste(g)
top = Image.new('L', (1, Hv)); [top.putpixel((0, y), int(230 * max(0, 1 - y / 760) ** 1.6)) for y in range(Hv)]
cv.alpha_composite(Image.merge('RGBA', [Image.new('L', (Wv, Hv), 0)] * 3 + [top.resize((Wv, Hv))]))
d = ImageDraw.Draw(cv)
text(d, (Wv / 2, 215), 'GTA 6', 260, 'white')
text(d, (Wv / 2, 445), 'HEISTS HAVE', 170, YEL)
text(d, (Wv / 2, 640), 'BEGUN!', 210, YEL)
# arrow at the teller with his hands up
arrow(d, (640, 1040), (930, 820), RED, 46)
# streamer reaction inset
cam = punch(cam_src.crop((300, 40, 700, 520)).resize((400, 480), Image.LANCZOS), 1.1, 1.08)
cam_r = rounded(cam, 40, 10)
shadow(cv, cam_r, (Wv - cam_r.width - 36, 1290))
badge(cv, Wv / 2 - 140, 1820, 1.0)
cv.convert('RGB').save('/home/user/eyo/shorts/gta6_heist/thumbnail_vertical.png')

# ---------------- horizontal 1280x720 (YouTube thumbnail)
Wh, Hh = 1280, 720
sc = 1.6
g = game.resize((int(954 * sc), int(920 * sc)), Image.LANCZOS)
x0, y0 = 40, 540
g = vignette(punch(g.crop((x0, y0, x0 + Wh, y0 + Hh))), 0.5)
ch = Image.new('RGBA', (Wh, Hh)); ch.paste(g)
left = Image.new('L', (Wh, 1)); [left.putpixel((x, 0), int(235 * max(0, 1 - x / 640) ** 1.2)) for x in range(Wh)]
ch.alpha_composite(Image.merge('RGBA', [Image.new('L', (Wh, Hh), 0)] * 3 + [left.resize((Wh, Hh))]))
d = ImageDraw.Draw(ch)
text(d, (36, 130), 'GTA 6', 175, 'white', anchor='lm')
text(d, (36, 285), 'HEISTS HAVE', 104, YEL, anchor='lm')
text(d, (36, 410), 'BEGUN!', 140, YEL, anchor='lm')
arrow(d, (668, 318), (545, 470), RED, 30)
cam = punch(cam_src.crop((300, 40, 700, 520)).resize((250, 300), Image.LANCZOS), 1.1, 1.08)
cam_r = rounded(cam, 26, 7)
shadow(ch, cam_r, (Wh - cam_r.width - 24, Hh - cam_r.height - 24))
badge(ch, 270, 640, 0.85)
ch.convert('RGB').save('/home/user/eyo/shorts/gta6_heist/thumbnail_16x9.png')
print('ok')
