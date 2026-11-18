"""GTA 6 Shorts template: turn a vertical streamer clip into a finished Short in one command.

What it adds (and nothing else):
  1. Hook (first ~2.3 s): AI English male voice reads the hook; the clip plays blurred and dimmed underneath
     while the hook text pops in word by word (last line yellow, numbers yellow), then the clip un-blurs.
  2. Twitch badge: when the clip starts, the Twitch logo spins in at bottom centre and a dark purple-edged
     pill unrolls with the streamer's name. Stays for the whole clip.
  3. End card (~4 s, after the clip): the last moment blurs and darkens, the channel avatar pops in with a
     purple ring, "MORE GTA 6 VIDEOS" appears, a SUBSCRIBE button is clicked by a cursor (turns SUBSCRIBED,
     bell rings), then a fade to black. Whoosh / pop / click / bell sounds.

Usage:
  python3 make_short.py CLIP.mp4 OUT.mp4 --name jasontheween --hook "GTA 6 heists have begun!"
Optional: --hook-say TEXT (pronunciation), --models DIR (Kokoro files, downloaded if missing), --avatar PNG, --cta "MORE GTA 6 VIDEOS",
          --badge-y 1640 (badge centre line; move it if it covers the clip's own text), --keep WORKDIR
"""
import argparse, math, os, re, shutil, subprocess, sys, tempfile, urllib.request
import numpy as np, soundfile as sf, skia
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'assets')
W, H, FPS, SR = 1080, 1920, 60, 48000
VO_DELAY = 0.1
KOKORO_URL = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'

# ------------------------------------------------------------------ helpers
def ease_out(u):
    u = min(1, max(0, u)); return 1 - (1 - u) ** 3

def back_out(u, k=2.2):
    u = min(1, max(0, u)); u -= 1; return 1 + (k + 1) * u ** 3 + k * u ** 2

def rgba(col, a):
    return (col & 0x00FFFFFF) | (int(255 * max(0, min(1, a))) << 24)

def font(name, size):
    return skia.Font(skia.Typeface.MakeFromFile(os.path.join(ASSETS, name)), size)

def oswald(size, wght):
    tf = skia.Typeface.MakeFromFile(os.path.join(ASSETS, 'Oswald[wght].ttf')).makeClone(
        skia.FontArguments().setVariationDesignPosition(skia.FontArguments.VariationPosition(
            skia.FontArguments.VariationPosition.Coordinates([skia.FontArguments.VariationPosition.Coordinate(0x77676874, wght)]))))
    return skia.Font(tf, size)

def probe_duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())

def loudness(path, ss=None, t=None):
    cmd = ['ffmpeg', '-hide_banner']
    if ss is not None:
        cmd += ['-ss', str(ss), '-t', str(t)]
    cmd += ['-i', path, '-af', 'ebur128', '-f', 'null', '-']
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', err)
    return float(m[-1]) if m else None

# ------------------------------------------------------------------ voice
NUM = {'0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'}

def syllables(word):
    w = word.lower()
    if re.fullmatch(r'[a-z]{2,4}', w) and w.upper() == word and not re.search(r'[aeiou]', w[1:]):
        return len(w)                                     # spelled acronyms like GTA
    w = ''.join(NUM.get(ch, ch) for ch in w)
    w = re.sub(r'[^a-z]', '', w)
    n = len(re.findall(r'[aeiouy]+', w))
    if n == 0:
        return len(w)                                     # letters read out, e.g. xQc
    if w.endswith('e') and n > 1 and not w.endswith('le'):
        n -= 1
    return max(1, n)

