"""Original score + sound design (all synthesised; no existing music is used).

A slow C-minor waltz for mandolin tremolo, harp and strings, written for this Short.
Writes two stems: music.wav (ducked under the voice at mix time) and sfx.wav.
Usage: python3 music.py TIMING_JSON OUT_DIR
"""
import sys, json
import numpy as np
from scipy import signal
import soundfile as sf
from timeline import layout, shots, DURATION

SR = 48000
N = int(DURATION * SR)
rng = np.random.default_rng(7)

def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)

NOTE = {n: i for i, n in enumerate(['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'])}
def nm(s):
    name, octv = s[:-1], int(s[-1])
    return 12 * (octv + 1) + NOTE[name]

def place(buf, x, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= buf.shape[0] or i + len(x) <= 0:
        return
    x = x[:max(0, buf.shape[0] - i)]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(x), 0] += x * gain * l * 1.414
    buf[i:i + len(x), 1] += x * gain * r * 1.414

def lp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'low')
    return signal.lfilter(b, a, x)

def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'high')
    return signal.lfilter(b, a, x)

def bp(x, f0, f1):
    b, a = signal.butter(2, [f0 / (SR / 2), f1 / (SR / 2)], 'band')
    return signal.lfilter(b, a, x)

def env(n, a, r, sustain=1.0):
    e = np.ones(n) * sustain
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, sustain, na)
    if nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e

def pluck(f, dur, bright=0.6, decay=0.996):
    """Karplus-Strong plucked string (vectorised per period)."""
    n = int(dur * SR)
    p = max(2, int(SR / f))
    y = np.zeros(n + p)
    burst = rng.uniform(-1, 1, p)
    burst = lp(burst, 1500 + 7000 * bright, 1)
    y[:p] = burst
    k = p
    while k < n + p:
        seg = y[k - p:k]
        nxt = decay * 0.5 * (seg + np.concatenate([seg[1:], seg[-1:]]))
        m = min(p, n + p - k)
        y[k:k + m] = nxt[:m]
        k += p
    out = y[p:]
    out *= env(n, 0.002, 0.08)
    return out / (np.abs(out).max() + 1e-9)

def mandolin_tremolo(m, dur, rate=13.0, gain=1.0):
    """Doubled-course mandolin tremolo: rapid alternating picks on two slightly detuned strings."""
    out = np.zeros(int((dur + 0.6) * SR))
    t, k = 0.0, 0
    while t < dur:
        f = midi(m) * (1.0 + (0.0025 if k % 2 else -0.0025))
        pk = pluck(f, 0.45, bright=0.75, decay=0.993) * (0.75 + 0.25 * rng.random()) * (0.85 if k % 2 else 1.0)
        i = int(t * SR)
        out[i:i + len(pk)] += pk[:len(out) - i]
        t += 1.0 / rate * (1 + rng.uniform(-0.06, 0.06)); k += 1
    e = np.ones(len(out)); fade = int(0.08 * SR)
    e[:fade] = np.linspace(0.3, 1, fade)
    e[int(dur * SR):] *= np.linspace(1, 0, len(out) - int(dur * SR))
    return hp(out * e * gain, 180)

def strings(ms, dur, att=0.8, rel=1.2, bright=6, vib=5.2):
    """Ensemble pad: detuned band-limited saws with vibrato."""
    n = int((dur + rel) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for m in ms:
        f0 = midi(m)
        for det in (-0.004, 0.0, 0.0045):
            ph0 = rng.uniform(0, 2 * np.pi)
            fv = f0 * (1 + det) * (1 + 0.003 * np.sin(2 * np.pi * vib * t + ph0))
            phase = 2 * np.pi * np.cumsum(fv) / SR
            for h in range(1, bright + 1):
                if f0 * h > 9000:
                    break
                out += np.sin(h * phase + ph0 * h) / h ** 1.35
    out = lp(out, 2600)
    e = np.ones(n)
    na = int(att * SR); e[:na] = np.linspace(0, 1, na) ** 1.5
    nr = int(rel * SR); e[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    return out * e / (len(ms) * 3)

def cello(m, dur, att=1.0, rel=1.5):
    return lp(strings([m, m - 12], dur, att, rel, bright=10, vib=4.5), 900) * 1.6

def boom(dur=3.0, f0=70, f1=32, gain=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 6)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    nz = lp(rng.normal(0, 1, n), 400) * np.exp(-t * 14) * 0.6
    return (x + nz) * gain

def whoosh(dur=1.2, gain=1.0):
    n = int(dur * SR)
    x = rng.normal(0, 1, n)
    x = bp(x, 300, 3200)
    e = np.linspace(0, 1, n) ** 3
    e[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))
    return x * e * gain * 0.25

def timpani(f=55, gain=1.0):
    n = int(1.6 * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t)) * np.exp(-t * 3.2)
    x += lp(rng.normal(0, 1, n), 300) * np.exp(-t * 30) * 0.5
    return x * gain

