# Crystal Lake: The Story (YouTube Short)

- **Video:** `crystal_lake_story.mp4` (1080x1920, 30 fps, 0:30, H.264 + AAC)
- **Topic:** what Peacock's *Crystal Lake* (the Friday the 13th prequel series, all 8 episodes out since October 15, 2026) is about, told in my own words from the published premise
- **Style:** animated Super 8 horror look: a misty lake at night, an empty rowboat, a faceless mother silhouette on the dock, a lamp-lit cabin window that turns red, car headlights, two strangers at the door, police lights and tape, dark woods. Film grain, flicker, gate weave, dust and scratches, with red key words.
- **Voice:** English narration by Kokoro TTS (`am_michael`)
- **Music:** original music-box notes, a detuned pad, wind and thumps

No footage, franchise mask or costume, or actor likeness is used. People appear only as faceless silhouettes.

## Upload text
**Title:** Crystal Lake Explained in 30 Seconds 🔪 Before Jason, There Was His Mother #shorts

**Description:**
Peacock's Friday the 13th prequel follows Pam Voorhees after her son Jason drowns in the town lake, as grief turns into obsession. Then two strangers start digging into her past… and bodies turn up around the lake. All 8 episodes are on Peacock. 👇 Have you watched it?

#crystallake #fridaythe13th #jasonvoorhees #pamelavoorhees #horror #peacock #shorts

## Rebuild
```bash
python3 voice.py /path/to/kokoro-models
python3 music.py narration.wav lines.json mix.wav
python3 render.py lines.json mix.wav crystal_lake_story.mp4
```
