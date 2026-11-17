"""Original nostalgic ambient piano + pad soundtrack, synthesized from scratch.

Writes music.wav (stereo, 44.1 kHz, 120 s). No samples or existing music used.
"""
import sys
import wave

import numpy as np

SR = 44100
DUR = 120.0
N = int(SR * DUR)
rng = np.random.default_rng(7)

BPM = 66
BEAT = 60.0 / BPM


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# D major. Chords as MIDI notes (low pad voicing).
CHORDS = {
    "Dmaj7": [50, 57, 61, 66],
    "Bm7": [47, 54, 57, 62],
    "Gmaj7": [43, 50, 54, 59],
    "Asus2": [45, 52, 57, 59],
    "Em7": [40, 50, 55, 59],
    "F#m7": [42, 49, 52, 57],
}
PROG_A = ["Dmaj7", "Bm7", "Gmaj7", "Asus2"]
PROG_B = ["Em7", "Gmaj7", "Dmaj7", "Asus2"]
PROG_C = ["Gmaj7", "F#m7", "Em7", "Asus2"]
# melody scale: D major pentatonic + leading tones, octave 5-6
SCALE = [62, 64, 66, 69, 71, 74, 76, 78, 81]

out_l = np.zeros(N)
out_r = np.zeros(N)


def add(buf, start, sig):
    s = int(start * SR)
    if s >= N:
        return
    e = min(N, s + len(sig))
    buf[s:e] += sig[: e - s]


def piano(freq, dur=4.0, vel=0.5):
    t = np.arange(int(dur * SR)) / SR
    sig = np.zeros_like(t)
    for k in range(1, 7):
        detune = 1 + 0.0007 * (k - 1) * k
        amp = vel / k ** 1.6
        sig += amp * np.sin(2 * np.pi * freq * k * detune * t) * np.exp(-t * (0.9 + 0.7 * k))
    attack = np.minimum(1, t / 0.006)
    # soft felt-hammer thump
    thump = 0.15 * vel * np.sin(2 * np.pi * freq * 0.5 * t) * np.exp(-t * 18)
    return (sig + thump) * attack


def pad(freqs, dur, vel=0.12):
    t = np.arange(int(dur * SR)) / SR
    sig = np.zeros_like(t)
    vib = 1 + 0.0025 * np.sin(2 * np.pi * 0.25 * t)
    for f in freqs:
        for k, a in ((1, 1.0), (2, 0.35), (3, 0.12)):
            ph = rng.uniform(0, 2 * np.pi)
            sig += a * np.sin(2 * np.pi * f * k * vib * t + ph)
            sig += 0.5 * a * np.sin(2 * np.pi * f * k * 1.003 * vib * t + ph)
    env = np.minimum(1, t / 1.6) * np.minimum(1, (dur - t) / 1.6).clip(0)
    return vel * sig / len(freqs) * env


# ---- arrangement -----------------------------------------------------------
# energy curve over time: soft intro, build, quiet night, warm ending
def energy(t):
    pts = [(0, 0.15), (12, 0.45), (25, 0.65), (60, 0.85), (80, 0.8),
           (92, 0.45), (104, 0.55), (112, 0.95), (120, 0.6)]
    xs, ys = zip(*pts)
    return float(np.interp(t, xs, ys))


