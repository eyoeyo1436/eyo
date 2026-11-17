"""Places the narration on the 60 s timeline and cuts a new shot every 2-4 s on spoken words."""
import json

DURATION = 60.0
FPS = 30

def layout(timing_path):
    t = json.load(open(timing_path))
    cur, prev = 0.3, 0
    for i, line in enumerate(t):
        if i:
            cur += 0.4 if line['section'] != prev else 0.22
        line['start'] = round(cur, 3)
        for w in line['words']:
            w['T0'] = round(cur + w['t0'], 3); w['T1'] = round(cur + w['t1'], 3)
        cur += line['dur']; prev = line['section']
    return t

def word_time(t, i, prefix, nth=0):
    hits = [w['T0'] for w in t[i]['words'] if w['w'].lower().strip(",.?!:;").startswith(prefix.lower())]
    return hits[nth]

def shots(t):
    """(start, end, name, camera=(zoom0, zoom1, x0, x1, y0, y1))"""
    S = lambda i: t[i]['start']
    cuts = [
        (0.0, 'hook_a', (1.14, 1.02, 0.0, 0.0, 0.02, 0.0)),
        (S(1) - 0.12, 'hook_b', (1.0, 1.12, 0.0, -0.02, 0.0, -0.02)),
        (S(2) - 0.15, 'watch', (1.04, 1.14, 0.03, -0.02, 0.0, 0.0)),
        (word_time(t, 2, 'young') - 0.1, 'bear_longing', (1.0, 1.12, 0.0, 0.0, 0.0, -0.02)),
        (S(3) - 0.12, 'wish', (1.0, 1.18, 0.0, 0.0, 0.0, 0.0)),
        (word_time(t, 3, 'love') - 0.1, 'nikki_sweet', (1.12, 1.02, 0.0, 0.0, -0.02, 0.0)),
        (S(4) - 0.12, 'getting', (1.0, 1.1, -0.02, 0.02, 0.0, 0.0)),
        (word_time(t, 4, 'comes') - 0.08, 'price', (1.0, 1.2, 0.0, 0.0, 0.0, -0.03)),
        (S(5) - 0.12, 'perf_charming', (1.0, 1.1, 0.02, -0.02, 0.0, 0.0)),
        (word_time(t, 5, 'transforming') - 0.08, 'perf_tilt', (1.06, 1.16, 0.0, 0.0, 0.0, -0.02)),
        (word_time(t, 5, 'into') - 0.08, 'perf_eyes', (1.0, 1.14, 0.0, 0.0, 0.0, 0.0)),
        (S(6) - 0.12, 'perf_hall', (1.18, 1.0, 0.0, 0.0, -0.03, 0.0)),
        (word_time(t, 6, 'sudden') - 0.08, 'perf_lunge', (0.84, 1.1, 0.0, 0.0, 0.0, -0.02)),
        (S(7) - 0.15, 'bedroom_wide', (1.0, 1.1, 0.0, 0.02, 0.0, 0.0)),
        (S(8) - 0.12, 'bear_terror', (1.0, 1.16, 0.0, 0.0, 0.0, -0.02)),
        (word_time(t, 8, 'and') - 0.08, 'doorway', (1.0, 1.08, 0.0, -0.03, 0.0, 0.0)),
        (S(9) - 0.12, 'red_grin', (1.12, 1.0, 0.0, 0.0, 0.0, 0.0)),
        (word_time(t, 9, 'with') - 0.08, 'dark_humor', (1.0, 1.1, 0.0, 0.0, 0.0, -0.02)),
        (S(10) - 0.15, 'final_alone', (1.0, 1.08, 0.0, 0.0, 0.0, 0.0)),
        (S(11) - 0.12, 'final_shadow', (1.0, 1.1, 0.0, 0.0, 0.0, 0.0)),
        (word_time(t, 11, 'what') - 0.08, 'final_close', (1.0, 1.12, 0.0, 0.02, 0.0, -0.02)),
        (S(12) - 0.15, 'final_wide', (1.1, 1.0, 0.0, 0.0, 0.0, 0.0)),
        (t[12]['start'] + t[12]['dur'] + 0.2, 'end', None),
    ]
    return [(max(0.0, st), cuts[i + 1][0] if i + 1 < len(cuts) else DURATION, nm, cam) for i, (st, nm, cam) in enumerate(cuts)]

if __name__ == '__main__':
    import sys
    t = layout(sys.argv[1])
    for st, en, nm, _ in shots(t):
        print(f"{st:6.2f}-{en:6.2f} ({en - st:4.2f}s) {nm}")
