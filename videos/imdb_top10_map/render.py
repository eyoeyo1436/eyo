"""IMDb Top 10 filming locations on a world map. 1920x1080, 60 fps, 60 s, no voice.

usage: python3 render.py sfx.wav out.mp4 [--stills t1,t2,...]
"""
import json, math, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import timeline as T
from films import FILMS, SNAPSHOT

W, H, FPS = 1920, 1080, 60
SS = 2  # supersampling for the map layer
GOLD, WHITE, MUTED = (245, 197, 24), (244, 246, 250), (150, 162, 185)
FONT = "fonts/Montserrat.ttf"
_fc = {}


def font(size, wght=700):
    k = (size, wght)
    if k not in _fc:
        f = ImageFont.truetype(FONT, size)
        f.set_variation_by_axes([wght])
        _fc[k] = f
    return _fc[k]


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def back_out(x):
    x = min(max(x, 0.0), 1.0)
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


seg = lambda t, a, b: min(max((t - a) / (b - a), 0.0), 1.0)


# ------------------------------------------------------------------ projection (Miller)
def proj(lon, lat):
    lat = np.clip(lat, -84, 84)
    return np.radians(lon), 1.25 * np.log(np.tan(np.pi / 4 + 0.4 * np.radians(lat)))


GEO = json.load(open("data/countries.geojson"))
COUNTRIES = []  # (name, [ring arrays (n,2) projected], bbox)
for f in GEO["features"]:
    name = f["properties"]["ADMIN"]
    if name == "Antarctica":
        continue
    g = f["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    rings = []
    for p in polys:
        a = np.array(p[0], float)
        x, y = proj(a[:, 0], a[:, 1])
        rings.append(np.stack([x, -y], 1))  # screen y grows downward
    allp = np.concatenate(rings)
    COUNTRIES.append((name, rings, (allp[:, 0].min(), allp[:, 1].min(), allp[:, 0].max(), allp[:, 1].max())))


def P(lon, lat):
    x, y = proj(lon, lat)
    return float(x), float(-y)


# ------------------------------------------------------------------ cameras
FOCUS = (1235, 560)          # where an entry's locations are centred (card sits on the left)
WORLD = (0.55, -0.62, 292.0)  # cx, cy, scale (pixels per radian)


def fit_cam(locs, cx_prev=None):
    pts = [P(lo, la) for _, la, lo, _ in locs]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if cx_prev is not None:  # pick the wrap copy nearest the previous camera
        xs = [x + 2 * np.pi * round((cx_prev - x) / (2 * np.pi)) for x in xs]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    s = min(1150 / max(w, 1e-3), 620 / max(h, 1e-3), 2300)
    return cx, cy, max(s, 230)


CAMS, prev = [], WORLD[0]
for start, film in T.entries():
    c = fit_cam(film[4], prev)
    CAMS.append((start, c))
    prev = c[0]


def lerp_cam(a, b, u, focus_a, focus_b):
    """Zoom out, travel, zoom in (smooth)."""
    e = ease(u)
    la, lb = math.log(a[2]), math.log(b[2])
    dist = math.hypot(b[0] - a[0], b[1] - a[1])
    need = math.log(max(min(1500 / max(dist, 1e-3), a[2], b[2]), 200))
    dip = max(0.0, (la + lb) / 2 - need)
    ls = la + (lb - la) * e - dip * math.sin(math.pi * e)
    fx = focus_a[0] + (focus_b[0] - focus_a[0]) * e
    fy = focus_a[1] + (focus_b[1] - focus_a[1]) * e
    return a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, math.exp(ls), (fx, fy)


CENTER = (W / 2, H / 2 + 20)


def camera(t):
    """Returns (cx, cy, scale, focus_screen_point)."""
    if t < T.INTRO:
        z = 1 + 0.04 * ease(seg(t, 0, T.INTRO))
        return WORLD[0], WORLD[1], WORLD[2] * z, CENTER
    if t >= T.OUTRO:
        last = CAMS[-1][1]
        cx = last[0] + 2 * np.pi * round((WORLD[0] - last[0]) / (2 * np.pi))
        u = seg(t, T.OUTRO, T.OUTRO + 1.8)
        return lerp_cam(last, (0.15, WORLD[1], 215.0), u, FOCUS, (1235, 590))
    i = max(k for k, (s, _) in enumerate(CAMS) if s <= t)
    start, cam = CAMS[i]
    film = T.entries()[i][1]
    prev_cam = CAMS[i - 1][1] if i else (WORLD[0], WORLD[1], WORLD[2] * 1.04)
    prev_focus = FOCUS if i else CENTER
    if film[0] == 1:  # #1: pull out to the whole world, then dive in
        if t < T.ONE_DIVE[0]:
            u = seg(t, start, T.ONE_DIVE[0])
            wcx = prev_cam[0] + 2 * np.pi * round((WORLD[0] - prev_cam[0]) / (2 * np.pi))
            return lerp_cam(prev_cam, (wcx, WORLD[1], WORLD[2]), u, FOCUS, CENTER)
        u = seg(t, *T.ONE_DIVE)
        wcx = prev_cam[0] + 2 * np.pi * round((WORLD[0] - prev_cam[0]) / (2 * np.pi))
        tgt = (cam[0] + 2 * np.pi * round((wcx - cam[0]) / (2 * np.pi)), cam[1], cam[2])
        if u < 1:
            return lerp_cam((wcx, WORLD[1], WORLD[2]), tgt, u ** 1.3, CENTER, FOCUS)
        drift = 1 + 0.05 * ease(seg(t, T.ONE_DIVE[1], T.OUTRO))
        return tgt[0], tgt[1], tgt[2] * drift, FOCUS
    u = seg(t, start, start + T.FLY)
    if u < 1:
        return lerp_cam(prev_cam, cam, u, prev_focus, FOCUS)
    drift = 1 + 0.045 * ease(seg(t, start + T.FLY, start + T.STEP))
    return cam[0], cam[1], cam[2] * drift, FOCUS


def to_screen(cam, x, y):
    cx, cy, s, (fx, fy) = cam
    x = x + 2 * np.pi * round((cx - x) / (2 * np.pi))
    return fx + (x - cx) * s, fy + (y - cy) * s


# ------------------------------------------------------------------ static backdrop
yy, xx = np.mgrid[0:H, 0:W]
_bg = np.exp(-(((xx - W * 0.6) / (W * 0.9)) ** 2 + ((yy - H * 0.45) / (H * 0.9)) ** 2))[..., None]
BG = Image.fromarray((np.array([5, 8, 15]) + _bg * np.array([12, 22, 40])).astype(np.uint8)).convert("RGBA")
VIGN = (1 - 0.45 * np.clip(((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2, 0, 1))[..., None].astype(np.float32)


def countries_of(film):
    return {c for *_, c in film[4]}


def draw_map(t, cam, current, visited, hl):
    big = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    cx, cy, s, (fx, fy) = cam
    # graticule
    for lon in range(-180, 181, 30):
        for k in (-1, 0, 1):
            x = fx + (math.radians(lon) + 2 * np.pi * k - cx) * s
            if -10 < x < W + 10:
                d.line([x * SS, 0, x * SS, H * SS], fill=(40, 60, 95, 55), width=2)
    for lat in range(-60, 81, 20):
        y = fy + (-P(0, lat)[1] * -1 - cy) * s if False else fy + (P(0, lat)[1] - cy) * s
        if -10 < y < H + 10:
            d.line([0, y * SS, W * SS, y * SS], fill=(40, 60, 95, 55), width=2)
    sw, sh = W / s, H / s
    for k in (-1, 0, 1):
        off = 2 * np.pi * k
        vx0, vx1 = cx - fx / s - off, cx + (W - fx) / s - off
        vy0, vy1 = cy - fy / s, cy + (H - fy) / s
        for name, rings, (bx0, by0, bx1, by1) in COUNTRIES:
            if bx1 < vx0 or bx0 > vx1 or by1 < vy0 or by0 > vy1:
                continue
            if name in current:
                fill, line = (int(70 + 60 * hl), int(60 + 48 * hl), int(40 + 8 * hl), 255), (int(110 + 120 * hl), int(98 + 92 * hl), 50, 255)
            elif name in visited:
                fill, line = (48, 60, 84, 255), (96, 112, 142, 255)
            else:
                fill, line = (34, 44, 64, 255), (70, 86, 114, 255)
            for r in rings:
                pts = ((r[:, 0] + off - cx) * s + fx) * SS, ((r[:, 1] - cy) * s + fy) * SS
                xy = np.stack(pts, 1).ravel().tolist()
                if len(xy) >= 6:
                    d.polygon(xy, fill=fill, outline=line)
    return big.resize((W, H), Image.LANCZOS)


# ------------------------------------------------------------------ pins, arcs, cards
def star(d, x, y, r, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def pin(lay, glow, x, y, p, label, side, t, tp, big=False):
    """p in [0,1]: drop progress."""
    if p <= 0:
        return
    d, g = ImageDraw.Draw(lay), ImageDraw.Draw(glow)
    drop = (1 - ease_out(p)) * 70
    sc = back_out(p) * (1.35 if big else 1.0)
    r = 11 * sc
    y0 = y - drop
    d.ellipse([x - 9, y + 3, x + 9, y + 8], fill=(0, 0, 0, int(110 * p)))
    for k in range(2):  # pulse rings
        q = ((t - tp) * 0.8 + k * 0.5) % 1.0
        if t > tp:
            rr = 10 + 46 * q
            g.ellipse([x - rr, y - rr * 0.55, x + rr, y + rr * 0.55], outline=GOLD + (int(170 * (1 - q)),), width=3)
    g.ellipse([x - r * 2.2, y0 - r * 2.2, x + r * 2.2, y0 + r * 2.2], fill=GOLD + (int(120 * p),))
    d.polygon([(x - r * 0.75, y0 - r * 0.4), (x + r * 0.75, y0 - r * 0.4), (x, y0 + r * 1.3)], fill=GOLD + (255,))
    d.ellipse([x - r, y0 - r * 2.0, x + r, y0], fill=GOLD + (255,))
    d.ellipse([x - r * 0.42, y0 - r * 1.42, x + r * 0.42, y0 - r * 0.58], fill=(255, 255, 255, 255))
    if label:
        a = ease(seg(p, 0.4, 1.0))
        f = font(26, 650)
        tw = d.textlength(label, font=f)
        lx = x + 26 if side > 0 else x - 26 - tw - 24
        if lx < 680 and x > 640:
            lx = x + 26
        if lx + tw + 24 > W - 30:
            lx = x - 26 - tw - 24
        ly = y0 - 30
        d.rounded_rectangle([lx, ly - 21, lx + tw + 24, ly + 21], 12, fill=(8, 12, 22, int(200 * a)),
                            outline=(245, 197, 24, int(140 * a)), width=2)
        d.text((lx + 12, ly), label, font=f, fill=WHITE + (int(255 * a),), anchor="lm")


def arc(lay, a, b, p, alpha=255, width=4):
    if p <= 0:
        return
    (x0, y0), (x1, y1) = a, b
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dist = math.hypot(x1 - x0, y1 - y0)
    cx, cy = mx, my - min(dist * 0.35, 320)
    n = 80
    pts = []
    for i in range(int(n * p) + 1):
        u = i / n
        pts.append(((1 - u) ** 2 * x0 + 2 * (1 - u) * u * cx + u * u * x1, (1 - u) ** 2 * y0 + 2 * (1 - u) * u * cy + u * u * y1))
    d = ImageDraw.Draw(lay)
    for i in range(0, len(pts) - 1, 2):  # dashed
        d.line([pts[i], pts[i + 1]], fill=GOLD + (alpha,), width=width)
    if p < 1 and len(pts) > 1:
        hx, hy = pts[-1]
        d.ellipse([hx - 7, hy - 7, hx + 7, hy + 7], fill=(255, 245, 210, alpha))


def wrap_lines(text, f, maxw, d):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) <= maxw:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def card(im, t, start, film, appear, leave):
    rank, title, year, rating, locs = film
    a = ease_out(seg(t, appear, appear + 0.45)) * (1 - ease(seg(t, leave, leave + 0.4)))
    if a <= 0:
        return
    x0 = 70 - 90 * (1 - a)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    is1 = rank == 1
    h = 640
    y0 = 230
    d.rounded_rectangle([x0, y0, x0 + 560, y0 + h], 28, fill=(10, 14, 26, int(215 * a)),
                        outline=(245, 197, 24, int((200 if is1 else 90) * a)), width=3 if is1 else 2)
    d.text((x0 + 40, y0 + 90), f"#{rank}", font=font(130, 800), fill=GOLD + (int(255 * a),), anchor="lm")
    if is1:
        d.text((x0 + 250, y0 + 74), "THE HIGHEST-RATED", font=font(24, 700), fill=GOLD + (int(255 * a),), anchor="lm")
        d.text((x0 + 250, y0 + 106), "FILM ON IMDb", font=font(24, 700), fill=GOLD + (int(255 * a),), anchor="lm")
    f = font(40 if len(title) < 28 else 34, 800)
    lines = wrap_lines(title, f, 480, d)
    y = y0 + 185
    for ln in lines:
        d.text((x0 + 40, y), ln, font=f, fill=WHITE + (int(255 * a),), anchor="lm")
        y += 48
    d.text((x0 + 40, y + 6), str(year), font=font(30, 500), fill=MUTED + (int(255 * a),), anchor="lm")
    # rating count-up
    c0, c1 = T.count_window(start, film)
    shown = rating * ease_out(seg(t, c0, c1))
    y += 80
    star(d, x0 + 62, y, 26, GOLD + (int(255 * a),))
    d.text((x0 + 100, y), f"{shown:.1f}", font=font(60, 800), fill=WHITE + (int(255 * a),), anchor="lm")
    d.text((x0 + 210, y + 10), "/ 10  IMDb rating", font=font(26, 600), fill=MUTED + (int(255 * a),), anchor="lm")
    by = y + 52
    d.rounded_rectangle([x0 + 40, by, x0 + 520, by + 12], 6, fill=(40, 48, 66, int(255 * a)))
    d.rounded_rectangle([x0 + 40, by, x0 + 40 + 480 * shown / 10, by + 12], 6, fill=GOLD + (int(255 * a),))
    y = by + 62
    d.text((x0 + 40, y), "FILMING LOCATIONS", font=font(22, 700), fill=MUTED + (int(255 * a),), anchor="lm")
    for j, (lab, *_rest) in enumerate(locs):
        pt = T.pin_times(start, film)[j]
        b = ease_out(seg(t, pt, pt + 0.35)) * a
        if b <= 0:
            continue
        yy_ = y + 40 + j * 38
        d.ellipse([x0 + 42, yy_ - 7, x0 + 56, yy_ + 7], fill=GOLD + (int(255 * b),))
        d.text((x0 + 72 - 14 * (1 - b), yy_), lab, font=font(25, 600), fill=WHITE + (int(255 * b),), anchor="lm")
    if is1:
        g = lay.filter(ImageFilter.GaussianBlur(18))
        im.alpha_composite(Image.eval(g, lambda v: v // 2))
    im.alpha_composite(lay)


CONF = [(np.random.default_rng(i).uniform(0, W), np.random.default_rng(i + 99).uniform(-600, 0),
         np.random.default_rng(i + 7).uniform(0.6, 1.4), np.random.default_rng(i + 3).uniform(0, 6.28)) for i in range(140)]


def confetti(d, t):
    if not (T.ONE_HIT <= t < T.ONE_HIT + 4.2):
        return
    u = t - T.ONE_HIT
    fade = 1 - seg(u, 3.2, 4.2)
    for x, y, s, ph in CONF:
        yy_ = y + u * 420 * s + 60 * u * u
        xx_ = x + 40 * math.sin(u * 3 * s + ph)
        if 0 < yy_ < H:
            a = ph + u * 6 * s
            w, h = 9 * s, 4 + 4 * abs(math.sin(a))
            col = (GOLD if int(ph * 10) % 3 else (255, 255, 255)) + (int(230 * fade),)
            d.polygon([(xx_ - w * math.cos(a), yy_ - w * math.sin(a)), (xx_ + h * math.sin(a), yy_ - h * math.cos(a)),
                       (xx_ + w * math.cos(a), yy_ + w * math.sin(a)), (xx_ - h * math.sin(a), yy_ + h * math.cos(a))], fill=col)


def header(im, t, cur_rank):
    d = ImageDraw.Draw(im)
    a = ease(seg(t, T.INTRO - 0.6, T.INTRO)) * (1 - ease(seg(t, T.OUTRO, T.OUTRO + 0.5)))
    if a > 0:
        d.text((70, 70), "IMDb TOP 10", font=font(30, 800), fill=GOLD + (int(255 * a),), anchor="lm")
        d.text((290, 70), "WHERE WERE THEY FILMED?", font=font(30, 500), fill=WHITE + (int(220 * a),), anchor="lm")
        for i, r in enumerate(range(10, 0, -1)):  # progress chips
            x = W - 70 - (9 - i) * 52
            on = r == cur_rank
            done = cur_rank is not None and r > cur_rank
            col = GOLD if on else ((120, 130, 150) if done else (60, 68, 86))
            d.rounded_rectangle([x - 22, 52, x + 22, 88], 10, fill=col + (int(255 * a),))
            d.text((x, 70), str(r), font=font(20, 800), fill=((10, 12, 20) if on else (230, 232, 240)) + (int(255 * a),), anchor="mm")
    d.text((W - 70, H - 40), f"Ratings: {SNAPSHOT}   ·   Map: Natural Earth", font=font(18, 500), fill=(120, 130, 150, 200), anchor="rm")


# ------------------------------------------------------------------ frame
ENTRIES = T.entries()


def frame(n):
    t = n / FPS
    cam = camera(t)
    i = None
    for k, (s, f) in enumerate(ENTRIES):
        if s <= t:
            i = k
    film = ENTRIES[i][1] if (i is not None and t < T.OUTRO) else None
    start = ENTRIES[i][0] if i is not None else 0
    current = countries_of(film) if film else set()
    visited = set()
    for s, f in ENTRIES:
        if s + 1.3 <= t:
            visited |= countries_of(f)
    pts = T.pin_times(start, film) if film else []
    hl = ease(seg(t, pts[0], pts[0] + 0.5)) if pts else 0
    im = BG.copy()
    im.alpha_composite(draw_map(t, cam, current, visited, hl))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # faint trail of earlier flights
    firsts = [P(f[4][0][2], f[4][0][1]) for _, f in ENTRIES]
    for k in range(1, len(ENTRIES)):
        if ENTRIES[k][0] + T.FLY < t and t < T.OUTRO + 0.2:
            arc(lay, to_screen(cam, *firsts[k - 1]), to_screen(cam, *firsts[k]), 1.0, 60, 2)
    if film:
        # live arc during the flight
        if i > 0 and film[0] != 1:
            arc(lay, to_screen(cam, *firsts[i - 1]), to_screen(cam, *firsts[i]), ease(seg(t, start, start + T.FLY)), 230)
        locs = film[4]
        scr = [to_screen(cam, *P(lo, la)) for _, la, lo, _ in locs]
        for j, (lab, la, lo, _) in enumerate(locs):
            x, y = scr[j]
            p = seg(t, pts[j] - 0.25, pts[j] + 0.2)
            side = 1
            for k2, (x2, y2) in enumerate(scr):
                if k2 != j and abs(y2 - y) < 60 and 0 < x2 - x < 300:
                    side = -1   # a neighbour sits just east: put this label on the west
            if film[0] == 1 and j == 1:
                arc(lay, to_screen(cam, *P(locs[0][2], locs[0][1])), (x, y), ease(seg(t, pts[1] - 0.6, pts[1])), 220)
            pin(lay, glow, x, y, p, lab, side, t, pts[j], big=film[0] == 1)
    if t >= T.OUTRO - 0.2:  # all filming locations on the world map + ranked legend
        for k, (s, f) in enumerate(ENTRIES):
            tk = T.OUTRO + 1.0 + 0.16 * k
            for lab, la, lo, _ in f[4]:
                x, y = to_screen(cam, *P(lo, la))
                p = seg(t, tk - 0.2, tk + 0.2)
                if p > 0:
                    gd = ImageDraw.Draw(glow)
                    gd.ellipse([x - 16, y - 16, x + 16, y + 16], fill=GOLD + (int(140 * p),))
                    ImageDraw.Draw(lay).ellipse([x - 6 * p, y - 6 * p, x + 6 * p, y + 6 * p], fill=(255, 236, 170, 255))
        legend = ease_out(seg(t, T.OUTRO + 0.6, T.OUTRO + 1.2))
        if legend > 0:
            d = ImageDraw.Draw(lay)
            x0 = 40 - 80 * (1 - legend)
            d.rounded_rectangle([x0, 170, x0 + 510, 880], 26, fill=(8, 12, 22, int(215 * legend)))
            for k, f in enumerate(sorted(FILMS, key=lambda f: f[0])):
                y = 225 + k * 66
                al = int(255 * ease_out(seg(t, T.OUTRO + 1.0 + 0.1 * k, T.OUTRO + 1.4 + 0.1 * k)) * legend)
                d.text((x0 + 28, y), f"#{f[0]}", font=font(28, 800), fill=GOLD + (al,), anchor="lm")
                ttl = {"The Lord of the Rings: The Return of the King": "LOTR: The Return of the King",
                       "The Lord of the Rings: The Fellowship of the Ring": "LOTR: The Fellowship",
                       "The Good, the Bad and the Ugly": "The Good, the Bad & the Ugly"}.get(f[1], f[1])
                d.text((x0 + 92, y), ttl, font=font(21, 650), fill=WHITE + (al,), anchor="lm")
                star(d, x0 + 446, y, 11, GOLD + (al,))
                d.text((x0 + 462, y), f"{f[3]:.1f}", font=font(24, 700), fill=WHITE + (al,), anchor="lm")
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
    im.alpha_composite(lay)
    if film:
        card(im, t, start, film, start + (0.85 if film[0] != 1 else T.ONE_HIT - start + 0.15),
             start + T.OUT if film[0] != 1 else T.OUTRO - 0.3)
    confetti(ImageDraw.Draw(im), t)
    header(im, t, film[0] if film else None)
    # intro / outro titles
    d = ImageDraw.Draw(im)
    if t < T.INTRO:
        a = ease(seg(t, 0.4, 1.2)) * (1 - ease(seg(t, T.INTRO - 0.7, T.INTRO - 0.1)))
        d.text((W / 2, H / 2 - 50), "IMDb TOP 10", font=font(110, 800), fill=GOLD + (int(255 * a),), anchor="mm")
        d.text((W / 2, H / 2 + 50), "WHERE IN THE WORLD WERE THEY FILMED?", font=font(44, 600), fill=WHITE + (int(255 * a),), anchor="mm")
    if t >= T.OUTRO + 1.6:
        a = ease(seg(t, T.OUTRO + 1.6, T.OUTRO + 2.2))
        d.text((1235, 110), "THE IMDb TOP 10, AROUND THE WORLD", font=font(44, 800), fill=GOLD + (int(255 * a),), anchor="mm")
    if T.ONE_DIVE[1] - 0.05 <= t < T.ONE_DIVE[1] + 0.25:  # flash on the #1 impact
        im.alpha_composite(Image.new("RGBA", (W, H), (255, 240, 200, int(170 * (1 - seg(t, T.ONE_DIVE[1] - 0.05, T.ONE_DIVE[1] + 0.25))))))
    a = np.asarray(im.convert("RGB"), np.float32) * VIGN
    a *= min(1, t / 0.6) * min(1, (T.DUR - t) / 0.7)
    return np.clip(a, 0, 255).astype(np.uint8).tobytes()


if __name__ == "__main__":
    if "--stills" in sys.argv:
        for ts in [float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")]:
            Image.frombytes("RGB", (W, H), frame(int(ts * FPS))).save(f"still_{ts:05.1f}.png")
        sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", sys.argv[1], "-c:v", "libx264", "-preset", "slow",
                           "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest",
                           "-movflags", "+faststart", sys.argv[2]], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for buf in pool.imap(frame, range(int(T.DUR * FPS)), chunksize=6):
            ff.stdin.write(buf)
    ff.stdin.close()
    ff.wait()
