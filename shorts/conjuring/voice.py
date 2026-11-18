"""Voice every sentence with Kokoro (local neural TTS) and write vo/<i>.wav + vo/timing.json.

Usage: python3 voice.py MODEL_DIR OUT_DIR
Word timings are estimated from phoneme counts, anchored to the pauses found in the audio.
"""
import sys, json, re, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
from script import SECTIONS, SPOKEN

MODEL_DIR, OUT = sys.argv[1], sys.argv[2]
SPEED = float(sys.argv[3]) if len(sys.argv) > 3 else 0.9
k = Kokoro(f"{MODEL_DIR}/kokoro-v1.0.onnx", f"{MODEL_DIR}/voices-v1.0.bin")
voice = 0.62 * k.get_voice_style("am_michael") + 0.38 * k.get_voice_style("am_onyx")

def phon_len(word):
    word = SPOKEN.get(re.sub(r"[^\w']", "", word), word)
    p = k.tokenizer.phonemize(re.sub(r"[^\w'-]", "", word) or word, "en-us")
    return max(1, len(p.replace(" ", "")))

def speech_regions(a, sr, min_gap=0.12):
    """Return [(start,end)] of voiced regions separated by silences >= min_gap."""
    hop = int(0.01 * sr)
    e = np.array([np.sqrt((a[i:i+hop]**2).mean()) for i in range(0, len(a)-hop, hop)])
    thr = max(0.012, 0.06 * e.max())
    on = e > thr
    regs, i, n = [], 0, len(on)
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]: j += 1
            regs.append([i, j]); i = j
        else: i += 1
    merged = []
    for r in regs:
        if merged and (r[0] - merged[-1][1]) * 0.01 < min_gap: merged[-1][1] = r[1]
        else: merged.append(r)
    return [(s*0.01, e*0.01) for s, e in merged]

out, idx = [], 0
for si, (s0, s1, sents) in enumerate(SECTIONS):
    for sent in sents:
        spoken_words = [SPOKEN.get(re.sub(r"[^\w']", "", w), None) for w in sent.split()]
        spoken = " ".join((s + re.sub(r"[\w']", "", w) if s else w) for w, s in zip(sent.split(), spoken_words))
        a, sr = k.create(spoken, voice=voice, speed=SPEED, lang="en-us")
        a = a.astype(np.float32)
        sf.write(f"{OUT}/{idx:02d}.wav", a, sr)
        words = sent.split()
        regs = speech_regions(a, sr, min_gap=0.07)
        sp0, sp1 = regs[0][0], regs[-1][1]
        gaps = [((regs[j][1] + regs[j+1][0]) / 2, regs[j][1], regs[j+1][0]) for j in range(len(regs)-1)]
        # predicted position of every word boundary from phoneme counts (+ pause weight at punctuation)
        L = []
        for w in words:
            L.append(phon_len(w))
            L.append(4.0 if re.search(r"[,;]$", w) else 0.0)  # pause pseudo-length
        L = np.array(L); c = np.concatenate([[0], np.cumsum(L)]) / L.sum()
        T = sp0 + c * (sp1 - sp0)
        # word i spans T[2i]..T[2i+1]; punctuation pause spans T[2i+1]..T[2i+2]
        anchors = []  # (word_index_after_pause, gap_start, gap_end)
        for wi, w in enumerate(words[:-1]):
            if re.search(r"[,;.]$", w) and gaps:
                pred = (T[2*wi+1] + T[2*wi+2]) / 2
                g = min(gaps, key=lambda g: abs(g[0] - pred))
                if abs(g[0] - pred) < 0.45: anchors.append((wi, g[1], g[2]))
        # piecewise: segment boundaries at anchors, distribute words inside each segment by phonemes
        segs, prev_w, prev_t = [], 0, sp0
        for wi, ga, gb in anchors:
            segs.append((prev_w, wi + 1, prev_t, ga)); prev_w, prev_t = wi + 1, gb
        segs.append((prev_w, len(words), prev_t, sp1))
        wt = []
        for a_w, b_w, ta, tb in segs:
            ln = np.array([phon_len(w) for w in words[a_w:b_w]], float)
            cc = np.concatenate([[0], np.cumsum(ln)]) / ln.sum()
            for k2, w in enumerate(words[a_w:b_w]):
                wt.append({"w": w, "t0": round(ta + cc[k2]*(tb-ta), 3), "t1": round(ta + cc[k2+1]*(tb-ta), 3)})
        groups = anchors
        out.append({"i": idx, "section": si, "text": sent, "dur": round(len(a)/sr, 3),
                    "regions": [[round(x,3) for x in r] for r in regs], "anchors": len(anchors), "words": wt})
        print(f"{idx:02d} sec{si} {len(a)/sr:5.2f}s regions={len(regs)} anchors={len(anchors)}  {sent[:50]}")
        idx += 1
json.dump(out, open(f"{OUT}/timing.json", "w"), indent=1)
