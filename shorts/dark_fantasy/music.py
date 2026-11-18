"""Original 15-second dark-fantasy cue (fully synthesised; no existing music is used).

D minor: music-box arpeggios, a breathy "aah" choir, organ, harp, heartbeat timpani, magic
shimmers on every crossfade, and a dragon's growl when the great eye opens.
Usage: python3 music.py OUT.wav [shot_starts as comma list, default 0,2.83,5.67,8.5,11.33]
"""
import sys
import numpy as np
from scipy import signal
import soundfile as sf

SR = 48000
DUR = 15.0
N = int(DUR * SR)
rng = np.random.default_rng(3)
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7,
        'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}

def nm(s):
    return 12 * (int(s[-1]) + 1) + NOTE[s[:-1]]

def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)

def place(buf, x, t, g=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(x) <= 0:
        return
    if i < 0:
        x = x[-i:]; i = 0
    x = x[:len(buf) - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(x), 0] += x * g * l * 1.414
    buf[i:i + len(x), 1] += x * g * r * 1.414

def filt(x, kind, f):
    b, a = signal.butter(2, np.array(f) / (SR / 2), kind)
    return signal.lfilter(b, a, x)

def env(n, att, rel):
    e = np.ones(n)
    na, nr = max(1, int(att * SR)), max(1, int(rel * SR))
    e[:na] = np.linspace(0, 1, na) ** 1.5
    e[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    return e

def music_box(m, dur=2.2):
    n = int(dur * SR); t = np.arange(n) / SR
    ph = 2 * np.pi * hz(m) * t
    x = (np.sin(ph) * np.exp(-t * 2.6) + 0.4 * np.sin(2.76 * ph) * np.exp(-t * 7) +
         0.2 * np.sin(5.4 * ph) * np.exp(-t * 12) + 0.1 * np.sin(8.9 * ph) * np.exp(-t * 20))
    x[:200] += rng.normal(0, 1, 200) * np.exp(-np.arange(200) / 30) * 0.2
    return x * 0.5

def saw_voices(ms, dur, detune=0.006, vib=5.0, harmonics=24):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n)
    for m in ms:
        for d in (-detune, 0, detune):
            ph0 = rng.uniform(0, 6.28)
            f = hz(m) * (1 + d) * (1 + 0.004 * np.sin(2 * np.pi * vib * t + ph0))
            ph = 2 * np.pi * np.cumsum(f) / SR
            for h in range(1, harmonics):
                if hz(m) * h > 12000:
                    break
                out += np.sin(h * ph + ph0) / h
    return out / (len(ms) * 3)

def choir(ms, dur, att=1.2, rel=1.2):
    """Breathy 'aah' choir: saw ensemble through vowel formants."""
    x = saw_voices(ms, dur, 0.008, 5.5)
    y = (filt(x, 'band', [600, 900]) * 1.0 + filt(x, 'band', [1000, 1300]) * 0.6 + filt(x, 'band', [2400, 2900]) * 0.25)
    y += filt(rng.normal(0, 1, len(x)), 'band', [700, 1400]) * 0.01
    return y * env(len(x), att, rel) * 3.0

def organ(ms, dur, att=0.4, rel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n)
    for m in ms:
        for h, a in ((1, 1.0), (2, 0.6), (3, 0.35), (4, 0.25), (6, 0.15), (8, 0.1)):
            out += a * np.sin(2 * np.pi * hz(m) * h * t)
    out *= 1 + 0.05 * np.sin(2 * np.pi * 6.0 * t)
    return filt(out, 'low', 3000) * env(n, att, rel) / len(ms) * 0.35

def harp(m, dur=2.5):
    n = int(dur * SR); p = max(2, int(SR / hz(m)))
    y = np.zeros(n + p); y[:p] = filt(rng.uniform(-1, 1, p), 'low', 5000)
    k = p
    while k < n + p:
        seg = y[k - p:k]
        nx = 0.997 * 0.5 * (seg + np.concatenate([seg[1:], seg[-1:]]))
        mm = min(p, n + p - k); y[k:k + mm] = nx[:mm]; k += p
    out = y[p:]
    return out / (np.abs(out).max() + 1e-9) * env(n, 0.002, 0.3)

def drone(m, dur, att=1.0, rel=1.5):
    x = saw_voices([m, m - 12], dur, 0.003, 3.0, 12)
    return filt(x, 'low', 400) * env(len(x), att, rel) * 2.2

def timpani(f=45, g=1.0):
    n = int(1.5 * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 1.5 * t)) * np.exp(-t * 3.5)
    x += filt(rng.normal(0, 1, n), 'low', 250) * np.exp(-t * 30) * 0.5
    return x * g

