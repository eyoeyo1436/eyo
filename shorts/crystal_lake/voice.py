"""Generate the English narration with Kokoro TTS (local, open-weight model).

usage: python3 voice.py MODEL_DIR   -> narration.wav + lines.json
MODEL_DIR holds kokoro-v1.0.onnx and voices-v1.0.bin from the kokoro-onnx releases.
"""
import json, sys
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

LINES = [
    "Before Jason, there was his mother.",
    "Crystal Lake is Peacock's new Friday the 13th prequel series.",
    "Pam Voorhees is a single mother who can't let go, after her young son Jason drowned in the town lake.",
    "As her grief turns into obsession, she slowly unravels into the killer horror fans know.",
    "Then two strangers show up at her door, digging into her past, and bodies start turning up around the lake.",
    "And Pam may not be the only danger out there.",
    "All eight episodes are streaming now, on Peacock.",
]
GAP = 0.16
d = sys.argv[1]
k = Kokoro(f"{d}/kokoro-v1.0.onnx", f"{d}/voices-v1.0.bin")
sr, parts, meta, t = 24000, [np.zeros(int(0.35 * 24000), np.float32)], [], 0.35
for line in LINES:
    a, sr = k.create(line, voice="am_michael", speed=1.2, lang="en-us")
    a = a.astype(np.float32)
    meta.append({"text": line, "start": round(t, 3), "end": round(t + len(a) / sr, 3)})
    t += len(a) / sr + GAP
    parts += [a, np.zeros(int(GAP * sr), np.float32)]
audio = np.concatenate(parts)
audio *= 0.95 / np.abs(audio).max()
sf.write("narration.wav", audio, sr)
json.dump(meta, open("lines.json", "w"), indent=1)
print(f"{len(audio)/sr:.2f}s", *[(m['start'], m['end']) for m in meta], sep="\n")
