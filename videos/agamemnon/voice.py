"""English male narration (Kokoro TTS), clause by clause for exact subtitle timing.

usage: python3 voice.py MODEL_DIR  -> narration.wav + timing.json
"""
import json, re, sys
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

SCRIPT = [
    "Before Odysseus could find his way home, one king had to fall. This is Agamemnon.",
    "King of Mycenae, the richest city in Greece, and brother of Menelaus.",
    "When Paris of Troy took Helen, Menelaus's wife, Agamemnon gathered more than a thousand ships, and led the kings of Greece to war.",
    "But at Aulis, the winds died. To bring them back, he sacrificed his own daughter, Iphigenia.",
    "For ten years he besieged Troy. His pride almost lost the war, when he took Achilles' prize, and the greatest warrior refused to fight.",
    "At last, Troy fell, and Agamemnon sailed home a conqueror.",
    "But his wife, Clytemnestra, had never forgiven him. With her lover Aegisthus, she killed him on the day he came home.",
    "In The Odyssey, his ghost warns Odysseus: when you reach home, trust no one.",
    "In Christopher Nolan's film, Benny Safdie plays him: the king whose homecoming is the dark mirror of Odysseus's own.",
]
SPEED, SR = float(sys.argv[2]) if len(sys.argv) > 2 else 1.1, 24000
k = Kokoro(f"{sys.argv[1]}/kokoro-v1.0.onnx", f"{sys.argv[1]}/voices-v1.0.bin")


def trim(a, thr=0.01):
    i = np.where(np.abs(a) > thr)[0]
    return a[max(i[0] - 240, 0): i[-1] + 960] if len(i) else a


audio, timing, t = np.zeros(80 * SR, np.float32), [], 0.4
for li, line in enumerate(SCRIPT):
    for c in [x.strip() for x in re.split(r"(?<=[,.:?])\s+", line) if x.strip()]:
        a, _ = k.create(c, voice="am_michael", speed=SPEED, lang="en-us")
        a = trim(a.astype(np.float32))
        s = int(t * SR)
        audio[s:s + len(a)] += a
        timing.append({"line": li, "text": c, "start": round(t, 3), "end": round(t + len(a) / SR, 3)})
        t += len(a) / SR + (0.38 if c.endswith((".", ":")) else 0.12)
    t += 0.15
print("ends at", round(timing[-1]["end"], 2))
audio = audio[: int(60 * SR)]
audio *= 0.95 / np.abs(audio).max()
sf.write("narration.wav", audio, SR)
json.dump(timing, open("timing.json", "w"), indent=1)
