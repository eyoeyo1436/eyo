"""Narration (display text), section timing targets, spoken-only respellings and subtitle highlights."""
SECTIONS = [
    (0.0, 5.0, ["Why is The Conjuring still considered one of the scariest horror movies ever made?"]),
    (5.0, 13.0, ["Directed by James Wan, the film understands something most horror movies forget: "
                 "what you don't see can be far more terrifying."]),
    (13.0, 22.0, ["Instead of relying on constant jump scares, it builds tension through silence, "
                  "strange sounds, and perfectly timed moments of terror."]),
    (22.0, 31.0, ["Vera Farmiga and Patrick Wilson make Ed and Lorraine Warren feel believable, "
                  "giving the supernatural story an emotional center."]),
    (31.0, 40.0, ["That's why The Conjuring works so well.",
                  "It doesn't just show you something frightening.",
                  "It makes you afraid of what might be waiting in the next room."]),
]
# Narrator says far-MEE-guh and "Wahn"; subtitles keep the real spelling.
SPOKEN = {"Farmiga": "Far-meega", "Wan": "Wahn"}
HIGHLIGHT = {"conjuring", "scariest", "horror", "terrifying", "don't", "see", "silence", "tension", "terror",
             "jump", "scares", "believable", "supernatural", "emotional", "afraid", "frightening", "waiting",
             "next", "room", "wan", "warren"}
