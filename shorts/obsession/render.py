"""Composite the Obsession Short: parallax camera, animated layers, glitches, grade, grain, subtitles, titles, mix.

Usage: python3 render.py VO_DIR MUSIC_DIR FONT_DIR OUT.mp4 [--workers 4] [--stills DIR]
"""
import sys, os, math, json, argparse, subprocess, tempfile
from functools import lru_cache
import numpy as np
import skia
import soundfile as sf
from scipy import signal

import scenes
from timeline import layout, shots, word_time, DURATION, FPS
from script import HIGHLIGHT

OW, OH = 1080, 1920
SR = 48000
GOLD = skia.Color(255, 52, 66)   # highlight colour: blood red
WHITE = skia.Color(250, 244, 232)

# ------------------------------------------------------------------ fonts
FONTS = {}
def font(name, size, weight=None):
    key = (name, size, weight)
    if key not in FONTS:
        tf = skia.Typeface.MakeFromFile(os.path.join(ARGS.fonts, name))
        if weight:
            C = skia.FontArguments.VariationPosition.Coordinate
            vp = skia.FontArguments.VariationPosition(skia.FontArguments.VariationPosition.Coordinates(
                [C(int.from_bytes(b'wght', 'big'), float(weight))]))
            fa = skia.FontArguments(); fa.setVariationDesignPosition(vp)
            tf = tf.makeClone(fa)
        f = skia.Font(tf, size)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        FONTS[key] = f
    return FONTS[key]

# ------------------------------------------------------------------ shots
@lru_cache(maxsize=4)
def shot_images(name):
    layers = scenes.SHOTS[name]()
    out = []
    for arr, depth, lname in layers:
        u8 = np.ascontiguousarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
        img = skia.Image.fromarray(u8, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
        out.append((img, depth, lname))
    return out

def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)

EVENTS = {}

def layer_alpha(name, lname, t, t0):
    """Per-layer animation inside a shot (seconds since the shot started = t - t0)."""
    u = t - t0
    flick = 1.0 if (int(t * 24) % 7) else 0.7
    if name == 'hook_b':
        if lname == 'nikki':
            return 1 - ease((u - 0.3) / 2.2)
        if lname == 'nikki_shadow':
            return ease((u - 0.2) / 2.4) * flick
    if name == 'wish':
        snap = EVENTS['snap'] - t0
        if lname == 'stick_whole':
            return 1.0 if u < snap else 0.0
        if lname == 'stick_broken':
            return 1.0 if u >= snap else 0.0
    if name == 'doorway' and lname == 'nikki':
        return ease((u - 0.25) / 1.0) * flick
    if name in ('final_shadow', 'final_wide') and lname == 'shadow':
        return ease((u - 0.1) / 1.4) if name == 'final_shadow' else 1.0
    if name == 'final_close' and lname == 'shadow_hand':
        return ease((u - 0.4) / 1.8)
    return 1.0

def layer_slide(name, lname, t, t0):
    """Extra motion for some layers: (dx, dy, scale)."""
    u = t - t0
    if name == 'final_close' and lname == 'shadow_hand':
        k = ease(u / 3.0)
        return (-140 * k, -60 * k, 1.0)
    if name == 'final_shadow' and lname == 'shadow':
        return (0, 0, 0.9 + 0.12 * ease(u / 2.0))
    return (0, 0, 1.0)

def shake(t):
    """Camera shake after impacts."""
    amp = 0.0
    for tk in EVENTS.get('impacts', []):
        d = t - tk
        if 0 <= d < 0.45:
            amp = max(amp, 22 * math.exp(-d * 9))
    return amp * math.sin(t * 91.0), amp * math.cos(t * 77.0)

