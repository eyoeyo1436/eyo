# Why Is The Conjuring (2013) So Terrifying? — YouTube Short

- **Video:** `why_is_the_conjuring_so_terrifying.mp4` (1080x1920, 30 fps, exactly 40.0 s, H.264 + AAC 48 kHz, −14 LUFS)
- **Cover:** `cover.png`
- **Style:** stylized 3D animation rendered in Blender Cycles: one fixed character model per person, real hair strands, subsurface-scattered skin, cloth shells, volumetric fog, moonlight through windows, shallow depth of field, a cold desaturated grade with teal shadows, film grain and a slight light flicker
- **Voice:** deep male documentary read (Kokoro neural TTS, `am_michael` + `am_onyx` blend). The narrator says "Farmiga" as Far-MEE-ga and "Wan" as WAHN; the subtitles keep the real spelling.
- **Sound:** original and synthesised by `music.py`: a low D drone, dissonant string clusters, wind and crickets, a ticking clock, a door creak, footsteps, a heartbeat that speeds up in the final approach, a D-minor string-and-piano theme under the Warrens, and a hit on the cut to black. The music ducks under the narration.

## Characters (one model each, used in every shot)
All three are built on the CC0 MakeHuman base mesh, with procedural expressions, posed arms, strand hair and layered clothing. They are original stylized designs, not likenesses of the actors.
- **Lorraine Warren:** long dark centre-parted hair, green eyes, a beige turtleneck under a dark coat.
- **Ed Warren:** short side-parted brown hair, a grey-blue shirt, a dark tie and a brown jacket; he carries the flashlight.
- **The presence:** a tall, thin woman with wild long hair. She appears only as a silhouette, except for one pale face in the dark.

## Shot list (a new shot every 2.2 to 3.7 s; the final approach holds for 6.2 s)
| Time | Narration | Shot |
|---|---|---|
| 0:00 | "Why is The Conjuring still considered…" | The farmhouse at night under a bare tree; a silhouette appears in the lit upstairs window. Title: **WHY IS THE CONJURING SO TERRIFYING?** |
| 0:02.5 | "…one of the scariest horror movies ever made?" | Push-in on the window: the figure stands half behind the curtain and drifts toward the glass |
| 0:05.2 | "Directed by James Wan," | A long, foggy, moonlit hallway |
| 0:07.3 | "…understands something most horror movies forget:" | A door creaks open by itself |
| 0:09.7 | "…what you don't see can be far more terrifying." | A shadow slides across the hallway wall; nobody is there |
| 0:13.3 | "Instead of relying on constant jump scares," | A dark bedroom in cold moonlight |
| 0:16.4 | "…it builds tension through silence, strange sounds," | A pale face waits inside a half-open wardrobe; two claps |
| 0:19.3 | "…and perfectly timed moments of terror." | A silhouette stands in the corner of the room |
| 0:21.8 | "Vera Farmiga and Patrick Wilson make Ed and Lorraine Warren…" | Ed and Lorraine walk down the hallway with a flashlight |
| 0:24.2 | "…feel believable," | Lorraine close-up |
| 0:26.8 | "…giving the supernatural story an emotional center." | Ed close-up |
| 0:30.6 | "That's why The Conjuring works so well." | The Warrens from behind, heading into the dark |
| 0:33.3 | "It doesn't just show you something frightening. It makes you afraid of what might be waiting in the next room." | A silhouette at the end of the hallway, backlit by the window; the camera creeps toward it as the heartbeat speeds up |
| 0:39.5 | — | Hard cut to black |

Subtitles are word-timed in karaoke style; CONJURING, SCARIEST, HORROR, TERRIFYING, SILENCE, TENSION, TERROR, BELIEVABLE, SUPERNATURAL, AFRAID, NEXT ROOM and similar words are red.

## Upload text
**Title:** Why Is The Conjuring (2013) So Terrifying? 👻 #theconjuring #horror

**Description:**
James Wan's The Conjuring scares you with what you don't see: silence, strange sounds and perfectly timed terror, with Vera Farmiga and Patrick Wilson as Ed and Lorraine Warren at its heart. What scene still haunts you? Tell me in the comments.

#theconjuring #horrormovie #jameswan #verafarmiga #patrickwilson #edandlorrainewarren #filmanalysis #shorts

## Facts used
Only what the brief states: The Conjuring (2013), directed by James Wan, with Vera Farmiga and Patrick Wilson as Lorraine and Ed Warren. The visuals follow the five scenes in the brief (farmhouse, hallway, bedroom, the Warrens, the final hallway). The wardrobe claps are a nod to the film's hide-and-clap game; no scene, dialogue or shot from the film is recreated.

## Files and rebuild
| File | Role |
|---|---|
| `script.py` | Narration, spoken respellings, highlight words |
| `voice.py` | Kokoro voice, line WAVs and word timings |
| `timeline.py` | Line layout and the cut list (cuts land on words) |
| `human.py` | Characters: MakeHuman morphs, expressions, arm posing, skin/eye/hair materials, strand hair, clothing shells |
| `sets3d.py` | Blender sets (farmhouse, hallway, bedroom, wardrobe), lights, fog, cameras, and the Cycles render of one shot |
| `render_all.py` | Renders every shot at 540x960 and 10 fps from the timeline |
| `music.py` | Score and sound effects |
| `post.py` | 10→30 fps motion interpolation, 2x upscale and sharpening, grade, title, subtitles, mix, encode |

```bash
python3 voice.py MODELS_DIR VO_DIR 1.08
python3 music.py VO_DIR/timing.json AUDIO_DIR
python3 render_all.py VO_DIR/timing.json FRAMES_DIR MH_DIR
python3 post.py FRAMES_DIR WORK_DIR VO_DIR AUDIO_DIR FONTS_DIR why_is_the_conjuring_so_terrifying.mp4 --workers 4
```
Needs Python 3, ffmpeg, `pip install bpy==5.3.0 skia-python kokoro-onnx soundfile scipy pillow numpy`, the Anton and Cinzel fonts (OFL, google/fonts), the Kokoro v1.0 model files (kokoro-onnx GitHub releases) and, in `MH_DIR`, the MakeHuman `base.obj` and the macro targets named in `human.py` (CC0, makehumancommunity/makehuman on GitHub).

Rendering ran on 4 CPU cores with no GPU: about 10 s per frame for the empty sets and 20 to 28 s per frame for the character shots, roughly 1.5 hours for all 13 shots. On a GPU the same render takes minutes.
