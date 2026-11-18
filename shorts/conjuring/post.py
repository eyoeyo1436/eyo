"""Post-production for the Conjuring Short: 10->30 fps interpolation, upscale, cold horror grade,
grain, title + word-timed subtitles, voice processing and mix. Writes exactly 40.0 s.

Usage: python3 post.py FRAMES_DIR WORK_DIR VO_DIR AUDIO_DIR FONTS_DIR OUT.mp4 [--workers 4] [--stills DIR]
"""
import os, sys, glob, math, argparse, subprocess
import numpy as np
import skia
import soundfile as sf
from scipy import signal
from PIL import Image, ImageFilter
from timeline import layout, shots, DURATION
from script import HIGHLIGHT

OW, OH, FPS, SR = 1080, 1920, 30, 48000
RED = skia.Color(232, 64, 58)
WHITE = skia.Color(246, 242, 232)
A = None
SEQ = {}
PLAN = []
CHUNKS = []
FONTS = {}

def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)

# ---------------------------------------------------------------- frames
def interpolate(frames_dir, work):
    for st, en, name in PLAN:
        if name == 'black':
            continue
        d = os.path.join(work, name)
        os.makedirs(d, exist_ok=True)
        if not glob.glob(os.path.join(d, '*.png')):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '10', '-pattern_type', 'glob',
                            '-i', os.path.join(frames_dir, f'{name}_*.png'),
                            '-vf', 'minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1',
                            os.path.join(d, 'f_%04d.png')], check=True)
        SEQ[name] = sorted(glob.glob(os.path.join(d, 'f_*.png')))