def draw_shot(canvas, name, cam, t, t0, t1, seed=0):
    u = ease((t - t0) / max(0.01, t1 - t0)) * 0.8 + 0.2 * (t - t0) / max(0.01, t1 - t0)
    z0, z1, x0, x1, y0, y1 = cam
    if name == 'perf_lunge':  # smash zoom in, then a slow creep
        k = ease((t - t0) / 0.22)
        z = z0 + (1.0 - z0) * k + (z1 - 1.0) * ease((t - t0 - 0.22) / (t1 - t0))
    else:
        z = z0 + (z1 - z0) * u
    px = (x0 + (x1 - x0) * u) * OW
    py = (y0 + (y1 - y0) * u) * OH
    sx, sy = shake(t)
    wx = 0.8 * math.sin(t * 13.1 + seed) + 0.5 * math.sin(t * 7.3) + sx
    wy = 0.8 * math.sin(t * 11.7 + seed * 2) + sy
    base = OW / scenes.W * 1.04
    sampling = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)
    for img, d, lname in shot_images(name):
        a = layer_alpha(name, lname, t, t0)
        if a <= 0.002:
            continue
        dx, dy, ls = layer_slide(name, lname, t, t0)
        zz = 1 + (z - 1) * (0.35 + 0.65 * d)
        sc = base * zz
        canvas.save()
        canvas.translate(OW / 2 + px * d + wx, OH / 2 + py * d + wy)
        canvas.scale(sc, sc)
        canvas.translate(-scenes.W / 2 + dx, -scenes.H / 2 + dy)
        if ls != 1.0:
            canvas.translate(scenes.W / 2, scenes.H * 0.75); canvas.scale(ls, ls); canvas.translate(-scenes.W / 2, -scenes.H * 0.75)
        p = skia.Paint(); p.setAlphaf(min(1.0, a))
        canvas.drawImage(img, 0, 0, sampling, p)
        canvas.restore()

# ------------------------------------------------------------------ text
def draw_text_line(c, words, cx, y, f, active_idx, t_pop, max_w=980):
    """words: [(text, highlighted)]. Draws a centred line with stroke + shadow; active word pops."""
    space = f.measureText(' ')
    widths = [f.measureText(w) for w, _ in words]
    total = sum(widths) + space * (len(words) - 1)
    scale = min(1.0, max_w / total)
    x = cx - total * scale / 2
    for i, ((w, hi), ww) in enumerate(zip(words, widths)):
        pop = 1.0
        if i == active_idx:
            pop = 1.0 + 0.10 * math.exp(-t_pop * 9)
        c.save()
        wx = x + ww * scale / 2
        c.translate(wx, y)
        c.scale(scale * pop, scale * pop)
        blob = skia.TextBlob.MakeFromString(w, f)
        sh = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 170))
        sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
        c.drawTextBlob(blob, -ww / 2 + 4, 6, sh)
        st = skia.Paint(AntiAlias=True, Color=skia.Color(8, 4, 2), Style=skia.Paint.kStroke_Style, StrokeWidth=11)
        st.setStrokeJoin(skia.Paint.kRound_Join)
        c.drawTextBlob(blob, -ww / 2, 0, st)
        fillc = GOLD if hi else WHITE
        if i > active_idx and active_idx >= 0:
            fillc = skia.ColorSetA(fillc, 150)
        c.drawTextBlob(blob, -ww / 2, 0, skia.Paint(AntiAlias=True, Color=fillc))
        c.restore()
        x += (ww + space) * scale

def make_chunks(t):
    chunks = []
    for line in t:
        ws = line['words']
        cur = []
        for i, w in enumerate(ws):
            cur.append(w)
            txt = ' '.join(x['w'] for x in cur)
            end_punct = w['w'][-1] in ',.?!'
            nxt_len = len(txt) + (len(ws[i + 1]['w']) + 1 if i + 1 < len(ws) else 0)
            if end_punct or len(cur) >= 4 or nxt_len > 22 or i == len(ws) - 1:
                chunks.append(cur); cur = []
    out = []
    for i, ch in enumerate(chunks):
        st = ch[0]['T0'] - 0.06
        en = ch[-1]['T1'] + 0.35
        if i + 1 < len(chunks):
            en = min(en, chunks[i + 1][0]['T0'] - 0.06)
        out.append((st, en, ch))
    return out

