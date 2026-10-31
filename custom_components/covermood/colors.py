"""Farben aus dem Cover – reine Funktionen ohne Home Assistant.

Port von cover.ts (Ambiframe), aber mit frei wählbarer Punktzahl und einem Farbverlauf über beliebig viele Lichter.
"""

from __future__ import annotations

import colorsys
import math
from collections.abc import Iterable, Sequence
from io import BytesIO
from typing import NamedTuple

from .const import SOURCE_REGIONS, SOURCE_ZONES

SIZE = 64  # Kantenlänge, auf die das Cover zum Messen verkleinert wird
BUCKETS = 24  # Farbtöne in 15°-Eimern
MIN_LIT = 0.2  # so viel Anteil heller Pixel braucht ein Bereich, um nicht als „schwarz“ zu gelten

Pixel = tuple[int, int, int, int]
Rect = tuple[float, float, float, float]  # links, oben, Breite, Höhe – Bruchteile des Bildes (0..1)


class Hs(NamedTuple):
    h: float  # Grad, 0..360
    s: float  # 0..1
    v: float = 1.0  # Helligkeit im Cover, 0..1 – nur für „Helligkeit folgt Cover“


class Pick(NamedTuple):
    color: Hs | None  # None: im ganzen Cover nichts Helles
    used: int  # welcher Bereich des Lichts zählte (0 = Hauptpunkt); -1 = alle zu dunkel, Ersatz aus dem Cover


def _weight(s: float, v: float) -> float:
    """Wie stark ein Pixel für die Farbe zählt: kräftig und hell. Sonst übertönen cremefarbene oder dunkle Flächen
    die bunten Stellen, auf die es ankommt."""
    return (s * v) ** 2


