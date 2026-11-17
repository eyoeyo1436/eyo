"""Original modal score (D Phrygian/Dorian colour): string drone, choir-like pad, frame drums during the war,
sea waves at the start and end, and soft impacts on scene turns. Narration stays on top.

usage: python3 music.py narration.wav timing.json mix.wav
"""
import json, sys
import numpy as np, soundfile as sf
from scipy.signal import fftconvolve, lfilter, butter, sosfilt

SR, DUR = 48000, 60.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(1200)
narr, nsr = sf.read(sys.argv[1])
TIM = json.load(open(sys.argv[2]))
LS = {}
for m in TIM:
    LS.setdefault(m["line"], m["start"])
lp = lambda x, a: lfilter([a], [1, a - 1], x)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def ens(freq, s0, s1, att=1.5, rel=2.0, voices=4, bright=10):
    n0, n1 = int(s0 * SR), min(int((s1 + rel) * SR), N)
    tt = t[n0:n1] - s0
    out = np.zeros(n1 - n0)
    for _ in range(voices):
        ph = 2 * np.pi * np.cumsum(freq * (1 + rng.uniform(-0.005, 0.005)) * (1 + 0.003 * np.sin(2 * np.pi * 5 * tt + rng.uniform(0, 6)))) / SR
        out += sum(np.sin(k * ph) / k for k in range(1, bright))
    e = np.clip(tt / att, 0, 1) * np.clip((s1 - s0 + rel - tt) / rel, 0, 1)
    return n0, n1, out * e / voices


strings, choir = np.zeros(N), np.zeros(N)
# chord plan per story beat (MIDI), modal and dark: Dm, Bb, Gm/D, Eb(phrygian), Dm, F, Bb-, Dm, D
plan = [(0, [38, 50, 57, 62]), (1, [46, 50, 58, 62]), (2, [43, 50, 55, 58]), (3, [39, 51, 55, 63]),
        (4, [38, 50, 57, 60]), (5, [41, 53, 57, 65]), (6, [34, 46, 53, 58]), (7, [38, 50, 53, 57]), (8, [38, 50, 57, 62, 66])]
starts = [0.0] + [LS[i] - 0.3 for i in range(1, 9)] + [DUR]
for i, (line, notes) in enumerate(plan):
    s0, s1 = starts[i], starts[i + 1]
    for m in notes:
        a, b, x = ens(hz(m), s0, s1)
        strings[a:b] += x * (0.5 if m < 45 else 0.3)
    for m in notes[1:]:
        a, b, x = ens(hz(m + 12), s0, s1, att=2.5, voices=3, bright=6)
        choir[a:b] += x * 0.25
strings = lp(strings, 0.10)
choir = bp(choir, 400, 1400) + 0.6 * bp(choir, 800, 1100)   # "aah" formant colour

# frame drums: war from the fleet (line 2) to Troy's fall (line 5)
drums = np.zeros(N)
w0, w1 = LS[2], LS[5] + 1.5
bt = 60 / 96
tt0 = w0
k = 0
while tt0 < w1:
    for off, amp in ((0, 1.0), (bt * 0.75, 0.5), (bt * 1.5, 0.8)):
        n = int(0.5 * SR)
        x = np.arange(n) / SR
        hit = np.sin(2 * np.pi * (80 * np.exp(-x * 8) + 55) * x) * np.exp(-x * 7) + bp(rng.normal(0, 1, n), 200, 1200) * np.exp(-x * 30) * 0.3
        i0 = int((tt0 + off) * SR)
        ramp = min(1, (tt0 - w0) / 6 + 0.35) * min(1, (w1 - tt0) / 2)
        drums[i0:i0 + n] += amp * ramp * hit[: N - i0]
    tt0 += bt * 2
    k += 1

# impacts on key turns: Aulis, Troy falls, murder, ghost, Nolan card
imp = np.zeros(N)
for s, amp in ((LS[3], 0.7), (LS[5], 1.0), (LS[6] + 5.0, 1.1), (LS[7], 0.6), (LS[8], 0.8)):
    n = int(3 * SR)
    x = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (50 * np.exp(-x * 3) + 30) * x) * np.exp(-x * 1.8) + lp(rng.normal(0, 1, n), 0.04) * np.exp(-x * 5) * 0.6
    i0 = int(s * SR)
    imp[i0:i0 + n] += amp * boom[: N - i0]

# sea: start (0-10 s) and end (ghost / homecoming parts)
sea = lp(rng.normal(0, 1, N), 0.06) * (0.55 + 0.45 * np.sin(2 * np.pi * 0.12 * t) ** 2)
sea_env = np.clip(1 - (t - 8) / 3, 0, 1) + np.clip((t - LS[5]) / 2, 0, 1) * np.clip((LS[6] - t) / 1.5, 0, 1) + np.clip((t - LS[8]) / 2, 0, 1)
sea *= sea_env * 0.5

music = 0.30 * strings + 0.18 * choir + 0.55 * drums + 0.6 * imp + sea
ir = lp(rng.normal(0, 1, int(3 * SR)) * np.exp(-np.arange(int(3 * SR)) / SR * 2), 0.3)
music = music + fftconvolve(music, ir)[:N] / np.abs(ir).sum() * 8
music *= np.clip(t / 0.4, 0, 1) * np.clip((DUR - t) / 1.6, 0, 1)

v = np.interp(np.arange(int(len(narr) / nsr * SR)) / SR, np.arange(len(narr)) / nsr, narr)
voice = np.zeros(N)
voice[: min(len(v), N)] = v[:N]
level = lp(np.abs(voice), 0.0006)
duck = 1 - 0.55 * np.clip(level / (level.max() * 0.3), 0, 1)
music *= 0.20 / np.abs(music).max()
mix = np.tanh((music * duck + voice) * 1.05) / np.tanh(1.05)
mix *= 0.93 / np.abs(mix).max()
sf.write(sys.argv[3], np.stack([mix, mix], 1).astype(np.float32), SR)
vr = np.sqrt(np.mean(voice[voice != 0] ** 2))
mr = np.sqrt(np.mean((music * duck) ** 2))
print(f"voice/music: {20 * np.log10(vr / mr):.1f} dB")