def clean(w):
    return w.upper().strip()

def is_hi(w):
    return w.lower().strip(',.?!;:"') in HIGHLIGHT

def draw_subtitles(c, chunks, t, y=1390):
    f = font('Anton-Regular.ttf', 96)
    for st, en, ch in chunks:
        if st <= t < en:
            active = -1
            for i, w in enumerate(ch):
                if t >= w['T0'] - 0.04:
                    active = i
            words = [(clean(w['w']), is_hi(w['w'])) for w in ch]
            fade = min(1.0, (t - st) / 0.08)
            c.saveLayerAlpha(None, int(255 * fade))
            tp = t - ch[active]['T0'] if active >= 0 else 1
            draw_text_line(c, words, OW / 2, y, f, active, tp)
            c.restore()
            break

def spaced(c, text, cx, y, f, color, tracking=0.12, alpha=255, glow=0, max_w=960):
    chars = list(text)
    ws = [f.measureText(ch) for ch in chars]
    tr = f.getSize() * tracking
    total = sum(ws) + tr * (len(chars) - 1)
    k = min(1.0, max_w / total)
    c.save(); c.translate(cx, y); c.scale(k, k); c.translate(-cx, -y)
    x = cx - total / 2
    paints = []
    if glow:
        g = skia.Paint(AntiAlias=True, Color=skia.ColorSetA(color, int(alpha * 0.55)))
        g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, glow))
        paints.append(g)
    st = skia.Paint(AntiAlias=True, Color=skia.Color(8, 4, 2, alpha), Style=skia.Paint.kStroke_Style, StrokeWidth=8)
    paints.append(st)
    paints.append(skia.Paint(AntiAlias=True, Color=skia.ColorSetA(color, alpha)))
    for p in paints:
        xx = x
        for ch, w in zip(chars, ws):
            c.drawString(ch, xx, y, f, p)
            xx += w + tr
    c.restore()

def jitter(t, k=3.0):
    return k * math.sin(t * 63.0) * (1 if int(t * 12) % 5 == 0 else 0.15)

def draw_hook_title(c, t):
    if t > 7.2:
        return
    a = ease((t - 0.2) / 0.6) * (1 - ease((t - 6.7) / 0.45))
    if a <= 0:
        return
    f1 = font('Cinzel[wght].ttf', 78, 800)
    f2 = font('Cinzel[wght].ttf', 128, 900)
    c.drawRect(skia.Rect.MakeWH(OW, 720), skia.Paint(Shader=skia.GradientShader.MakeLinear(
        [skia.Point(0, 0), skia.Point(0, 720)], [skia.Color(0, 0, 0, int(200 * a)), skia.Color(0, 0, 0, 0)])))
    spaced(c, 'LOVE CAN BECOME A', OW / 2 + jitter(t, 1.5), 330, f1, WHITE, 0.08, int(255 * a))
    na = ease((t - 1.0) / 0.5) * a
    spaced(c, 'NIGHTMARE.', OW / 2 + jitter(t), 480, f2, GOLD, 0.06, int(255 * na), glow=24)

def draw_end_card(c, t, t_end):
    a = ease((t - (t_end + 0.25)) / 0.9)
    if a <= 0:
        return
    a *= 1 - ease((t - (DURATION - 0.35)) / 0.35)
    f2 = font('Cinzel[wght].ttf', 150, 900)
    f3 = font('Cinzel[wght].ttf', 70, 600)
    g = jitter(t, 6) if t - t_end < 1.4 else 0
    if t - t_end < 1.4 and int(t * 20) % 4 == 0:  # red/cyan split while it settles
        spaced(c, 'OBSESSION', OW / 2 + 8 + g, 900, f2, skia.Color(40, 220, 255), 0.06, int(120 * a))
    spaced(c, 'OBSESSION', OW / 2 + g, 900, f2, GOLD, 0.06, int(255 * a), glow=30)
    lp = skia.Paint(AntiAlias=True, Color=skia.ColorSetA(GOLD, int(180 * a)), StrokeWidth=3)
    c.drawLine(OW / 2 - 300, 950, OW / 2 - 90, 950, lp); c.drawLine(OW / 2 + 90, 950, OW / 2 + 300, 950, lp)
    spaced(c, '(2025)', OW / 2, 1030, f3, WHITE, 0.18, int(235 * a))