def _hue_dist(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def palette_from_pixels(pixels: Iterable[Pixel], n: int) -> list[Hs]:
    """Bis zu n prägende Farbtöne (kräftigste zuerst); fehlende werden aus verschobenen Varianten aufgefüllt."""
    buckets = [[0.0] * 4 for _ in range(BUCKETS)]  # Gewicht, h*Gewicht, s*Gewicht, v*Gewicht
    grey = 0
    for r, g, b, a in pixels:
        if a < 128:
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)  # HSV: so rechnet auch hs_color der Lichter
        h *= 360
        if v < 0.25:  # (fast) schwarz ist keine Farbe und auch nicht „grau“
            continue
        if s < 0.15:
            grey += 1
            continue
        w = _weight(s, v)
        k = buckets[int(h // 15) % BUCKETS]
        k[0] += w
        k[1] += h * w
        k[2] += s * w
        k[3] += v * w
    gap = max(8, min(28, 120 / n))  # je mehr Punkte, desto näher dürfen Töne beieinander liegen
    picked: list[Hs] = []
    for w, hw, sw, vw in sorted((k for k in buckets if k[0] > 0), reverse=True):
        c = Hs(hw / w, sw / w, vw / w)
        if any(_hue_dist(p.h, c.h) < gap for p in picked):
            continue
        picked.append(c)
        if len(picked) == n:
            break
    if not picked:
        return [Hs(0, 0)] * n if grey else []
    found = len(picked)
    while len(picked) < n:
        base = picked[len(picked) % found]
        picked.append(Hs((base.h + 25 * (1 + (len(picked) - found) // found)) % 360, base.s, base.v))
    return picked


def measure(pixels: Iterable[Pixel], size: int, rects: Sequence[Rect]) -> list[Hs | None]:
    """Farbe je Rechteck: Mittel der kräftigen Pixel darin. Der Farbton wird als Vektor gemittelt,
    damit 350° und 10° nicht bei 180° landen. Ein Rechteck ohne Farbe wird weiß/grau; ein (fast) schwarzes
    Rechteck – weniger als MIN_LIT helle Pixel – liefert None."""
    acc = [[0.0] * 8 for _ in rects]  # x, y (Farbton als Vektor), s*w, v*w, w, Summe v heller Pixel, Zahl heller, Zahl aller
    for i, (r, g, b, a) in enumerate(pixels):
        if a < 128:
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        px, py = ((i % size) + 0.5) / size, ((i // size) + 0.5) / size
        for z, (x, y, rw, rh) in zip(acc, rects):
            if not (x <= px < x + rw and y <= py < y + rh):
                continue
            z[7] += 1
            if v < 0.25:
                continue
            z[5] += v
            z[6] += 1
            if s < 0.05:
                continue
            w = _weight(s, v)
            z[0] += w * math.cos(h * math.tau)
            z[1] += w * math.sin(h * math.tau)
            z[2] += w * s
            z[3] += w * v
            z[4] += w
    return [
        None
        if not z[7] or z[6] / z[7] < MIN_LIT
        else Hs(math.degrees(math.atan2(z[1], z[0])) % 360, z[2] / z[4], z[3] / z[4])
        if z[4]
        else Hs(0, 0, z[5] / z[6])
        for z in acc
    ]


def regions_from_pixels(pixels: Iterable[Pixel], size: int, rects: Sequence[Rect]) -> list[Hs]:
    """Wie measure, aber ein dunkles Rechteck wird grau statt None."""
    return [c or Hs(0, 0) for c in measure(pixels, size, rects)]


def pick_points(pixels: Sequence[Pixel], size: int, lights_rects: Sequence[Sequence[Rect]]) -> list[Pick]:
    """Je Licht die Farbe seines ersten hellen Bereichs (Hauptpunkt, dann die Ersatzpunkte der Reihe nach).
    Ist keiner hell genug, bekommt das Licht eine prägende Farbe des ganzen Covers."""
    flat = measure(pixels, size, [r for rects in lights_rects for r in rects])
    fallback = palette_from_pixels(pixels, len(lights_rects))
    picks, at = [], 0
    for i, rects in enumerate(lights_rects):
        found = flat[at : at + len(rects)]
        at += len(rects)
        k = next((k for k, c in enumerate(found) if c), None)
        if k is not None:
            picks.append(Pick(found[k], k))
        else:
            picks.append(Pick(fallback[i % len(fallback)] if fallback else None, -1))
    return picks


def zones_from_pixels(pixels: Iterable[Pixel], size: int, n: int) -> list[Hs]:
    """Farbe je senkrechtem Streifen (links → rechts); [] bei einem Cover ganz ohne Farbe."""
    colors = regions_from_pixels(pixels, size, [(i / n, 0.0, 1 / n, 1.0) for i in range(n)])
    return colors if any(c.s for c in colors) else []


def load_cover(data: bytes) -> tuple[list[Pixel], bytes]:
    """Cover-Bytes (jedes Format, das Pillow kennt) → (SIZE×SIZE RGBA-Pixel zeilenweise, kleines JPEG für den Editor)."""
    from PIL import Image  # liefert Home Assistant selbst mit

    img = Image.open(BytesIO(data))
    img.draft("RGB", (SIZE * 4, SIZE * 4))  # JPEGs gleich verkleinert lesen
    rgba = img.convert("RGBA")
    raw = rgba.resize((SIZE, SIZE)).tobytes()  # quadratisch gestaucht: Bruchteile des Bildes bleiben vergleichbar
    thumb = BytesIO()
    rgba.convert("RGB").resize(_fit(rgba.size, 480)).save(thumb, "JPEG", quality=80)
    return list(zip(raw[0::4], raw[1::4], raw[2::4], raw[3::4])), thumb.getvalue()


def _fit(size: tuple[int, int], longest: int) -> tuple[int, int]:
    k = min(1.0, longest / max(size))
    return max(1, round(size[0] * k)), max(1, round(size[1] * k))


def analyse(pixels: Sequence[Pixel], n: int, source: str, lights_rects: Sequence[Sequence[Rect]] = ()) -> list[Pick]:
    """Pixel → Farbpunkte: je Licht seine Bereiche, n Streifen oder n prägende Farbtöne."""
    if source == SOURCE_REGIONS:
        return pick_points(pixels, SIZE, lights_rects)
    colors = zones_from_pixels(pixels, SIZE, n) if source == SOURCE_ZONES else palette_from_pixels(pixels, n)
    return [Pick(c, 0) for c in colors]


def to_hex(c: Hs) -> str:
    return "#%02x%02x%02x" % tuple(round(v * 255) for v in colorsys.hsv_to_rgb(c.h / 360, c.s, 1))


def tune(c: Hs, boost: float, minimum: float, cap: float = 1.0) -> Hs:
    """Sättigung verstärken und in [minimum, cap] halten; echte Graus bleiben grau."""
    if c.s < 0.05:
        return c
    return c._replace(s=min(cap, max(c.s * boost, minimum)))


def lerp(a: Hs, b: Hs, t: float) -> Hs:
    """Mischen auf dem kürzesten Weg über den Farbkreis."""
    d = (b.h - a.h + 180) % 360 - 180
    return Hs((a.h + d * t) % 360, a.s + (b.s - a.s) * t, a.v + (b.v - a.v) * t)


def sample(palette: Sequence[Hs], t: float, cyclic: bool) -> Hs:
    """Farbe an Stelle t des Verlaufs; zyklisch läuft der Verlauf als Ring (für wandernde Farben)."""
    n = len(palette)
    if n == 1:
        return palette[0]
    if cyclic:
        pos = (t % 1.0) * n
        i = int(pos) % n
        return lerp(palette[i], palette[(i + 1) % n], pos - int(pos))
    pos = min(max(t, 0.0), 1.0) * (n - 1)
    i = min(int(pos), n - 2)
    return lerp(palette[i], palette[i + 1], pos - i)


def spread(palette: Sequence[Hs], count: int, offset: float = 0.0, cyclic: bool = False) -> list[Hs]:
    """Farbverlauf über count Lichter; offset verschiebt den Ring (nur zyklisch)."""
    if cyclic:
        return [sample(palette, i / count + offset, True) for i in range(count)]
    return [sample(palette, i / (count - 1) if count > 1 else 0.0, False) for i in range(count)]
