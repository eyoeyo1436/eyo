"""Original upbeat background music + sound effects, mixed under the Turkish voiceover.

usage: python3 audio.py voice_raw.wav timing.json mix.wav
"""
import json, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, lfilter

SR, DUR, VO = 48000, 30.0, 0.3     # voice starts 0.3 s in
N = int(DUR * SR)
rng = np.random.default_rng(42)
TIM = json.load(open(sys.argv[2]))
S = lambda i: TIM[i]["start"] + VO
L, R = np.zeros(N), np.zeros(N)


def put(x, t, pan=0.0, g=1.0):
    i = int(t * SR)
    if i >= N or i + len(x) <= 0:
        return
    x = x[: N - i] * g
    L[i:i + len(x)] += x * np.cos((pan + 1) * np.pi / 4) * 1.41
    R[i:i + len(x)] += x * np.sin((pan + 1) * np.pi / 4) * 1.41


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "bandpass", fs=SR, output="sos"), x)


hz = lambda m: 440 * 2 ** ((m - 69) / 12)
tt = lambda d: np.arange(int(d * SR)) / SR

# ------------------------------------------------------------------ music: 112 bpm, bright pluck + pad + soft drums
BPM = 112
beat = 60 / BPM
CH = [[60, 64, 67, 71], [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 67]]   # Cmaj7  Am7  Fmaj7  G
music_L, music_R = np.zeros(N), np.zeros(N)


def mput(x, t, pan=0.0):
    i = int(t * SR)
    if i >= N:
        return
    x = x[: N - i]
    music_L[i:i + len(x)] += x * np.cos((pan + 1) * np.pi / 4) * 1.41
    music_R[i:i + len(x)] += x * np.sin((pan + 1) * np.pi / 4) * 1.41


def pluck(f, d=0.5):
    t = tt(d)
    return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)) * np.exp(-t * 7)


def pad(notes, d):
    t = tt(d)
    x = sum(np.sin(2 * np.pi * hz(m) * t * (1 + det)) for m in notes for det in (-0.003, 0.003))
    return x * np.minimum(t / 0.4, 1) * np.minimum((d - t) / 0.4, 1) / len(notes)


bar = 4 * beat
nbars = int(DUR / bar) + 1
for b in range(nbars):
    t0 = b * bar
    ch = CH[b % 4]
    mput(pad(ch, bar) * 0.10, t0)
    mput(np.sin(2 * np.pi * hz(ch[0] - 24) * tt(bar * 0.95)) * np.exp(-tt(bar * 0.95) * 1.2) * 0.22, t0)  # bass
    for k in range(8):  # eighth-note arpeggio
        if t0 + k * beat / 2 > 26.2 and b >= nbars - 1:
            break
        m = ch[[0, 2, 1, 3, 2, 1, 3, 2][k]] + 12
        mput(pluck(hz(m)) * 0.13, t0 + k * beat / 2, 0.3 if k % 2 else -0.3)
    for k in range(4):  # soft kick on beats, shaker on off-beats
        if t0 + k * beat < 1.0:
            continue
        kt = tt(0.25)
        mput(np.sin(2 * np.pi * (110 * np.exp(-kt * 25) + 45) * kt) * np.exp(-kt * 14) * 0.30, t0 + k * beat)
        sh = bp(rng.normal(0, 1, int(0.06 * SR)), 5000, 11000) * np.exp(-tt(0.06) * 60) * 0.10
        mput(sh, t0 + k * beat + beat / 2, 0.4)
# ending: ring out a final C chord at 26.3
mput(pad([48, 60, 64, 67, 72], 3.6) * 0.18, 26.3)
fade = np.ones(N)
fade[int(26.0 * SR):] = 0.0
fade = lfilter([0.0005], [1, -0.9995], fade)   # smooth fade of the loop under the ending chord
music_L *= fade
music_R *= fade
mput(pad([48, 60, 64, 67, 72], 3.6) * 0.18, 26.3)