bar = BEAT * 4
t = 0.0
section = 0
prev_idx = 4
while t < DUR - 0.5:
    if t < 30:
        prog = PROG_A
    elif t < 60:
        prog = PROG_B if section % 2 else PROG_A
    elif t < 90:
        prog = PROG_C if section % 2 else PROG_A
    else:
        prog = PROG_B if section % 2 else PROG_A
    for name in prog:
        if t >= DUR - 0.5:
            break
        notes = CHORDS[name]
        e = energy(t)
        p = pad([midi_hz(n) for n in notes], bar + 1.8, 0.10 + 0.08 * e)
        add(out_l, t, p * 1.0)
        add(out_r, t, p * 0.92)
        # bass note
        if t > 10:
            b = piano(midi_hz(notes[0] - 12), 5, 0.35 * e)
            add(out_l, t, b)
            add(out_r, t, b)
        # broken-chord left hand
        if t > 18:
            for i, n in enumerate(notes[1:]):
                if rng.random() < 0.5 + 0.4 * e:
                    pv = piano(midi_hz(n + 12), 3.5, 0.12 * e)
                    pan = 0.4 + 0.2 * i
                    add(out_l, t + BEAT * (i + 1) * 0.5 + BEAT, pv * (1 - pan) * 2)
                    add(out_r, t + BEAT * (i + 1) * 0.5 + BEAT, pv * pan * 2)
        # melody
        if t > 4:
            for beat in range(4):
                bt = t + beat * BEAT
                prob = 0.25 + 0.45 * e if beat in (0, 2) else 0.12 + 0.3 * e
                if rng.random() < prob:
                    chord_pcs = {n % 12 for n in notes}
                    step = rng.choice([-2, -1, -1, 0, 1, 1, 2])
                    idx = int(np.clip(prev_idx + step, 0, len(SCALE) - 1))
                    if beat == 0:  # prefer chord tones on downbeat
                        cands = [i for i, m in enumerate(SCALE) if m % 12 in chord_pcs]
                        idx = min(cands, key=lambda i: abs(i - idx))
                    prev_idx = idx
                    v = 0.22 + 0.25 * e + rng.uniform(-0.04, 0.04)
                    off = rng.uniform(0, 0.03)
                    pv = piano(midi_hz(SCALE[idx]), 4.5, v)
                    pan = rng.uniform(0.35, 0.65)
                    add(out_l, bt + off, pv * (1 - pan) * 2)
                    add(out_r, bt + off, pv * pan * 2)
                    # occasional eighth-note grace
                    if rng.random() < 0.2 * e:
                        j = int(np.clip(idx + rng.choice([-1, 1]), 0, len(SCALE) - 1))
                        pv = piano(midi_hz(SCALE[j]), 3.5, v * 0.7)
                        add(out_l, bt + BEAT / 2, pv)
                        add(out_r, bt + BEAT / 2, pv)
        t += bar
    section += 1

# final resolving chord + high D
end_t = DUR - 9.5
for i, n in enumerate([50, 57, 62, 66, 69, 74]):
    pv = piano(midi_hz(n), 9, 0.28)
    add(out_l, end_t + i * 0.12, pv)
    add(out_r, end_t + i * 0.12, pv)

# chest-open "pling" at 60.5s
for i, n in enumerate([81, 86, 90]):
    pv = piano(midi_hz(n), 3, 0.25)
    add(out_l, 60.5 + i * 0.09, pv)
    add(out_r, 60.5 + i * 0.09, pv)


# ---- reverb (FFT convolution with synthetic decaying noise IR) ------------
def reverb(x, seed, seconds=3.2):
    r = np.random.default_rng(seed)
    L = int(seconds * SR)
    tt = np.arange(L) / SR
    ir = r.standard_normal(L) * np.exp(-tt * 2.1)
    # darken the tail (simple one-pole low-pass via cumulative averaging in freq)
    ir_f = np.fft.rfft(ir)
    freqs = np.fft.rfftfreq(L, 1 / SR)
    ir_f /= 1 + (freqs / 3500) ** 2
    ir = np.fft.irfft(ir_f, L)
    ir[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << int(np.ceil(np.log2(len(x) + L)))
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return y


wet_l = reverb(out_l, 1)
wet_r = reverb(out_r, 2)
mix_l = out_l * 0.62 + wet_l * 0.55
mix_r = out_r * 0.62 + wet_r * 0.55

# ---- vinyl/tape nostalgia: hiss + crackle + gentle wow ---------------------
hiss = rng.standard_normal(N)
hf = np.fft.rfft(hiss)
fr = np.fft.rfftfreq(N, 1 / SR)
hf /= 1 + (fr / 2500) ** 2
hiss = np.fft.irfft(hf, N)
hiss *= 0.004 / (np.std(hiss) + 1e-9)
crackle = np.zeros(N)
pos = rng.integers(0, N, size=int(DUR * 6))
crackle[pos] = rng.uniform(-1, 1, size=len(pos)) * rng.uniform(0.005, 0.03, size=len(pos))
mix_l += hiss + crackle
mix_r += hiss * 0.9 + np.roll(crackle, 37)

# master fade in/out + normalize
tt = np.arange(N) / SR
fade = np.minimum(1, tt / 2.5) * np.minimum(1, (DUR - tt) / 4.0).clip(0)
mix_l *= fade
mix_r *= fade
peak = max(np.abs(mix_l).max(), np.abs(mix_r).max())
mix_l = np.tanh(mix_l / peak * 1.1) * 0.85
mix_r = np.tanh(mix_r / peak * 1.1) * 0.85

stereo = np.stack([mix_l, mix_r], axis=1)
pcm = (stereo * 32767).astype(np.int16)
outp = sys.argv[1] if len(sys.argv) > 1 else "music.wav"
with wave.open(outp, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", outp)
