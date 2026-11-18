"""Render every shot of the Conjuring Short (Cycles, 10 fps, 540x960) using the timeline durations."""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import layout, shots
timing, out, mh = sys.argv[1], sys.argv[2], sys.argv[3]
only = sys.argv[4].split(',') if len(sys.argv) > 4 else None
t = layout(timing)
for st, en, name in shots(t):
    if name == 'black' or (only and name not in only):
        continue
    dur = en - st + 0.2
    cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sets3d.py'), name, out, mh,
           '--res', '540x960', '--samples', '10', '--dur', f'{dur:.2f}', '--fps', '10']
    print('RUN', name, f'{dur:.2f}s', flush=True)
    subprocess.run(cmd, check=False)
print('ALLDONE', flush=True)
