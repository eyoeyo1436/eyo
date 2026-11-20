import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
S, OUT = sys.argv[1], sys.argv[2]
F = S + '/fonts/'
RED = (235, 40, 40)
grin = Image.open(S + '/obt/k_26.3.png').convert('RGB')
bear = Image.open(S + '/obt/f_53.png').convert('RGB')

def text(d, xy, s, size, fill, anchor='mm', font='Anton-Regular.ttf'):
    f = ImageFont.truetype(F + font, size); sw = max(4, size // 11)
    d.text((xy[0] + size * .04, xy[1] + size * .06), s, font=f, fill=(0, 0, 0), anchor=anchor, stroke_width=sw, stroke_fill=(0, 0, 0))
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=(0, 0, 0))

def grad(im, y0, y1, a=255):
    w, h = im.size; g = np.zeros(h); g[y0:y1] = np.linspace(0, 1, y1 - y0) ** 1.2; g[y1:] = 1
    m = Image.fromarray(np.tile((g * a).astype(np.uint8)[:, None], (1, w)))
    im.paste(Image.new('RGB', im.size, (0, 0, 0)), (0, 0), m)

def red_vignette(im, k=0.9):
    w, h = im.size; y, x = np.mgrid[0:h, 0:w]
    d = np.clip(np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) - 0.55, 0, None)
    a = np.asarray(im).astype(float); t = np.clip(d * k, 0, 1)[..., None]
    a = a * (1 - t) + np.array([90, 0, 0]) * t * 0.6
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def circle_inset(img, box, size, ring=10):
    c = img.crop(box).resize((size, size), Image.LANCZOS)
    c = ImageEnhance.Contrast(c).enhance(1.1)
    out = Image.new('RGBA', (size + 2 * ring, size + 2 * ring), (0, 0, 0, 0)); d = ImageDraw.Draw(out)
    d.ellipse((0, 0, out.width - 1, out.height - 1), fill=RED + (255,))
    m = Image.new('L', (size * 4, size * 4), 0); ImageDraw.Draw(m).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    c = c.convert('RGBA'); c.putalpha(m.resize((size, size), Image.LANCZOS)); out.alpha_composite(c, (ring, ring))
    return out

# ---- vertical
g = ImageEnhance.Contrast(grin).enhance(1.12)
g = g.crop((0, 330, 1080, 1225)).resize((1300, 1077), Image.LANCZOS).crop((110, 0, 1190, 1077))
cv = Image.new('RGB', (1080, 1920), (0, 0, 0)); cv.paste(g, (0, 230))
grad(cv, 1100, 1300)
cv = red_vignette(cv)
cv = cv.convert('RGBA')
d = ImageDraw.Draw(cv)
text(d, (540, 1430), 'SHE LOVES HIM', 170, 'white')
text(d, (540, 1650), 'TOO MUCH', 250, RED)
text(d, (540, 1830), 'OBSESSION (2025)', 60, (220, 220, 220), font='Cinzel[wght].ttf')
cv.convert('RGB').save(OUT + '_vertical.png')

# ---- 16:9
face = ImageEnhance.Contrast(grin).enhance(1.12).crop((0, 520, 1080, 1225)).resize((1106, 722), Image.LANCZOS)
ch = Image.new('RGB', (1280, 720), (8, 0, 0)); ch.paste(face, (1280 - 1106 + 160, -1))
m = Image.fromarray(np.tile((255 * np.clip(1 - (np.arange(1280) - 560) / 260, 0, 1) ** 1.5).astype(np.uint8)[None, :], (720, 1)))
ch.paste(Image.new('RGB', ch.size, (8, 0, 0)), (0, 0), m)
ch = red_vignette(ch, 0.7).convert('RGBA')
d = ImageDraw.Draw(ch)
text(d, (40, 170), 'SHE LOVES HIM', 112, 'white', 'lm')
text(d, (40, 330), 'TOO MUCH', 170, RED, 'lm')
text(d, (40, 470), "OBSESSION (2025)", 44, (220, 220, 220), 'lm', 'Cinzel[wght].ttf')
ch.convert('RGB').save(OUT + '_16x9.png')
