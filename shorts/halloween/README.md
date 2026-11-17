# Why Halloween (1978) Worked: YouTube Short

- **Video:** `halloween_1978_why_it_worked.mp4` (1080x1920, 30 fps, 0:30, H.264 + AAC)
- **Style:** 70s VHS horror look. A suburban street at night with an orange sky, falling leaves, a street lamp and a distant faceless figure. VHS scan lines, colour fringing, "PLAY" and "OCT. 31 1978" on-screen text, and a glitch on every cut.
- **Voice:** English narration by Kokoro TTS (voice `am_michael`)
- **Music:** original music-box notes, a detuned pad, wind and thumps. It is not the film's theme.

No film footage, the film's mask, its characters or its music are used. Everything is drawn by `render.py`.

## Upload text
**Title:** Why Halloween (1978) Still Terrifies Everyone 🎃 #halloween #shorts

**Description:**
Made for about $300K, it earned around $70M. The mask was a cheap store-bought one painted white. The director wrote the music in about 3 days. And the autumn leaves? Painted paper, in a California spring. Is it still the scariest movie ever? 👇

#halloween #halloween1978 #johncarpenter #horrormovies #slasher #movies #shorts

## Rebuild
```bash
python3 voice.py /path/to/kokoro-models
python3 music.py narration.wav lines.json mix.wav
python3 render.py lines.json mix.wav halloween_1978_why_it_worked.mp4
```
