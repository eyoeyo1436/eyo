"""One-command GTA 6 Shorts: Twitch clip URL (or file) -> finished Short in our approved format.

  python3 auto.py --list                       # today's top English GTA 6 clips (12-60 s), one line each
  python3 auto.py URL [URL ...] --plan         # download + transcribe + detect webcam + pick window, print a short plan
  python3 auto.py URL [--hook "..."] [--start S --end E] [--cam X,Y,W,H] [--name login]   # build the Short

Everything is cached per clip in cache/<slug>/ (video, metadata, transcript), so --plan followed by a build
does the slow work once. Output: ../gta6_clips/<login>_<slug>.mp4. Console output is kept to a few lines.

Automatic choices (all overridable):
  layout  vertical clips are used as they are; horizontal clips get the webcam found automatically
          (persistent rectangle edges in a frame corner) put on top, game below, word subtitles on the seam
  window  clips up to 42 s are used whole; longer ones keep the ~38 s with the most speech and loud moments,
          starting ~3.6 s before the first word so the hook does not cover it
  hook    from keywords in the title/transcript (police, car, plane, heist, NPC...), with the streamer's name;
          names without vowels (xQc) are spelled out for the voice
"""
import argparse, json, os, re, subprocess, sys, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')
OUTDIR = os.path.join(os.path.dirname(HERE), 'gta6_clips')
GQL = 'https://gql.twitch.tv/gql'
CID = 'kimne78kx3ncx6brgo4mv6wki5h1ko'
GAME = 'Grand Theft Auto VI'

def gql(query):
    r = urllib.request.Request(GQL, json.dumps({'query': query}).encode(), {'Client-ID': CID, 'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(r, timeout=30))['data']

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        sys.exit(f'FAILED: {" ".join(cmd[:3])}...\n{p.stderr[-1500:]}')
    return p.stdout

# ------------------------------------------------------------------ clip list / fetch
def list_top(period='LAST_DAY', n=15):
    q = ('query { game(name:"%s") { clips(first:100, criteria:{period:%s, sort:VIEWS_DESC}) { edges { node { '
         'slug title viewCount durationSeconds language broadcaster { login } } } } } }' % (GAME, period))
    rows = []
    for attempt in range(3):                                  # Twitch sometimes answers null; retry with a smaller page
        g = gql(q.replace('first:100', 'first:%d' % (100 if attempt == 0 else 50)))
        if g and g.get('game') and g['game'].get('clips'):
            rows = [e['node'] for e in g['game']['clips']['edges']]
            break
    rows = [r for r in rows if r['language'] == 'EN' and 12 <= r['durationSeconds'] <= 60][:n]
    for r in rows:
        print(f"{r['viewCount']:6d}v {r['durationSeconds']:3.0f}s {r['broadcaster']['login']:14s} {r['title'][:50]!r} https://clips.twitch.tv/{r['slug']}")

def slug_of(src):
    m = re.search(r'(?:clips\.twitch\.tv/|/clip/)([\w-]+)', src)
    return m.group(1) if m else None

def fetch(src):
    """Return (cache dir, metadata). Downloads Twitch clips once."""
    slug = slug_of(src)
    if not slug:                                              # local file
        base = re.sub(r'\W+', '_', os.path.splitext(os.path.basename(src))[0])[:40]
        d = os.path.join(CACHE, base); os.makedirs(d, exist_ok=True)
        meta = {'slug': base, 'title': base, 'login': None, 'display': None, 'file': os.path.abspath(src)}
        return d, meta
    d = os.path.join(CACHE, slug); os.makedirs(d, exist_ok=True)
    mp = os.path.join(d, 'meta.json')
    if os.path.exists(mp):
        return d, json.load(open(mp))
    info = gql('query { clip(slug:"%s") { title durationSeconds broadcaster { login displayName } } }' % slug)['clip']
    f = os.path.join(d, 'clip.mp4')
    run(['yt-dlp', '-q', '--no-warnings', '-f', 'best[height>=720]/best', '-o', f, f'https://clips.twitch.tv/{slug}'])
    meta = {'slug': slug, 'title': info['title'], 'login': info['broadcaster']['login'],
            'display': info['broadcaster']['displayName'], 'file': f}
    json.dump(meta, open(mp, 'w'))
    return d, meta

def probe(f):
    j = json.loads(run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                        '-show_entries', 'format=duration', '-of', 'json', f]))
    return j['streams'][0]['width'], j['streams'][0]['height'], float(j['format']['duration'])