def make_voice(text, models, work, say=None):
    os.makedirs(models, exist_ok=True)
    for f in ('kokoro-v1.0.onnx', 'voices-v1.0.bin'):
        p = os.path.join(models, f)
        if not os.path.exists(p):
            print('downloading', f, flush=True)
            urllib.request.urlretrieve(KOKORO_URL + f, p)
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(models, 'kokoro-v1.0.onnx'), os.path.join(models, 'voices-v1.0.bin'))
    v = 0.62 * k.get_voice_style('am_michael') + 0.38 * k.get_voice_style('am_onyx')
    a, sr = k.create(say or text, voice=v, speed=1.1, lang='en-us')
    nz = np.where(np.abs(a) > 0.01)[0]
    a = a[max(0, nz[0] - 200): nz[-1] + 2400]
    raw = os.path.join(work, 'hook_raw.wav'); sf.write(raw, a, sr)
    # voiced span for word timing
    env = np.abs(a); win = int(sr * 0.01)
    rms = np.sqrt(np.convolve(env ** 2, np.ones(win) / win, mode='same'))
    on = np.where(rms > rms.max() * 0.08)[0]
    t0, t1 = on[0] / sr, on[-1] / sr
    words = text.split()
    syl = np.array([syllables(w) for w in words], float)
    starts = t0 + (t1 - t0) * np.concatenate([[0], np.cumsum(syl)[:-1]]) / syl.sum()
    # loud, compressed voice that sits just above a typical clip (-11.5 LUFS)
    norm = os.path.join(work, 'hook_n.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af',
                    'aresample=48000,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2',
                    '-ac', '2', norm], check=True)
    lu = loudness(norm) or -18.0
    out = os.path.join(work, 'hook.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', norm, '-af',
                    f'volume={-11.7 - lu:.2f}dB,alimiter=limit=0.89:attack=2:release=40:level=disabled', out], check=True)
    return out, len(a) / sr, list(zip(words, starts))

