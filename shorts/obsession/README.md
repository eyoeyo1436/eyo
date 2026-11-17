# Why Is Obsession So Disturbing? | The Horror Behind Love — YouTube Short

- **Video:** `obsession_horror_behind_love.mp4` (1080x1920, 30 fps, exactly 60.0 s, H.264 ~10 Mbps + AAC 48 kHz, −14 LUFS)
- **Cover:** `cover.png`
- **Style:** 2D horror-comic illustration drawn entirely in code: bold ink, hatching and halftone, under-lighting and moonlight, a cold desaturated grade that keeps the reds, film grain, glitch hits and parallax camera moves
- **Voice:** deep male documentary read (Kokoro neural TTS, `am_michael` + `am_onyx` blend). The narrator says "Inde Navarrette" as IN-dee nav-ə-RET-ee; the subtitles keep the real spelling.
- **Music:** original and synthesised by `music.py`: a music-box lullaby (the "love" theme) that slowly detunes and sours, over drones, dissonant string clusters, heartbeats and stingers

## Characters (one fixed design each, used in every shot)
- **Bear:** lean face, messy dark fringe, light stubble, anxious brows, dark-green hoodie with drawstrings over a grey tee.
- **Nikki:** soft oval face, big lashed eyes, long wavy dark hair with a middle part, red knit sweater. The same face goes from sweet (blush, smiling eyes) to unsettling (pale, staring, tiny pupils, the too-wide grin, the head tilt).

## Shot list (a new shot every 1.6 to 3.6 s)
| Time | Narration | Shot |
|---|---|---|
| 0:00 | "What if the person you loved…" | Bear holds the broken wishing stick; Nikki smiles behind him. **LOVE CAN BECOME A NIGHTMARE.** |
| 0:03.5 | "…makes Obsession so terrifying." | Nikki dissolves into a glowing-eyed silhouette |
| 0:07.1 | "The film follows Bear," | Bear watches Nikki from behind a doorframe |
| 0:09.0 | "…desperately in love…" | Bear close-up, longing |
| 0:11.9 | "He makes one wish:" | The One Wish Willow snaps on "wish" (flash, sparks) |
| 0:13.5 | "…to love him more than anything." | Nikki, sweet |
| 0:15.6 | "But getting exactly what you want…" | Nikki clings adoringly; Bear's smile wavers |
| 0:17.4 | "…a horrifying price." | Nikki's grin stretches under cold light |
| 0:19.8 | "Inde Navarrette delivers…" | Nikki, charming, in warm light |
| 0:22.8 | "…transforming Nikki…" | Frozen smile, head tilts too far |
| 0:25.5 | "…into someone deeply disturbing." | Extreme close-up: unblinking eyes |
| 0:28.0 | "Her expressions, movements," | Contorted stance in a hallway, warped shadow |
| 0:30.0 | "…and sudden changes…" | Smash-zoom lunge with a glitch |
| 0:33.4 | "But the real genius is its premise." | Bear's moonlit bedroom |
| 0:36.0 | "…the desire to be loved," | Bear terrified, sweating, heartbeat |
| 0:39.1 | "…and turns it into psychological horror." | Nikki appears in the dark doorway behind him |
| 0:41.8 | "…disturbing violence…" | Red comic burst behind Nikki's smile (suggested, not shown) |
| 0:44.3 | "…uncomfortable dark humor." | A too-tight hug: her bliss, his frozen grin |
| 0:46.9 | "Obsession isn't really a story about love." | Bear alone under one lamp |
| 0:49.9 | "It's about control, possession," | Nikki's shadow rises on the wall behind him |
| 0:51.8 | "…destroys someone's freedom." | A shadow hand creeps over his shoulder |
| 0:55.1 | "That's why this film stays with you." | The shadow towers; slow fade toward black |
| 0:57.6 | — | **OBSESSION (2025)** |

Subtitles are word-timed and karaoke style; LOVE, CONTROL, OBSESSION, POSSESSION, DESIRE, FREEDOM, HORROR and similar words are red.

## Upload text
**Title:** Why Is Obsession So Disturbing? | The Horror Behind Love 🖤 #obsession #horror

**Description:**
What if the person you loved became obsessed with you? Curry Barker's Obsession turns a single wish into psychological horror, led by Inde Navarrette's unforgettable performance as Nikki. Have you seen it? Tell me in the comments.

#obsession #horrormovie #currybarker #indenavarrette #psychologicalhorror #filmanalysis #moviereview #shorts

## Facts used
Bear (Michael Johnston) wishes on a supernatural toy for his friend Nikki (Inde Navarrette) to love him, and her love becomes a suffocating obsession. Written and directed by Curry Barker; premiered at TIFF Midnight Madness in September 2025; distributed by Focus Features. The visuals stick to the premise in the brief. No specific scenes, dialogue or violence from the film are recreated.

## Files and rebuild
Same pipeline as `../godfather`: `script.py` (text, spoken respellings, highlights), `voice.py`, `timeline.py`, `ink.py`, `characters.py`, `scenes.py`, `music.py`, `render.py`.
```bash
python3 voice.py MODELS_DIR VO_DIR 1.08
python3 music.py VO_DIR/timing.json AUDIO_DIR
python3 render.py VO_DIR AUDIO_DIR FONTS_DIR master.mp4 --workers 4
```
Needs Python 3, ffmpeg, `pip install skia-python kokoro-onnx soundfile scipy pillow numpy`, the Anton and Cinzel fonts (OFL, google/fonts) and the Kokoro v1.0 model files (kokoro-onnx GitHub releases). The master is re-encoded two-pass at 10 Mbps for delivery.
