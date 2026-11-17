"""Narration (display text), section timing targets, spoken-only respellings and subtitle highlights."""
SECTIONS = [
    (0.0, 8.0, ["What if the person you loved became obsessed with you?",
                "That's exactly what makes Obsession so terrifying."]),
    (8.0, 20.0, ["The film follows Bear, a young man desperately in love with his friend Nikki.",
                 "He makes one wish: for her to love him more than anything.",
                 "But getting exactly what you want comes with a horrifying price."]),
    (20.0, 34.0, ["Inde Navarrette delivers an unforgettable performance, transforming Nikki "
                  "from a charming young woman into someone deeply disturbing.",
                  "Her expressions, movements, and sudden changes make every scene unpredictable."]),
    (34.0, 48.0, ["But the real genius is its premise.",
                  "It takes something familiar, the desire to be loved, and turns it into psychological horror.",
                  "The film also mixes disturbing violence with uncomfortable dark humor."]),
    (48.0, 60.0, ["Obsession isn't really a story about love.",
                  "It's about control, possession, and what happens when desire destroys someone's freedom.",
                  "That's why this film stays with you."]),
]
# The narrator says the actress's name as IN-dee nav-uh-RET-ee; subtitles keep the real spelling.
SPOKEN = {"Inde": "Indy", "Navarrette": "Navuh-retty"}
HIGHLIGHT = {"love", "loved", "obsessed", "obsession", "terrifying", "bear", "nikki", "wish", "horrifying",
             "price", "unforgettable", "disturbing", "unpredictable", "genius", "premise", "horror",
             "violence", "control", "possession", "desire", "freedom"}