# ------------------------------------------------------------------ grade
_GRAIN = None
def grain_bank():
    global _GRAIN
    if _GRAIN is None:
        rng = np.random.default_rng(11)
        bank = []
        for _ in range(12):
            g = rng.normal(0, 1, (OH // 2, OW // 2)).astype(np.float32)
            g = np.repeat(np.repeat(g, 2, 0), 2, 1)
            bank.append(g)
        _GRAIN = bank
    return _GRAIN

VIG = None
def grade(rgb, fi, t):
    """Cold, desaturated horror grade that keeps the reds; vignette, grain, flicker, glitches."""
    global VIG
    if VIG is None:
        yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
        d = np.sqrt(((xx - OW / 2) / (OW * 0.6)) ** 2 + ((yy - OH * 0.46) / (OH * 0.58)) ** 2)
        VIG = (1 - 0.5 * np.clip(d - 0.33, 0, 1) ** 1.5)[..., None].astype(np.float32)
    x = rgb
    lum = (x @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    red = np.clip((x[..., 0:1] - np.maximum(x[..., 1:2], x[..., 2:3])) * 3.0, 0, 1)   # how red a pixel is
    sat = 0.72 + 0.4 * red
    x = lum + (x - lum) * sat
    shadow_tint = np.array([0.90, 1.0, 1.12], np.float32)
    x = x * (shadow_tint + (1 - shadow_tint) * np.clip(lum * 1.6, 0, 1))         # teal shadows, neutral highs
    x = np.clip(x * 1.06, 0, 1)
    x = x * x * (3 - 2 * x) * 0.4 + x * 0.6
    x = x + np.array([0.012, 0.016, 0.024], np.float32) * (1 - x)
    x *= VIG
    x *= 1.0 + 0.02 * math.sin(t * 41.0) + 0.012 * math.sin(t * 17.0)
    g = grain_bank()[(fi * 7) % 12]
    x += g[..., None] * (0.04 * (1.2 - lum * 0.6))
    gl = glitch_amount(t)
    if gl > 0:  # RGB split + a displaced band
        sh = int(14 * gl)
        x[..., 0] = np.roll(x[..., 0], sh, axis=1)
        x[..., 2] = np.roll(x[..., 2], -sh, axis=1)
        rng = np.random.default_rng(fi)
        y0 = rng.integers(0, OH - 120); hgt = rng.integers(30, 120)
        x[y0:y0 + hgt] = np.roll(x[y0:y0 + hgt], rng.integers(-60, 60), axis=1)
    fl = flash_amount(t)
    if fl > 0:
        x = x + (1 - x) * fl
    return np.clip(x, 0, 1)

def glitch_amount(t):
    a = 0.0
    for tk in EVENTS.get('glitches', []):
        d = t - tk
        if 0 <= d < 0.25:
            a = max(a, 1 - d / 0.25)
    return a

def flash_amount(t):
    a = 0.0
    for tk, k in EVENTS.get('flashes', []):
        d = t - tk
        if 0 <= d < 0.3:
            a = max(a, k * math.exp(-d * 14))
    return a

# ------------------------------------------------------------------ frame
TRANS = {  # shot -> dissolve length (s) into it; absent = hard cut (most cuts are hard, for suspense)
    'hook_b': 0.5, 'bear_longing': 0.25, 'nikki_sweet': 0.3, 'perf_charming': 0.3, 'perf_tilt': 0.4,
    'final_alone': 0.4, 'final_shadow': 0.3, 'final_wide': 0.35,
}

def render_frame(fi, plan, chunks):
    t = fi / FPS
    surf = skia.Surface(OW, OH)
    c = surf.getCanvas()
    c.clear(skia.ColorBLACK)
    idx = max(i for i, s in enumerate(plan) if s[0] <= t + 1e-6)
    st, en, name, cam = plan[idx]
    t_end = [s for s in plan if s[2] == 'end'][0][0]

    def shot_layer(i, alpha=255):
        s0, s1, nm, cm = plan[i]
        if nm == 'end':
            return
        c.saveLayerAlpha(None, alpha)
        draw_shot(c, nm, cm, t, s0, s1 + 0.6, seed=i)
        c.restore()

    if name == 'end':
        # the closed door lingers, then everything falls to black
        k = (1 - ease((t - st) / 0.6)) * 0.25
        if k > 0:
            shot_layer(idx - 1, int(255 * k))
    else:
        dis = TRANS.get(name, 0)
        if dis and t - st < dis and idx > 0:
            shot_layer(idx - 1)
            shot_layer(idx, int(255 * ease((t - st) / dis)))
        else:
            shot_layer(idx)
    if name == 'hook_a':
        a = 1 - ease(t / 0.7)
        c.drawRect(skia.Rect.MakeWH(OW, OH), skia.Paint(Color=skia.Color(0, 0, 0, int(255 * a))))
    if name == 'final_wide':  # slow fade toward black
        a = ease((t - st) / (en - st)) * 0.75
        c.drawRect(skia.Rect.MakeWH(OW, OH), skia.Paint(Color=skia.Color(0, 0, 0, int(255 * a))))
    arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3].astype(np.float32) / 255.0
    arr = grade(arr, fi, t)
    # text goes on top of the grade so it stays crisp
    u8 = np.ascontiguousarray(np.dstack([(arr * 255).astype(np.uint8), np.full((OH, OW), 255, np.uint8)]))
    img = skia.Image.fromarray(u8, colorType=skia.kRGBA_8888_ColorType)
    s2 = skia.Surface(OW, OH)
    c2 = s2.getCanvas()
    c2.drawImage(img, 0, 0)
    draw_hook_title(c2, t)
    draw_end_card(c2, t, t_end)
    draw_subtitles(c2, chunks, t, 1400)
    return s2.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]

def worker(args):
    wi, f0, f1, plan, chunks, path = args
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
                          '-pix_fmt', 'yuv420p', '-g', '30', path], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        p.stdin.write(np.ascontiguousarray(render_frame(fi, plan, chunks)).tobytes())
    p.stdin.close(); p.wait()
    return path