VIG = None
GRAIN = None
def grade(x, fi, t):
    """Muted, cold horror grade: desaturated, teal-green shadows, warm practicals kept, vignette, grain."""
    global VIG, GRAIN
    if VIG is None:
        yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
        d = np.sqrt(((xx - OW / 2) / (OW * 0.62)) ** 2 + ((yy - OH * 0.47) / (OH * 0.6)) ** 2)
        VIG = (1 - 0.55 * np.clip(d - 0.3, 0, 1) ** 1.4)[..., None].astype(np.float32)
        rng = np.random.default_rng(5)
        GRAIN = [np.repeat(np.repeat(rng.normal(0, 1, (OH // 2, OW // 2)).astype(np.float32), 2, 0), 2, 1) for _ in range(10)]
    lum = (x @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    x = lum + (x - lum) * 0.72
    shadow = np.array([0.92, 1.0, 1.06], np.float32)
    x = x * (shadow + (1 - shadow) * np.clip(lum * 2.0, 0, 1))
    x = np.clip(x * 1.12, 0, 1)
    x = x * x * (3 - 2 * x) * 0.35 + x * 0.65
    x = x + np.array([0.012, 0.016, 0.018], np.float32) * (1 - x)
    x *= VIG
    x *= 1.0 + 0.015 * math.sin(t * 33.0) + 0.01 * math.sin(t * 13.0)
    x += GRAIN[fi % 10][..., None] * (0.03 * (1.25 - lum * 0.6))
    return np.clip(x, 0, 1)

def shot_at(t):
    for st, en, name in PLAN:
        if st <= t < en:
            return st, en, name
    return PLAN[-1]

def video_frame(fi):
    t = fi / FPS
    st, en, name = shot_at(t)
    if name == 'black':
        return np.zeros((OH, OW, 3), np.float32), name
    seq = SEQ[name]
    i = min(len(seq) - 1, int((t - st) * FPS))
    im = Image.open(seq[i]).convert('RGB').resize((OW, OH), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=70, threshold=2))
    x = np.asarray(im).astype(np.float32) / 255.0
    x = grade(x, fi, t)
    # quick dips to black between the narration's sections
    for tc in DIPS:
        d = abs(t - tc)
        if d < 0.1:
            x *= d / 0.1
    x *= ease(t / 0.35)
    return x, name

# ---------------------------------------------------------------- text
def font(name, size, weight=None):
    key = (name, size, weight)
    if key not in FONTS:
        tf = skia.Typeface.MakeFromFile(os.path.join(A.fonts, name))
        if weight:
            C = skia.FontArguments.VariationPosition.Coordinate
            vp = skia.FontArguments.VariationPosition(skia.FontArguments.VariationPosition.Coordinates(
                [C(int.from_bytes(b'wght', 'big'), float(weight))]))
            fa = skia.FontArguments(); fa.setVariationDesignPosition(vp)
            tf = tf.makeClone(fa)
        f = skia.Font(tf, size); f.setEdging(skia.Font.Edging.kAntiAlias)
        FONTS[key] = f
    return FONTS[key]

def make_chunks(t):
    chunks = []
    for line in t:
        ws = line['words']; cur = []
        for i, w in enumerate(ws):
            cur.append(w)
            txt = ' '.join(x['w'] for x in cur)
            nxt = len(txt) + (len(ws[i + 1]['w']) + 1 if i + 1 < len(ws) else 0)
            if w['w'][-1] in ',.?!:' or len(cur) >= 4 or nxt > 22 or i == len(ws) - 1:
                chunks.append(cur); cur = []
    out = []
    for i, ch in enumerate(chunks):
        st = ch[0]['T0'] - 0.06
        en = ch[-1]['T1'] + 0.3
        if i + 1 < len(chunks):
            en = min(en, chunks[i + 1][0]['T0'] - 0.06)
        out.append((st, en, ch))
    return out

def draw_words(c, words, cx, y, f, active, tpop, max_w=980):
    space = f.measureText(' ')
    widths = [f.measureText(w) for w, _ in words]
    total = sum(widths) + space * (len(words) - 1)
    k = min(1.0, max_w / total)
    x = cx - total * k / 2
    for i, ((w, hi), ww) in enumerate(zip(words, widths)):
        pop = 1.0 + (0.08 * math.exp(-tpop * 9) if i == active else 0)
        c.save(); c.translate(x + ww * k / 2, y); c.scale(k * pop, k * pop)
        blob = skia.TextBlob.MakeFromString(w, f)
        sh = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 180))
        sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
        c.drawTextBlob(blob, -ww / 2 + 3, 5, sh)
        st = skia.Paint(AntiAlias=True, Color=skia.Color(6, 6, 8), Style=skia.Paint.kStroke_Style, StrokeWidth=10)
        st.setStrokeJoin(skia.Paint.kRound_Join)
        c.drawTextBlob(blob, -ww / 2, 0, st)
        col = RED if hi else WHITE
        if i > active >= 0:
            col = skia.ColorSetA(col, 150)
        c.drawTextBlob(blob, -ww / 2, 0, skia.Paint(AntiAlias=True, Color=col))
        c.restore()
        x += (ww + space) * k

def subtitles(c, t):
    f = font('Anton-Regular.ttf', 92)
    for st, en, ch in CHUNKS:
        if st <= t < en:
            active = max([i for i, w in enumerate(ch) if t >= w['T0'] - 0.04] or [-1])
            words = [(w['w'].upper(), w['w'].lower().strip(',.?!:;"') in HIGHLIGHT) for w in ch]
            c.saveLayerAlpha(None, int(255 * min(1, (t - st) / 0.08)))
            draw_words(c, words, OW / 2, 1430, f, active, t - ch[active]['T0'] if active >= 0 else 1)
            c.restore()
            break

def spaced(c, text, cx, y, f, color, tracking, alpha, glow=0, max_w=960):
    chars = list(text); ws = [f.measureText(ch) for ch in chars]
    tr = f.getSize() * tracking
    total = sum(ws) + tr * (len(chars) - 1)
    k = min(1.0, max_w / total)
    c.save(); c.translate(cx, y); c.scale(k, k); c.translate(-cx, -y)
    x = cx - total / 2
    paints = []
    if glow:
        g = skia.Paint(AntiAlias=True, Color=skia.ColorSetA(color, int(alpha * 0.5)))
        g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, glow)); paints.append(g)
    paints.append(skia.Paint(AntiAlias=True, Color=skia.Color(4, 4, 6, alpha), Style=skia.Paint.kStroke_Style, StrokeWidth=7))
    paints.append(skia.Paint(AntiAlias=True, Color=skia.ColorSetA(color, alpha)))
    for p in paints:
        xx = x
        for ch, w in zip(chars, ws):
            c.drawString(ch, xx, y, f, p); xx += w + tr
    c.restore()

def title(c, t):
    if t > 5.0:
        return
    a = ease((t - 0.1) / 0.5) * (1 - ease((t - 4.55) / 0.4))
    if a <= 0:
        return
    c.drawRect(skia.Rect.MakeWH(OW, 700), skia.Paint(Shader=skia.GradientShader.MakeLinear(
        [skia.Point(0, 0), skia.Point(0, 700)], [skia.Color(0, 0, 0, int(190 * a)), skia.Color(0, 0, 0, 0)])))
    spaced(c, 'WHY IS', OW / 2, 300, font('Cinzel[wght].ttf', 62, 700), WHITE, 0.3, int(255 * a))
    spaced(c, 'THE CONJURING', OW / 2, 420, font('Cinzel[wght].ttf', 108, 900), WHITE, 0.05, int(255 * a), glow=18)
    spaced(c, 'SO TERRIFYING?', OW / 2, 520, font('Cinzel[wght].ttf', 66, 800), RED, 0.18, int(255 * a), glow=14)

def render(fi):
    t = fi / FPS
    x, name = video_frame(fi)
    u8 = np.ascontiguousarray(np.dstack([(x * 255).astype(np.uint8), np.full((OH, OW), 255, np.uint8)]))
    s = skia.Surface(OW, OH)
    c = s.getCanvas()
    c.drawImage(skia.Image.fromarray(u8, colorType=skia.kRGBA_8888_ColorType), 0, 0)
    if name != 'black':
        title(c, t)
        subtitles(c, t)
    return s.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]

