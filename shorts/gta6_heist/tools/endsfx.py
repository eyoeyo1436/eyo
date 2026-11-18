"""End-card sounds: whoosh as the avatar arrives, a soft pop for the text, mouse click on subscribe, bell ding."""
import numpy as np, soundfile as sf
from scipy import signal
SR, T = 48000, 24.0
out = np.zeros(int(SR * T)); rng = np.random.default_rng(3)
def put(x, t, g):
    i = int(t * SR); out[i:i + len(x)] += g * x[:len(out) - i]
n = int(0.55 * SR); env = np.sin(np.linspace(0, np.pi, n)) ** 2
noise = rng.standard_normal(n)
b, a = signal.butter(2, [300 / (SR / 2), 4000 / (SR / 2)], 'band'); wh = signal.lfilter(b, a, noise) * env
put(wh / np.abs(wh).max(), 19.95, 0.35)
tt = np.arange(int(0.12 * SR)) / SR
pop = np.sin(2 * np.pi * (520 - 1800 * tt) * tt) * np.exp(-tt * 35); put(pop, 20.45, 0.3)
tc = np.arange(int(0.03 * SR)) / SR
click = (rng.standard_normal(len(tc)) * np.exp(-tc * 400) + np.sin(2 * np.pi * 2200 * tc) * np.exp(-tc * 250))
put(click / np.abs(click).max(), 22.03, 0.55)
td = np.arange(int(1.4 * SR)) / SR
ding = sum(g * np.sin(2 * np.pi * f * td) * np.exp(-td * d) for f, g, d in ((1318.5, 1.0, 3.0), (2637, 0.35, 5), (3951, 0.15, 7), (1975.5, 0.3, 4)))
put(ding / np.abs(ding).max(), 22.2, 0.32)
sf.write('endsfx.wav', np.c_[out, out].astype(np.float32), SR)
