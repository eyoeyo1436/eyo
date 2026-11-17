"""Generate the English narration with Kokoro TTS (local, open-weight model).

usage: python3 voice.py MODEL_DIR   -> narration.wav + lines.json
MODEL_DIR holds kokoro-v1.0.onnx and voices-v1.0.bin from the kokoro-onnx releases.
"""
import json, sys
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

LINES = [
    "In 2008, a comic book movie did something nobody thought it could.",
    "It crossed one billion dollars worldwide.",
    "Heath Ledger disappeared into the Joker, and won an Oscar after his death.",
    "Christopher Nolan shot key scenes on IMAX cameras, and flipped a real truck on the streets of Chicago.",
    "It didn't feel like a superhero movie. It felt like a crime epic.",
    "And when it was left out of Best Picture, the Oscars expanded the category the very next year.",
    "It didn't just tell a hero's story. It asked what a hero costs.",
    "Is it still the best one ever made?",
]
GAP = 0.32
d = sys.argv[1]
k = Kokoro(f"{d}/kokoro-v1.0.onnx", f"{d}/voices-v1.0.bin")
sr, parts, meta, t = 24000, [np.zeros(int(0.35 * 24000), np.float32)], [], 0.35
for line in LINES:
    a, sr = k.create(line, voice="am_michael", speed=1.0, lang="en-us")
    a = a.astype(np.float32)
    meta.append({"text": line, "start": round(t, 3), "end": round(t + len(a) / sr, 3)})
    t += len(a) / sr + GAP
    parts += [a, np.zeros(int(GAP * sr), np.float32)]
audio = np.concatenate(parts)
audio *= 0.95 / np.abs(audio).max()
sf.write("narration.wav", audio, sr)
json.dump(meta, open("lines.json", "w"), indent=1)
print(f"{len(audio)/sr:.2f}s", *[(m['start'], m['end']) for m in meta], sep="\n")
