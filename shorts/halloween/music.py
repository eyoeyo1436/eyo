"""Original eerie score (music-box notes, detuned pad, wind, thumps) mixed under the narration.

usage: python3 music.py narration.wav lines.json mix.wav
"""
import json, sys
import numpy as np, soundfile as sf
from scipy.signal import lfilter

SR, DUR = 48000, 30.0
rng = np.random.default_rng(1978)
t = np.arange(int(SR * DUR)) / SR
narr, nsr = sf.read(sys.argv[1])
lines = json.load(open(sys.argv[2]))
lp = lambda x, a: lfilter([a], [1, a - 1], x)

# detuned pad on A minor with a flat-sixth rub (F over A), slowly beating
pad = sum(np.sin(2 * np.pi * f * (1 + d) * t) for f in (110, 130.81, 174.61) for d in (0, 0.006))
pad = lp(pad, 0.05) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t))

# music-box notes: a slow, irregular descending figure (original), with long decays
box = np.zeros_like(t)
notes = [880, 830.6, 659.3, 622.3, 587.3, 523.3, 440, 415.3]
tt, i = 1.0, 0
while tt < 29:
    f = notes[i % len(notes)] * (0.5 if (i // len(notes)) % 2 else 1)
    n = int(2.5 * SR)
    s = int(tt * SR)
    x = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 4.07 * x)) * np.exp(-x * 2.4)
    box[s:s + n] += tone[: len(box) - s]
    tt += [0.75, 0.75, 1.5, 0.75, 1.25, 0.5, 1.5][i % 7]
    i += 1

wind = lp(rng.normal(0, 1, len(t)), 0.01) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.17 * t + 1))
wind *= 4

hits = np.zeros_like(t)
for m in lines[1:]:
    s = int(m["start"] * SR) - int(0.04 * SR)
    n = int(1.8 * SR)
    x = np.arange(n) / SR
    thump = np.sin(2 * np.pi * (60 * np.exp(-x * 5) + 32) * x) * np.exp(-x * 3)
    thump += np.sin(2 * np.pi * 1760 * x) * np.exp(-x * 9) * 0.15  # metallic sting
    hits[s:s + n] += thump[: len(hits) - s]

fade = np.clip(t / 1.2, 0, 1) * np.clip((DUR - t) / 1.0, 0, 1)
music = (0.18 * pad + 0.22 * box + 0.12 * wind + 0.5 * hits) * fade

v = np.interp(np.arange(int(len(narr) / nsr * SR)) / SR, np.arange(len(narr)) / nsr, narr)
voice = np.zeros_like(t)
voice[: min(len(v), len(t))] = v[: len(t)]
level = lp(np.abs(voice), 0.0008)
duck = 1 - 0.5 * np.clip(level / (level.max() * 0.35), 0, 1)
mix = np.tanh((music * duck + voice) * 1.1) / np.tanh(1.1)
mix *= 0.93 / np.abs(mix).max()
sf.write(sys.argv[3], np.stack([mix, mix], 1).astype(np.float32), SR)
print("ok")