# ------------------------------------------------------------------ audio
def mix_audio(t, out_wav):
    n = int(DURATION * SR)
    voice = np.zeros(n)
    for line in t:
        a, sr = sf.read(os.path.join(ARGS.vo, f"{line['i']:02d}.wav"))
        a = signal.resample_poly(a, SR // 8000, sr // 8000)
        i = int(line['start'] * SR)
        voice[i:i + len(a)] += a[:n - i]
    # voice chain: rumble cut, chest warmth, presence, gentle compression
    b, a_ = signal.butter(2, 70 / (SR / 2), 'high'); voice = signal.lfilter(b, a_, voice)
    def peq(x, f0, gain_db, q):
        A = 10 ** (gain_db / 40); w0 = 2 * np.pi * f0 / SR; al = np.sin(w0) / (2 * q)
        bb = [1 + al * A, -2 * np.cos(w0), 1 - al * A]; aa = [1 + al / A, -2 * np.cos(w0), 1 - al / A]
        return signal.lfilter(bb, aa, x)
    voice = peq(voice, 140, 3.0, 0.8)
    voice = peq(voice, 3200, 2.0, 1.0)
    voice = peq(voice, 7500, -2.0, 0.9)
    env = np.sqrt(signal.lfilter([0.002], [1, -0.998], voice ** 2)) + 1e-6
    thr = 0.08
    gain = np.where(env > thr, (thr / env) ** (1 - 1 / 3.0), 1.0)
    voice = voice * gain
    voice /= np.abs(voice).max() + 1e-9
    # small room
    rng = np.random.default_rng(3); L = int(0.5 * SR); tt = np.arange(L) / SR
    ir = rng.normal(0, 1, L) * np.exp(-tt * 14); ir /= np.sqrt((ir ** 2).sum())
    wet = signal.fftconvolve(voice, ir)[:n]
    voice = voice + 0.06 * wet
    music, _ = sf.read(os.path.join(ARGS.music, 'music.wav'))
    sfx, _ = sf.read(os.path.join(ARGS.music, 'sfx.wav'))
    venv = signal.lfilter([0.0006], [1, -0.9994], np.abs(voice))
    venv = venv / (venv.max() + 1e-9)
    duck = 1 - 0.6 * np.clip(venv * 3.0, 0, 1)
    mix = np.zeros((n, 2))
    mix += voice[:, None] * 0.82
    mix += music[:n] * (0.30 * duck)[:, None]
    mix += sfx[:n] * 0.42
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    sf.write(out_wav, mix.astype(np.float32), SR)

def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument('vo'); ap.add_argument('music'); ap.add_argument('fonts'); ap.add_argument('out')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--stills', default=None, help='write a few PNG frames to this dir and exit')
    ap.add_argument('--remux', default=None, help='re-mix audio onto an already rendered video')
    ARGS = ap.parse_args()
    t = layout(os.path.join(ARGS.vo, 'timing.json'))
    plan = shots(t)
    chunks = make_chunks(t)
    cut = {nm: st for st, en, nm, _ in plan}
    snap = word_time(t, 3, 'wish') + 0.05
    EVENTS.update(snap=snap,
                  impacts=[snap, cut['watch'], cut['price'], cut['perf_lunge'], cut['doorway'] + 0.6, cut['red_grin'], cut['end']],
                  glitches=[cut['watch'], cut['price'], cut['perf_eyes'], cut['perf_lunge'], cut['doorway'] + 0.6, cut['red_grin'], cut['end'],
                            cut['hook_b'] + 1.9, cut['final_shadow'] + 0.4],
                  flashes=[(snap, 0.9), (cut['perf_lunge'], 0.6), (cut['red_grin'], 0.35)])
    if ARGS.stills:
        import PIL.Image
        for sec in [1.5, 5.6, 8.0, 10.5, 12.6, 13.2, 14.5, 16.5, 18.5, 21.0, 24.0, 26.5, 29.0, 31.5, 34.5, 37.5, 40.5, 43.0, 45.5, 48.0, 50.8, 53.5, 56.3, 58.8]:
            fr = render_frame(int(sec * FPS), plan, chunks)
            PIL.Image.fromarray(fr).save(os.path.join(ARGS.stills, f'f_{sec:05.1f}.png'))
        print('stills done'); return
    tmp = tempfile.mkdtemp(prefix='gf_', dir=os.path.dirname(os.path.abspath(ARGS.out)))
    if ARGS.remux:
        wav = os.path.join(tmp, 'mix.wav')
        mix_audio(t, wav)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', ARGS.remux, '-i', wav, '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                        '-t', str(DURATION), '-movflags', '+faststart', ARGS.out], check=True)
        print('remuxed', ARGS.out); return
    total = int(DURATION * FPS)
    bounds = np.linspace(0, total, ARGS.workers + 1).astype(int)
    jobs = [(i, bounds[i], bounds[i + 1], plan, chunks, os.path.join(tmp, f'seg{i}.mp4')) for i in range(ARGS.workers)]
    wav = os.path.join(tmp, 'mix.wav')
    mix_audio(t, wav)
    import multiprocessing as mp
    with mp.get_context('fork').Pool(ARGS.workers) as pool:
        segs = pool.map(worker, jobs)
    lst = os.path.join(tmp, 'list.txt')
    open(lst, 'w').write(''.join(f"file '{s}'\n" for s in segs))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-i', wav,
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11',
                    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', str(DURATION), '-movflags', '+faststart', ARGS.out], check=True)
    print('wrote', ARGS.out)

if __name__ == '__main__':
    main()
