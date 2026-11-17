"""Shared timing for picture and sound (seconds)."""
from films import FILMS

DUR = 60.0
INTRO = 4.0          # world map + title
STEP = 5.0           # each of #10 .. #2
FLY = 1.4            # camera flight at the start of each entry
PIN0 = 1.25          # first pin drops at this offset
PIN_GAP = 0.28       # gap between pins of the same film
COUNT = (1.45, 2.35)  # rating count-up window
OUT = 4.55           # card slides out
ONE_START = INTRO + STEP * 9          # 49.0
ONE_DIVE = (ONE_START + 1.2, ONE_START + 2.8)   # world -> Ohio
ONE_HIT = ONE_START + 2.8             # 51.8 impact
OUTRO = 56.0


def entries():
    """[(start, film)] in play order (#10 first)."""
    out = []
    for i, f in enumerate(FILMS):
        out.append((INTRO + STEP * i if f[0] != 1 else ONE_START, f))
    return out


def pin_times(start, film):
    if film[0] == 1:
        return [ONE_HIT, ONE_HIT + 1.9]
    return [start + PIN0 + PIN_GAP * k for k in range(len(film[4]))]


def count_window(start, film):
    if film[0] == 1:
        return (ONE_HIT + 0.35, ONE_HIT + 1.45)
    return (start + COUNT[0], start + COUNT[1])
