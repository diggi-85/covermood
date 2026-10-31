"""Stimmungen (Bewegung) und Stile (Farbbehandlung).

Neue Stimmung = ein Eintrag in MODES + eine Zeile in translations/*.json (selector.mode, entity.select.mode)
und im Editor (T.modes in frontend/covermood-panel.js). Ein neuer Stil: ein Eintrag in STYLES + T.styles im Editor.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Mode:
    fade: float  # Sekunden, in denen ein neues Cover einblendet
    every: float  # Sekunden zwischen zwei Wanderschritten; 0 = Farben stehen still
    shift: float  # Bruchteil des Farbrings, den die Farben je Schritt weiterwandern


@dataclass(frozen=True)
class Style:
    boost: float  # Sättigung × Faktor
    floor: float  # Mindestsättigung des Stils
    cap: float  # Höchstsättigung des Stils


MODES: dict[str, Mode] = {
    "calm": Mode(fade=6, every=30, shift=0.06),
    "static": Mode(fade=4, every=0, shift=0),
    "party": Mode(fade=0.5, every=2, shift=0.12),
}

STYLES: dict[str, Style] = {
    "vibrant": Style(boost=1.3, floor=0.6, cap=1.0),
    "pastel": Style(boost=0.5, floor=0.12, cap=0.45),
    "faithful": Style(boost=1.0, floor=0.0, cap=1.0),
    "intense": Style(boost=1.7, floor=0.85, cap=1.0),
}