# ------------------------------------------------------------------ webcam detection
def detect_cam(f, sw, sh, dur):
    """Find the streamer's webcam: a face that stays in the same place in most sampled frames (OpenCV Haar) marks it
    (game faces come and go). Returns a face-centred crop with the top panel's aspect, shrunk until it holds no
    gameplay (pixels that change a lot over the clip). None if there is no steady face."""
    import cv2
    w, h, n = 960, 540, 24
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-vf', f'fps={n / max(dur, 1):.4f},scale={w}:{h},format=gray',
                          '-f', 'rawvideo', '-'], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w)
    det = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    det2 = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
    faces = []
    for im in fr:
        for d in (det, det2):
            for (x, y, fw, fh) in d.detectMultiScale(im, 1.1, 5, minSize=(28, 28), maxSize=(260, 260)):
                faces.append((x + fw / 2, y + fh / 2, fw))
    if not faces:
        return None
    F = np.array(faces)
    # the face position seen in the most frames (webcam faces barely move; game faces come and go)
    votes = [(np.sum(np.hypot(F[:, 0] - x, F[:, 1] - y) < max(30, s * 0.8)), x, y, s) for x, y, s in F]
    cnt, fx, fy, fs = max(votes)
    if cnt < max(3, len(fr) * 0.2):
        return None
    near = F[np.hypot(F[:, 0] - fx, F[:, 1] - fy) < max(30, fs * 0.8)]
    fx, fy, fs = np.median(near, 0)
    import cv2 as _cv
    V = _cv.blur(fr.astype(np.float32).std(0), (5, 5))
    hot = V > max(16.0, 0.8 * np.median(V))                          # pixels that change like gameplay
    # a box with the top panel's aspect, centred a little below the face, shrunk until it holds (almost) no gameplay
    asp = 1080 / 680
    I = np.pad(np.cumsum(np.cumsum(hot, 0), 1), ((1, 0), (1, 0))).astype(np.float64)
    def frac(l, t, cw, ch):
        l, t, r, b = int(l), int(t), int(l + cw), int(t + ch)
        return (I[b, r] - I[t, r] - I[b, l] + I[t, l]) / max(1, (r - l) * (b - t))
    hh = fs * 4.5
    while True:
        ch, cw = hh, hh * asp
        best = None
        for dx in np.linspace(-0.32, 0.32, 9):                     # the face may sit off-centre in the webcam
            for dy in np.linspace(-0.12, 0.2, 5):
                l = min(max(0, fx - cw / 2 + dx * cw), w - cw); t = min(max(0, fy - ch / 2 + dy * ch), h - ch)
                fr_ = frac(l, t, cw, ch)
                if best is None or fr_ < best[0]:
                    best = (fr_, l, t)
        if best[0] < 0.04 or hh < fs * 1.7:
            break
        hh *= 0.95
    _, left, top = best
    k = sw / w
    return [int(left * k), int(top * k), int(cw * k), int(ch * k)]

# ------------------------------------------------------------------ transcript, window, hook
def transcript(d, f):
    p = os.path.join(d, 'words.json')
    if not os.path.exists(p):
        sys.path.insert(0, HERE)
        from verticalize import transcribe
        json.dump(transcribe(f, os.path.join(HERE, 'models', 'sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8')), open(p, 'w'))
    return p, json.load(open(p))

def pick_window(f, words, dur, L=38.0):
    if dur <= 42:
        return 0.0, dur
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-ac', '1', '-ar', '8000', '-f', 's16le', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32)
    sec = np.sqrt([np.mean(a[i * 8000:(i + 1) * 8000] ** 2) + 1 for i in range(int(dur))])
    loud = (sec > np.percentile(sec, 75)).astype(float)
    wps = np.zeros(int(dur) + 1)
    for w in words:
        wps[min(int(w['t0']), len(wps) - 1)] += 1
    score = wps[:len(loud)] + 2 * loud
    best_s = max(range(0, int(dur - L) + 1), key=lambda s: score[s:s + int(L)].sum())
    inside = [w for w in words if best_s <= w['t0'] <= best_s + L]
    start = max(0.0, (inside[0]['t0'] if inside else best_s) - 3.6)
    end = min(dur, max(start + 15, (inside[-1]['t1'] if inside else best_s + L) + 2.0), start + 45)
    return round(start, 1), round(end, 1)

