# eyo: YouTube Shorts

The user writes in Turkish; reply in Turkish, briefly.

## GTA 6 Shorts: one command, minimum credits
The user approved this format and wants it to stay the standard. The reference video is `shorts/gta6_heist/gta6_heists_have_begun.mp4`. Everything runs through `shorts/gta6_template/auto.py`; details are in `shorts/gta6_template/README.md`.

```bash
cd shorts/gta6_template
python3 auto.py --list                        # today's top English GTA 6 clips, one line each
python3 auto.py URL [URL ...] --plan          # text plan: webcam box, window, hook, transcript (cached)
python3 auto.py URL [--hook "..."] [--start S --end E] [--cam X,Y,W,H]   # build -> shorts/gta6_clips/
```

### How to work cheaply
These rules exist because the user asked to spend as few credits as possible.
- Do not make contact sheets and do not look at video frames. Read the plan text instead: the transcript has times, and that is enough to choose `--start`/`--end` and to write a better `--hook`.
- Only view the small `cache/<slug>/cam_check.jpg` (320 px) if the cam line looks wrong: NOT FOUND, or an unexpected position.
- Run a build once. Do not re-run it to "check". The DONE line already reports size and loudness.
- Skip clips with nudity. Watch for titles or transcripts mentioning strip clubs or showers; YouTube restricts them.
- Do not read the scripts unless something fails. Keep replies to a few lines.
- Thumbnails: `python3 thumbnail.py cache/<slug>/clip.mp4 OUT --t <moment> --cx <x> --cam 0,0,367,293 --name <login> --text "LINE|GTA 6|LAST!"`. Pick the moment from one small tile, e.g. `ffmpeg -i clip -vf fps=1/4,scale=192:108,tile=5x3 -frames:v 1 t.jpg`, not from separate frames. Check one small combined preview.
- After building, commit and push the mp4, then send it with SendUserFile.

### What the template does (do not change it)
- **Hook:** an AI English male voice reads a short hook. The clip plays blurred underneath, and the hook text pops in word by word.
- **Twitch badge:** an animated Twitch logo and name badge at bottom centre.
- **End card:** a blurred background with the avatar, "MORE GTA 6 VIDEOS" and a subscribe-click animation, then a fade to black.
- **Horizontal clips:** these get the approved vertical layout:
  - the webcam (found automatically from the streamer's face) on top;
  - the game below;
  - word-by-word subtitles with a purple box on the active word.
- **Vertical clips:** used as they are; the clip's own subtitles and edit are never touched.
