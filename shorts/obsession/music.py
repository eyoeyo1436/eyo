"""Original horror score + sound design (all synthesised; no existing music is used).

A music-box lullaby (the "love" theme) that detunes and decays as the obsession grows, over
low drones, dissonant string clusters, heartbeats and stingers.
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
NOTE.update({'C#': 1, 'D#': 3, 'F#': 6, 'G#': 8, 'A#': 10})
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

def music_box(m, dur=2.5, detune=0.0):
    """Bell-like music-box tine: inharmonic partials with fast decay. detune bends it sour."""
    n = int(dur * SR); t = np.arange(n) / SR
    f = midi(m) * (1 + detune * 0.03 * np.sin(2 * np.pi * 0.7 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) * np.exp(-t * 3.0) + 0.45 * np.sin(2.76 * ph) * np.exp(-t * 7) +
         0.25 * np.sin(5.4 * ph) * np.exp(-t * 12) + 0.15 * np.sin(8.9 * ph) * np.exp(-t * 20))
    click = rng.normal(0, 1, 300) * np.exp(-np.arange(300) / 40) * 0.3
    x[:300] += click
    return x * 0.6

def lullaby(buf, t0, notes, step, gain=0.3, detune=0.0, slow=0.0):
    t = t0
    for k, (m, ln) in enumerate(notes):
        if m:
            place(buf, music_box(nm(m), 2.5, detune), t, gain, 0.15)
        t += ln * step * (1 + slow * k / max(1, len(notes)))
    return t

def cluster(ms, dur, gain=1.0, att=1.0, rel=1.0):
    return strings(ms, dur, att, rel, bright=7, vib=6.5) * gain

def stinger(gain=1.0):
    """Horror hit: sub drop + metallic scrape + noise burst."""
    n = int(2.5 * SR); t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-t * 3) + 28) / SR) * np.exp(-t * 2.2)
    scrape = bp(rng.normal(0, 1, n), 1800, 5200) * np.exp(-t * 5) * 0.5
    ring = (np.sin(2 * np.pi * 1131 * t) + np.sin(2 * np.pi * 1597 * t)) * np.exp(-t * 4) * 0.08
    return (sub * 1.1 + scrape + ring) * gain

def riser(dur=1.5, gain=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    x = bp(rng.normal(0, 1, n), 600, 6000) * (t / dur) ** 3
    tone = np.sin(2 * np.pi * np.cumsum(200 + 1600 * (t / dur) ** 2) / SR) * (t / dur) ** 4 * 0.2
    return (x * 0.35 + tone) * gain

def heartbeat(gain=1.0):
    n = int(0.6 * SR); t = np.arange(n) / SR
    beat = lambda d: np.sin(2 * np.pi * 48 * t) * np.exp(-t * 18) * (t >= 0)
    x = beat(0)
    i = int(0.22 * SR); x[i:] += 0.7 * np.sin(2 * np.pi * 44 * t[:n - i]) * np.exp(-t[:n - i] * 18)
    return lp(x, 200) * gain

def snap_sfx():
    n = int(0.5 * SR); t = np.arange(n) / SR
    crack = hp(rng.normal(0, 1, n), 1500) * np.exp(-t * 60)
    body = bp(rng.normal(0, 1, n), 200, 1200) * np.exp(-t * 25) * 0.8
    chime = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((2093, 3), (2637, 4), (3136, 5), (4186, 6))) * 0.08
    shimmer = np.zeros(n); shimmer[:] = chime
    return crack + body, np.concatenate([shimmer, np.zeros(int(1.5 * SR))])

def build(timing_path, outdir):
    t = layout(timing_path)
    cut = {name: (st, en) for st, en, name, _ in shots(t)}
    mus = np.zeros((N, 2)); sfx = np.zeros((N, 2))
    from timeline import word_time
    step = 0.42
    theme = [('E5', 1), ('G5', 1), ('B5', 2), ('A5', 1), ('G5', 1), ('F#5', 2), ('E5', 1), ('D5', 1), ('E5', 2), ('B4', 2)]

    # HOOK: the lullaby plays sweetly, then sours as Nikki becomes a silhouette
    place(mus, cello(nm('E2'), 7.2, att=2.0, rel=1.0), 0.0, 0.45)
    lullaby(mus, 0.25, theme[:6], step, 0.32)
    hb = cut['hook_b'][0]
    lullaby(mus, hb + 0.1, theme[6:], step, 0.3, detune=1.0, slow=0.5)
    place(mus, cluster([nm('E4'), nm('F4'), nm('Bb4')], cut['watch'][0] - hb + 0.4, 0.22, att=2.0, rel=0.6), hb, 1.0, -0.2)
    place(sfx, riser(1.6), hb + 1.6, 0.5)
    place(sfx, stinger(0.7), cut['watch'][0] - 0.02, 0.45)

    # STORY: pulse under the narration, the wish, the price
    t1, t2 = cut['watch'][0], cut['perf_charming'][0]
    place(mus, cello(nm('E2'), t2 - t1, att=0.5, rel=0.8), t1, 0.5)
    for k in range(int((t2 - t1) / 0.9)):
        place(mus, timpani(41, 0.25), t1 + k * 0.9, 1.0)
    lullaby(mus, t1 + 0.2, theme[:4], step * 1.2, 0.22)
    snap_t = word_time(t, 3, 'wish') + 0.05
    crack, shim = snap_sfx()
    place(sfx, crack, snap_t, 0.9); place(sfx, shim, snap_t, 0.6, 0.2)
    place(sfx, riser(0.9, 0.6), snap_t - 0.9, 1.0)
    place(sfx, boom(2.5, gain=0.6), snap_t, 0.5)
    lullaby(mus, cut['nikki_sweet'][0] + 0.1, theme[:6], step, 0.28)
    tp = cut['price'][0]
    place(mus, cluster([nm('E3'), nm('F3'), nm('B3'), nm('C4')], 2.6, 0.32, att=0.3, rel=0.6), tp, 1.0)
    place(sfx, stinger(0.75), tp - 0.02, 1.0)

    # PERFORMANCE: sweet theme once more, then it falls apart
    t3 = cut['perf_charming'][0]
    lullaby(mus, t3 + 0.1, theme, step * 0.9, 0.26, detune=0.3)
    place(mus, strings([nm('E4'), nm('G4'), nm('B4')], 3.0, att=0.8, rel=1.0, bright=4), t3, 0.12)
    tt = cut['perf_tilt'][0]
    place(mus, cluster([nm('D#4'), nm('E4'), nm('F4'), nm('A#4')], cut['perf_lunge'][0] - tt, 0.24, att=2.5, rel=0.2), tt, 1.0, 0.2)
    place(mus, cello(nm('E1') + 12, cut['perf_lunge'][0] - tt, att=1.0, rel=0.2), tt, 0.5)
    lullaby(mus, tt + 0.3, theme[:5], step * 1.5, 0.22, detune=2.5, slow=1.0)
    for k in range(6):
        place(sfx, heartbeat(0.9), cut['perf_eyes'][0] + 0.1 + k * 0.72, 1.0)
    tl = cut['perf_lunge'][0]
    place(sfx, riser(1.2, 0.7), tl - 1.2, 1.0)
    place(sfx, stinger(1.0), tl - 0.02, 1.0)
    place(sfx, whoosh(0.5, 2.0), tl - 0.35, 1.0)

    # WHY IT WORKS: bedroom dread, the doorway reveal, the red panel
    t4 = cut['bedroom_wide'][0]
    place(mus, cello(nm('E2'), cut['final_alone'][0] - t4, att=1.0, rel=0.8), t4, 0.5)
    place(mus, strings([nm('B5'), nm('C6')], cut['doorway'][0] - t4, att=2.5, rel=0.5, bright=3), t4, 0.07, 0.4)
    for k in range(int((cut['doorway'][0] - cut['bear_terror'][0]) / 0.62)):
        place(sfx, heartbeat(0.8), cut['bear_terror'][0] + k * 0.62, 1.0)
    td = cut['doorway'][0]
    place(sfx, stinger(0.8), td + 0.6, 1.0)
    place(mus, cluster([nm('C4'), nm('C#4'), nm('G4'), nm('G#4')], 2.6, 0.3, att=0.2, rel=0.5), td + 0.6, 1.0)
    tr = cut['red_grin'][0]
    place(sfx, boom(2.0, gain=0.8), tr - 0.02, 0.45)
    place(mus, cluster([nm('E3'), nm('F3'), nm('Bb3')], 2.5, 0.3, att=0.1, rel=0.5), tr, 1.0)
    th = cut['dark_humor'][0]
    lullaby(mus, th + 0.1, [('E5', 1), ('E5', 1), ('G5', 1), ('E5', 1), ('B5', 2)], step * 0.75, 0.3, detune=1.2)  # wrong-footed, too-cheerful

    # FINAL MESSAGE: emptiness, the shadow, the last sour note of the lullaby
    tf = cut['final_alone'][0]
    place(mus, cello(nm('E1') + 12, DURATION - tf, att=1.5, rel=2.0), tf, 0.55)
    place(mus, strings([nm('E3'), nm('B3'), nm('G4')], DURATION - tf, att=3.0, rel=2.0, bright=5), tf, 0.16)
    place(sfx, riser(1.8, 0.6), cut['final_shadow'][0] - 0.3, 1.0)
    place(mus, cluster([nm('E4'), nm('F4')], cut['final_wide'][0] - cut['final_shadow'][0], 0.18, att=1.5, rel=0.5), cut['final_shadow'][0], 1.0, -0.3)
    lullaby(mus, cut['final_close'][0] + 0.2, theme[:4], step * 1.6, 0.2, detune=3.0, slow=1.5)
    for k in range(4):
        place(sfx, heartbeat(0.7 - k * 0.12), cut['final_wide'][0] + k * 0.95, 1.0)
    te = cut['end'][0]
    place(sfx, stinger(0.9), te - 0.02, 1.0)
    place(mus, music_box(nm('E5'), 3.0, detune=4.0), te + 0.6, 0.3)

    # whooshes into most cuts; room tone + creaks
    for name in ('bear_longing', 'nikki_sweet', 'getting', 'perf_tilt', 'perf_eyes', 'perf_hall', 'bedroom_wide',
                 'bear_terror', 'dark_humor', 'final_alone', 'final_close', 'final_wide'):
        place(sfx, whoosh(0.7, 0.8), cut[name][0] - 0.7, 1.0)
    for tc in (cut['perf_hall'][0] + 0.4, cut['bedroom_wide'][0] + 0.8, cut['final_alone'][0] + 1.0):
        n = int(0.9 * SR); tt_ = np.arange(n) / SR  # floorboard creak
        creak = bp(rng.normal(0, 1, n), 300, 900) * (0.5 + 0.5 * np.sin(2 * np.pi * 23 * tt_)) * np.sin(np.pi * tt_ / 0.9)
        place(sfx, creak, tc, 0.35, 0.4)
    room = lp(rng.normal(0, 1, N), 250) * 0.015
    hiss = hp(rng.normal(0, 1, N), 4000) * 0.002
    sfx[:, 0] += room + hiss; sfx[:, 1] += np.roll(room + hiss, 433)

    mus = reverb(mus, 3.2, 0.38, 1)
    sfx_rev = reverb(sfx, 1.8, 0.2, 2)
    fade = np.ones(N); fs = int((DURATION - 1.2) * SR); fade[fs:] = np.linspace(1, 0, N - fs) ** 1.5
    mus *= fade[:, None]; sfx_rev *= fade[:, None]
    mus /= np.abs(mus).max() + 1e-9; sfx_rev /= np.abs(sfx_rev).max() + 1e-9
    sf.write(f'{outdir}/music.wav', (mus * 0.9).astype(np.float32), SR)
    sf.write(f'{outdir}/sfx.wav', (sfx_rev * 0.9).astype(np.float32), SR)

if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
