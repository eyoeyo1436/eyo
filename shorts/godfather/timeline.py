"""Places every narration line on the 60 s timeline and cuts the shots to the spoken words."""
import json
from script import SECTIONS

DURATION = 60.0
FPS = 30

def layout(timing_path):
    t = json.load(open(timing_path))
    starts, cur, prev_sec = [], 0.35, 0
    for i, line in enumerate(t):
        if i > 0:
            if line['section'] != prev_sec:
                cur += 0.8 if prev_sec == 0 else 0.45
            else:
                cur += 0.28
        line['start'] = round(cur, 3)
        for w in line['words']:
            w['T0'] = round(cur + w['t0'], 3); w['T1'] = round(cur + w['t1'], 3)
        starts.append(cur)
        cur += line['dur']
        prev_sec = line['section']
    return t

def word_time(t, line_i, word_prefix):
    for w in t[line_i]['words']:
        if w['w'].lower().startswith(word_prefix.lower()):
            return w['T0']
    raise KeyError(word_prefix)

def shots(t):
    """(start, end, shot_name, camera) — camera: (zoom0, zoom1, x0, x1, y0, y1) in normalised pan units."""
    S = lambda i: t[i]['start']
    cuts = [
        (0.0, 'vito_close', (1.18, 1.04, 0.0, 0.0, -0.02, 0.0)),
        (2.75, 'michael_reveal', (1.00, 1.10, 0.03, -0.01, 0.0, -0.02)),
        (S(1) - 0.15, 'vito_office', (1.12, 1.0, -0.03, 0.02, 0.0, 0.0)),
        (S(2) - 0.12, 'family', (1.0, 1.12, 0.0, 0.0, 0.03, 0.0)),
        (S(3) - 0.12, 'michael_quiet', (1.02, 1.14, 0.02, -0.02, 0.0, -0.02)),
        (S(4) - 0.15, 'diptych', (1.0, 1.06, 0.0, 0.0, 0.0, 0.0)),
        (S(5) - 0.12, 'michael_outsider', (1.05, 1.15, -0.04, 0.02, 0.0, -0.02)),
        (S(6) - 0.12, 'michael_cold', (1.0, 1.16, 0.0, 0.0, 0.0, -0.03)),
        (S(7) - 0.15, 'office_shadows', (1.12, 1.0, 0.02, -0.02, 0.0, 0.0)),
        (word_time(t, 7, 'Gordon') - 0.1, 'restaurant', (1.0, 1.1, 0.0, 0.0, 0.0, -0.02)),
        (word_time(t, 7, 'Nino') - 0.25, 'restaurant_close', (1.0, 1.18, 0.0, 0.02, 0.0, -0.03)),
        (S(8) - 0.2, 'silence', (1.0, 1.08, 0.0, 0.0, 0.0, 0.0)),
        (S(9) - 0.15, 'oranges', (1.15, 1.02, 0.0, 0.03, 0.0, 0.0)),
        (word_time(t, 9, 'still') - 0.05, 'rose_detail', (1.0, 1.12, 0.0, -0.02, 0.0, 0.02)),
        (S(10) - 0.15, 'michael_office', (1.0, 1.12, 0.0, 0.0, 0.0, -0.02)),
        (S(11) - 0.12, 'door', (1.08, 1.0, 0.0, 0.0, 0.0, 0.0)),
        (S(12) - 0.25, 'end', None),
    ]
    out = []
    for i, (st, name, cam) in enumerate(cuts):
        en = cuts[i + 1][0] if i + 1 < len(cuts) else DURATION
        out.append((max(0.0, st), en, name, cam))
    return out

if __name__ == '__main__':
    import sys
    t = layout(sys.argv[1])
    for line in t:
        print(f"{line['start']:6.2f}-{line['start'] + line['dur']:6.2f}  {line['text'][:60]}")
    for s in shots(t):
        print(f"{s[0]:6.2f}-{s[1]:6.2f} {s[2]}")
