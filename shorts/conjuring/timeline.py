"""Narration layout and the 13-shot cut list for the Conjuring Short (40.0 s)."""
import json

DURATION = 40.0

def layout(timing_path):
    t = json.load(open(timing_path))
    cur, prev = 0.2, 0
    for i, line in enumerate(t):
        if i:
            cur += 0.35 if line['section'] != prev else 0.22
        line['start'] = round(cur, 3)
        for w in line['words']:
            w['T0'] = round(cur + w['t0'], 3); w['T1'] = round(cur + w['t1'], 3)
        cur += line['dur']; prev = line['section']
    return t

def word_time(t, i, prefix, nth=0):
    hits = [w['T0'] for w in t[i]['words'] if w['w'].lower().strip(",.?!:;").startswith(prefix.lower())]
    return hits[nth]

def shots(t):
    S = lambda i: t[i]['start']
    end_speech = t[-1]['start'] + t[-1]['dur']
    cuts = [
        (0.0, 'farm_ext'),
        (word_time(t, 0, 'scariest') - 0.1, 'window_close'),
        (S(1) - 0.1, 'hallway'),
        (word_time(t, 1, 'understands') - 0.1, 'door_opens'),
        (word_time(t, 1, 'what') - 0.15, 'shadow_wall'),
        (S(2) - 0.1, 'bedroom'),
        (word_time(t, 2, 'tension') - 0.1, 'wardrobe'),
        (word_time(t, 2, 'perfectly') - 0.1, 'corner'),
        (S(3) - 0.1, 'warrens_enter'),
        (word_time(t, 3, 'Ed') - 0.1, 'lorraine_close'),
        (word_time(t, 3, 'giving') - 0.1, 'ed_close'),
        (S(4) - 0.1, 'warrens_back'),
        (S(5) - 0.1, 'hall_end'),
        (end_speech + 0.12, 'black'),
    ]
    return [(st, cuts[i + 1][0] if i + 1 < len(cuts) else DURATION, nm) for i, (st, nm) in enumerate(cuts)]

if __name__ == '__main__':
    import sys
    t = layout(sys.argv[1])
    for line in t:
        print(f"{line['start']:6.2f}-{line['start'] + line['dur']:6.2f} {line['text'][:60]}")
    for st, en, nm in shots(t):
        print(f"{st:6.2f}-{en:6.2f} ({en - st:4.2f}s) {nm}")
