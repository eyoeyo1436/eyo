"""Original dark score + rain, mixed under the narration.

usage: python3 music.py narration.wav lines.json mix.wav
"""
import json, sys
import numpy as np, soundfile as sf

SR, DUR = 48000, 40.0
rng = np.random.default_rng(2008)
t = np.arange(int(SR * DUR)) / SR
narr, nsr = sf.read(sys.argv[1])
lines = json.load(open(sys.argv[2]))


def lowpass(x, a):
    # one-pole low-pass via cumulative filtering in blocks (fast enough here)
    from scipy.signal import lfilter
    return lfilter([a], [1, a - 1], x)


def env(t0, t1, fade=1.0):
    return np.clip((t - t0) / fade, 0, 1) * np.clip((t1 - t) / fade, 0, 1)


# low D drone: detuned saws, filtered, slow swell
f0 = 36.71
drone = sum(np.sin(2 * np.pi * f0 * k * (1 + d) * t) / k
            for d in (0, 0.003, -0.004) for k in range(1, 9))
drone = lowpass(drone, 0.02) * 0.9
drone *= 0.55 + 0.45 * np.sin(2 * np.pi * 0.07 * t - 1.5)

# one sustained string note that slowly rises a semitone over the video (tension)
pitch = 146.83 * 2 ** (np.clip(t / DUR, 0, 1) / 12)
phase = 2 * np.pi * np.cumsum(pitch * (1 + 0.004 * np.sin(2 * np.pi * 5.2 * t))) / SR
string = sum(np.sin(k * phase) / k ** 1.3 for k in range(1, 7))
string = lowpass(string, 0.08) * env(3.0, 39.5, 3.0) * (0.25 + 0.5 * t / DUR)

# ticking pulse (clock-like) from 8 s, speeds up near the end
pulse = np.zeros_like(t)
bpm_t, beat = 8.0, 0
while bpm_t < 37:
    i = int(bpm_t * SR)
    n = int(0.05 * SR)
    pulse[i:i + n] += rng.normal(0, 1, n) * np.exp(-np.arange(n) / (0.006 * SR))
    bpm_t += 0.5 if bpm_t < 28 else 0.25
pulse = np.diff(np.concatenate([[0], pulse])) * 0.35

# deep impacts on each line start
hits = np.zeros_like(t)
for m in lines[1:] + [{"start": 35.1}]:
    i = int(m["start"] * SR) - int(0.05 * SR)
    n = int(2.5 * SR)
    tt = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (48 * np.exp(-tt * 3) + 28) * tt) * np.exp(-tt * 2.2)
    boom += lowpass(rng.normal(0, 1, n), 0.05) * np.exp(-tt * 6) * 0.8
    hits[i:i + n] += boom[: len(hits) - i]

rain = lowpass(rng.normal(0, 1, len(t)), 0.35) - lowpass(rng.normal(0, 1, len(t)), 0.02)
rain *= 0.05

music = 0.30 * drone + 0.22 * string + 0.20 * pulse + 0.55 * hits + rain
music *= env(0, DUR, 0.8)

# narration, resampled to 48 kHz, with side-chain ducking of the music
v = np.interp(np.arange(int(len(narr) / nsr * SR)) / SR, np.arange(len(narr)) / nsr, narr)
voice = np.zeros_like(t)
voice[: len(v)] = v[: len(t)]
level = lowpass(np.abs(voice), 0.0008)
duck = 1 - 0.55 * np.clip(level / (level.max() * 0.35), 0, 1)
mix = music * duck + voice * 1.0
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix *= 0.93 / np.abs(mix).max()
sf.write(sys.argv[3], np.stack([mix, mix], 1).astype(np.float32), SR)
print("ok", len(mix) / SR)