def worker(job):
    f0, f1, path = job
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '15',
                          '-pix_fmt', 'yuv420p', '-g', '30', path], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        p.stdin.write(np.ascontiguousarray(render(fi)).tobytes())
    p.stdin.close(); p.wait()
    return path

# ---------------------------------------------------------------- audio
def mix(t, out_wav):
    n = int(DURATION * SR)
    voice = np.zeros(n)
    for line in t:
        a, sr = sf.read(os.path.join(A.vo, f"{line['i']:02d}.wav"))
        a = signal.resample_poly(a, SR // 8000, sr // 8000)
        i = int(line['start'] * SR)
        voice[i:i + len(a)] += a[:n - i]
    b, a_ = signal.butter(2, 70 / (SR / 2), 'high'); voice = signal.lfilter(b, a_, voice)
    def peq(x, f0, g, q):
        Ag = 10 ** (g / 40); w0 = 2 * np.pi * f0 / SR; al = np.sin(w0) / (2 * q)
        return signal.lfilter([1 + al * Ag, -2 * np.cos(w0), 1 - al * Ag], [1 + al / Ag, -2 * np.cos(w0), 1 - al / Ag], x)
    voice = peq(peq(peq(voice, 140, 3.0, 0.8), 3200, 2.0, 1.0), 7500, -2.0, 0.9)
    envv = np.sqrt(signal.lfilter([0.002], [1, -0.998], voice ** 2)) + 1e-6
    voice *= np.where(envv > 0.08, (0.08 / envv) ** (2 / 3), 1.0)
    voice /= np.abs(voice).max() + 1e-9
    rng = np.random.default_rng(3); L = int(0.45 * SR); tt = np.arange(L) / SR
    ir = rng.normal(0, 1, L) * np.exp(-tt * 14); ir /= np.sqrt((ir ** 2).sum())
    voice = voice + 0.06 * signal.fftconvolve(voice, ir)[:n]
    music, _ = sf.read(os.path.join(A.audio, 'music.wav'))
    sfx, _ = sf.read(os.path.join(A.audio, 'sfx.wav'))
    venv = signal.lfilter([0.0006], [1, -0.9994], np.abs(voice)); venv /= venv.max() + 1e-9
    duck = 1 - 0.6 * np.clip(venv * 3, 0, 1)
    out = voice[:, None] * 0.82 + music[:n] * (0.32 * duck)[:, None] + sfx[:n] * 0.5
    out /= max(1.0, np.abs(out).max() / 0.95)
    sf.write(out_wav, out.astype(np.float32), SR)

DIPS = []

def main():
    global A, PLAN, CHUNKS, DIPS
    ap = argparse.ArgumentParser()
    for k in ('frames', 'work', 'vo', 'audio', 'fonts', 'out'):
        ap.add_argument(k)
    ap.add_argument('--workers', type=int, default=4); ap.add_argument('--stills', default=None)
    A = ap.parse_args()
    t = layout(os.path.join(A.vo, 'timing.json'))
    PLAN = shots(t)
    CHUNKS = make_chunks(t)
    cut = {nm: st for st, en, nm in PLAN}
    DIPS = [cut['bedroom'], cut['warrens_enter'], cut['warrens_back']]
    os.makedirs(A.work, exist_ok=True)
    interpolate(A.frames, A.work)
    if A.stills:
        for sec in (1.2, 3.8, 6.2, 8.8, 11.5, 14.5, 17.8, 20.5, 23.0, 25.5, 28.5, 31.8, 35.0, 38.8, 39.7):
            Image.fromarray(render(int(sec * FPS))).save(os.path.join(A.stills, f's_{sec:04.1f}.png'))
        return
    total = int(DURATION * FPS)
    b = np.linspace(0, total, A.workers + 1).astype(int)
    jobs = [(b[i], b[i + 1], os.path.join(A.work, f'seg{i}.mp4')) for i in range(A.workers)]
    wav = os.path.join(A.work, 'mix.wav')
    mix(t, wav)
    import multiprocessing as mp
    with mp.get_context('fork').Pool(A.workers) as pool:
        segs = pool.map(worker, jobs)
    lst = os.path.join(A.work, 'list.txt')
    open(lst, 'w').write(''.join(f"file '{s}'\n" for s in segs))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', wav, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'libx264', '-preset', 'slow', '-b:v', '11M', '-maxrate', '15M', '-bufsize', '22M', '-pix_fmt', 'yuv420p',
                    '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                    '-t', str(DURATION), '-movflags', '+faststart', A.out], check=True)
    print('wrote', A.out)

if __name__ == '__main__':
    main()
