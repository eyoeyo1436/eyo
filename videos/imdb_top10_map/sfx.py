"""Sound design only (no voice, no music): whooshes for camera flights, pin drops with a chime,
rating tick-ups, card swishes, a drum roll and crash for #1, a soft outro chord, quiet air bed.
All sounds are synthesized here.

usage: python3 sfx.py out.wav
"""
import sys
import numpy as np, soundfile as sf
from scipy.signal import fftconvolve, butter, sosfilt
import timeline as T

SR = 48000
N = int(T.DUR * SR)
rng = np.random.default_rng(250)
L_, R_ = np.zeros(N), np.zeros(N)


def put(x, t, pan=0.0, gain=1.0):
    i = int(t * SR)
    if i >= N:
        return
    x = x[: N - i] * gain
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L_[i:i + len(x)] += x * l * 1.41
    R_[i:i + len(x)] += x * r * 1.41


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-np.maximum(t - a, 0) / d)


def whoosh(dur=1.35, lo=250, hi=2600):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    x = rng.normal(0, 1, n)
    out = np.zeros(n)
    blocks = 40
    for b in range(blocks):  # sweep band centre up then down
        s, e = b * n // blocks, (b + 1) * n // blocks
        c = lo + (hi - lo) * np.sin(np.pi * (b + 0.5) / blocks) ** 1.5
        out[s:e] = bp(x, c * 0.6, c * 1.5)[s:e]
    shape = np.sin(np.pi * t) ** 2.2
    return out * shape * 0.5


def bell(f, dur=1.6, bright=1.0):
    t = np.arange(int(dur * SR)) / SR
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * dcy)
            for m, a, dcy in ((1, 1, 3.0), (2.76, 0.45 * bright, 5), (5.4, 0.25 * bright, 8), (8.93, 0.1 * bright, 12)))
    return x * np.minimum(t / 0.002, 1)


def thump(f0=95, dur=0.35):
    t = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * (f0 * np.exp(-t * 9) + 40) * t) * np.exp(-t * 14)


def click(dur=0.012):
    n = int(dur * SR)
    return bp(rng.normal(0, 1, n), 2500, 7000) * np.exp(-np.arange(n) / (0.002 * SR))


def swish(dur=0.28):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    return bp(rng.normal(0, 1, n), 1800, 9000) * np.sin(np.pi * t) ** 2 * 0.25


def pan_of(lon):
    return float(np.clip(lon / 150, -0.8, 0.8))


# ---- intro: sub boom + airy riser
put(thump(55, 2.0) * 1.4, 0.05)
n = int(3.6 * SR)
put(bp(rng.normal(0, 1, n), 800, 8000) * np.linspace(0, 1, n) ** 2.5 * 0.18, 0.2)
put(bell(523.25, 2.5, 0.6) * 0.25, 1.0)

# ---- entries
pitches = [392.0, 415.3, 440.0, 466.2, 493.9, 523.3, 554.4, 587.3, 622.3]   # rises toward the top
prev_lon = 0.0
for k, (start, film) in enumerate(T.entries()):
    rank, title, year, rating, locs = film
    lon = locs[0][2]
    if rank == 1:
        # zoom out to the world, drum roll, dive, impact
        put(whoosh(1.2, 300, 2000) * 0.9, start + 0.0, pan_of(prev_lon) * 0.5)
        roll_s, roll_e = start + 0.2, T.ONE_HIT
        tt = roll_s
        while tt < roll_e:
            prog = (tt - roll_s) / (roll_e - roll_s)
            put(bp(rng.normal(0, 1, 2400), 900, 6000) * np.exp(-np.arange(2400) / 500) * (0.12 + 0.35 * prog), tt,
                rng.uniform(-0.2, 0.2))
            tt += 0.09 - 0.06 * prog
        put(whoosh(1.6, 200, 3500) * 1.1, T.ONE_DIVE[0], pan_of(lon) * 0.5)
        put(thump(70, 1.6) * 1.8, T.ONE_HIT)
        n = int(3.5 * SR)
        crash = bp(rng.normal(0, 1, n), 3000, 14000) * np.exp(-np.arange(n) / SR * 1.6) * 0.35
        put(crash, T.ONE_HIT, -0.3)
        put(crash[::-1][:0] if False else crash * 0.9, T.ONE_HIT + 0.01, 0.3)
        for f in (523.3, 659.3, 784.0, 1046.5):
            put(bell(f, 3.0, 0.7) * 0.22, T.ONE_HIT + 0.02)
        for _ in range(26):  # confetti sparkle
            put(bell(rng.uniform(1800, 3200), 0.5, 0.3) * 0.05, T.ONE_HIT + rng.uniform(0.1, 2.6), rng.uniform(-0.8, 0.8))
        put(whoosh(1.0, 400, 2400) * 0.6, T.ONE_HIT + 1.5, 0.4)
        put(thump(110, 0.3) * 0.7, T.ONE_HIT + 1.9, pan_of(locs[1][2]))
        put(bell(784.0, 1.5) * 0.3, T.ONE_HIT + 1.92, pan_of(locs[1][2]))
        put(swish(), start + 2.4, -0.6)
    else:
        put(whoosh() * 0.8, start + 0.0, (pan_of(lon) - pan_of(prev_lon)) * 0.5)
        put(swish(), start + 0.95, -0.6)               # card slides in (left)
        for j, pt in enumerate(T.pin_times(start, film)):
            p = pan_of(locs[j][2])
            put(thump() * 0.8, pt, p)
            put(click() * 0.6, pt, p)
            put(bell(pitches[k] * (1.5 if j else 1.0), 1.4) * 0.22, pt + 0.01, p)
        put(swish(0.22) * 0.7, start + T.OUT, -0.6)    # card slides out
    # rating count-up ticks + final ding
    c0, c1 = T.count_window(start, film)
    steps = int(round(rating * 10))
    for s in range(0, steps, 3):
        put(click() * 0.35, c0 + (c1 - c0) * (s / steps) ** 0.6, -0.5)
    put(bell(1318.5, 1.2, 0.8) * (0.28 if rank == 1 else 0.18), c1, -0.5)
    prev_lon = lon

# ---- outro: soft major chord and all pins twinkling
for i, f in enumerate((261.6, 329.6, 392.0, 493.9, 587.3)):
    put(bell(f, 4.0, 0.5) * 0.14, T.OUTRO + 0.6 + i * 0.12, (i - 2) * 0.2)
for i in range(10):
    put(bell(1568 + 60 * i, 0.6, 0.3) * 0.05, T.OUTRO + 1.0 + i * 0.16, (i - 5) / 6)
put(whoosh(1.4, 200, 1600) * 0.6, T.OUTRO)

# ---- quiet air bed
air = bp(rng.normal(0, 1, N), 150, 1200) * 0.012
L_ += air
R_ += np.roll(air, 4800)

# small-room reverb
ir = rng.normal(0, 1, int(1.2 * SR)) * np.exp(-np.arange(int(1.2 * SR)) / SR * 5)
for ch in (L_, R_):
    ch += fftconvolve(ch, ir)[:N] / np.abs(ir).sum() * 6
mix = np.stack([L_, R_], 1)
mix *= np.clip(np.arange(N) / SR / 0.05, 0, 1)[:, None] * np.clip((T.DUR - np.arange(N) / SR) / 0.8, 0, 1)[:, None]
mix = np.tanh(mix * 1.2)
mix *= 0.9 / np.abs(mix).max()
sf.write(sys.argv[1], mix.astype(np.float32), SR)
print("ok")
