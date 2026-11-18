# eyo: YouTube Shorts

The user writes in Turkish; reply in Turkish.

## GTA 6 Shorts: use the template
Every GTA 6 Short made from a streamer clip uses `shorts/gta6_template/make_short.py`. The user approved this format and wants it to stay the standard. See `shorts/gta6_template/README.md`; the approved reference video is `shorts/gta6_heist/gta6_heists_have_begun.mp4`.

```bash
python3 shorts/gta6_template/make_short.py CLIP.mp4 OUT.mp4 --name <twitch name> --hook "<short English hook>"
```

The template adds only three things:
- an AI English male voice hook, with the clip blurred underneath and the hook text popping in word by word;
- an animated Twitch logo and name badge at bottom centre;
- a blurred end card with the avatar, "MORE GTA 6 VIDEOS", a subscribe click animation, then a fade to black.

Do not touch the clip's own subtitles or edit. If the badge covers the clip's on-screen text, move it with `--badge-y`.
