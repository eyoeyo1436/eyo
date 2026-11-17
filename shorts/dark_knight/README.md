# Why The Dark Knight Worked: YouTube Short

- **Video:** `the_dark_knight_why_it_worked.mp4` (1080x1920, 30 fps, 0:40, H.264 + AAC)
- **Style:** dark noir motion graphics. A rainy city skyline at night, fog, film grain and a cold colour grade, with red and gold accents. Each scene starts with a lightning flash and a camera shake. Captions appear a few words at a time.
- **Voice:** English narration by Kokoro TTS (open-weight, voice `am_michael`)
- **Music:** original score: low drone, a slowly rising string note, a ticking pulse and impact hits, with rain

No film footage, posters, logos or actor likenesses are used. Everything is drawn by `render.py`.

## Upload text
**Title:** Why The Dark Knight Was SO Successful 🃏 #thedarkknight #shorts

**Description:**
$1 billion. A posthumous Oscar for Heath Ledger. A real truck flipped in Chicago. And the snub that made the Oscars change their rules. Is it still the greatest superhero movie ever made? 👇

#thedarkknight #batman #joker #heathledger #christophernolan #movies #shorts

## Rebuild
```bash
pip install kokoro-onnx soundfile scipy pillow numpy
python3 voice.py /path/to/kokoro-models   # kokoro-v1.0.onnx + voices-v1.0.bin -> narration.wav, lines.json
python3 music.py narration.wav lines.json mix.wav
python3 render.py lines.json mix.wav the_dark_knight_why_it_worked.mp4
```
Fonts: Bebas Neue and Oswald (SIL Open Font License), in `fonts/`.