HOOKS = [(r'police|cops?\b|chase|wanted|arrest', "{n} vs GTA 6 police!"),
         (r'plane|fly|flight|pilot|helicopter', "{n} tried flying in GTA 6..."),
         (r'heist|rob|stick ?up|teller|bank|cash', "GTA 6 heists have begun!"),
         (r'\bcar\b|steal|jack|truck', "{n}'s first GTA 6 car theft!"),
         (r'npc|insult|said|called', "GTA 6 NPCs are savage!"),
         (r'strip|club|dance', "{n} found the GTA 6 club..."),
         (r'release|countdown|launch|first time', "{n} finally plays GTA 6!")]

def auto_hook(name, title, words):
    text = (title + ' ' + ' '.join(w['w'] for w in words)).lower()
    for pat, h in HOOKS:
        if re.search(pat, text):
            return h.format(n=name)
    return f"{name} just broke GTA 6!"

def spoken(hook, name):
    """Spell out names the voice would mangle (no vowels, e.g. xQc -> X-Q-C)."""
    if name and not re.search(r'[aeiouy]', name.lower()) and len(name) <= 5:
        return re.sub(re.escape(name), '-'.join(name.upper()), hook, flags=re.I)
    return None

# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', nargs='*')
    ap.add_argument('--list', action='store_true'); ap.add_argument('--period', default='LAST_DAY')
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--hook'); ap.add_argument('--hook-say'); ap.add_argument('--name')
    ap.add_argument('--start', type=float); ap.add_argument('--end', type=float); ap.add_argument('--cam')
    ap.add_argument('--badge-y', type=int); ap.add_argument('--out')
    ap.add_argument('--fix', action='append', default=[])
    ap.add_argument('--subs', action='store_true', help='burn our word subtitles (off: the stream already has captions)')
    a = ap.parse_args()
    if a.list:
        return list_top(a.period)
    for src in a.src:
        d, meta = fetch(src)
        f = meta['file']
        sw, sh, dur = probe(f)
        vertical = sh > sw
        wp, words = transcript(d, f)
        name = a.name or meta['login'] or 'streamer'
        disp = meta['display'] or name
        if vertical:
            cam, start, end = None, 0.0, dur
        else:
            cam = [int(v) for v in a.cam.split(',')] if a.cam else detect_cam(f, sw, sh, dur)
            start, end = pick_window(f, words, dur)
        if a.start is not None: start = a.start
        if a.end is not None: end = a.end
        sel = [w for w in words if start <= w['t0'] <= end]
        hook = a.hook or auto_hook(disp, meta['title'], sel)
        say = a.hook_say or spoken(hook, disp)
        print(f"[{meta['slug'][:40]}] {disp} | {meta['title'][:50]!r} | {dur:.1f}s {sw}x{sh}")
        print(f"  cam: {','.join(map(str, cam)) if cam else ('vertical clip' if vertical else 'NOT FOUND -> game only')}"
              f" | window: {start:.1f}-{end:.1f} | hook: {hook!r}" + (f" (say {say!r})" if say else ''))
        print('  words: ' + ' '.join(f"[{w['t0']:.0f}]{w['w']}" for w in words)[:900])
        if a.plan:
            if cam:
                chk = os.path.join(d, 'cam_check.jpg')
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{(start + end) / 2:.1f}', '-i', f, '-frames:v', '1', '-vf',
                                f"drawbox={cam[0]}:{cam[1]}:{cam[2]}:{cam[3]}:color=lime:t=8,scale=320:-2", chk])
                print(f'  cam check image: {chk}')
            continue
        os.makedirs(OUTDIR, exist_ok=True)
        out = a.out or os.path.join(OUTDIR, f"{name}_{meta['slug'][:24]}.mp4")
        if vertical and a.start is None and a.end is None:
            vert = f
        else:
            vert = os.path.join(d, 'vertical.mp4')
            cmd = [sys.executable, os.path.join(HERE, 'verticalize.py'), f, vert, '--start', str(start), '--end', str(end), '--words', wp]
            cmd += ['--cam', ','.join(map(str, cam))] if cam else ['--no-cam']
            if not a.subs:
                cmd += ['--no-subs']
            for fx in a.fix:
                cmd += ['--fix', fx]
            run(cmd)
        cmd = [sys.executable, os.path.join(HERE, 'make_short.py'), vert, out, '--name', name, '--hook', hook]
        if say: cmd += ['--hook-say', say]
        if a.badge_y: cmd += ['--badge-y', str(a.badge_y)]
        res = run(cmd)
        lu = re.search(r'hook LUFS (\S+) \| clip LUFS (\S+)', res)
        print(f"  DONE {out} ({os.path.getsize(out) / 1e6:.0f} MB" + (f", hook {lu.group(1)} / clip {lu.group(2)} LUFS)" if lu else ')'))

if __name__ == '__main__':
    main()