# ------------------------------------------------------------------ overlay
class Overlay:
    def __init__(self, a, words, voice_len, clip_dur):
        self.a = a
        self.hook_out = VO_DELAY + voice_len + 0.05            # caption leaves, clip un-blurs
        self.clip_start = self.hook_out + 0.1                  # Twitch badge animates in
        self.badge_static = self.clip_start + 1.3
        self.end0 = clip_dur - 0.55                            # end card starts
        self.total = self.end0 + 4.1
        self.click = self.end0 + 2.15
        self.LOGO = skia.Image.open(os.path.join(ASSETS, 'twitch_logo.png'))
        self.AV = skia.Image.open(a.avatar)
        self.SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)
        self.YEL, self.WHT, self.RED = skia.Color(255, 214, 0), skia.ColorWHITE, skia.Color(230, 33, 23)
        self.NF = oswald(50, 600)
        self.TF = font('Anton-Regular.ttf', 118)
        self.BF = oswald(64, 700)
        self.layout_caption(words)

    # hook caption: greedy lines of up to ~11 characters, the last word(s) on their own big yellow line
    def layout_caption(self, words):
        lines, cur = [], []
        for w, t in words[:-1]:
            if cur and len(' '.join(x for x, _ in cur + [(w, t)])) > 11:
                lines.append(cur); cur = []
            cur.append((w.upper(), t + VO_DELAY))
        if cur:
            lines.append(cur)
        lines.append([(words[-1][0].upper(), words[-1][1] + VO_DELAY)])
        self.lines = []
        base = skia.Font(skia.Typeface.MakeFromFile(os.path.join(ASSETS, 'Anton-Regular.ttf')), 100)
        sizes = []
        for ln in lines:
            txt = ' '.join(w for w, _ in ln)
            sizes.append(min(200 if len(txt) <= 7 else 150, 100 * 940 / max(1, base.measureText(txt))))
        total_h = sum(s * 0.95 for s in sizes)
        y = 960 - total_h / 2 + sizes[0] * 0.75
        for i, (ln, s) in enumerate(zip(lines, sizes)):
            self.lines.append((ln, font('Anton-Regular.ttf', s), y, i == len(lines) - 1))
            if i + 1 < len(sizes):
                y += s * 0.55 + sizes[i + 1] * 0.45 + 18

    def caption(self, c, t):
        if t > self.hook_out + 0.25:
            return
        out = 1 - ease_out((t - self.hook_out) / 0.2)
        for ln, f, y, last in self.lines:
            sp = f.getSize() * 0.22
            total = sum(f.measureText(w) for w, _ in ln) + sp * (len(ln) - 1)
            x = (W - total) / 2
            for w, t0 in ln:
                ww = f.measureText(w)
                u = (t - t0) / 0.16
                if u > 0:
                    al = min(1, u * 2) * out
                    sc = back_out(u) * (0.92 + 0.08 * out)
                    cx, cy = x + ww / 2, y - f.getSize() * 0.35
                    c.save(); c.translate(cx, cy); c.scale(sc, sc); c.translate(-cx, -cy)
                    blob = skia.TextBlob(w, f)
                    c.drawTextBlob(blob, x + 6, y + 10, skia.Paint(Color=skia.Color(0, 0, 0, int(150 * al)),
                                   MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14), AntiAlias=True))
                    c.drawTextBlob(blob, x, y, skia.Paint(Color=skia.Color(0, 0, 0, int(255 * al)), Style=skia.Paint.kStroke_Style,
                                   StrokeWidth=f.getSize() * 0.09, StrokeJoin=skia.Paint.kRound_Join, AntiAlias=True))
                    col = self.YEL if (last or re.search(r'\d', w)) else self.WHT
                    c.drawTextBlob(blob, x, y, skia.Paint(Color=rgba(col, al), AntiAlias=True))
                    c.restore()
                x += ww + sp

    def credit(self, c, t):
        u = t - self.clip_start
        if u <= 0:
            return
        fade = 1 - ease_out((t - self.end0) / 0.35)
        if fade <= 0:
            return
        NF, LS, CY, name = self.NF, 86, self.a.badge_y, self.a.name
        nw = NF.measureText(name)
        gap, padr = 16, 30
        full = LS + gap + nw + padr
        r = ease_out((u - 0.25) / 0.5)
        x_logo = W / 2 - LS / 2 + (((W - full) / 2) - (W / 2 - LS / 2)) * r
        if r > 0:
            pw = (full - LS / 2) * r
            ra = fade * min(1, r * 1.5)
            rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x_logo + LS / 2, CY - 34, pw, 68), 34, 34)
            c.drawRRect(rr, skia.Paint(Color=skia.Color(0, 0, 0, int(110 * ra)), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10), AntiAlias=True))
            c.drawRRect(rr, skia.Paint(Color=skia.Color(14, 12, 20, int(200 * ra)), AntiAlias=True))
            c.drawRRect(rr, skia.Paint(Color=skia.Color(145, 70, 255, int(230 * ra)), Style=skia.Paint.kStroke_Style, StrokeWidth=3, AntiAlias=True))
            c.save(); c.clipRRect(rr, True)
            ta = ease_out((u - 0.45) / 0.4)
            c.drawString(name, x_logo + LS + gap - (1 - ta) * 50, CY + NF.getSize() * 0.36, NF,
                         skia.Paint(Color=skia.Color(255, 255, 255, int(255 * ta * fade)), AntiAlias=True))
            c.restore()
        p = back_out(u / 0.34, 2.6)
        al = min(1, u / 0.12) * fade
        c.save(); cx = x_logo + LS / 2
        c.translate(cx, CY); c.rotate((1 - min(1, u / 0.34)) * -30); c.scale(p, p); c.translate(-cx, -CY)
        c.drawImageRect(self.LOGO, skia.Rect.MakeXYWH(x_logo, CY - LS / 2, LS, LS), self.SAMP, skia.Paint(Alpha=int(255 * al), AntiAlias=True))
        c.restore()

    @staticmethod
    def bell(c, x, y, s, ang, col):
        c.save(); c.translate(x, y); c.rotate(ang); c.scale(s, s)
        p = skia.Path(); p.moveTo(0, -30); p.cubicTo(20, -30, 24, -12, 24, 4); p.lineTo(30, 18); p.lineTo(-30, 18); p.lineTo(-24, 4)
        p.cubicTo(-24, -12, -20, -30, 0, -30); p.close()
        paint = skia.Paint(Color=col, AntiAlias=True)
        c.drawPath(p, paint); c.drawCircle(0, 25, 7, paint); c.drawCircle(0, -32, 5, paint)
        c.restore()

    @staticmethod
    def cursor(c, x, y, s):
        pts = [(0, 0), (0, 52), (13, 40), (22, 62), (31, 58), (22, 37), (40, 37)]
        p = skia.Path(); p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        p.close()
        c.save(); c.translate(x, y); c.scale(s, s)
        c.drawPath(p, skia.Paint(Color=skia.Color(0, 0, 0, 120), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4), AntiAlias=True))
        c.drawPath(p, skia.Paint(Color=skia.ColorWHITE, AntiAlias=True))
        c.drawPath(p, skia.Paint(Color=skia.ColorBLACK, Style=skia.Paint.kStroke_Style, StrokeWidth=3, StrokeJoin=skia.Paint.kRound_Join, AntiAlias=True))
        c.restore()

    def outlined(self, c, txt, x, y, f, col, al):
        blob = skia.TextBlob(txt, f)
        c.drawTextBlob(blob, x + 5, y + 8, skia.Paint(Color=skia.Color(0, 0, 0, int(140 * al)), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 12), AntiAlias=True))
        c.drawTextBlob(blob, x, y, skia.Paint(Color=skia.Color(0, 0, 0, int(255 * al)), Style=skia.Paint.kStroke_Style,
                       StrokeWidth=f.getSize() * 0.08, StrokeJoin=skia.Paint.kRound_Join, AntiAlias=True))
        c.drawTextBlob(blob, x, y, skia.Paint(Color=rgba(col, al), AntiAlias=True))

    def endcard(self, c, t):
        u = t - self.end0
        if u <= 0:
            return
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Color=skia.Color(0, 0, 0, int(255 * 0.45 * ease_out(u / 0.5)))))
        AV_D, AV_Y = 440, 700
        ua = u - 0.25
        if ua > 0:
            s = back_out(ua / 0.45, 1.8); al = min(1, ua / 0.15)
            cx, cy = W / 2, AV_Y
            c.save(); c.translate(cx, cy); c.scale(s, s); c.translate(-cx, -cy)
            c.drawCircle(cx, cy, AV_D / 2 + 26, skia.Paint(Color=skia.Color(145, 70, 255, int(150 * al)), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 40), AntiAlias=True))
            c.drawCircle(cx, cy, AV_D / 2 + 12, skia.Paint(Color=skia.Color(255, 255, 255, int(255 * al)), AntiAlias=True))
            c.drawCircle(cx, cy, AV_D / 2 + 6, skia.Paint(Color=skia.Color(145, 70, 255, int(255 * al)), AntiAlias=True))
            c.drawImageRect(self.AV, skia.Rect.MakeXYWH(cx - AV_D / 2, cy - AV_D / 2, AV_D, AV_D), self.SAMP, skia.Paint(Alpha=int(255 * al), AntiAlias=True))
            c.restore()
        ut = u - 0.55
        if ut > 0:
            al = min(1, ut / 0.2); dy = (1 - ease_out(ut / 0.4)) * 60
            parts = [(w + ' ', self.YEL if re.search(r'\d|GTA', w) else self.WHT) for w in self.a.cta.upper().split()]
            TF = self.TF
            tw = TF.measureText(self.a.cta.upper())
            if tw > 1000:
                TF = font('Anton-Regular.ttf', 118 * 1000 / tw); tw = TF.measureText(self.a.cta.upper())
            x = (W - tw) / 2
            for i, (p, col) in enumerate(parts):
                txt = p if i < len(parts) - 1 else p.rstrip()
                self.outlined(c, txt, x, 1100 + dy, TF, col, al); x += TF.measureText(txt)
        ub = u - 0.9
        if ub > 0:
            clicked = t >= self.click
            press = 1 - 0.08 * math.sin(math.pi * min(1, max(0, (t - self.click + 0.06) / 0.18))) if t >= self.click - 0.06 else 1
            s = back_out(ub / 0.4, 2.0) * press; al = min(1, ub / 0.15)
            label = 'SUBSCRIBED' if clicked else 'SUBSCRIBE'
            lw = self.BF.measureText(label)
            bw, bh = lw + 90, 118
            cx, cy = W / 2 - 50, 1290
            c.save(); c.translate(cx, cy); c.scale(s, s); c.translate(-cx, -cy)
            rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - bw / 2, cy - bh / 2, bw, bh), bh / 2, bh / 2)
            c.drawRRect(rr, skia.Paint(Color=skia.Color(0, 0, 0, int(120 * al)), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16), AntiAlias=True))
            c.drawRRect(rr, skia.Paint(Color=rgba(skia.Color(72, 72, 78) if clicked else self.RED, al), AntiAlias=True))
            c.drawString(label, cx - lw / 2, cy + self.BF.getSize() * 0.36, self.BF, skia.Paint(Color=skia.Color(255, 255, 255, int(255 * al)), AntiAlias=True))
            c.restore()
            ring = t - (self.click + 0.15)
            ang = 22 * math.sin(ring * 28) * math.exp(-ring * 3.5) if ring > 0 else 0
            self.bell(c, cx + bw / 2 + 85, cy - 4, 1.35 * back_out(ub / 0.4, 2.0), ang, rgba(self.YEL if ring > 0 else self.WHT, al))
            uc = t - (self.click - 0.55)
            if uc > 0:
                k = ease_out(uc / 0.5)
                x = W + 40 + (cx + bw * 0.18 - W - 40) * k
                y = 1600 + (cy + 6 - 1600) * k
                if t > self.click + 0.5:
                    m = ease_out((t - self.click - 0.5) / 0.4); x += 140 * m; y += 40 * m
                self.cursor(c, x, y, 1.5 * (0.88 if self.click - 0.03 <= t < self.click + 0.1 else 1.0))
        fb = ease_out((t - (self.total - 0.75)) / 0.75)
        if fb > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Color=skia.Color(0, 0, 0, int(255 * fb))))

    def frame(self, t):
        surf = skia.Surface(W, H); c = surf.getCanvas(); c.clear(skia.ColorTRANSPARENT)
        if t < self.end0:
            self.caption(c, t)
        self.endcard(c, t)
        self.credit(c, t)
        return surf.makeImageSnapshot()

    def render(self, dir_a, dir_b):
        os.makedirs(dir_a, exist_ok=True); os.makedirs(dir_b, exist_ok=True)
        na = int(self.badge_static * FPS) + 1
        for fi in range(na):
            self.frame(fi / FPS).save(os.path.join(dir_a, f'o_{fi:04d}.png'), skia.kPNG)
        nb = int(round((self.total - self.end0) * FPS))
        for k in range(nb):
            self.frame(self.end0 + k / FPS).save(os.path.join(dir_b, f'o_{k:04d}.png'), skia.kPNG)

