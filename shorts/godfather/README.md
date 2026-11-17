# Why Is The Godfather So Good? — YouTube Short

- **Video:** `why_is_the_godfather_so_good.mp4` (1080x1920, 30 fps, exactly 60.0 s, H.264 ~10 Mbps + AAC 48 kHz, −14 LUFS)
- **Cover:** `cover.png`
- **Style:** illustrated graphic-novel animation, drawn entirely in code (ink outlines, hatched shadows, the film's top-light that sinks the eyes into darkness), warm amber grade, film grain, gate weave, parallax camera moves
- **Voice:** deep male documentary read (Kokoro neural TTS, a blend of the `am_michael` and `am_onyx` voices), EQ'd and compressed for warmth
- **Music:** an original slow C-minor waltz for mandolin tremolo, harp and strings, synthesised by `music.py` (no existing music, and no Nino Rota themes)

## Shot list
| Time | Narration | Shot |
|---|---|---|
| 0:00 | "How did a movie about the Mafia…" | Vito close-up fades up from black, title card; Michael revealed as light crosses his face |
| 0:05.7 | "…isn't simply about organized crime." | Vito in his office: venetian blinds, the cat, the ring |
| 0:09.9 | "family, power, loyalty…" | The family portrait at Connie's wedding |
| 0:14.8 | "Every character feels real…" | Michael, in his Marine uniform, sitting quietly at the wedding |
| 0:19.6 | "Michael's transformation…" | Split frame: the war hero in sunlight / the Don in shadow |
| 0:24.2 | "He begins as a man who wants nothing to do…" | Michael apart from the celebration |
| 0:29.4 | "…the very thing he once rejected." | Cold close-up through blind shadows, heartbeat drum |
| 0:33.6 | "Francis Ford Coppola's direction," | Empty office, lamp and smoke |
| 0:36.0 | "Gordon Willis's unforgettable cinematography," | The restaurant: checked tablecloth, the train getting louder |
| 0:39.3 | "…Nino Rota's haunting score…" | Close on Michael, sweating, eyes darting |
| 0:44.1 | "Even silence becomes powerful." | The score cuts out; one blade of light across Vito's eyes |
| 0:46.9 | "That's why The Godfather still stands apart." | Oranges, the rose |
| 0:50.0 | "…a story about power." | Michael behind the Don's desk |
| 0:53.2 | "It shows you what power can turn a person into." | Kay's view: the door closes on Michael and his men |
| 0:56.6 | "That's what makes it a masterpiece." | Fade to black, **THE GODFATHER (1972)** |

Subtitles are word-timed, karaoke style (the spoken word pops); key words (FAMILY, POWER, TRANSFORMATION, SILENCE, MASTERPIECE…) are gold.

## Upload text
**Title:** Why Is The Godfather So Good? 🌹 #thegodfather #movies

**Description:**
How did a movie about the Mafia become one of the greatest films ever made? Family, power, loyalty, and Michael Corleone's transformation, plus Coppola's direction, Gordon Willis's shadows, and Nino Rota's score. Is it the greatest film ever made? Tell me in the comments.

#thegodfather #godfather #michaelcorleone #filmanalysis #cinema #classicmovies #moviefacts #shorts

## Files
| File | What it does |
|---|---|
| `script.py` | Narration text, sections, highlighted words |
| `voice.py` | Voices each sentence with Kokoro and estimates word timings (phoneme counts anchored to detected pauses) |
| `timeline.py` | Places the lines on the 60 s timeline and cuts shots to spoken words |
| `ink.py` | Drawing toolkit on skia (smooth shapes, ink lines, hatching, light) |
| `characters.py` | Fixed character designs: Vito, Michael (young and later), supporting family |
| `scenes.py` | The 16 illustrated shots, each in parallax layers |
| `music.py` | Original score and sound design stems |
| `render.py` | Camera, transitions, grade, grain, subtitles, title cards, voice processing, mix and encode |

## Rebuild
Needs Python 3, ffmpeg, and `pip install skia-python kokoro-onnx soundfile scipy pillow numpy` (skia needs `libegl1` on Linux).
Fonts (SIL Open Font License, from google/fonts): Anton, Cinzel. Voice model: `kokoro-v1.0.onnx` and `voices-v1.0.bin` from the kokoro-onnx GitHub releases.
```bash
python3 voice.py MODELS_DIR VO_DIR
python3 music.py VO_DIR/timing.json AUDIO_DIR
python3 render.py VO_DIR AUDIO_DIR FONTS_DIR master.mp4 --workers 4
```
`render.py --stills DIR` writes preview frames; `--remux VIDEO` re-mixes the audio onto an existing render.

## Notes
- All visuals are original illustrations of the characters. No film footage, stills or the film's logo are used.
- The scenes shown (the wedding, the office cat, the restaurant, the oranges, the closing door) are all from the film. Nothing in the narration is invented.
