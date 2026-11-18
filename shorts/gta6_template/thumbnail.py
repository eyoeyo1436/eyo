"""Thumbnails for a GTA 6 Short, built from the full-resolution source clip.

  python3 thumbnail.py CLIP.mp4 OUT_PREFIX --t 24.5 --text "XQC'S FIRST|GTA 6|CARJACKING!" --name xqc
                       [--cam X,Y,W,H] [--face-t 28.5] [--cx 960]
Writes OUT_PREFIX_vertical.png (1080x1920, Shorts cover) and OUT_PREFIX_16x9.png (1280x720).
  --t      moment for the game picture; --cx its horizontal centre for the vertical crop
  --text   lines separated by |; the last line and any number are yellow
  --zoom   zoom in (e.g. 1.25) around --cx/--cy to cut the stream's own captions and overlays at the edges
  --cam    webcam rectangle in the source (streamer reaction inset); --face-t the moment for it (default --t)
"""
import argparse, os, re, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

A = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets') + '/'
YEL, PUR = (255, 214, 0), (145, 70, 255)

def grab(clip, t):
    p = tempfile.mktemp(suffix='.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', clip, '-frames:v', '1', p], check=True)
    return Image.open(p).convert('RGB')

def punch(im, sat=1.25, con=1.12):
    im = ImageEnhance.Color(im).enhance(sat); im = ImageEnhance.Contrast(im).enhance(con)
    return im.filter(ImageFilter.UnsharpMask(2.0, 80, 2))

def shade(im, axis, length, strength=230):
    """dark gradient from the top (axis=0) or the left (axis=1) for the text"""
    w, h = im.size
    n = h if axis == 0 else w
    g = (strength * np.clip(1 - np.arange(n) / length, 0, 1) ** 1.4).astype(np.uint8)
    m = Image.fromarray(np.tile(g[:, None], (1, w)) if axis == 0 else np.tile(g[None, :], (h, 1)))
    im.paste(Image.new('RGB', im.size, (0, 0, 0)), (0, 0), m)

def vignette(im, k=0.5):
    w, h = im.size; y, x = np.mgrid[0:h, 0:w]
    d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    m = np.clip(1 - k * np.clip(d - 0.45, 0, None) ** 1.4, 0, 1)
    return Image.fromarray((np.asarray(im).astype(float) * m[..., None]).astype(np.uint8))

def text(d, xy, s, size, fill, anchor):
    f = ImageFont.truetype(A + 'Anton-Regular.ttf', size)
    sw = max(4, size // 11)
    d.text((xy[0] + size * 0.04, xy[1] + size * 0.06), s, font=f, fill=(0, 0, 0), anchor=anchor, stroke_width=sw, stroke_fill=(0, 0, 0))
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=(0, 0, 0))

def fit(s, size, maxw):
    f = ImageFont.truetype(A + 'Anton-Regular.ttf', size)
    return min(size, int(size * maxw / max(1, f.getlength(s))))

def lines(d, parts, x, y0, maxw, sizes, anchor):
    y = y0
    for i, s in enumerate(parts):
        size = fit(s, sizes[min(i, len(sizes) - 1)] if i < len(parts) - 1 else sizes[-1], maxw)
        col = YEL if (i == len(parts) - 1) else 'white'
        if col == 'white' and re.search(r'\d', s):                     # "GTA 6": number in yellow
            m = re.search(r'\d+', s)
            pre, num = s[:m.start()], s[m.start():]
            f = ImageFont.truetype(A + 'Anton-Regular.ttf', size)
            total = f.getlength(s)
            sx = x - total / 2 if anchor == 'mm' else x
            text(d, (sx, y), pre, size, 'white', 'lm'); text(d, (sx + f.getlength(pre), y), num, size, YEL, 'lm')
        else:
            text(d, (x, y), s, size, col, anchor)
        y += size * 0.98

def rounded(im, r, border):
    w, h = im.size
    out = Image.new('RGBA', (w + 2 * border, h + 2 * border), (0, 0, 0, 0))
    bm = Image.new('L', (out.width * 4, out.height * 4), 0)
    ImageDraw.Draw(bm).rounded_rectangle((0, 0, out.width * 4 - 1, out.height * 4 - 1), radius=(r + border) * 4, fill=255)
    out.paste(Image.new('RGBA', out.size, PUR + (255,)), (0, 0), bm.resize(out.size, Image.LANCZOS))
    m = Image.new('L', (w * 4, h * 4), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 4 - 1, h * 4 - 1), radius=r * 4, fill=255)
    im = im.convert('RGBA'); im.putalpha(m.resize((w, h), Image.LANCZOS)); out.alpha_composite(im, (border, border))
    return out

def paste_shadow(canvas, im, xy):
    sh = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    blk = Image.new('RGBA', im.size, (0, 0, 0, 255)); blk.putalpha(im.split()[-1].point(lambda v: v * 0.6))
    sh.alpha_composite(blk, (xy[0] + 8, xy[1] + 12))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16))); canvas.alpha_composite(im, xy)