# ------------------------------------------------------------------ end-card sounds
def end_sfx(path, ov):
    T = ov.total + 0.5
    out = np.zeros(int(SR * T)); rng = np.random.default_rng(3)
    def put(x, t, g):
        i = int(t * SR); out[i:i + len(x)] += g * x[:len(out) - i]
    n = int(0.55 * SR)
    b, a = signal.butter(2, [300 / (SR / 2), 4000 / (SR / 2)], 'band')
    wh = signal.lfilter(b, a, rng.standard_normal(n)) * np.sin(np.linspace(0, np.pi, n)) ** 2
    put(wh / np.abs(wh).max(), ov.end0 + 0.05, 0.35)
    tt = np.arange(int(0.12 * SR)) / SR
    put(np.sin(2 * np.pi * (520 - 1800 * tt) * tt) * np.exp(-tt * 35), ov.end0 + 0.55, 0.3)
    tc = np.arange(int(0.03 * SR)) / SR
    click = rng.standard_normal(len(tc)) * np.exp(-tc * 400) + np.sin(2 * np.pi * 2200 * tc) * np.exp(-tc * 250)
    put(click / np.abs(click).max(), ov.click - 0.02, 0.55)
    td = np.arange(int(1.4 * SR)) / SR
    ding = sum(g * np.sin(2 * np.pi * f * td) * np.exp(-td * d) for f, g, d in ((1318.5, 1.0, 3.0), (2637, 0.35, 5), (3951, 0.15, 7), (1975.5, 0.3, 4)))
    put(ding / np.abs(ding).max(), ov.click + 0.15, 0.32)
    sf.write(path, np.c_[out, out].astype(np.float32), SR)

# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('clip'); ap.add_argument('out')
    ap.add_argument('--name', required=True, help='Twitch name shown next to the logo')
    ap.add_argument('--hook', default='GTA 6 heists have begun!', help='hook line (spoken and shown)')
    ap.add_argument('--hook-say', default=None, help='how the voice should say the hook, if different (e.g. "X-Q-C" for xQc)')
    ap.add_argument('--cta', default='MORE GTA 6 VIDEOS')
    ap.add_argument('--avatar', default=os.path.join(ASSETS, 'avatar.png'))
    ap.add_argument('--badge-y', type=int, default=1640, help='badge centre line in the 1080x1920 frame')
    ap.add_argument('--models', default=os.path.join(HERE, 'models'))
    ap.add_argument('--keep', default=None, help='keep intermediate files in this folder')
    a = ap.parse_args()

    work = a.keep or tempfile.mkdtemp(prefix='gta6short_')
    os.makedirs(work, exist_ok=True)
    clip_dur = probe_duration(a.clip)
    hook_wav, voice_len, words = make_voice(a.hook, a.models, work, a.hook_say)
    ov = Overlay(a, words, voice_len, clip_dur)
    print(f'clip {clip_dur:.2f}s, hook {voice_len:.2f}s, final {ov.total:.2f}s', flush=True)
    ov.render(os.path.join(work, 'ova'), os.path.join(work, 'ovb'))
    sfx = os.path.join(work, 'endsfx.wav'); end_sfx(sfx, ov)

    ho, e0, tot = ov.hook_out, ov.end0, ov.total
    duck = (f"if(lt(t,0.05),1,if(lt(t,{ho:.3f}),0.25,if(lt(t,{ho + 0.35:.3f}),0.25+0.75*(t-{ho:.3f})/0.35,"
            f"if(lt(t,{e0:.3f}),1,max(0,1-(t-{e0:.3f})/0.5)))))")
    fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,fps={FPS},"
          f"tpad=stop_mode=clone:stop_duration=5,trim=0:{tot:.3f},split=3[s][b][e];"
          f"[b]trim=0:{ho + 0.45:.3f},setpts=PTS-STARTPTS,gblur=sigma=42,eq=brightness=-0.08:saturation=0.85,format=rgba,"
          f"fade=t=out:st={ho - 0.05:.3f}:d=0.35:alpha=1[bl];"
          f"[e]trim=start={e0 - 0.4:.3f},gblur=sigma=36,format=rgba,fade=t=in:st={e0 - 0.2:.3f}:d=0.5:alpha=1[el];"
          f"[s][bl]overlay=eof_action=pass[v1];[v1][el]overlay=eof_action=pass[v2];"
          f"[v2][1:v]overlay=eof_action=repeat:enable='lt(t,{e0:.3f})'[v3];[v3][2:v]overlay=eof_action=pass[v];"
          f"[0:a]apad,atrim=0:{tot:.3f},volume='{duck}':eval=frame[ca];"
          f"[3:a]adelay={int(VO_DELAY * 1000)}|{int(VO_DELAY * 1000)}[vo];"
          f"[ca][vo][4:a]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.95[a]")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.clip,
                    '-framerate', str(FPS), '-i', os.path.join(work, 'ova', 'o_%04d.png'),
                    '-framerate', str(FPS), '-itsoffset', f'{e0:.3f}', '-i', os.path.join(work, 'ovb', 'o_%04d.png'),
                    '-i', hook_wav, '-i', sfx, '-filter_complex', fc, '-map', '[v]', '-map', '[a]',
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(FPS),
                    '-c:a', 'aac', '-b:a', '192k', '-ar', str(SR), '-t', f'{tot:.3f}', '-movflags', '+faststart', a.out], check=True)
    print('hook LUFS', loudness(a.out, 0.1, voice_len), '| clip LUFS', loudness(a.out, ho + 0.4, max(1, e0 - ho - 0.8)))
    print('wrote', a.out)
    if not a.keep:
        shutil.rmtree(work, ignore_errors=True)

if __name__ == '__main__':
    main()
