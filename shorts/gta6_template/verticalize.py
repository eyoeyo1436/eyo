"""Turn a horizontal (16:9) Twitch clip into the vertical layout of our GTA 6 Shorts, ready for make_short.py.

Layout (1080x1920): the streamer's webcam on top, the game below (centre crop), and word-by-word subtitles on
the seam between them: white bold text, the word being spoken on a purple box, swear words starred.
Subtitles come from an offline speech model (sherpa-onnx Parakeet TDT, word timings).

Usage:
  python3 verticalize.py CLIP.mp4 OUT.mp4 --cam X,Y,W,H [--start S --end E] [--game-cx 960] [--cam-split 680]
                         [--asr-model DIR] [--words words.json] [--fix "wrong=right" ...]
  --cam      webcam rectangle in the source frame (pixels)
  --words    reuse a transcript json ([{w,t0,t1}], source-clip times) instead of running the speech model
  --fix      correct a misheard word in the subtitles, e.g. --fix "Medit=" (empty removes it)
"""
import argparse, json, os, re, subprocess, sys, tempfile
import numpy as np, skia

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'assets')
W, H, FPS = 1080, 1920, 60
PURPLE = skia.Color(145, 70, 255)
SWEARS = re.compile(r'^(fuck|fucking|fucked|shit|bitch|pussy|dick|cunt|nigg\w*|fag\w*|retard\w*|whore|slut)\W*$', re.I)
ASR_URL = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8.tar.bz2'

def transcribe(src, model_dir):
    import sherpa_onnx
    if not os.path.exists(os.path.join(model_dir, 'tokens.txt')):
        os.makedirs(os.path.dirname(model_dir.rstrip('/')) or '.', exist_ok=True)
        tar = model_dir.rstrip('/') + '.tar.bz2'
        subprocess.run(['curl', '-sSL', '-o', tar, ASR_URL], check=True)
        subprocess.run(['tar', 'xjf', tar, '-C', os.path.dirname(model_dir.rstrip('/')) or '.'], check=True)
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    m = model_dir
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(encoder=f'{m}/encoder.int8.onnx', decoder=f'{m}/decoder.int8.onnx',
            joiner=f'{m}/joiner.int8.onnx', tokens=f'{m}/tokens.txt', model_type='nemo_transducer', num_threads=4)
    words, CH = [], 8.0
    for s0 in np.arange(0, len(a) / 16000, CH):
        st = rec.create_stream(); st.accept_waveform(16000, a[int(s0 * 16000): int((s0 + CH) * 16000)]); rec.decode_stream(st)
        cur = None
        for tok, t in zip(st.result.tokens, st.result.timestamps):
            if tok.startswith('▁') or tok.startswith(' ') or cur is None:
                if cur:
                    words.append(cur)
                cur = {'w': tok.lstrip('▁ '), 't0': float(s0 + t)}
            else:
                cur['w'] += tok
        if cur:
            words.append(cur)
    for i, w in enumerate(words):
        nxt = words[i + 1]['t0'] if i + 1 < len(words) else w['t0'] + 0.5
        w['t1'] = min(nxt, w['t0'] + 0.6)
    return [w for w in words if w['w']]

