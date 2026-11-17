# Agamemnon: The King Whose Homecoming Went Wrong (YouTube video, not a Short)

- **Video:** `agamemnon_the_odyssey.mp4` (1920x1080, 30 fps, 1:00, H.264 + AAC)
- **Style:** flat 2D cartoon in a pale-blue palette (soft sky blue, grey-blue sea, sand, bronze), with a light film wash and slow camera push-ins
- **Agamemnon's design:** an original cartoon based on Mycenaean archaeology: Dendra-style bronze plate armour (neck guard, shoulder plates, girdle bands), bronze greaves, a boar's-tusk helmet with a plume, a red cloak and a sceptre. It is not the film's costume and not the actor's likeness.
- **Voice:** English male narration by Kokoro TTS (`am_michael`), with burned-in subtitles timed per clause
- **Music:** original modal score (strings, choir-like pad, frame drums during the war, impacts, sea). The voice sits about 10 dB above it.

## Story (Greek myth, public domain)
| Time | Scene |
|---|---|
| 0:00 | Storm at sea: "Before Odysseus could get home…", then the reveal of Agamemnon, "KING OF KINGS" |
| 0:06 | Mycenae, the Lion Gate and gold; brother Menelaus |
| 0:11 | Paris sails off with Helen; the fleet grows to 1,000+ ships |
| 0:18 | Aulis: no wind, the sacrifice of Iphigenia (only a distant silhouette, nothing graphic), the wind returns |
| 0:25 | Ten-year siege of Troy; the quarrel with Achilles ("PRIDE") |
| 0:33 | Troy falls (wooden horse, fire), and he sails home a conqueror |
| 0:37 | Mycenae at night: Clytemnestra in the doorway, Aegisthus in the shadows; the lights go out and the crown falls |
| 0:45 | Underworld: his ghost warns Odysseus, "TRUST NO ONE." |
| 0:51 | Closing card: Agamemnon in Christopher Nolan's The Odyssey, played by Benny Safdie; the king and his reflection as "the dark mirror" |

## Upload text
**Title:** Agamemnon Explained in 60 Seconds: The King From Nolan's The Odyssey ⚔️

**Description:**
King of Mycenae, leader of 1,000 ships, conqueror of Troy… and murdered on the day he came home. Agamemnon's story is the dark mirror of Odysseus's journey. In Christopher Nolan's The Odyssey he is played by Benny Safdie.

#theodyssey #christophernolan #agamemnon #greekmythology #odysseus #troy #mythology

## Rebuild
```bash
python3 voice.py /path/to/kokoro-models
python3 music.py narration.wav timing.json mix.wav
python3 render.py timing.json mix.wav agamemnon_the_odyssey.mp4
```
