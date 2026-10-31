from io import BytesIO

from PIL import Image

from custom_components.covermood.colors import (
    Hs,
    analyse,
    measure,
    pick_points,
    load_cover,
    palette_from_pixels,
    regions_from_pixels,
    spread,
    tune,
    zones_from_pixels,
)


def solid(rgb, count=100):
    return [(*rgb, 255)] * count


RED, GREEN, BLUE = (230, 30, 30), (30, 230, 30), (30, 30, 230)


def test_palette_picks_dominant_hues_strongest_first():
    pal = palette_from_pixels(solid(RED, 50) + solid(GREEN, 30) + solid(BLUE, 10), 3)
    assert [round(c.h / 120) for c in pal] == [0, 1, 2]


def test_palette_pads_to_requested_count():
    pal = palette_from_pixels(solid(RED), 5)
    assert len(pal) == 5
    assert [c.h for c in pal[1:3]] == [pal[0].h + 25, pal[0].h + 50]


def test_palette_grey_and_empty():
    assert palette_from_pixels(solid((128, 128, 128)), 3) == [Hs(0, 0)] * 3
    assert palette_from_pixels([(255, 0, 0, 0)] * 10, 3) == []  # komplett durchsichtig


def test_zones_follow_left_to_right():
    size = 4
    row = solid(RED, 2) + solid(BLUE, 2)
    zones = zones_from_pixels(row * size, size, 2)
    assert round(zones[0].h) == 0 and round(zones[1].h) == 240
    assert zones_from_pixels(solid((128, 128, 128), 16), 4, 2) == []


def test_spread_linear_and_cyclic():
    pal = [Hs(0, 1), Hs(120, 1)]
    assert spread(pal, 3) == [Hs(0, 1), Hs(60, 1), Hs(120, 1)]
    assert spread(pal, 2, cyclic=True) == [Hs(0, 1), Hs(120, 1)]
    assert spread(pal, 2, offset=0.5, cyclic=True) == [Hs(120, 1), Hs(0, 1)]  # halber Ring weiter
    assert spread(pal, 1) == [Hs(0, 1)]


def test_hue_blends_over_shortest_way():
    mid = spread([Hs(350, 1), Hs(10, 1)], 3)[1]
    assert min(mid.h, 360 - mid.h) < 1e-6  # über 0°, nicht über 180°


def test_tune_keeps_grey_grey():
    assert tune(Hs(40, 0.0), 1.3, 0.7) == Hs(40, 0.0)
    assert tune(Hs(40, 0.5), 1.3, 0.7) == Hs(40, 0.7)
    assert tune(Hs(40, 0.9), 1.3, 0.0).s == 1.0
    assert tune(Hs(40, 0.9), 0.5, 0.0, cap=0.3).s == 0.3  # Pastell deckelt


def test_analyse_png_bytes():
    buf = BytesIO()
    Image.new("RGB", (200, 200), RED).save(buf, "PNG")
    pixels, thumb = load_cover(buf.getvalue())
    pal = analyse(pixels, 3, "palette")
    assert len(pal) == 3 and round(pal[0].color.h) == 0
    assert thumb[:2] == b"\xff\xd8"  # JPEG für den Editor


def test_dark_background_does_not_drown_the_colorful_spot():
    # Dunkles Foto: gleich viele Pixel dunkles Violett und Himmelblau. Das Blau ist gemeint und muss deutlich
    # überwiegen (mit der alten HSL-Gewichtung lag der Farbton bei ca. 234°, jetzt bei ca. 221°).
    dark_purple, sky = (80, 40, 70), (100, 160, 255)
    pixels = solid(dark_purple, 50) + solid(sky, 50)
    (region,) = regions_from_pixels(pixels, 10, [(0, 0, 1, 1)])
    assert abs(region.h - 217) < 8
    assert abs(palette_from_pixels(pixels, 1)[0].h - 217) < 8


def test_regions_measure_their_own_area():
    size = 4
    pixels = (solid(RED, 2) + solid(BLUE, 2)) * size  # links rot, rechts blau
    left, right = regions_from_pixels(pixels, size, [(0, 0, 0.5, 1), (0.5, 0, 0.5, 1)])
    assert round(left.h) == 0 and round(right.h) == 240
    (corner,) = regions_from_pixels(pixels, size, [(0.75, 0, 0.25, 0.5)])  # nur oben rechts
    assert round(corner.h) == 240
    (grey,) = regions_from_pixels(solid((128, 128, 128), 16), 4, [(0, 0, 1, 1)])
    assert grey[:2] == (0, 0)  # hell, aber ohne Farbe → weiß


BLACK = (5, 5, 5)


def test_black_region_is_not_a_colour_but_grey_is():
    row = solid(BLACK, 2) + solid(RED, 2)
    black, red = measure(row * 4, 4, [(0, 0, 0.5, 1), (0.5, 0, 0.5, 1)])
    assert black is None and round(red.h) == 0
    assert measure(solid(BLACK, 16), 4, [(0, 0, 1, 1)]) == [None]


def test_brightness_of_the_measured_region_is_kept():
    dim, bright = measure(solid((100, 20, 20), 8) + solid((255, 40, 40), 8), 4, [(0, 0, 1, 0.5), (0, 0.5, 1, 0.5)])
    assert dim.v < 0.5 < bright.v


def test_spots_fall_back_to_the_next_then_to_the_cover():
    # Links schwarz, Mitte rot, rechts schwarz; oben schwarz, unten blau
    size = 4
    row = solid(BLACK, 1) + solid(RED, 2) + solid(BLACK, 1)
    pixels = row * 2 + solid(BLUE, 8)
    spots = [
        [(0, 0, 0.25, 0.5), (0.25, 0, 0.5, 0.5)],  # Hauptpunkt schwarz → Ersatz rot
        [(0, 0, 0.25, 0.5), (0.75, 0, 0.25, 0.5)],  # beide schwarz → Farbe aus dem Cover
        [(0.25, 0, 0.5, 0.5), (0, 0, 0.25, 0.5)],  # Hauptpunkt rot, Ersatz bleibt unbenutzt
    ]
    first, second, third = pick_points(pixels, size, spots)
    assert first.used == 1 and round(first.color.h) == 0
    assert second.used == -1 and second.color.s > 0.5  # irgendeine prägende Farbe (Rot oder Blau)
    assert third.used == 0
    assert pick_points(solid(BLACK, 16), size, spots[:1]) == [(None, -1)]  # ganz dunkles Cover → nichts
