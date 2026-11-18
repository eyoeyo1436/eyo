"""Original score + sound design for the Conjuring Short (fully synthesised; no film audio).

Writes music.wav (ducked under the voice at mix time) and sfx.wav.
Usage: python3 music.py TIMING_JSON OUT_DIR
"""
import sys
import numpy as np
from scipy import signal
import soundfile as sf
from timeline import layout, shots, DURATION

SR = 48000
N = int(DURATION * SR)
rng = np.random.default_rng(13)
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

def filt(x, kind, f, order=2):
    b, a = signal.butter(order, np.array(f) / (SR / 2), kind)
    return signal.lfilter(b, a, x)

def env(n, att, rel):
    e = np.ones(n)
    na, nr = max(1, int(att * SR)), max(1, int(rel * SR))
    e[:na] = np.linspace(0, 1, na) ** 1.5
    e[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    return e

def strings(ms, dur, att=1.0, rel=1.0, vib=5.0, bright=10):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n)
    for m in ms:
        for d in (-0.004, 0, 0.004):
            ph0 = rng.uniform(0, 6.28)
            f = hz(m) * (1 + d) * (1 + 0.003 * np.sin(2 * np.pi * vib * t + ph0))
            ph = 2 * np.pi * np.cumsum(f) / SR
            for h in range(1, bright):
                if hz(m) * h > 9000:
                    break
                out += np.sin(h * ph + ph0) / h ** 1.3
    return filt(out, 'low', 2500) * env(n, att, rel) / (len(ms) * 3)

def drone(m, dur, att=2.0, rel=2.0):
    return filt(strings([m, m - 12, m + 7], dur, att, rel, 3.0, 14), 'low', 500) * 2.0

def cluster(ms, dur, att=1.5, rel=0.3):
    """Dissonant high-string cluster with tremolo."""
    x = strings(ms, dur, att, rel, 7.0, 6)
    t = np.arange(len(x)) / SR
    return x * (0.75 + 0.25 * np.sin(2 * np.pi * 11 * t))

