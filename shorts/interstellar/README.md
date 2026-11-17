# Interstellar: The Black Hole Was Realistic? (YouTube Short)

- **Video:** `interstellar_black_hole_realistic.mp4` (1080x1920, 30 fps, 0:40, H.264 + AAC)
- **Voice:** your script, word for word, read in English by Kokoro TTS (American male voice `am_michael`, speed 1.27 so it fits 40 s)
- **Subtitles:** burned in, bold white Montserrat with key terms in gold, kept inside the vertical safe area. Timing is exact at every clause boundary because each clause was voiced separately. Words within a clause are timed by syllable count.
- **Music:** an original orchestral-style score (strings, low brass, timpani, riser, hall reverb). The voice sits about 9 dB above it, and the music ducks further while the voice speaks.

## No film footage
Interstellar footage isn't licensed for this, so every black-hole shot is an **original simulation**: real light paths traced through curved spacetime (`raytrace.py`, Schwarzschild geodesics, `u'' + u = 3u²`), shaded with a thin-disk temperature profile, orbital Doppler beaming and gravitational redshift (`shade.py`). The lensed arc over the top of the hole, the arc under it and the thin photon ring all come from the physics, not from drawing. Simplification: the simulation uses a non-spinning black hole. Gargantua in the film spins fast, which changes the shape slightly.

## Accuracy notes
- Gargantua is called "the fictional black hole of Interstellar" on screen.
- The research card cites the real paper: O. James, E. von Tunzelmann, P. Franklin, K. S. Thorne, *Gravitational lensing by spinning black holes in astrophysics, and in the movie Interstellar*, Classical and Quantum Gravity 32 (2015).
- The "far side of the disk" highlight marks exactly the disk points that lie behind the hole, computed from the ray-traced data.

## Upload text
**Title:** Interstellar's Black Hole Was Scientifically Accurate?! 🕳️ #interstellar #shorts

**Description:**
Christopher Nolan didn't want a black hole that only looked cool. Physicist Kip Thorne and the VFX team calculated how light really bends around a spinning black hole, and the work ended up in a peer-reviewed paper. Visuals: an original general-relativity simulation.

#interstellar #blackhole #christophernolan #physics #space #science #shorts

## Rebuild
```bash
pip install kokoro-onnx soundfile scipy pillow numpy
python3 voice.py /path/to/kokoro-models        # -> narration.wav, timing.json
python3 music.py narration.wav timing.json mix.wav
python3 raytrace.py                            # -> maps/*.npz (about 20 s)
python3 render.py timing.json mix.wav interstellar_black_hole_realistic.mp4   # about 10 min on 4 cores
```
