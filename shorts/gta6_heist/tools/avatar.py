"""Clean up the channel avatar: cut the circle out of the dark frame, upscale, sharpen, lift colour."""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB')
cx, cy, r = 97.0, 101.5, 95.5
im = im.crop((int(cx - r), int(cy - r), int(cx + r), int(cy + r)))
D = 840
im = im.resize((D // 2, D // 2), Image.BICUBIC).filter(ImageFilter.UnsharpMask(1.2, 60, 2))
im = im.resize((D, D), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2.0, 70, 3))
im = ImageEnhance.Contrast(im).enhance(1.06); im = ImageEnhance.Color(im).enhance(1.1)
m = Image.new('L', (D * 4, D * 4), 0); ImageDraw.Draw(m).ellipse((6, 6, D * 4 - 6, D * 4 - 6), fill=255)
im.putalpha(m.resize((D, D), Image.LANCZOS)); im.save(out); print(im.size)
