"""Original orchestral-style score (strings, low brass, timpani, riser) mixed under the narration.
Narration stays clearly on top: music sits low and is ducked further while the voice speaks.

usage: python3 music.py narration.wav timing.json mix.wav
"""
import json, sys
import numpy as np, soundfile as sf
from scipy.signal import fftconvolve, lfilter

SR, DUR = 48000, 40.0
rng = np.random.default_rng(14)
t = np.arange(int(SR * DUR)) / SR
narr, nsr = sf.read(sys.argv[1])
timing = json.load(open(sys.argv[2]))
lp = lambda x, a: lfilter([a], [1, a - 1], x)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)


def saw_ens(freq, start, end, att=1.2, rel=1.5, voices=5):
    """Ensemble strings: detuned band-limited saws with vibrato and slow attack."""
    n0, n1 = int(start * SR), min(int((end + rel) * SR), len(t))
    tt = t[n0:n1] - start
    out = np.zeros(n1 - n0)
    for v in range(voices):
        det = 1 + rng.uniform(-0.006, 0.006)
        vib = 1 + 0.003 * np.sin(2 * np.pi * (5 + rng.uniform(-0.5, 0.5)) * tt + rng.uniform(0, 6))
        ph = 2 * np.pi * np.cumsum(freq * det * vib) / SR
        out += sum(np.sin(k * ph) / k for k in range(1, 12))
    envl = np.clip(tt / att, 0, 1) * np.clip((end - start + rel - tt) / rel, 0, 1)
    return n0, n1, out * envl / voices


# chord plan (original): D minor world, lifting to F major at the reveal and resolving on D
CHORDS = [(0.0, [50, 57, 62, 65, 69]), (4.2, [46, 53, 58, 62, 65]), (10.6, [43, 50, 55, 58, 62]),
          (16.6, [45, 52, 57, 61, 64]), (23.0, [46, 53, 58, 62, 67]), (29.0, [41, 48, 53, 57, 60, 65]),
          (35.1, [50, 57, 62, 66, 69, 74])]
strings = np.zeros_like(t)
for i, (s0, notes) in enumerate(CHORDS):
    e = CHORDS[i + 1][0] if i + 1 < len(CHORDS) else DUR - 0.5
    for m in notes:
        n0, n1, x = saw_ens(hz(m), s0, e, att=1.0 if i else 0.4)
        strings[n0:n1] += x * (0.5 if m < 52 else 0.35)
strings = lp(strings, 0.12) * (0.55 + 0.45 * np.clip((t - 25) / 10, 0, 1))  # builds toward the end

# low brass swells on scene turns
brass = np.zeros_like(t)
for s0, m in ((4.2, 38), (16.6, 33), (29.0, 29), (35.1, 38)):
    n0, n1, x = saw_ens(hz(m), s0, s0 + 3.5, att=0.8, rel=1.2, voices=3)
    brass[n0:n1] += x
brass = lp(brass, 0.04)

# timpani hits
timp = np.zeros_like(t)
for s0, amp in ((0.08, 1.0), (4.2, 0.8), (10.6, 0.6), (16.6, 0.9), (23.0, 0.6), (29.0, 1.0), (35.1, 1.2)):
    n = int(2.4 * SR)
    x = np.arange(n) / SR
    hit = (np.sin(2 * np.pi * (72 * np.exp(-x * 4) + 44) * x) * np.exp(-x * 2.0)
           + lp(rng.normal(0, 1, n), 0.08) * np.exp(-x * 14) * 0.6)
    i0 = int(s0 * SR)
    timp[i0:i0 + n] += amp * hit[: len(t) - i0]

# riser into the reveal (27.0 -> 29.0) and a soft high shimmer at the end
riser = np.zeros_like(t)
a, b = int(27.0 * SR), int(29.0 * SR)
x = np.linspace(0, 1, b - a)
riser[a:b] = lp(rng.normal(0, 1, b - a), 0.3) * x ** 3 * 0.5
shim = np.sin(2 * np.pi * hz(86) * t) * np.clip((t - 35.1) / 2, 0, 1) * np.clip((DUR - t) / 2, 0, 1) * 0.05

music = 0.30 * strings + 0.35 * brass + 0.55 * timp + riser + shim
# hall reverb: exponentially decaying noise impulse response
ir = rng.normal(0, 1, int(2.6 * SR)) * np.exp(-np.arange(int(2.6 * SR)) / SR * 2.4)
ir = lp(ir, 0.25)
music = music + 0.22 * fftconvolve(music, ir)[: len(t)] / np.abs(ir).sum() * 40
music *= np.clip(t / 0.2, 0, 1) * np.clip((DUR - t) / 1.2, 0, 1)

v = np.interp(np.arange(int(len(narr) / nsr * SR)) / SR, np.arange(len(narr)) / nsr, narr)
voice = np.zeros_like(t)
voice[: min(len(v), len(t))] = v[: len(t)]
level = lp(np.abs(voice), 0.0006)
duck = 1 - 0.6 * np.clip(level / (level.max() * 0.3), 0, 1)
music *= 0.30 / (np.abs(music).max() + 1e-9)
mix = np.tanh((music * duck + voice) * 1.05) / np.tanh(1.05)
mix *= 0.93 / np.abs(mix).max()
sf.write(sys.argv[3], np.stack([mix, mix], 1).astype(np.float32), SR)
vr = np.sqrt(np.mean(voice[voice != 0] ** 2))
mr = np.sqrt(np.mean((music * duck) ** 2))
print(f"voice/music RMS ratio: {20 * np.log10(vr / mr):.1f} dB")
