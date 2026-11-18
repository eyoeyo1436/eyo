import sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
M = sys.argv[1]
k = Kokoro(f'{M}/kokoro-v1.0.onnx', f'{M}/voices-v1.0.bin')
v = 0.62 * k.get_voice_style('am_michael') + 0.38 * k.get_voice_style('am_onyx')
a, sr = k.create("GTA 6 heists have begun!", voice=v, speed=1.1, lang='en-us')
nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, nz[0]-200): nz[-1]+2400]
sf.write('hook.wav', a, sr); print(sr, len(a)/sr)
