"""English documentary narration with Kokoro TTS, synthesized clause by clause so
subtitle timing is exact at every clause boundary.

usage: python3 voice.py MODEL_DIR  -> narration.wav + timing.json
"""
import json, re, sys
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

# (target start in seconds, line) - the user's script, verbatim
SCRIPT = [
    (0.15, "One of the most realistic black holes ever shown in cinema came from a movie."),
    (4.0, "In Interstellar, Christopher Nolan wanted a black hole that wasn't just visually impressive... but scientifically accurate."),
    (10.0, "Scientists actually worked with the filmmakers to calculate how light would bend around a massive spinning black hole."),
    (17.0, "The result was Gargantua. Its incredible glowing ring isn't just a visual effect. It's gravitational lensing."),
    (24.0, "Light from behind the black hole bends around it, allowing you to see parts of the accretion disk that would normally be hidden."),
    (32.0, "And here's the unbelievable part: the research behind this visual effect even contributed to scientific studies. Interstellar didn't just imagine a black hole. It helped us visualize one."),
]
SPEED = float(sys.argv[2]) if len(sys.argv) > 2 else 1.27
SR = 24000
k = Kokoro(f"{sys.argv[1]}/kokoro-v1.0.onnx", f"{sys.argv[1]}/voices-v1.0.bin")


def trim(a, thr=0.01):
    idx = np.where(np.abs(a) > thr)[0]
    return a[max(idx[0] - 240, 0): idx[-1] + 960] if len(idx) else a


lines = []
for start, text in SCRIPT:
    clauses = [c.strip() for c in re.split(r"(?<=[,.:?])\s+|(?<=\.\.\.)\s*", text) if c.strip()]
    parts = []
    for c in clauses:
        a, _ = k.create(c, voice="am_michael", speed=SPEED, lang="en-us")
        a = trim(a.astype(np.float32))
        pause = 0.22 if c.endswith((".", ":")) else 0.07
        pause = 0.26 if c.endswith("...") else pause
        parts.append((c, a, pause))
    lines.append((start, parts))

# lay lines out at their target times; if a line runs long, the next one starts right after it
audio = np.zeros(int(60 * SR), np.float32)
timing, t = [], 0.0
for start, parts in lines:
    t = max(t, 0.1)
    for c, a, pause in parts:
        s = int(t * SR)
        audio[s:s + len(a)] += a
        timing.append({"text": c, "start": round(t, 3), "end": round(t + len(a) / SR, 3)})
        t += len(a) / SR + pause
print("ends at", round(timing[-1]["end"], 2))
for m in timing:
    print(m["start"], m["end"], m["text"])
audio = audio[: int(40 * SR)]
audio *= 0.95 / np.abs(audio).max()
sf.write("narration.wav", audio, SR)
json.dump(timing, open("timing.json", "w"), indent=1)
