"""IMDb Top 10 (IMDb Top 250 snapshot of 27 September 2025) and main filming locations.

Each location: (label, latitude, longitude, Natural Earth country name to highlight).
"""
SNAPSHOT = "IMDb Top 250 · snapshot of 27 Sep 2025"

FILMS = [  # rank 10 -> 1 (shown in this order)
    (10, "The Good, the Bad and the Ugly", 1966, 8.8, [
        ("Tabernas Desert, Almería", 37.05, -2.39, "Spain"),
        ("Sad Hill Cemetery, Burgos", 41.99, -3.27, "Spain"),
        ("Rome (studio)", 41.85, 12.57, "Italy")]),
    (9, "Pulp Fiction", 1994, 8.8, [
        ("Los Angeles", 34.05, -118.24, "United States of America")]),
    (8, "The Lord of the Rings: The Fellowship of the Ring", 2001, 8.9, [
        ("Matamata (Hobbiton)", -37.87, 175.68, "New Zealand"),
        ("Wellington", -41.29, 174.78, "New Zealand"),
        ("Queenstown", -45.03, 168.66, "New Zealand")]),
    (7, "Schindler's List", 1993, 9.0, [
        ("Kraków", 50.06, 19.94, "Poland"),
        ("Oświęcim", 50.03, 19.20, "Poland")]),
    (6, "The Lord of the Rings: The Return of the King", 2003, 9.0, [
        ("Mount Ruapehu", -39.28, 175.57, "New Zealand"),
        ("Wellington", -41.29, 174.78, "New Zealand"),
        ("Twizel", -44.26, 170.10, "New Zealand")]),
    (5, "12 Angry Men", 1957, 9.0, [
        ("New York City", 40.71, -74.00, "United States of America")]),
    (4, "The Godfather Part II", 1974, 9.0, [
        ("Lake Tahoe", 39.10, -120.03, "United States of America"),
        ("New York City", 40.72, -73.99, "United States of America"),
        ("Santo Domingo (as Havana)", 18.47, -69.89, "Dominican Republic"),
        ("Savoca, Sicily", 37.95, 15.34, "Italy"),
        ("Trieste", 45.65, 13.78, "Italy")]),
    (3, "The Dark Knight", 2008, 9.1, [
        ("Chicago", 41.88, -87.63, "United States of America"),
        ("Hong Kong", 22.28, 114.16, "Hong Kong S.A.R.")]),
    (2, "The Godfather", 1972, 9.2, [
        ("New York City", 40.61, -74.10, "United States of America"),
        ("Los Angeles", 34.07, -118.40, "United States of America"),
        ("Savoca, Sicily", 37.95, 15.34, "Italy")]),
    (1, "The Shawshank Redemption", 1994, 9.3, [
        ("Mansfield, Ohio", 40.78, -82.50, "United States of America"),
        ("St. Croix (as Zihuatanejo)", 17.68, -64.90, "United States Virgin Islands")]),
]
