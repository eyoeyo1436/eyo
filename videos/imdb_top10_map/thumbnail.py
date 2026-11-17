"""YouTube thumbnail (1280x720) for the IMDb Top 10 filming-locations video.

usage: python3 thumbnail.py thumbnail.png
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import render as R
from films import FILMS

W, H = R.W, R.H
cam = (-3.0, -0.72, 250.0, (W * 0.5, H * 0.56))
im = R.BG.copy()
countries = {c for f in FILMS for *_, c in f[4]}
im.alpha_composite(R.draw_map(0, cam, countries, set(), 1.0))
# darken the left for the headline
g = np.linspace(1, 0, W)[None, :, None] ** 1.6
shade = (np.concatenate([np.zeros((H, W, 3)), np.ones((H, W, 1)) * 235 * g], 2)).astype(np.uint8)
shade[..., :3] = (4, 7, 14)
im.alpha_composite(Image.fromarray(shade, "RGBA"))
lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
firsts = [R.P(f[4][0][2], f[4][0][1]) for f in FILMS]
for k in range(1, len(firsts)):
    R.arc(lay, R.to_screen(cam, *firsts[k - 1]), R.to_screen(cam, *firsts[k]), 1.0, 150, 3)
for f in FILMS:
    for lab, la, lo, _ in f[4]:
        x, y = R.to_screen(cam, *R.P(lo, la))
        if f[0] != 1:
            R.pin(lay, glow, x, y, 1.0, None, 1, 0, 0)
im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12)))
im.alpha_composite(lay)
# hero pin with "#1 ?" (curiosity: which film is number one?)
hx, hy = R.to_screen(cam, *R.P(-82.5, 40.78))
lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(lay)
d.ellipse([hx - 150, hy - 330, hx + 150, hy - 30], fill=R.GOLD + (255,))
d.polygon([(hx - 120, hy - 140), (hx + 120, hy - 140), (hx, hy + 40)], fill=R.GOLD + (255,))
d.ellipse([hx - 115, hy - 295, hx + 115, hy - 65], fill=(10, 14, 26, 255))
d.text((hx, hy - 180), "#1", font=R.font(120, 900), fill=R.GOLD + (255,), anchor="mm")
d.text((hx + 112, hy - 300), "?", font=R.font(110, 900), fill=(255, 255, 255, 255), anchor="mm",
       stroke_width=8, stroke_fill=(10, 14, 26))
im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(40)))
im.alpha_composite(lay)
# headline
d = ImageDraw.Draw(im)
d.rounded_rectangle([70, 120, 330, 230], 22, fill=R.GOLD)
d.text((200, 175), "IMDb", font=R.font(84, 900), fill=(12, 12, 16), anchor="mm")
d.text((70, 355), "TOP 10", font=R.font(210, 900), fill=(255, 255, 255), anchor="lm", stroke_width=6, stroke_fill=(5, 8, 15))
d.text((76, 530), "WHERE WERE", font=R.font(92, 900), fill=R.GOLD, anchor="lm", stroke_width=5, stroke_fill=(5, 8, 15))
d.text((76, 640), "THEY FILMED?", font=R.font(92, 900), fill=R.GOLD, anchor="lm", stroke_width=5, stroke_fill=(5, 8, 15))
a = np.asarray(im.convert("RGB"), np.float32) * R.VIGN
Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((1280, 720), Image.LANCZOS).save(sys.argv[1])