def badge(canvas, cx, cy, name, scale=1.0):
    LS = int(86 * scale)
    f = ImageFont.truetype(A + 'Oswald[wght].ttf', int(50 * scale)); f.set_variation_by_axes([600])
    nw = f.getlength(name); full = LS + 16 * scale + nw + 30 * scale; x0 = int(cx - full / 2)
    layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    h = 68 * scale
    d.rounded_rectangle((x0 + LS / 2, cy - h / 2, x0 + full, cy + h / 2), radius=h / 2, fill=(14, 12, 20, 215), outline=PUR + (255,), width=max(2, int(3 * scale)))
    d.text((x0 + LS + 16 * scale, cy), name, font=f, fill='white', anchor='lm')
    layer.alpha_composite(Image.open(A + 'twitch_logo.png').resize((LS, LS), Image.LANCZOS), (x0, int(cy - LS / 2)))
    canvas.alpha_composite(layer)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('clip'); ap.add_argument('out')
    ap.add_argument('--t', type=float, required=True); ap.add_argument('--text', required=True); ap.add_argument('--name', required=True)
    ap.add_argument('--cam'); ap.add_argument('--face-t', type=float); ap.add_argument('--cx', type=int, default=960)
    ap.add_argument('--text-y', type=int, default=320); ap.add_argument('--shift', type=int, default=0); ap.add_argument('--zoom', type=float, default=1.0); ap.add_argument('--cy', type=int, default=540)
    a = ap.parse_args()
    parts = [p.strip().upper() for p in a.text.split('|')]
    full = grab(a.clip, a.t)
    k = full.size[0] / 1920
    # optional zoom: drop the stream's caption strip / overlays at the edges (cy = vertical centre, 1080p units)
    zw, zh = int(full.size[0] / a.zoom), int(full.size[1] / a.zoom)
    zx = int(min(max(a.cx * k - zw / 2, 0), full.size[0] - zw)) if a.zoom > 1 else 0
    zy = int(min(max(a.cy * k - zh / 2, 0), full.size[1] - zh))
    src = full.crop((zx, zy, zx + zw, zy + zh)) if a.zoom > 1 else full
    sw, sh = src.size
    cam = None
    if a.cam:
        x, y, w, h = [int(v) for v in a.cam.split(',')]
        face = grab(a.clip, a.face_t if a.face_t is not None else a.t)
        cam = punch(face.crop((x, y, x + w, y + h)), 1.1, 1.06)
    # ---------- vertical
    cw = int(sh * 9 / 16)
    lo = cw / 2 + ((x + w) if cam and x < sw / 2 else 0)            # keep the webcam/chat column out of the crop
    cx = int(min(max(a.cx * k - zx, lo if a.zoom == 1 else cw / 2), sw - cw / 2))
    g = src.crop((cx - cw // 2, 0, cx - cw // 2 + cw, sh)).resize((1080, 1920), Image.LANCZOS)
    if a.shift:                                                   # push the picture down; dark blurred fill on top
        top = g.crop((0, 0, 1080, 1920 - a.shift))
        fill = g.resize((1080, 1920)).filter(ImageFilter.GaussianBlur(40))
        g = fill; g.paste(top, (0, a.shift))
    g = vignette(punch(g), 0.55); shade(g, 0, 820 + a.shift // 2)
    cv = Image.new('RGBA', (1080, 1920)); cv.paste(g)
    d = ImageDraw.Draw(cv)
    lines(d, parts, 540, a.text_y, 1000, [230, 200, 200], 'mm')
    if cam:
        ci = cam.resize((460, int(460 * cam.height / cam.width)), Image.LANCZOS)
        r = rounded(ci, 36, 10); paste_shadow(cv, r, (1080 - r.width - 34, 1880 - r.height - 150))
    badge(cv, 540 if not cam else 330, 1840, a.name)
    cv.convert('RGB').save(a.out + '_vertical.png')
    # ---------- 16:9
    g = vignette(punch(src.resize((1280, int(1280 * sh / sw)), Image.LANCZOS).crop((0, 0, 1280, 720))), 0.5)
    shade(g, 1, 700, 240)
    ch = Image.new('RGBA', (1280, 720)); ch.paste(g)
    d = ImageDraw.Draw(ch)
    lines(d, parts, 36, 140, 600, [170, 130, 150], 'lm')
    if cam:
        ci = cam.resize((300, int(300 * cam.height / cam.width)), Image.LANCZOS)
        r = rounded(ci, 26, 7); paste_shadow(ch, r, (1280 - r.width - 24, 720 - r.height - 24))
    badge(ch, 250, 650, a.name, 0.85)
    ch.convert('RGB').save(a.out + '_16x9.png')
    print('wrote', a.out + '_vertical.png', a.out + '_16x9.png')

if __name__ == '__main__':
    main()
