"""Vertical Shorts cover (1080x1920), built from render.py's drawing pieces.

usage: python3 thumbnail.py thumbnail.png
"""
import sys
from PIL import Image, ImageDraw, ImageFilter
out = sys.argv[1]
sys.argv = ["render.py", "lines.json"]
import render as R

im = R.city(6.0)
im.alpha_composite(Image.new("RGBA", im.size, (40, 0, 0, 70)))
# red backlight behind the card
glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
ImageDraw.Draw(glow).ellipse([190, 560, 890, 1340], fill=(*R.RED, 150))
im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
card = R.card(0, 5).resize((546, 780), Image.BICUBIC).rotate(-6, Image.BICUBIC, expand=True)
sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
sh.putalpha(card.getchannel("A").point(lambda v: v * 0.8))
im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(25)), (R.W // 2 - card.width // 2 + 20, 600))
im.alpha_composite(card, (R.W // 2 - card.width // 2, 570))
d = ImageDraw.Draw(im)
R.rain(d, 3.3, 110)
R.text_c(d, 250, "THE DARK KNIGHT", R.font(R.BEBAS, 150), R.WHITE, stroke=6)
R.glow_text(im, 420, "WHY IT WORKED", R.font(R.BEBAS, 205), (*R.RED, 255), 20, 3)
# gold box-office badge
d = ImageDraw.Draw(im)
d.rounded_rectangle([170, 1460, 910, 1640], 26, fill=(10, 10, 14), outline=R.GOLD, width=6)
R.glow_text(im, 1552, "$1 BILLION", R.font(R.BEBAS, 170), (*R.GOLD, 255), 14, 1)
a = R.np.asarray(im.convert("RGB"), dtype=R.np.float32) * R.VIGN
a[..., 2] *= 1.06
Image.fromarray(R.np.clip(a, 0, 255).astype(R.np.uint8)).save(out)