def piano(m, dur=3.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = hz(m)
    x = sum(np.sin(2 * np.pi * f * h * t * (1 + 0.0004 * h * h)) * np.exp(-t * (1.2 + h * 0.6)) / h for h in range(1, 8))
    x[:120] *= np.linspace(0, 1, 120)
    return x * 0.5

def wind(dur, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    x = filt(rng.normal(0, 1, n), 'band', [150, 900])
    mod = 0.6 + 0.4 * np.sin(2 * np.pi * 0.23 * t + 1) * np.sin(2 * np.pi * 0.11 * t)
    whistle = np.sin(2 * np.pi * np.cumsum(620 + 120 * np.sin(2 * np.pi * 0.17 * t)) / SR) * 0.03
    return (x * mod * 0.6 + whistle) * env(n, 0.8, 0.8) * g

def crickets(dur, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    chirp = (np.sin(2 * np.pi * 4300 * t) * (np.sin(2 * np.pi * 28 * t) > 0.3) * (np.sin(2 * np.pi * 1.3 * t) > 0.2))
    return filt(chirp, 'band', [3500, 5200]) * 0.05 * g

def tick(g=1.0):
    n = int(0.06 * SR); t = np.arange(n) / SR
    return filt(rng.normal(0, 1, n), 'band', [1800, 5000]) * np.exp(-t * 120) * g

def creak(dur, g=1.0):
    """Door hinge creak: a slowly gliding, rough friction tone."""
    n = int(dur * SR); t = np.arange(n) / SR
    f = 260 + 140 * np.sin(np.pi * t / dur) + 40 * np.sin(2 * np.pi * 3.1 * t)
    stick = (np.sin(2 * np.pi * np.cumsum(28 + 18 * np.sin(2 * np.pi * 0.7 * t)) / SR) > 0.2).astype(float)
    x = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) * (0.4 + 0.6 * stick)
    x = filt(x, 'band', [300, 2400]) + filt(rng.normal(0, 1, n), 'band', [800, 3000]) * 0.15 * stick
    return x * env(n, 0.15, 0.3) * g

def footstep(g=1.0):
    n = int(0.5 * SR); t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 25)
    board = filt(rng.normal(0, 1, n), 'band', [250, 900]) * np.exp(-t * 12) * 0.4
    return (thud + board) * g

def clap(g=1.0):
    n = int(0.35 * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for k, off in enumerate((0, 0.006, 0.011)):   # a clap is a few tiny bursts
        i = int(off * SR)
        burst = filt(rng.normal(0, 1, n - i), 'band', [700, 2600]) * np.exp(-t[:n - i] * (60 if k < 2 else 18))
        x[i:] += burst
    return x * g

def boom(g=1.0, dur=3.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 28 + 55 * np.exp(-t * 4)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.3) + filt(rng.normal(0, 1, n), 'low', 250) * np.exp(-t * 10) * 0.6) * g

def whoosh(dur=1.0, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    x = filt(rng.normal(0, 1, n), 'band', [200, 2500]) * np.sin(np.pi * t / dur) ** 2
    return x * 0.5 * g

def heartbeat(g=1.0):
    n = int(0.6 * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 48 * t) * np.exp(-t * 18)
    i = int(0.2 * SR); x[i:] += 0.7 * np.sin(2 * np.pi * 44 * t[:n - i]) * np.exp(-t[:n - i] * 18)
    return filt(x, 'low', 200) * g

def screech(dur=1.2, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 1800 + 900 * t / dur
    x = sum(signal.sawtooth(2 * np.pi * np.cumsum(f * r) / SR) for r in (1.0, 1.06, 1.13)) / 3
    return filt(x, 'band', [1200, 6000]) * (t / dur) ** 2 * g * 0.4

def reverb(x, secs=2.5, mix=0.3, seed=1):
    r = np.random.default_rng(seed)
    n = int(secs * SR); t = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = r.normal(0, 1, n) * np.exp(-t * 6.9 / secs)
        ir = filt(ir, 'low', 5000); ir /= np.sqrt((ir ** 2).sum())
        out[:, ch] = signal.fftconvolve(x[:, ch], ir)[:len(x)]
    return x * (1 - mix) + out * mix

def build(timing_path, outdir):
    t = layout(timing_path)
    cut = {name: (st, en) for st, en, name in shots(t)}
    mus = np.zeros((N, 2)); sfx = np.zeros((N, 2))
    T_end = cut['black'][0]
    # --- underscore: a low D drone that never quite resolves
    place(mus, drone(nm('D2'), cut['warrens_enter'][0] + 0.5, att=1.5, rel=1.0), 0.0, 0.5)
    place(mus, cluster([nm('A5'), nm('Bb5')], cut['hallway'][0], att=2.5, rel=0.4), 0.0, 0.12, 0.3)
    # silhouette in the window: a muffled hit
    s0 = cut['farm_ext'][0] + 0.7
    place(sfx, boom(0.45, 2.5), s0, 1.0)
    place(sfx, whoosh(0.8, 0.5), s0 - 0.5, 1.0)
    place(sfx, wind(cut['hallway'][0] + 0.5, 0.6), 0.0, 1.0)
    place(sfx, crickets(cut['hallway'][0], 1.0), 0.0, 1.0, -0.4)
    # hallway: a clock, the door, the shadow
    th = cut['hallway'][0]
    for k in range(int((cut['bedroom'][0] - th) / 1.0)):
        place(sfx, tick(0.35 if k % 2 else 0.25), th + 0.2 + k * 1.0, 1.0, 0.5)
    td0, td1 = cut['door_opens']
    place(sfx, creak((td1 - td0) * 0.65, 0.5), td0 + (td1 - td0) * 0.2, 1.0, 0.4)
    place(mus, cluster([nm('E5'), nm('F5'), nm('Bb5')], td1 - td0 + 0.4, att=1.0, rel=0.3), td0, 0.14)
    ts0, ts1 = cut['shadow_wall']
    place(sfx, whoosh(1.4, 0.8), ts0 + 0.6, 1.0, -0.3)
    for k in range(3):
        place(sfx, footstep(0.5), ts0 + 0.5 + k * 0.62, 1.0, 0.2 - k * 0.2)
    place(mus, drone(nm('G#2'), ts1 - ts0, att=0.6, rel=0.4), ts0, 0.35)   # tritone against the D
    # bedroom: near silence, then the claps, then the corner
    tb = cut['bedroom'][0]
    place(sfx, wind(cut['corner'][1] - tb, 0.25), tb, 1.0, -0.5)
    tw0, tw1 = cut['wardrobe']
    place(sfx, clap(0.9), tw0 + 1.0, 1.0, 0.1)
    place(sfx, clap(0.9), tw0 + 1.38, 1.0, 0.1)
    place(mus, cluster([nm('C#6'), nm('D6'), nm('G6')], tw1 - tw0 + 0.3, att=0.6, rel=0.3), tw0 + 1.4, 0.13)
    tc0, tc1 = cut['corner']
    place(mus, drone(nm('D2'), tc1 - tc0 + 0.3, att=1.0, rel=0.3), tc0, 0.45)
    place(sfx, filt(rng.normal(0, 1, int((tc1 - tc0) * SR)), 'band', [2500, 6000]) * 0.05, tc0, 1.0)   # breathy whisper air
    # the Warrens: warmth and humanity — strings and sparse piano in D minor
    ta = cut['warrens_enter'][0]
    prog = [(['D3', 'F3', 'A3'], 2.8), (['Bb2', 'D3', 'F3'], 2.8), (['G2', 'Bb2', 'D3'], 2.9)]
    tt = ta
    for chord, d in prog:
        place(mus, strings([nm(c) for c in chord], d + 0.6, att=0.8, rel=1.0), tt, 0.5, -0.2)
        tt += d
    for k, (n_, dt) in enumerate((('A4', 0.2), ('F4', 1.1), ('D5', 2.6), ('C5', 3.7), ('Bb4', 5.2), ('A4', 6.4), ('D4', 7.6))):
        place(mus, piano(nm(n_)), ta + dt, 0.35, 0.2)
    # turning back toward the dark
    tb2 = cut['warrens_back'][0]
    place(mus, drone(nm('D2'), T_end - tb2, att=1.0, rel=0.05), tb2, 0.55)
    for k in range(4):
        place(sfx, heartbeat(0.6), tb2 + 0.3 + k * 0.8, 1.0)
    # final approach: rising cluster, accelerating heartbeat, then the hard cut
    te0 = cut['hall_end'][0]
    span = T_end - te0
    place(mus, cluster([nm('D5'), nm('Eb5'), nm('A5'), nm('Bb5')], span, att=span * 0.9, rel=0.02), te0, 0.3)
    place(sfx, screech(1.6, 0.6), T_end - 1.6, 1.0)
    tk = te0 + 0.2
    gap = 0.85
    while tk < T_end - 0.15:
        place(sfx, heartbeat(0.75), tk, 1.0)
        tk += gap
        gap = max(0.32, gap * 0.9)
    place(sfx, boom(1.0, 3.0), T_end, 1.0)
    # room tone throughout (very low), cut on the black
    room = filt(rng.normal(0, 1, N), 'low', 300) * 0.01
    sfx[:, 0] += room; sfx[:, 1] += np.roll(room, 317)
    mus = reverb(mus, 3.0, 0.35, 1)
    sfx = reverb(sfx, 1.8, 0.22, 2)
    e = int(T_end * SR)
    mus[e:] = 0.0                                   # the score stops dead on the cut to black
    sfx[e + int(1.6 * SR):] *= 0
    mus /= np.abs(mus).max() + 1e-9; sfx /= np.abs(sfx).max() + 1e-9
    sf.write(f'{outdir}/music.wav', (mus * 0.9).astype(np.float32), SR)
    sf.write(f'{outdir}/sfx.wav', (sfx * 0.9).astype(np.float32), SR)

if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
