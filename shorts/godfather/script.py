"""Narration script, section timing and subtitle chunks (single source of truth)."""
# Each section: (start_s, end_s, [sentences]). Sentences are voiced one by one.
SECTIONS = [
    (0.0, 7.0, ["How did a movie about the Mafia become one of the greatest films ever made?"]),
    (7.0, 20.0, ["Because The Godfather isn't simply about organized crime.",
                 "It's about family, power, loyalty, and the corruption of the human soul.",
                 "Every character feels real, and every decision has consequences."]),
    (20.0, 34.0, ["Michael's transformation is what makes the story unforgettable.",
                  "He begins as a man who wants nothing to do with his family's criminal empire.",
                  "But slowly, he becomes the very thing he once rejected."]),
    (34.0, 46.0, ["Francis Ford Coppola's direction, Gordon Willis's unforgettable cinematography, "
                  "and Nino Rota's haunting score create an atmosphere that feels timeless.",
                  "Even silence becomes powerful."]),
    (46.0, 56.0, ["That's why The Godfather still stands apart.",
                  "It doesn't just tell you a story about power.",
                  "It shows you what power can turn a person into."]),
    (56.0, 60.0, ["That's what makes it a masterpiece."]),
]
# Words rendered in the gold highlight colour in subtitles.
HIGHLIGHT = {"mafia", "godfather", "family", "power", "loyalty", "corruption", "soul",
             "consequences", "michael's", "transformation", "unforgettable", "rejected",
             "coppola's", "willis's", "rota's", "timeless", "silence", "powerful", "masterpiece"}