def chunks(words):
    """2-3 word groups; break on sentence punctuation or pauses."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        txt = ' '.join(x['w'] for x in cur)
        if (nxt is None or len(cur) >= 3 or len(txt) >= 14 or re.search(r'[.?!]$', w['w'])
                or nxt['t0'] - w['t1'] > 0.45):
            out.append(cur); cur = []
    return out

def display(word):
    return re.sub(r'[A-Za-z]', '*', word) if SWEARS.match(word) else word

def montserrat(size):
    return skia.Font(skia.Typeface.MakeFromFile(os.path.join(ASSETS, 'Montserrat-ExtraBold.ttf')), size)

def render_state(path, words, active, y):
    f = montserrat(60)
    sp = f.measureText(' ')
    items = [display(w['w']) for w in words]
    total = sum(f.measureText(t) for t in items) + sp * (len(items) - 1)
    x = (W - total) / 2
    surf = skia.Surface(W, H); c = surf.getCanvas(); c.clear(skia.ColorTRANSPARENT)
    for i, t in enumerate(items):
        tw = f.measureText(t)
        if i == active:
            r = skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x - 10, y - 52, x + tw + 10, y + 16), 12, 12)
            c.drawRRect(r, skia.Paint(Color=PURPLE, AntiAlias=True))
        blob = skia.TextBlob(t, f)
        c.drawTextBlob(blob, x + 3, y + 5, skia.Paint(Color=skia.Color(0, 0, 0, 170), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6), AntiAlias=True))
        c.drawTextBlob(blob, x, y, skia.Paint(Color=skia.Color(0, 0, 0, 255), Style=skia.Paint.kStroke_Style, StrokeWidth=7,
                       StrokeJoin=skia.Paint.kRound_Join, AntiAlias=True))
        c.drawTextBlob(blob, x, y, skia.Paint(Color=skia.ColorWHITE, AntiAlias=True))
        x += tw + sp
    surf.makeImageSnapshot().save(path, skia.kPNG)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('clip'); ap.add_argument('out')
    ap.add_argument('--cam', required=True); ap.add_argument('--start', type=float, default=0.0); ap.add_argument('--end', type=float, default=None)
    ap.add_argument('--game-cx', type=int, default=960); ap.add_argument('--cam-split', type=int, default=680)
    ap.add_argument('--asr-model', default=os.path.join(HERE, 'models', 'sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8'))
    ap.add_argument('--words', default=None); ap.add_argument('--fix', action='append', default=[])
    a = ap.parse_args()
    work = tempfile.mkdtemp(prefix='vert_')
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                            '-show_entries', 'format=duration', '-of', 'json', a.clip], capture_output=True, text=True, check=True)
    pj = json.loads(probe.stdout); sw, sh = pj['streams'][0]['width'], pj['streams'][0]['height']
    end = a.end or float(pj['format']['duration'])
    sc = sw / 1920.0
    cx, cy, cw, ch = [int(int(v) * 1.0) for v in a.cam.split(',')]

    words = json.load(open(a.words)) if a.words else transcribe(a.clip, a.asr_model)
    fixes = dict(f.split('=', 1) for f in a.fix)
    sel = []
    for w in words:
        key = re.sub(r'\W', '', w['w'])
        if key in fixes:
            if not fixes[key]:
                continue
            w = dict(w, w=w['w'].replace(key, fixes[key]))
        if w['t0'] >= a.start and w['t1'] <= end + 0.3:
            sel.append(dict(w, t0=w['t0'] - a.start, t1=min(w['t1'], end) - a.start))
    json.dump(sel, open(os.path.join(work, 'words.json'), 'w'))

    # subtitle states -> concat list of stills with durations
    dur = end - a.start
    blank = os.path.join(work, 'blank.png')
    surf = skia.Surface(W, H); surf.getCanvas().clear(skia.ColorTRANSPARENT); surf.makeImageSnapshot().save(blank, skia.kPNG)
    events = []                                    # (t, png)
    seam = a.cam_split + 22
    for ci, ch_words in enumerate(chunks(sel)):
        for wi, w in enumerate(ch_words):
            p = os.path.join(work, f's_{ci:03d}_{wi}.png')
            render_state(p, ch_words, wi, seam)
            events.append((w['t0'], p))
        events.append((ch_words[-1]['t1'] + 0.25, blank))
    events.sort(key=lambda e: e[0])
    lst = ['ffconcat version 1.0']
    t_prev, p_prev = 0.0, blank
    for t, p in events:
        t = max(t, t_prev)
        if t > t_prev:
            lst += [f"file '{p_prev}'", f'duration {t - t_prev:.3f}']
        t_prev, p_prev = t, p
    lst += [f"file '{p_prev}'", f'duration {max(0.04, dur - t_prev):.3f}', f"file '{p_prev}'"]
    open(os.path.join(work, 'subs.txt'), 'w').write('\n'.join(lst) + '\n')

    gh = H - a.cam_split
    gw_src = int(round(W * sh / gh / 2)) * 2
    gx = max(0, min(sw - gw_src, int(a.game_cx * sc - gw_src / 2)))
    cam_h = int(round(cw * a.cam_split / W))
    cam_y = cy + max(0, (ch - cam_h) // 2)
    fc = (f"[0:v]trim={a.start}:{end},setpts=PTS-STARTPTS,fps={FPS},split[c][g];"
          f"[c]crop={cw}:{cam_h}:{cx}:{cam_y},scale={W}:{a.cam_split}:flags=lanczos,unsharp=5:5:0.6[cam];"
          f"[g]crop={gw_src}:{sh}:{gx}:0,scale={W}:{gh}:flags=lanczos[game];"
          f"[cam][game]vstack,setsar=1[st];"
          f"[1:v]fps={FPS},format=rgba[sub];[st][sub]overlay=eof_action=pass:format=auto[v];"
          f"[0:a]atrim={a.start}:{end},asetpts=PTS-STARTPTS,loudnorm=I=-13:TP=-1.5:LRA=11,aresample=48000[a]")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.clip, '-f', 'concat', '-safe', '0', '-i', os.path.join(work, 'subs.txt'),
                    '-filter_complex', fc, '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
                    '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', f'{dur:.3f}', a.out], check=True)
    print('subtitles:', ' '.join(f"[{w['t0']:.1f}]{display(w['w'])}" for w in sel))
    print('wrote', a.out)

if __name__ == '__main__':
    main()