def boom(g=1.0):
    n = int(3.0 * SR); t = np.arange(n) / SR
    f = 30 + 60 * np.exp(-t * 5)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.5)
    return (x + filt(rng.normal(0, 1, n), 'low', 300) * np.exp(-t * 12) * 0.6) * g

def swell(dur=0.8, g=1.0):
    """Reverse-cymbal style swell into a cut."""
    n = int(dur * SR); t = np.arange(n) / SR
    x = filt(rng.normal(0, 1, n), 'band', [2500, 12000]) * (t / dur) ** 3
    x[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return x * 0.5 * g

def shimmer(g=1.0, up=True):
    """Glissando of bell tones: the magic sparkle on each crossfade."""
    out = np.zeros(int(2.2 * SR))
    notes = [nm(s) for s in ('D5', 'F5', 'A5', 'C6', 'D6', 'F6', 'A6', 'D7')]
    if not up:
        notes = notes[::-1]
    for k, m in enumerate(notes):
        mb = music_box(m, 1.4) * 0.6
        i = int(k * 0.045 * SR)
        out[i:i + len(mb)] += mb[:len(out) - i]
    return out * g

def growl(dur=1.6, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 55 + 10 * np.sin(2 * np.pi * 7 * t) + rng.normal(0, 4, n).cumsum() * 0.002
    x = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sin(2 * np.pi * 11 * t))
    x = filt(x, 'low', 600) + filt(rng.normal(0, 1, n), 'band', [80, 500]) * 0.6
    return x * env(n, 0.25, 0.6) * g

def reverb(x, secs=3.0, mix=0.35, seed=1):
    r = np.random.default_rng(seed)
    n = int(secs * SR); t = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = r.normal(0, 1, n) * np.exp(-t * 6.9 / secs)
        ir = filt(ir, 'low', 6000); ir /= np.sqrt((ir ** 2).sum())
        out[:, ch] = signal.fftconvolve(x[:, ch], ir)[:len(x)]
    return x * (1 - mix) + out * mix

def build(out_path, starts):
    s_sky, s_path, s_hall, s_sorc, s_hoard = starts
    mus = np.zeros((N, 2))
    # SKY: ethereal choir + music-box arpeggio + drone
    place(mus, drone(nm('D3'), s_path + 0.6, att=1.5, rel=0.8), 0.0, 0.5)
    place(mus, choir([nm('D4'), nm('F4'), nm('A4')], s_path + 0.8, att=1.4, rel=0.9), 0.0, 0.5)
    for k, n_ in enumerate(['D5', 'A5', 'F5', 'D6', 'A5', 'F5', 'E5', 'A5']):
        place(mus, music_box(nm(n_)), 0.25 + k * 0.33, 0.45, 0.3 * (1 if k % 2 else -1))
    # PATH: heartbeat timpani + harp arpeggios
    for k in range(4):
        place(mus, timpani(44, 0.55), s_path + 0.1 + k * 0.72, 1.0)
    for k, n_ in enumerate(['Bb3', 'D4', 'F4', 'Bb4', 'A3', 'C#4', 'E4', 'A4']):
        place(mus, harp(nm(n_)), s_path + 0.15 + k * 0.36, 0.28, -0.3)
    place(mus, choir([nm('Bb3'), nm('D4'), nm('F4')], 1.6, 0.4, 0.5), s_path, 0.45)
    place(mus, choir([nm('A3'), nm('C#4'), nm('E4')], 1.8, 0.3, 0.8), s_path + 1.45, 0.45)
    place(mus, drone(nm('A2'), s_hall - s_path + 0.5, 0.3, 0.5), s_path, 0.45)
    # HALL: organ Gm -> Eb, choir doubling, candle chimes
    place(mus, organ([nm('G3'), nm('Bb3'), nm('D4'), nm('G2')], 1.7, 0.3, 0.4), s_hall, 1.0)
    place(mus, organ([nm('Eb3'), nm('G3'), nm('Bb3'), nm('Eb2')], 1.6, 0.2, 0.8), s_hall + 1.5, 1.0)
    place(mus, choir([nm('G4'), nm('Bb4'), nm('D5')], 3.0, 0.5, 0.8), s_hall, 0.35)
    for k, n_ in enumerate(['G5', 'D6', 'Bb5']):
        place(mus, music_box(nm(n_), 1.5), s_hall + 0.4 + k * 0.8, 0.3, 0.4)
    # SORCERER: mysterious Neapolitan colour, celesta motif, pages
    place(mus, choir([nm('Eb4'), nm('G4'), nm('Bb4')], 1.8, 0.3, 0.5), s_sorc, 0.55)
    place(mus, choir([nm('C#4'), nm('E4'), nm('A4')], 1.7, 0.3, 0.8), s_sorc + 1.6, 0.55)
    place(mus, drone(nm('Eb2') + 12, 1.8, 0.2, 0.4), s_sorc, 0.4)
    place(mus, drone(nm('A2'), 1.7, 0.2, 0.8), s_sorc + 1.6, 0.45)
    for k, n_ in enumerate(['Eb6', 'Bb5', 'G5', 'Eb5', 'C#6', 'A5', 'E5', 'A5']):
        place(mus, music_box(nm(n_), 1.6), s_sorc + 0.1 + k * 0.38, 0.38, 0.35 * (1 if k % 2 else -1))
    # HOARD: darkness, eyes open, the dragon's eye, final D minor
    place(mus, drone(nm('D2') + 12, DUR - s_hoard, 0.3, 1.2), s_hoard, 0.6)
    place(mus, choir([nm('D4'), nm('Eb4'), nm('A4')], 2.3, 0.6, 0.4), s_hoard, 0.4)   # dissonant cluster
    for k in range(8):
        place(mus, music_box(nm('A6') - (k % 3) * 5, 0.8), s_hoard + 0.55 + k * 0.24, 0.18, 0.6 * (1 if k % 2 else -1))
    t_eye = s_hoard + 2.35
    place(mus, swell(0.9, 1.4), t_eye - 0.9, 1.0)
    place(mus, boom(1.1), t_eye, 1.0)
    place(mus, growl(1.8, 1.0), t_eye + 0.05, 0.7)
    place(mus, choir([nm('D3'), nm('A3'), nm('D4'), nm('F4'), nm('A4')], DUR - t_eye, 0.15, 1.0), t_eye, 0.8)
    place(mus, organ([nm('D2'), nm('D3'), nm('A3'), nm('F4')], DUR - t_eye, 0.1, 1.0), t_eye, 1.0)
    # transitions: swell into each cut, shimmer on each crossfade
    for k, st in enumerate((s_path, s_hall, s_sorc, s_hoard)):
        place(mus, swell(0.7), st - 0.6, 0.8)
        place(mus, shimmer(0.5, up=(k % 2 == 0)), st - 0.05, 1.0, 0.2)
        place(mus, boom(0.35), st + 0.1, 1.0)
    place(mus, shimmer(0.4), 0.05, 1.0, -0.2)
    mus = reverb(mus, 3.2, 0.36)
    fade = np.ones(N); fi = int(0.4 * SR); fade[:fi] = np.linspace(0, 1, fi)
    fo = int((DUR - 1.0) * SR); fade[fo:] = np.linspace(1, 0, N - fo) ** 1.4
    mus *= fade[:, None]
    mus /= np.abs(mus).max() + 1e-9
    sf.write(out_path, (mus * 0.9).astype(np.float32), SR)

if __name__ == '__main__':
    starts = [float(v) for v in (sys.argv[2] if len(sys.argv) > 2 else '0,2.83,5.67,8.5,11.33').split(',')]
    build(sys.argv[1], starts)
