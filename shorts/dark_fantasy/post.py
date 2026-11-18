"""Post-production for the dark-fantasy Short.

Takes the 15 fps Cycles renders, motion-interpolates each shot to 30 fps, then for every output
frame: upscales to 1080x1920, applies the crunchy over-sharpened 90s-CG look (double unsharp mask,
boosted saturation, crushed blacks), bloom, per-shot twinkling star glints and magic particles,
glowing crossfades, and fades in/out. Muxes the score and writes exactly 15.0 s.

Usage: python3 post.py FRAMES_DIR WORK_DIR MUSIC_WAV OUT.mp4 [--workers 4] [--stills DIR]
"""
import os, sys, glob, math, argparse, subprocess
import numpy as np
from PIL import Image, ImageFilter

OW, OH, FPS = 1080, 1920, 30
DURATION = 15.0
XFADE = 0.4
SHOTS = ['sky', 'path', 'hall', 'sorcerer', 'hoard']

# per-shot particle recipe: (kind, count, colours)
PARTICLES = {
    'sky': [('glint', 85, [(255, 200, 60), (255, 225, 120)]), ('mote', 30, [(140, 170, 255)])],
    'path': [('mote', 50, [(80, 255, 150), (90, 220, 255)]), ('glint', 25, [(255, 214, 90)])],
    'hall': [('ember', 60, [(255, 170, 70), (255, 220, 140)]), ('glint', 20, [(220, 210, 255)])],
    'sorcerer': [('mote', 70, [(110, 255, 230), (190, 120, 255)]), ('glint', 35, [(255, 214, 90)])],
    'hoard': [('ember', 50, [(255, 70, 50), (255, 160, 60)]), ('glint', 40, [(255, 220, 110)])],
}

def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)

# ------------------------------------------------------------------ interpolation
def interpolate(frames_dir, work):
    """15 fps PNGs -> 30 fps motion-compensated PNGs per shot. Returns {shot: [paths]}."""
    out = {}
    for shot in SHOTS:
        d = os.path.join(work, shot)
        os.makedirs(d, exist_ok=True)
        if not glob.glob(os.path.join(d, '*.png')):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '15', '-pattern_type', 'glob',
                            '-i', os.path.join(frames_dir, f'{shot}_*.png'),
                            '-vf', 'minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1',
                            os.path.join(d, 'f_%04d.png')], check=True)
        out[shot] = sorted(glob.glob(os.path.join(d, 'f_*.png')))
    return out

def plan(seqs):
    """Shot start times with XFADE overlaps."""
    starts, t = {}, 0.0
    for i, shot in enumerate(SHOTS):
        starts[shot] = t
        t += len(seqs[shot]) / FPS - XFADE
    return starts

