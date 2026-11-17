"""'You Woke Up in Your Old Minecraft World' - nostalgic pixel-art Short (120 s).

Everything (world, textures, font, overlays) is procedurally drawn here.
Frames are rendered at 180x320 and upscaled with nearest-neighbour by ffmpeg
to 1080x1920 for crisp pixels.

usage: python3 render.py music.wav out.mp4 [--preview SECONDS]
"""
import subprocess
import sys

import numpy as np

W, H, B = 180, 320, 10
FPS = 30
DUR = 120.0
rng = np.random.default_rng(1436)

# ----------------------------------------------------------------- pixel font
F = {
 "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
 "B": ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
 "C": [" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "],
 "D": ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
 "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
 "F": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
 "G": [" ### ", "#   #", "#    ", "# ###", "#   #", "#   #", " ####"],
 "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
 "I": ["###", " # ", " # ", " # ", " # ", " # ", "###"],
 "J": ["  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "],
 "K": ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
 "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
 "M": ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
 "N": ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
 "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
 "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
 "Q": [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
 "R": ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
 "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
 "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
 "U": ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
 "V": ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
 "W": ["#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"],
 "X": ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
 "Y": ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
 "Z": ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
 "0": [" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "],
 "1": [" # ", "## ", " # ", " # ", " # ", " # ", "###"],
 "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
 "3": ["#####", "   # ", "  #  ", "   # ", "    #", "#   #", " ### "],
 "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
 "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
 "6": ["  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "],
 "7": ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
 "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
 "9": [" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "],
 ".": [" ", " ", " ", " ", " ", " ", "#"],
 ",": ["  ", "  ", "  ", "  ", "  ", " #", "# "],
 "!": ["#", "#", "#", "#", "#", " ", "#"],
 "?": [" ### ", "#   #", "    #", "   # ", "  #  ", "     ", "  #  "],
 "'": ["#", "#", " ", " ", " ", " ", " "],
 '"': ["# #", "# #", "   ", "   ", "   ", "   ", "   "],
 ":": [" ", "#", " ", " ", " ", "#", " "],
 "-": ["   ", "   ", "   ", "###", "   ", "   ", "   "],
 "<": ["   #", "  # ", " #  ", "#   ", " #  ", "  # ", "   #"],
 ">": ["#   ", " #  ", "  # ", "   #", "  # ", " #  ", "#   "],
 "*": ["     ", " # # ", "#####", "#####", " ### ", "  #  ", "     "],  # heart
 " ": ["  ", "  ", "  ", "  ", "  ", "  ", "  "],
}
GLYPH = {k: np.array([[c == "#" for c in row] for row in v]) for k, v in F.items()}


def text_width(s, scale=1):
    return sum((GLYPH[c].shape[1] + 1) * scale for c in s) - scale


def wrap(s, maxw, scale):
    lines, cur = [], ""
    for word in s.split(" "):
        if word == "\n":
            lines.append(cur)
            cur = ""
            continue
        t = (cur + " " + word).strip()
        if text_width(t, scale) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def draw_text(img, s, x, y, color, scale=1, shadow=(25, 25, 25), alpha=1.0):
    cx = x
    for c in s:
        g = GLYPH.get(c, GLYPH["?"])
        if scale > 1:
            g = g.repeat(scale, 0).repeat(scale, 1)
        h, w = g.shape
        for (ox, oy, col) in (((scale, scale, shadow),) if shadow else ()) + ((0, 0, color),):
            ys, xs = np.nonzero(g)
            ys = ys + y + oy
            xs = xs + cx + ox
            ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
            img[ys[ok], xs[ok]] = img[ys[ok], xs[ok]] * (1 - alpha) + np.array(col) * alpha
        cx += w + scale


def draw_block_text(img, s, cy, color, scale=1, alpha=1.0, maxw=W - 16, shadow=(25, 25, 25), full=None):
    # layout is computed on the full caption so typewriter text doesn't jump around
    full = full or s
    lines = wrap(full, maxw, scale)
    lh = 9 * scale
    y0 = int(cy - len(lines) * lh / 2)
    left = len(s)
    for i, ln in enumerate(lines):
        x = (W - text_width(ln, scale)) // 2
        part = ln[:max(0, left)]
        left -= len(ln) + 1
        if part:
            draw_text(img, part, x, y0 + i * lh, color, scale, shadow, alpha)


WHITE, YELLOW = (255, 255, 255), (255, 255, 85)


def draw_lines(img, lines, y0, scale, alpha):
    for i, (ln, col) in enumerate(lines):
        sh = (63, 63, 21) if col == YELLOW else (25, 25, 25)
        draw_text(img, ln, (W - text_width(ln, scale)) // 2, y0 + i * 9 * scale, col, scale, sh, alpha)


# ------------------------------------------------------------ block textures
AIR, GRASS, DIRT, STONE, LOG, LEAF, PLANK, COBBLE, GLASS, WATER, WHEAT, FARM, \
    TORCH, CHEST, SIGN, WEB, DOOR, SAND, ROSE, DANDE, TALL, COAL, IRON, DIA, BEDROCK, \
    FENCE = range(26)


def noise_tile(base, var, seed, alpha=255):
    r = np.random.default_rng(seed)
    t = np.zeros((B, B, 4))
    n = r.integers(-var, var + 1, size=(B, B, 1))
    t[..., :3] = np.clip(np.array(base) + n, 0, 255)
    t[..., 3] = alpha
    return t


def make_textures():
    T = {}
    for v in range(3):
        s = 100 + v * 17
        dirt = noise_tile((134, 96, 67), 14, s)
        for _ in range(6):
            y, x = rng.integers(0, B, 2)
            dirt[y, x, :3] = (105, 74, 52)
        grass = dirt.copy()
        top = noise_tile((106, 170, 64), 16, s + 1)
        r = np.random.default_rng(s + 2)
        for x in range(B):
            d = 2 + r.integers(0, 3)
            grass[:d, x] = top[:d, x]
        T[(DIRT, v)] = dirt
        T[(GRASS, v)] = grass
        stone = noise_tile((125, 125, 125), 12, s + 3)
        for _ in range(5):
            y, x = rng.integers(0, B - 1, 2)
            stone[y, x:x + 2, :3] = (100, 100, 100)
        T[(STONE, v)] = stone
        for ore, col in ((COAL, (30, 30, 30)), (IRON, (216, 175, 147)), (DIA, (90, 230, 220))):
            o = stone.copy()
            rr = np.random.default_rng(s + ore)
            for _ in range(5):
                y, x = rr.integers(1, B - 2, 2)
                o[y:y + 2, x:x + 2, :3] = col
            T[(ore, v)] = o
        cob = noise_tile((120, 120, 120), 10, s + 4)
        for _ in range(9):
            y, x = rng.integers(0, B - 2, 2)
            cob[y:y + 3, x:x + 3, :3] = rng.integers(95, 150)
        cob[::3, :, :3] *= 0.8
        T[(COBBLE, v)] = cob
        bed = noise_tile((60, 60, 60), 30, s + 5)
        T[(BEDROCK, v)] = bed
        sand = noise_tile((219, 207, 163), 9, s + 6)
        T[(SAND, v)] = sand
    plank = noise_tile((162, 130, 78), 8, 50)
    plank[[0, 5], :, :3] = (110, 85, 50)
    plank[1:5, 3, :3] = (130, 100, 60)
    plank[6:, 7, :3] = (130, 100, 60)
    T[(PLANK, 0)] = plank
    door = noise_tile((120, 88, 50), 8, 51)
    door[:, [0, 9], :3] = (80, 58, 34)
    door[[0, 9], :, :3] = (80, 58, 34)
    door[5, 7, :3] = (40, 40, 40)
    T[(DOOR, 0)] = door
    log = noise_tile((104, 82, 50), 10, 52)
    log[:, ::3, :3] = (78, 60, 36)
    T[(LOG, 0)] = log
    for v in range(3):
        leaf = noise_tile((58, 120, 38), 22, 60 + v)
        r = np.random.default_rng(70 + v)
        holes = r.random((B, B)) < 0.12
        leaf[holes, :3] = (30, 70, 20)
        T[(LEAF, v)] = leaf
    glass = np.zeros((B, B, 4))
    glass[..., :3] = (200, 230, 240)
    glass[..., 3] = 50
    glass[[0, -1], :, 3] = 230
    glass[:, [0, -1], 3] = 230
    glass[2, 2:4, 3] = 200
    glass[3, 2, 3] = 200
    T[(GLASS, 0)] = glass
    water = noise_tile((50, 90, 200), 10, 80, alpha=190)
    T[(WATER, 0)] = water
    farm = noise_tile((92, 60, 38), 8, 81)
    farm[::3, :, :3] = (70, 45, 28)
    T[(FARM, 0)] = farm
    for v in range(3):  # wheat stages
        wh = np.zeros((B, B, 4))
        r = np.random.default_rng(90 + v)
        for x in range(1, B, 2):
            hgt = 4 + v * 2 + r.integers(0, 2)
            col = [(90, 160, 40), (170, 170, 60), (215, 185, 80)][v]
            wh[B - hgt:, x, :3] = col
            wh[B - hgt:, x, 3] = 255
            wh[B - hgt:B - hgt + 2, x - 1 if x > 0 else x, :3] = col
            wh[B - hgt:B - hgt + 2, x - 1 if x > 0 else x, 3] = 255
        T[(WHEAT, v)] = wh
    torch = np.zeros((B, B, 4))
    torch[4:, 4:6, :3] = (110, 80, 45)
    torch[4:, 4:6, 3] = 255
    torch[2:4, 4:6, :3] = (255, 200, 60)
    torch[2:4, 4:6, 3] = 255
    torch[1, 4:6, :3] = (255, 245, 170)
    torch[1, 4:6, 3] = 255
    T[(TORCH, 0)] = torch
    chest = noise_tile((168, 116, 45), 8, 95)
    chest[[0, -1], :, :3] = (90, 60, 25)
    chest[:, [0, -1], :3] = (90, 60, 25)
    chest[4, :, :3] = (90, 60, 25)
    chest[3:6, 4:6, :3] = (200, 200, 200)
    T[(CHEST, 0)] = chest
    sign = np.zeros((B, B, 4))
    sign[1:6, :, :3] = (165, 130, 80)
    sign[1:6, :, 3] = 255
    sign[[1, 5], :, :3] = (120, 92, 55)
    sign[6:, 4:6, :3] = (100, 75, 45)
    sign[6:, 4:6, 3] = 255
    for yy in (2, 4):
        sign[yy, 2:8:2, :3] = (40, 30, 20)
    T[(SIGN, 0)] = sign
    web = np.zeros((B, B, 4))
    for i in range(B):
        for (yy, xx) in ((i, i), (i, B - 1 - i), (B // 2, i), (i, B // 2)):
            web[yy, xx] = (230, 230, 230, 170)
    web[2, 2:8] = web[7, 2:8] = (230, 230, 230, 140)
    T[(WEB, 0)] = web
    for kind, col in ((ROSE, (210, 30, 30)), (DANDE, (250, 220, 40))):
        f = np.zeros((B, B, 4))
        f[5:, 5, :3] = (50, 130, 30)
        f[5:, 5, 3] = 255
        f[7, 4, :3] = (50, 130, 30)
        f[7, 4, 3] = 255
        f[2:5, 4:7, :3] = col
        f[2:5, 4:7, 3] = 255
        f[3, 5, :3] = (250, 240, 120) if kind == ROSE else (220, 150, 20)
        T[(kind, 0)] = f
    tall = np.zeros((B, B, 4))
    r = np.random.default_rng(5)
    for x in range(1, B - 1):
        if r.random() < 0.6:
            h = r.integers(3, 8)
            tall[B - h:, x, :3] = (80 + r.integers(0, 40), 150 + r.integers(0, 30), 50)
            tall[B - h:, x, 3] = 255
    T[(TALL, 0)] = tall
    fence = np.zeros((B, B, 4))
    fence[:, 4:6] = (140, 110, 65, 255)
    fence[2:4, :] = (140, 110, 65, 255)
    fence[6:8, :] = (140, 110, 65, 255)
    T[(FENCE, 0)] = fence
    return T


TEX = make_textures()


def tex(kind, x, y):
    for v in (((x * 7 + y * 13) % 3), 0):
        if (kind, v) in TEX:
            return TEX[(kind, v)]
    raise KeyError(kind)


# ----------------------------------------------------------------- the world
NX, NY = 140, H // B
fg = np.zeros((NX, NY), dtype=int)
bgw = np.zeros((NX, NY), dtype=int)  # back walls

base = 21
surf = np.full(NX, base, dtype=float)
xs = np.arange(NX)
surf += np.round(0.8 * np.sin(xs * 0.35) + 0.6 * np.sin(xs * 0.13 + 1))
# hill around 92, lake 104-114
hill = 6 * np.exp(-((xs - 92) / 9.0) ** 2)
surf -= np.round(hill)
surf = surf.astype(int)
flat = {(20, 32): 21, (33, 47): 21, (55, 70): 21}
for (a, b), lvl in flat.items():
    surf[a:b] = lvl
surf[103:116] = 22

for x in range(NX):
    s = surf[x]
    for y in range(s, NY):
        if y == s:
            fg[x, y] = GRASS
        elif y < s + 3:
            fg[x, y] = DIRT
        elif y >= NY - 1:
            fg[x, y] = BEDROCK
        else:
            r = rng.random()
            fg[x, y] = DIA if (r < 0.012 and y > 27) else IRON if r < 0.04 else COAL if r < 0.09 else STONE
# small cave pocket underground
for x in range(8, 16):
    for y in range(26, 29):
        if (x - 12) ** 2 / 16 + (y - 27.5) ** 2 / 2.5 < 1:
            fg[x, y] = AIR
            bgw[x, y] = STONE
fg[12, 28] = TORCH
# lake
for x in range(104, 115):
    for y in range(22, 25):
        if y == 22 or (106 <= x <= 112) or (y == 23 and 105 <= x <= 113):
            fg[x, y] = WATER
for x in (103, 115):
    fg[x, 22] = SAND


def tree(x, top_h=4):
    s = surf[x]
    for k in range(1, top_h + 1):
        fg[x, s - k] = LOG
    ty = s - top_h
    for dx in range(-2, 3):
        for dy in range(-2, 1):
            if abs(dx) == 2 and dy == -2:
                continue
            if fg[x + dx, ty + dy] == AIR:
                fg[x + dx, ty + dy] = LEAF
    fg[x, ty - 2] = LEAF if fg[x, ty - 2] == AIR else fg[x, ty - 2]
    for dx in (-1, 0, 1):
        if fg[x + dx, ty - 3] == AIR:
            fg[x + dx, ty - 3] = LEAF


for tx, th in ((4, 4), (9, 5), (16, 4), (49, 4), (73, 5), (80, 4), (98, 4), (120, 5), (127, 4)):
    tree(tx, th)

# decoration
for x in range(NX):
    s = surf[x]
    if fg[x, s - 1] == AIR and fg[x, s] == GRASS:
        r = rng.random()
        if r < 0.22:
            fg[x, s - 1] = TALL
        elif r < 0.28:
            fg[x, s - 1] = ROSE
        elif r < 0.33:
            fg[x, s - 1] = DANDE

# --- dirt hut 24-29 (on surface 21)
HUT = (24, 29)
for x in range(HUT[0], HUT[1] + 1):
    for y in range(21 - 4, 21):
        fg[x, y] = AIR
        bgw[x, y] = DIRT
    fg[x, 17] = DIRT
for y in range(17, 21):
    fg[HUT[0], y] = DIRT
    fg[HUT[1], y] = DIRT
fg[HUT[1], 19] = AIR  # door hole
fg[HUT[1], 20] = AIR
fg[25, 18] = TORCH
fg[27, 20] = CHEST  # crafting/chest inside? -> a bed would be nicer, keep chest
fg[26, 16] = DIRT  # lumpy roof
fg[30, 20] = AIR
fg[31, 20] = SIGN
fg[30, 19] = TORCH
fg[30, 20] = AIR
# fix floor under hut to dirt
for x in range(HUT[0], HUT[1] + 1):
    fg[x, 21] = DIRT

# --- wheat farm 35-45 with water channel at 40
for x in range(35, 46):
    if x == 40:
        fg[x, 21] = WATER
    else:
        fg[x, 21] = FARM
        fg[x, 20] = WHEAT
fg[34, 20] = FENCE
fg[46, 20] = FENCE
fg[34, 19] = TORCH
# overgrown: flowers popping between
fg[47, 20] = AIR
# --- the old chest
CHEST_X = 48
fg[CHEST_X, 20] = CHEST
fg[CHEST_X, 19] = AIR

# --- friend's house 57-67
FH = (57, 67)
for x in range(FH[0], FH[1] + 1):
    fg[x, 21] = COBBLE
    for y in range(15, 21):
        fg[x, y] = AIR
        bgw[x, y] = PLANK
for y in range(15, 21):
    fg[FH[0], y] = LOG
    fg[FH[1], y] = LOG
for x in range(FH[0], FH[1] + 1):
    fg[x, 15] = PLANK
# roof steps
for i, y in enumerate(range(14, 10, -1)):
    for x in range(FH[0] - 1 + i, FH[1] + 2 - i):
        fg[x, y] = COBBLE if i % 2 == 0 else PLANK
for y in (17, 18):
    for x in (59, 60, 64, 65):
        fg[x, y] = GLASS
fg[62, 19] = DOOR
fg[62, 20] = DOOR
bgw[62, 19] = bgw[62, 20] = PLANK
fg[61, 18] = AIR
fg[58, 16] = WEB
fg[66, 16] = WEB
fg[63, 20] = CHEST
fg[60, 20] = WEB
fg[68, 20] = SIGN
fg[66, 19] = TORCH  # interior torch still burning

# torches up the hill and on top
for x in (76, 84, 89, 95, 101):
    s = surf[x]
    if fg[x, s - 1] in (AIR, TALL, ROSE, DANDE):
        fg[x, s - 1] = TORCH

TORCHES = [(x, y) for x in range(NX) for y in range(NY) if fg[x, y] == TORCH]

# render world image (RGBA) - foreground + back walls
WORLD = np.zeros((H, NX * B, 4))
for x in range(NX):
    for y in range(NY):
        px, py = x * B, y * B
        if bgw[x, y]:
            t = tex(bgw[x, y], x, y).copy()
            t[..., :3] *= 0.5
            WORLD[py:py + B, px:px + B] = t
        k = fg[x, y]
        if k:
            t = tex(k, x, y)
            a = t[..., 3:4] / 255
            WORLD[py:py + B, px:px + B, :3] = WORLD[py:py + B, px:px + B, :3] * (1 - a) + t[..., :3] * a
            WORLD[py:py + B, px:px + B, 3] = np.maximum(WORLD[py:py + B, px:px + B, 3], t[..., 3])
# subtle block outline shading for depth (top highlight / bottom shade on solids)
SOLID = {GRASS, DIRT, STONE, LOG, PLANK, COBBLE, FARM, COAL, IRON, DIA, BEDROCK, SAND, DOOR, CHEST}

# per-block light: sky light from above with depth falloff, torch light (block steps)
SKY = np.zeros((NX, NY))
for x in range(NX):
    lvl = 15
    for y in range(NY):
        SKY[x, y] = lvl
        if fg[x, y] in SOLID or bgw[x, y]:
            lvl = max(0, lvl - (3 if fg[x, y] in SOLID else 1))
TL = np.zeros((NX, NY))
for (tx, ty) in TORCHES:
    for x in range(max(0, tx - 14), min(NX, tx + 15)):
        for y in range(NY):
            TL[x, y] = max(TL[x, y], 14 - abs(x - tx) - abs(y - ty))
TL = TL.clip(0, 15)


def light_lut(level):
    return 0.06 + 0.94 * (0.82 ** (15 - level))


# ---------------------------------------------------------- background hills
def hill_layer(seed, amp, basey, color, width):
    r = np.random.default_rng(seed)
    cols = width // B + 2
    h = np.zeros(cols)
    v = 0
    for i in range(cols):
        v = np.clip(v + r.integers(-1, 2), -amp, amp)
        h[i] = v
    img = np.zeros((H, width, 4))
    for i in range(cols):
        top = int((basey - h[i]) * B)
        x0 = i * B
        img[top:, x0:x0 + B, :3] = color
        img[top:top + B, x0:x0 + B, :3] = np.array(color) * 1.12
        img[top:, x0:x0 + B, 3] = 255
    return img


FAR = hill_layer(3, 4, 15, (120, 150, 190), 1400)
MID = hill_layer(4, 3, 18, (80, 135, 85), 1600)

STARS = [(rng.integers(0, W), rng.integers(0, 190), rng.random()) for _ in range(90)]
CLOUDS = []
for i in range(10):
    cx = rng.integers(0, 900)
    cy = rng.integers(10, 110)
    cw = rng.integers(3, 7) * B
    CLOUDS.append((cx, cy, cw))

# ---------------------------------------------------------------- timeline


def keyed(t, pts):
    xs_, ys_ = zip(*pts)
    i = np.searchsorted(xs_, t) - 1
    i = int(np.clip(i, 0, len(xs_) - 2))
    a, b = xs_[i], xs_[i + 1]
    u = np.clip((t - a) / (b - a), 0, 1)
    u = u * u * (3 - 2 * u)
    return ys_[i] + (ys_[i + 1] - ys_[i]) * u


CAM = [(0, 7.5), (17, 14), (24, 24), (32, 27), (40, 29.5), (46, 31), (49, 38), (54, 42),
       (58, 47), (75, 48.5), (82, 62), (90, 64), (97, 75), (104, 84), (111, 90.5), (120, 93)]
DAY = [(0, 0.12), (4, 0.25), (18, 1.0), (86, 1.0), (93, 0.45), (98, 0.12), (108, 0.12),
       (116, 0.55), (120, 0.7)]
SUN = [(0, 230), (5, 205), (20, 70), (84, 70), (98, 230), (120, 230)]   # sun y on screen
MOON = [(0, 330), (92, 330), (100, 50), (108, 70), (118, 230), (120, 260)]
DAWN_SUN = [(0, 999), (106, 240), (120, 150)]

CAPS = [
    (0.9, 4.2, "YOU WAKE UP..."),
    (4.6, 10.2, "THE SUN IS RISING OVER THE BLOCKS."),
    (10.6, 17.2, "SOMETHING FEELS... FAMILIAR."),
    (17.6, 25.2, "THIS IS YOUR OLD WORLD. THE ONE YOU MADE WHEN YOU WERE 9."),
    (25.6, 33.2, "YOUR FIRST HOUSE. A TINY DIRT HUT."),
    (33.6, 40.2, "YOU HID IN HERE ON YOUR VERY FIRST NIGHT."),
    (40.6, 47.2, "THE SIGN STILL SAYS:"),
    (47.6, 54.2, "THE FARM YOU FORGOT ABOUT... IT KEPT GROWING."),
    (54.6, 60.2, "YOUR OLD CHEST IS STILL HERE."),
    (60.8, 68.2, "3 DIAMONDS. YOU WERE SAVING THEM FOR SOMETHING BIG."),
    (68.6, 75.2, "YOU NEVER USED THEM."),
    (75.6, 82.2, "YOUR BEST FRIEND'S HOUSE."),
    (82.6, 90.2, "THAT WAS THE LAST TIME YOU PLAYED TOGETHER."),
    (90.6, 97.2, "THE SUN GOES DOWN. JUST LIKE IT USED TO."),
    (97.6, 104.2, "THE TORCHES ARE STILL BURNING."),
    (104.6, 111.2, "MAYBE YOU NEVER REALLY OUTGREW IT."),
    (111.6, 116.6, "MAYBE IT WAS JUST... WAITING FOR YOU."),
]

VIGNETTE = None


def make_vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    return np.clip(1.08 - d ** 2 * 0.55, 0.45, 1)[..., None]


VIGNETTE = make_vignette()


def mix(a, b, u):
    return np.array(a) * (1 - u) + np.array(b) * u


def sky(t, day):
    top_day, hor_day = (110, 160, 250), (185, 215, 255)
    top_n, hor_n = (8, 10, 30), (25, 30, 65)
    top_dawn, hor_dawn = (90, 90, 170), (255, 150, 95)
    top = mix(top_n, top_day, day)
    hor = mix(hor_n, hor_day, day)
    # warm tint around sunrise/sunset
    warm = max(0, 1 - abs(day - 0.45) / 0.35)
    top = mix(top, top_dawn, warm * 0.5)
    hor = mix(hor, hor_dawn, warm * 0.85)
    g = np.linspace(0, 1, H)[:, None] ** 1.3
    col = top[None, :] * (1 - g) + hor[None, :] * g
    return np.repeat(col[:, None, :], W, axis=1)


def composite(dst, src, alpha_mul=1.0):
    a = src[..., 3:4] / 255 * alpha_mul
    dst[:] = dst * (1 - a) + src[..., :3] * a


def chest_ui(img, t, t0):
    u = np.clip((t - t0) / 0.35, 0, 1)
    img[:] = img * (1 - 0.45 * u)
    pw, ph = 9 * 16 + 8, 3 * 16 + 22
    x0 = (W - pw) // 2
    y0 = int(178 + (1 - u) * 40)
    panel = img[y0:y0 + ph, x0:x0 + pw]
    panel[:] = (198, 198, 198)
    panel[0, :] = panel[:, 0] = (255, 255, 255)
    panel[-1, :] = panel[:, -1] = (85, 85, 85)
    draw_text(img, "CHEST", x0 + 5, y0 + 5, (64, 64, 64), shadow=None)
    items = {3: "dia", 4: "dia", 5: "dia", 0: "sword", 10: "apple", 19: "book", 22: "seeds", 25: "map"}
    for i in range(27):
        sx = x0 + 4 + (i % 9) * 16
        sy = y0 + 16 + (i // 9) * 16
        img[sy:sy + 16, sx:sx + 16] = (139, 139, 139)
        img[sy, sx:sx + 16] = img[sy:sy + 16, sx] = (55, 55, 55)
        img[sy + 15, sx:sx + 16] = img[sy:sy + 16, sx + 15] = (255, 255, 255)
        it = items.get(i)
        if not it:
            continue
        ix, iy = sx + 3, sy + 3
        if it == "dia":
            pop = 1 + 0.15 * np.sin(t * 6 + i)
            shape = ["   ##   ", "  #### ", " ###### ", "########", " ###### ", "  ####  ", "   ##   ", "        "]
            for yy, row in enumerate(shape):
                for xx, c in enumerate(row):
                    if c == "#":
                        col = (150, 255, 245) if (xx + yy) % 4 == 0 else (60, 215, 205)
                        img[iy + yy + 1, ix + xx] = np.clip(np.array(col) * pop, 0, 255)
        elif it == "sword":
            for k in range(8):
                img[iy + 8 - k, ix + 1 + k] = (230, 230, 230) if k > 2 else (120, 80, 40)
        elif it == "apple":
            img[iy + 3:iy + 9, ix + 1:ix + 8] = (210, 30, 40)
            img[iy + 2, ix + 4] = (90, 60, 30)
            img[iy + 1, ix + 5:ix + 7] = (60, 160, 40)
        elif it == "book":
            img[iy + 1:iy + 9, ix + 1:ix + 8] = (120, 60, 40)
            img[iy + 2:iy + 8, ix + 2:ix + 7] = (240, 230, 200)
        elif it == "seeds":
            for (yy, xx) in ((3, 2), (5, 5), (7, 3), (4, 7)):
                img[iy + yy, ix + xx] = (70, 160, 50)
        elif it == "map":
            img[iy + 1:iy + 9, ix + 1:ix + 9] = (220, 205, 160)
            img[iy + 3:iy + 7, ix + 3:ix + 7] = (100, 150, 80)


def sign_closeup(img, t, t0):
    u = np.clip((t - t0) / 0.4, 0, 1)
    sw, sh = 140, 66
    x0 = (W - sw) // 2
    y0 = int(165 + (1 - u) * 30)
    a = u
    reg = img[y0:y0 + sh, x0:x0 + sw]
    wood = noise_tile((165, 130, 80), 8, 3)[..., :3]
    tile = np.tile(wood, (sh // B + 1, sw // B + 1, 1))[:sh, :sw]
    tile[::B // 2, :] *= 0.9
    reg[:] = reg * (1 - a) + tile * a
    reg[[0, -1], :] = reg[:, [0, -1]].mean() * 0 + np.array((110, 85, 50))
    draw_text(img, "MY HOUSE", (W - text_width("MY HOUSE")) // 2, y0 + 12, (20, 15, 10), shadow=None, alpha=a)
    draw_text(img, "NO GRIEFING!!", (W - text_width("NO GRIEFING!!")) // 2, y0 + 26, (20, 15, 10), shadow=None, alpha=a)
    draw_text(img, "- ME, AGE 9", (W - text_width("- ME, AGE 9")) // 2, y0 + 44, (60, 40, 25), shadow=None, alpha=a)


def player(img, x, y, day):
    # simple blocky person seen from behind-side, red hoodie
    def r(x0, y0, w, h, c):
        img[max(0, y0):y0 + h, max(0, x0):x0 + w] = np.array(c) * (0.35 + 0.65 * day)
    r(x + 1, y, 6, 6, (95, 60, 35))        # hair/back of head
    r(x + 5, y + 2, 2, 4, (220, 170, 130))  # face edge
    r(x, y + 6, 8, 8, (190, 45, 45))        # hoodie
    r(x + 2, y + 6, 4, 2, (160, 35, 35))
    r(x + 1, y + 14, 3, 7, (45, 55, 110))   # legs
    r(x + 4, y + 14, 3, 7, (40, 50, 100))


def frame(t):
    day = keyed(t, DAY)
    img = sky(t, day)
    cam = keyed(t, CAM) * B - W / 2
    night = 1 - day
    # stars
    if night > 0.4:
        sa = (night - 0.4) / 0.6
        for sx, sy, ph in STARS:
            tw = 0.6 + 0.4 * np.sin(t * 2.5 + ph * 20)
            img[sy, sx] = img[sy, sx] * (1 - sa * tw) + np.array((255, 255, 230)) * sa * tw
    # sun (morning/day/evening) and moon, plus second sunrise at the end
    sy = keyed(t, SUN)
    if sy < 225:
        sx = int(W * 0.72)
        sy = int(sy)
        img[sy - 9:sy + 9, sx - 9:sx + 9] = img[sy - 9:sy + 9, sx - 9:sx + 9] * 0.4 + np.array((255, 240, 160)) * 0.6
        img[sy - 7:sy + 7, sx - 7:sx + 7] = (255, 250, 200)
    my = int(keyed(t, MOON))
    if my < 225:
        mx = int(W * 0.25)
        img[my - 6:my + 6, mx - 6:mx + 6] = (225, 230, 240)
        img[my - 3:my + 1, mx - 4:mx - 1] = (190, 195, 210)
        img[my + 1:my + 4, mx + 1:mx + 4] = (200, 205, 215)
    if t > 106:
        dsy = int(keyed(t, DAWN_SUN))
        sx = int(W * 0.68)
        img[dsy - 10:dsy + 10, sx - 10:sx + 10] = img[dsy - 10:dsy + 10, sx - 10:sx + 10] * 0.5 + np.array((255, 190, 110)) * 0.5
        img[dsy - 8:dsy + 8, sx - 8:sx + 8] = (255, 225, 160)
    # clouds
    ca = 0.35 + 0.55 * day
    ccol = mix((60, 60, 90), (255, 255, 255), day)
    for cx, cy, cw in CLOUDS:
        x = int((cx - cam * 0.1 - t * 3) % 900) - 300
        if -cw < x < W:
            a, b = max(0, x), min(W, x + cw)
            img[cy:cy + B, a:b] = img[cy:cy + B, a:b] * (1 - ca) + ccol * ca
    # parallax hills tinted by daylight and haze
    for layer, par, haze in ((FAR, 0.15, 0.55), (MID, 0.4, 0.25)):
        off = int(cam * par) % (layer.shape[1] - W)
        crop = layer[:, off:off + W].copy()
        tint = 0.25 + 0.75 * day
        crop[..., :3] = crop[..., :3] * tint * (1 - haze) + img * haze
        composite(img, crop)
    # world
    ci = int(round(cam))
    ci = max(0, min(ci, NX * B - W))
    crop = WORLD[:, ci:ci + W].copy()
    # lighting grid
    bx0 = ci // B
    nb = W // B + 2
    sky_lvl = SKY[bx0:bx0 + nb].T * day
    flick = 0.6 * np.sin(t * 9.0) + 0.4 * np.sin(t * 13.7)
    lvl = np.maximum(sky_lvl, TL[bx0:bx0 + nb].T + flick * 0.5)
    L = light_lut(lvl)
    # warm torch tint where torch dominates
    warm = np.clip((TL[bx0:bx0 + nb].T - sky_lvl) / 10, 0, 1)
    Lp = L.repeat(B, 0).repeat(B, 1)
    Wp = warm.repeat(B, 0).repeat(B, 1)
    sh = ci - bx0 * B
    Lp = Lp[:H, sh:sh + W, None]
    Wp = Wp[:H, sh:sh + W, None]
    crop[..., :3] *= Lp
    crop[..., :3] *= 1 + Wp * np.array((0.35, 0.12, -0.25))
    composite(img, crop)
    # player on the hill at the end
    if t > 103:
        pa = np.clip((t - 103) / 1.5, 0, 1)
        if pa > 0:
            px = 91 * B - ci
            py = surf[91] * B - 21
            tmp = img.copy()
            player(tmp, px, py, max(day, 0.3))
            img = img * (1 - pa) + tmp * pa
    # sign close-up and chest UI
    if 42.2 <= t < 47.4:
        sign_closeup(img, t, 42.2)
    if 60.4 <= t < 68.6:
        chest_ui(img, t, 60.4)
    # chat message
    if 79.0 <= t < 89.5:
        a = np.clip((t - 79) / 0.2, 0, 1) * np.clip((89.5 - t) / 1.0, 0, 1)
        msg = "SAM LEFT THE GAME"
        y0 = 238
        bg = img[y0 - 2:y0 + 9, 4:4 + text_width(msg) + 6]
        bg[:] = bg * (1 - 0.5 * a)
        draw_text(img, msg, 7, y0, (255, 255, 85), shadow=(63, 63, 21), alpha=a)
        if t > 84:
            a2 = np.clip((t - 84) / 0.2, 0, 1) * np.clip((89.5 - t) / 1.0, 0, 1)
            m2 = "LAST ONLINE: 2014"
            bg = img[y0 + 9:y0 + 20, 4:4 + text_width(m2) + 6]
            bg[:] = bg * (1 - 0.5 * a2)
            draw_text(img, m2, 7, y0 + 11, (170, 170, 170), shadow=(42, 42, 42), alpha=a2)
    # nostalgic grade: warm, slightly faded, vignette, grain
    img = img * np.array((1.04, 1.0, 0.92)) * 0.94 + 10
    img *= VIGNETTE
    img += rng.normal(0, 3.0, size=(H, W, 1))
    # opening eyes
    if t < 4.5:
        if t < 1.6:
            open_ = 0.0
        else:
            u = (t - 1.6)
            # blink: open a bit, close, then open fully
            open_ = float(np.interp(u, [0, 0.5, 0.8, 1.1, 2.6], [0, 0.35, 0.05, 0.4, 1.0]))
        lid = int((1 - open_) * H / 2)
        if lid > 0:
            img[:lid] = 0
            img[H - lid:] = 0
        if open_ < 1:
            img *= 0.4 + 0.6 * open_
    # hook title
    if t < 4.2:
        a = np.clip((4.2 - t) / 0.5, 0, 1)
        draw_lines(img, [("YOU WOKE UP IN", WHITE), ("YOUR OLD", WHITE), ("MINECRAFT", YELLOW),
                         ("WORLD", YELLOW)], 30, 2, a)
    # captions (typewriter)
    for (a_, b_, s) in CAPS:
        if a_ <= t < b_:
            n = int((t - a_) * 24)
            alpha = np.clip((b_ - t) / 0.4, 0, 1)
            shown = s[:n]
            draw_block_text(img, shown, 112 if t > 4.2 else 165, (255, 255, 255), 2, alpha, maxw=W - 14,
                            full=s)
    # ending card
    if t >= 116.6:
        a = np.clip((t - 116.6) / 0.6, 0, 1)
        img = img * (1 - 0.35 * a)
        draw_lines(img, [("DO YOU", WHITE), ("REMEMBER YOUR", WHITE), ("FIRST WORLD?", YELLOW)], 52, 2, a)
        if t > 117.6:
            draw_block_text(img, "TELL ME IN THE COMMENTS *", 124, (220, 220, 220), 1,
                            np.clip((t - 117.6) / 0.5, 0, 1))
    # final fade
    img *= np.clip((DUR - t) / 1.2, 0, 1) if t > DUR - 1.2 else 1
    return np.clip(img, 0, 255).astype(np.uint8)


def main():
    music, out = sys.argv[1], sys.argv[2]
    dur = DUR
    start = 0.0
    if "--preview" in sys.argv:
        start = float(sys.argv[sys.argv.index("--preview") + 1])
        dur = start + 6
    if "--stills" in sys.argv:
        from PIL import Image
        for ts in [float(v) for v in sys.argv[sys.argv.index("--stills") + 1].split(",")]:
            Image.fromarray(frame(ts)).resize((W * 3, H * 3), Image.NEAREST).save(f"{out}_{ts:06.1f}.png")
        return
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-ss", str(start), "-t", str(dur - start), "-i", music,
           "-vf", "scale=1080:1920:flags=neighbor", "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(round((dur - start) * FPS))
    for i in range(nf):
        p.stdin.write(frame(start + i / FPS).tobytes())
        if i % 300 == 0:
            print(f"frame {i}/{nf}", flush=True)
    p.stdin.close()
    p.wait()
    print("done", out)


if __name__ == "__main__":
    main()