def reverb(x, secs=2.6, mix=0.3, seed=1):
    r = np.random.default_rng(seed)
    n = int(secs * SR); t = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = r.normal(0, 1, n) * np.exp(-t * 6.9 / secs)
        ir = lp(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
        out[:, ch] = signal.fftconvolve(x[:, ch], ir)[:len(x)]
    return x * (1 - mix) + out * mix

def waltz(buf, t0, bars, chords, beat, gain=0.5):
    """Harp/guitar accompaniment: bass note on beat 1, chord on beats 2 and 3."""
    for b in range(bars):
        root, tri = chords[b % len(chords)]
        tb = t0 + b * 3 * beat
        place(buf, pluck(midi(root), 2.2, 0.4, 0.998), tb, gain * 0.9, -0.2)
        for k in (1, 2):
            for j, m in enumerate(tri):
                place(buf, pluck(midi(m), 1.4, 0.55, 0.996), tb + k * beat + j * 0.012, gain * 0.32, 0.25)

def melody(buf, t0, beat, notes, gain=0.45, pan=0.1):
    t = t0
    for m, ln in notes:
        if m is not None:
            place(buf, mandolin_tremolo(nm(m), ln * beat * 0.97), t, gain, pan)
        t += ln * beat

def build(timing_path, outdir):
    t = layout(timing_path)
    cut = {name: (st, en) for st, en, name, _ in shots(t)}
    mus = np.zeros((N, 2)); sfx = np.zeros((N, 2))
    beat = 2.5 / 3  # 72 bpm in 3/4

    # --- HOOK (0 - 5.7): low drone, distant high strings, a single mandolin note on the reveal
    place(mus, cello(nm('C2'), 5.4, att=1.5, rel=1.5), 0.0, 0.55)
    place(mus, strings([nm('G5'), nm('C6')], 5.0, att=2.5, rel=1.5, bright=4), 0.3, 0.12, 0.3)
    place(mus, mandolin_tremolo(nm('G4'), 2.3), cut['michael_reveal'][0] + 0.1, 0.32, 0.1)

    # --- PART 1 (characters): theme A
    t1 = cut['vito_office'][0]
    chordsA = [(nm('C3'), [nm('G3'), nm('C4'), nm('Eb4')]), (nm('C3'), [nm('G3'), nm('C4'), nm('Eb4')]),
               (nm('F2'), [nm('F3'), nm('Ab3'), nm('C4')]), (nm('G2'), [nm('G3'), nm('B3'), nm('D4')]),
               (nm('Ab2'), [nm('Ab3'), nm('C4'), nm('Eb4')]), (nm('G2'), [nm('G3'), nm('B3'), nm('D4')])]
    waltz(mus, t1, 6, chordsA, beat, 0.42)
    for b, (root, tri) in enumerate(chordsA):
        place(mus, strings(tri, 3 * beat, att=0.6, rel=0.9), t1 + b * 3 * beat, 0.16, -0.3)
    melody(mus, t1, beat, [('C5', 2), ('D5', 0.5), ('Eb5', 0.5), ('F5', 1), ('Eb5', 1), ('C5', 1),
                           ('Ab4', 2), ('C5', 1), ('B4', 2), ('D5', 1),
                           ('Eb5', 1), ('G5', 1), ('F5', 1), ('Eb5', 1), ('D5', 1), ('C5', 1)], 0.42)

    # --- PART 2 (transformation): theme darkens, then the mandolin falls silent
    t2 = t1 + 6 * 3 * beat
    chordsB = [(nm('F2'), [nm('F3'), nm('Ab3'), nm('C4')]), (nm('C3'), [nm('G3'), nm('C4'), nm('Eb4')]),
               (nm('Ab2'), [nm('Ab3'), nm('C4'), nm('Eb4')]), (nm('G2'), [nm('G3'), nm('B3'), nm('D4')])]
    waltz(mus, t2, 4, chordsB, beat, 0.38)
    for b, (root, tri) in enumerate(chordsB):
        place(mus, strings(tri + [root + 12], 3 * beat, att=0.7, rel=1.0), t2 + b * 3 * beat, 0.2, -0.3)
    melody(mus, t2, beat, [('C5', 1), ('Eb5', 1), ('Ab5', 1), ('G5', 2), ('Eb5', 1),
                           ('F5', 1), ('Eb5', 1), ('Db5', 1), ('C5', 3)], 0.4)
    tc = cut['michael_cold'][0]
    place(mus, cello(nm('C2'), cut['michael_cold'][1] - tc + 0.5, att=0.6), tc, 0.6)
    place(mus, strings([nm('Db4'), nm('G4'), nm('C5')], 4.2, att=1.2, rel=1.2), tc, 0.18)  # unresolved, cold
    for k in range(5):  # heartbeat timpani
        place(mus, timpani(49, 0.5), tc + 0.2 + k * 0.85, 1.0)

    # --- PART 3 (craft): suspended atmosphere, then the restaurant tension and the train
    t3, t3e = cut['office_shadows'][0], cut['silence'][0]
    place(mus, strings([nm('C3'), nm('G3'), nm('D4'), nm('Eb4')], t3e - t3 - 0.3, att=1.5, rel=0.25), t3, 0.24)
    place(mus, strings([nm('G5'), nm('D6')], t3e - t3 - 0.3, att=3.0, rel=0.25, bright=3), t3 + 1.0, 0.07, 0.4)
    place(mus, cello(nm('C2'), t3e - t3 - 0.3, att=1.0, rel=0.25), t3, 0.45)
    tr = cut['restaurant'][0]
    for k in range(int((t3e - tr) / 0.6)):  # rising pulse
        place(mus, timpani(55, 0.18 + 0.5 * k / 14), tr + k * 0.6, 1.0)
    n_tr = int((t3e - tr) * SR)
    rumble = lp(np.cumsum(rng.normal(0, 1, n_tr)), 160); rumble -= lp(rumble, 20)
    rumble /= np.abs(rumble).max() + 1e-9
    ramp = np.linspace(0, 1, n_tr) ** 2.6
    squeal = np.sin(2 * np.pi * np.cumsum(2200 + 400 * np.linspace(0, 1, n_tr)) / SR) * np.linspace(0, 1, n_tr) ** 6 * 0.12
    clack = np.zeros(n_tr)
    for k in range(int((t3e - tr) / 0.23)):
        i = int(k * 0.23 * SR) + (int(0.06 * SR) if k % 2 else 0)
        if i < n_tr - 2000:
            clack[i:i + 2000] += bp(rng.normal(0, 1, 2000), 300, 2000) * np.exp(-np.arange(2000) / 300)
    train = (rumble * 0.9 + clack * 0.25 * np.linspace(0, 1, n_tr) ** 2 + squeal) * ramp
    train[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))
    place(sfx, train, tr, 0.55)

    # --- SILENCE: everything stops (the frame is near-black, only room tone)
    # --- PART 4 (legacy): the theme returns in full
    t4 = cut['oranges'][0]
    chordsC = [(nm('C3'), [nm('G3'), nm('C4'), nm('Eb4')]), (nm('Ab2'), [nm('Ab3'), nm('C4'), nm('Eb4')]),
               (nm('F2'), [nm('F3'), nm('Ab3'), nm('C4')]), (nm('G2'), [nm('G3'), nm('B3'), nm('D4'), nm('F4')])]
    waltz(mus, t4, 4, chordsC, beat, 0.4)
    for b, (root, tri) in enumerate(chordsC):
        place(mus, strings(tri + [root + 24], 3 * beat, att=0.5, rel=1.0, bright=8), t4 + b * 3 * beat, 0.26, -0.2)
        place(mus, cello(root, 3 * beat, att=0.3, rel=0.8), t4 + b * 3 * beat, 0.35)
    melody(mus, t4, beat, [('G5', 1), ('F5', 1), ('Eb5', 1), ('C5', 2), ('Eb5', 1),
                           ('D5', 1), ('C5', 1), ('Ab4', 1), ('B4', 2.6)], 0.46)

    # --- ENDING: final C-minor chord and fade
    te = cut['end'][0]
    place(mus, strings([nm('C3'), nm('G3'), nm('C4'), nm('Eb4'), nm('G4')], DURATION - te, att=0.8, rel=2.0, bright=8), te, 0.28)
    place(mus, cello(nm('C2'), DURATION - te, att=0.6, rel=2.0), te, 0.5)
    for j, m in enumerate(['C3', 'G3', 'C4', 'Eb4', 'G4', 'C5']):
        place(mus, pluck(midi(nm(m)), 3.0, 0.5, 0.998), te + 0.4 + j * 0.13, 0.28, -0.2 + j * 0.08)
    place(mus, mandolin_tremolo(nm('C5'), 2.2), te + 1.3, 0.3, 0.1)

    # --- SOUND DESIGN: hits on the big cuts, whooshes into transitions, the door, room tone
    for name, g in (('vito_close', 0.9), ('vito_office', 0.5), ('diptych', 0.6), ('michael_cold', 0.55),
                    ('office_shadows', 0.5), ('oranges', 0.85), ('end', 0.6)):
        place(sfx, boom(2.2, gain=g), max(0, cut[name][0] - 0.02), 0.4)
    for name in ('michael_reveal', 'family', 'michael_outsider', 'restaurant', 'rose_detail', 'michael_office', 'door'):
        w = whoosh(0.9)
        place(sfx, w, cut[name][0] - 0.9, 0.5, 0.0)
    td = cut['door'][0] + 2.85  # the door shuts
    n = int(1.2 * SR); tt = np.arange(n) / SR
    thud = np.sin(2 * np.pi * 58 * tt) * np.exp(-tt * 9) + lp(rng.normal(0, 1, n), 500) * np.exp(-tt * 25) * 0.7
    place(sfx, thud, td, 0.9)
    place(sfx, hp(rng.normal(0, 1, 1200), 2500) * np.exp(-np.arange(1200) / 150), td + 0.07, 0.25, 0.3)
    # very quiet room tone + projector flutter + film crackle
    room = lp(rng.normal(0, 1, N), 350) * 0.012
    flutter = hp(rng.normal(0, 1, N), 3000) * 0.0025 * (1 + 0.5 * np.sin(2 * np.pi * 24 * np.arange(N) / SR))
    crackle = np.zeros(N)
    for i in rng.integers(0, N - 200, 260):
        crackle[i:i + 60] += rng.normal(0, 1, 60) * np.exp(-np.arange(60) / 10) * rng.uniform(0.01, 0.05)
    bed = room + flutter + crackle
    sfx[:, 0] += bed; sfx[:, 1] += np.roll(bed, 371)

    mus = reverb(mus, 2.8, 0.32, 1)
    sfx_rev = reverb(sfx, 1.6, 0.18, 2)
    # silence gap: hard dip of the score
    s0, s1 = cut['silence']
    g = np.ones(N)
    a, b = int((s0 - 0.05) * SR), int(s1 * SR)
    g[a:b] = 0.0
    g[max(0, a - int(0.25 * SR)):a] = np.linspace(1, 0, a - max(0, a - int(0.25 * SR)))
    mus *= g[:, None]
    fade = np.ones(N); fs = int((DURATION - 1.6) * SR); fade[fs:] = np.linspace(1, 0, N - fs) ** 1.5
    mus *= fade[:, None]; sfx_rev *= fade[:, None]
    mus /= np.abs(mus).max() + 1e-9; sfx_rev /= np.abs(sfx_rev).max() + 1e-9
    sf.write(f'{outdir}/music.wav', (mus * 0.9).astype(np.float32), SR)
    sf.write(f'{outdir}/sfx.wav', (sfx_rev * 0.9).astype(np.float32), SR)

if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