# ------------------------------------------------------------------ sound effects
def whoosh(d=0.45):
    n = int(d * SR)
    x = bp(rng.normal(0, 1, n), 600, 5000)
    return x * np.sin(np.pi * np.linspace(0, 1, n)) ** 2 * 0.35


def pop(f=900):
    t = tt(0.12)
    return np.sin(2 * np.pi * f * np.exp(-t * 18) * t) * np.exp(-t * 30) * 0.6


def ding(f=1568):
    t = tt(1.0)
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t)) * np.exp(-t * 4) * 0.25


def buzz(d=0.9):
    t = tt(d)
    on = (np.sin(2 * np.pi * 6 * t) > 0).astype(float)
    return np.sign(np.sin(2 * np.pi * 180 * t)) * 0.08 * on * np.exp(-t * 0.5)


def stamp():
    t = tt(0.3)
    return (np.sin(2 * np.pi * (140 * np.exp(-t * 20) + 50) * t) * np.exp(-t * 18)
            + bp(rng.normal(0, 1, len(t)), 300, 3000) * np.exp(-t * 40) * 0.5) * 0.9


def boing():   # comic factory-bulge
    t = tt(0.5)
    return np.sin(2 * np.pi * (220 + 120 * np.sin(2 * np.pi * 8 * t) * np.exp(-t * 4)) * t) * np.exp(-t * 6) * 0.3


cuts = [S(1), S(2), S(5), S(6), S(10), S(13)]
for c in cuts:
    put(whoosh(), c - 0.25)
put(boing(), 0.9, -0.3)
put(boing(), 1.6, 0.3)
for i, pan in ((2, -0.5), (3, 0.0), (4, 0.5)):   # map pins: Organize Sanayi, Meram, Selçuklu
    put(pop(900 + 200 * (i - 2)), S(i) + 0.15, pan)
put(buzz(), S(5) + 0.2, 0.2)
for i, f in ((7, 1046), (8, 1175), (9, 1318)):   # needs / budget / goal bubbles
    put(pop(f), S(i), 0.3)
put(pop(1400), S(10) + 0.4)
put(stamp(), S(12) + 1.35, 0.1)
put(ding(1568), S(12) + 1.4)
put(ding(2093), S(15) + 0.05)
put(ding(1568), S(15) + 0.2)

# ------------------------------------------------------------------ voice + mix
v, vsr = sf.read(sys.argv[1])
if v.ndim > 1:
    v = v.mean(1)
v = np.interp(np.arange(int(len(v) / vsr * SR)) / SR, np.arange(len(v)) / vsr, v)
voice = np.zeros(N)
i0 = int(VO * SR)
voice[i0:i0 + len(v)] = v[: N - i0]
voice *= 0.9 / np.abs(voice).max()
level = lfilter([0.0008], [1, -0.9992], np.abs(voice))
duck = 1 - 0.55 * np.clip(level / (level.max() * 0.3), 0, 1)
ir = rng.normal(0, 1, int(0.8 * SR)) * np.exp(-tt(0.8) * 7)
mL = music_L + fftconvolve(music_L, ir)[:N] / np.abs(ir).sum() * 4
mR = music_R + fftconvolve(music_R, ir)[:N] / np.abs(ir).sum() * 4
mus = 0.55 / max(np.abs(mL).max(), np.abs(mR).max())
outL = mL * mus * duck + L * 0.8 + voice
outR = mR * mus * duck + R * 0.8 + voice
mix = np.tanh(np.stack([outL, outR], 1) * 1.05)
mix *= np.clip(np.arange(N) / SR / 0.05, 0, 1)[:, None] * np.clip((DUR - np.arange(N) / SR) / 0.6, 0, 1)[:, None]
mix *= 0.92 / np.abs(mix).max()
sf.write(sys.argv[3], mix.astype(np.float32), SR)
vr = np.sqrt(np.mean(voice[voice != 0] ** 2))
mr = np.sqrt(np.mean(((mL * mus * duck) ** 2)[int(1 * SR):int(25 * SR)]))
print(f"voice over music: {20 * np.log10(vr / mr):.1f} dB")