# ------------------------------------------------------------------ look
def crunch(img):
    """Upscale + the over-sharpened, high-saturation late-90s render look."""
    img = img.resize((OW, OH), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=2.4, percent=170, threshold=1))
    img = img.filter(ImageFilter.UnsharpMask(radius=0.9, percent=90, threshold=0))
    x = np.asarray(img).astype(np.float32) / 255.0
    lum = (x @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    x = lum + (x - lum) * 1.28                      # saturation
    x = np.clip((x - 0.035) / 0.965, 0, 1)          # crush blacks
    x = np.clip(x * 1.06, 0, 1)
    return x

def bloom(x, strength=0.55):
    lum = x.max(axis=2, keepdims=True)
    hi = np.clip((lum - 0.6) / 0.4, 0, 1) * x
    im = Image.fromarray((hi * 255).astype(np.uint8))
    small = im.resize((OW // 4, OH // 4), Image.BILINEAR)
    b1 = np.asarray(small.filter(ImageFilter.GaussianBlur(4)).resize((OW, OH), Image.BILINEAR)).astype(np.float32) / 255
    b2 = np.asarray(small.filter(ImageFilter.GaussianBlur(14)).resize((OW, OH), Image.BILINEAR)).astype(np.float32) / 255
    return 1 - (1 - x) * (1 - np.clip((b1 * 0.7 + b2 * 0.9) * strength, 0, 1))   # screen

# ------------------------------------------------------------------ particles
class Particles:
    def __init__(self, shot, seed):
        self.items = []
        rng = np.random.default_rng(seed)
        for kind, n, cols in PARTICLES[shot]:
            for _ in range(n):
                self.items.append(dict(kind=kind, x=rng.uniform(0, OW), y=rng.uniform(0, OH),
                                       phase=rng.uniform(0, 6.28), speed=rng.uniform(0.6, 1.6),
                                       size=rng.uniform(0.6, 1.4), col=cols[rng.integers(len(cols))],
                                       vx=rng.uniform(-25, 25), vy=rng.uniform(-90, -25)))

    def draw(self, x, t):
        """Additive drawing into float image x (in place)."""
        for p in self.items:
            if p['kind'] == 'glint':                 # four-point twinkling star
                tw = max(0.0, math.sin(t * 3.2 * p['speed'] + p['phase'])) ** 3
                if tw < 0.05:
                    continue
                L = int(36 * p['size'] * (0.4 + 0.6 * tw))
                self._star(x, p['x'], p['y'], L, p['col'], tw)
            else:
                age = (t * p['speed'] * 0.35 + p['phase'] / 6.28) % 1.0
                px = (p['x'] + p['vx'] * t + 18 * math.sin(t * 1.3 + p['phase'])) % OW
                py = (p['y'] + p['vy'] * t * (1.6 if p['kind'] == 'ember' else 1.0)) % OH
                a = math.sin(math.pi * age)
                r = (3.0 if p['kind'] == 'mote' else 2.2) * p['size']
                self._dot(x, px, py, r, p['col'], a * 0.9)

    @staticmethod
    def _dot(x, cx, cy, r, col, a):
        R = int(r * 4) + 2
        x0, x1 = int(max(0, cx - R)), int(min(OW, cx + R))
        y0, y1 = int(max(0, cy - R)), int(min(OH, cy + R))
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r)
        g = (np.exp(-d2) + 0.35 * np.exp(-d2 / 6)) * a
        x[y0:y1, x0:x1] += g[..., None] * (np.array(col, np.float32) / 255.0)

    @staticmethod
    def _star(x, cx, cy, L, col, a):
        c = np.array(col, np.float32) / 255.0
        x0, x1 = int(max(0, cx - L)), int(min(OW, cx + L + 1))
        y0, y1 = int(max(0, cy - L)), int(min(OH, cy + L + 1))
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dx, dy = np.abs(xx - cx), np.abs(yy - cy)
        rays = np.exp(-dy / 1.2) * np.clip(1 - dx / L, 0, 1) + np.exp(-dx / 1.2) * np.clip(1 - dy / L, 0, 1)
        core = np.exp(-(dx ** 2 + dy ** 2) / 6.0)
        g = (rays * 1.1 + core * 1.4) * a
        x[y0:y1, x0:x1] += g[..., None] * c

# ------------------------------------------------------------------ frames
SEQS = STARTS = PARTS = None

def shot_frame(shot, t):
    seq = SEQS[shot]
    i = int(round((t - STARTS[shot]) * FPS))
    i = min(max(i, 0), len(seq) - 1)
    return crunch(Image.open(seq[i]).convert('RGB'))

def render(fi):
    t = fi / FPS
    active = [s for s in SHOTS if STARTS[s] - 1e-6 <= t < STARTS[s] + len(SEQS[s]) / FPS]
    cur = active[-1]
    x = shot_frame(cur, t)
    PARTS[cur].draw(x, t)
    flash = 0.0
    if len(active) > 1:                               # glowing crossfade
        prev = active[-2]
        u = ease((t - STARTS[cur]) / XFADE)
        xp = shot_frame(prev, t)
        PARTS[prev].draw(xp, t)
        x = xp * (1 - u) + x * u
        flash = math.sin(math.pi * u) * 0.35
    x = bloom(np.clip(x, 0, 1), 0.55 + flash)
    if flash:
        x = x + (np.array([0.35, 0.45, 1.0], np.float32) - x) * flash * 0.25
    x *= ease(t / 0.6) * (1 - ease((t - (DURATION - 0.7)) / 0.7))
    rng = np.random.default_rng(fi)
    x += rng.normal(0, 0.018, (OH // 2, OW // 2, 1)).repeat(2, 0).repeat(2, 1)
    return (np.clip(x, 0, 1) * 255).astype(np.uint8)

def worker(args):
    f0, f1, path = args
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
                          '-pix_fmt', 'yuv420p', '-g', '30', path], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        p.stdin.write(render(fi).tobytes())
    p.stdin.close(); p.wait()
    return path

def main():
    global SEQS, STARTS, PARTS
    ap = argparse.ArgumentParser()
    ap.add_argument('frames'); ap.add_argument('work'); ap.add_argument('music'); ap.add_argument('out')
    ap.add_argument('--workers', type=int, default=4); ap.add_argument('--stills', default=None)
    a = ap.parse_args()
    SEQS = interpolate(a.frames, a.work)
    STARTS = plan(SEQS)
    PARTS = {s: Particles(s, i + 1) for i, s in enumerate(SHOTS)}
    print('shot starts:', {k: round(v, 2) for k, v in STARTS.items()}, 'end:', round(STARTS['hoard'] + len(SEQS['hoard']) / FPS, 2))
    if a.stills:
        for sec in (0.8, 2.0, 3.1, 4.5, 6.0, 7.5, 9.5, 10.8, 12.0, 13.5, 14.3):
            Image.fromarray(render(int(sec * FPS))).save(os.path.join(a.stills, f's_{sec:04.1f}.png'))
        return
    total = int(DURATION * FPS)
    b = np.linspace(0, total, a.workers + 1).astype(int)
    jobs = [(b[i], b[i + 1], os.path.join(a.work, f'seg{i}.mp4')) for i in range(a.workers)]
    import multiprocessing as mp
    with mp.get_context('fork').Pool(a.workers) as pool:
        segs = pool.map(worker, jobs)
    lst = os.path.join(a.work, 'list.txt')
    open(lst, 'w').write(''.join(f"file '{s}'\n" for s in segs))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', a.music,
                    '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow', '-b:v', '12M', '-maxrate', '16M',
                    '-bufsize', '24M', '-pix_fmt', 'yuv420p', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac',
                    '-b:a', '192k', '-ar', '48000', '-t', str(DURATION), '-movflags', '+faststart', a.out], check=True)
    print('wrote', a.out)

if __name__ == '__main__':
    main()
