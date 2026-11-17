# IMDb Top 10: Where Were They Filmed? (YouTube video, not a Short)

- **Video:** `imdb_top10_filming_locations.mp4` (1920x1080 landscape, 60 fps, 1:00, H.264 + AAC 256k)
- **No voice and no music.** The audio is sound design only (`sfx.py`):
  - a whoosh for every camera flight, panned in the direction of travel
  - a thump, click and chime for each pin drop, rising in pitch toward #1 and panned to the pin's position
  - ticks while the rating counts up, ending on a "ding"
  - swishes as the info card slides in and out
  - for #1: a drumroll, an impact, a crash and confetti sparkles
  - a soft chord at the end
- **Flow:** world-map intro, then a countdown from #10 to #1. For each film the camera zooms out, flies along a dashed arc and zooms in, the pins drop, the filming countries light up gold, and a card shows the rank, title, year, a counting IMDb rating with a bar, and the filming locations. #1 gets a pull-out to the whole world, a drumroll, a dive to Ohio, a flash and confetti. The ending shows every location on the world map next to a ranked list.

## Data
Rankings and ratings come from the **IMDb Top 250 snapshot of 27 September 2025**, the most recent list I could verify. imdb.com can't be reached from this environment, and the top 10 can change, so check it against the live chart before uploading.

| # | Film | Rating | Main filming locations shown |
|---|---|---|---|
| 1 | The Shawshank Redemption (1994) | 9.3 | Ohio State Reformatory, Mansfield, Ohio; Sandy Point, St. Croix, US Virgin Islands (the "Zihuatanejo" ending) |
| 2 | The Godfather (1972) | 9.2 | New York City; Los Angeles; Savoca, Sicily |
| 3 | The Dark Knight (2008) | 9.1 | Chicago; Hong Kong |
| 4 | The Godfather Part II (1974) | 9.0 | Lake Tahoe; New York City; Santo Domingo, Dominican Republic (as Havana); Savoca, Sicily; Trieste |
| 5 | 12 Angry Men (1957) | 9.0 | New York City |
| 6 | LOTR: The Return of the King (2003) | 9.0 | Mount Ruapehu; Wellington; Twizel (New Zealand) |
| 7 | Schindler's List (1993) | 9.0 | Kraków; Oświęcim (Poland) |
| 8 | LOTR: The Fellowship of the Ring (2001) | 8.9 | Matamata (Hobbiton); Wellington; Queenstown (New Zealand) |
| 9 | Pulp Fiction (1994) | 8.8 | Los Angeles |
| 10 | The Good, the Bad and the Ugly (1966) | 8.8 | Tabernas Desert, Almería; Sad Hill Cemetery, Burgos (Spain); Rome studios (Italy) |

Map: Natural Earth 1:50m countries (public domain), Miller projection.

## Upload text
**Title:** Where Were IMDb's Top 10 Movies Filmed? 🌍 (World Map)

**Description:**
From Spain's deserts to New Zealand's volcanoes: the real filming locations of IMDb's 10 highest-rated movies, counted down on a world map to #1. Which location surprised you most? 👇
Ratings: IMDb Top 250 (snapshot 27 Sep 2025). Map data: Natural Earth.

#imdb #movies #filmlocations #shawshankredemption #thegodfather #thedarkknight #lordoftherings #map

## Rebuild
```bash
python3 sfx.py sfx.wav
python3 render.py sfx.wav imdb_top10_filming_locations.mp4      # about 8 min on 4 cores
python3 render.py sfx.wav x.mp4 --stills 5,20,52                  # preview frames
```
