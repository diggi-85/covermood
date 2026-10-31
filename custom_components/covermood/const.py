"""Konstanten für Covermood."""

DOMAIN = "covermood"
SUBENTRY_ROOM = "room"

CONF_AREA = "area"
CONF_PLAYERS = "players"
CONF_LIGHTS = "lights"  # Reihenfolge = Richtung des Farbverlaufs
CONF_MODE = "mode"
CONF_SOURCE = "source"
CONF_POINTS = "points"
CONF_TURN_ON = "turn_on"
CONF_BRIGHTNESS = "brightness"
CONF_RESTORE = "restore"
CONF_STYLE = "style"  # Farbbehandlung: lebendig, pastell, originalgetreu, intensiv
CONF_MIN_SAT = "min_sat"  # % – darunter wird nie gesättigter gefärbt
CONF_MIN_BRI = "min_bri"  # % – Untergrenze der Helligkeit (nur wenn Covermood die Helligkeit setzt)
CONF_BRI_MODE = "bri_mode"
CONF_FADE = "fade"  # s, überschreibt die Überblendzeit der Stimmung; None = Wert der Stimmung
CONF_EVERY = "every"  # s, überschreibt „Wandern alle …“ der Stimmung; None = Wert der Stimmung
CONF_ONLY_SOURCES = "only_sources"  # nur wenn die Quelle (Attribut „source“) des Players eine dieser ist
CONF_ONLY_WHILE = "only_while"  # nur solange diese Entität „on“ ist
CONF_DRIFT_POINTS = "drift_points"  # eigene Punkte wandern reihum von Lampe zu Lampe
CONF_DEFAULT_COLOR = "default_color"  # [Farbton, Sättigung %] – wird am Ende statt des Wiederherstellens gesetzt

BRI_KEEP = "keep"  # Helligkeit der Lichter bleibt unberührt
BRI_FIXED = "fixed"  # fester Wert (CONF_BRIGHTNESS)
BRI_COVER = "cover"  # folgt der Helligkeit des Covers, zwischen CONF_MIN_BRI und CONF_BRIGHTNESS
BRI_MODES = [BRI_KEEP, BRI_FIXED, BRI_COVER]

SOURCE_PALETTE = "palette"  # prägende Farbtöne des Covers
SOURCE_ZONES = "zones"  # Farbe je senkrechtem Streifen des Covers
SOURCE_REGIONS = "regions"  # je Licht ein Bereich, den der Benutzer im Editor festlegt
SOURCES = [SOURCE_PALETTE, SOURCE_ZONES, SOURCE_REGIONS]
CONF_REGIONS = "regions"  # {Licht: [[links, oben, Breite, Höhe], …]} in Bruchteilen des Covers; erster = Hauptpunkt, Rest = Ersatz

URL_BASE = "/covermood_static"
PANEL_PATH = "covermood"
DATA_REGISTERED = f"{DOMAIN}_registered"  # Statischer Pfad und WebSocket-Befehle nur einmal je HA-Lauf

DEFAULT_MODE = "calm"
DEFAULT_POINTS = 4
DEFAULT_BRIGHTNESS = 60  # % – nur für Lichter, die Covermood selbst einschaltet
DEFAULT_STYLE = "vibrant"
DEFAULT_MIN_SAT = 35
DEFAULT_MIN_BRI = 20
MIN_POINTS, MAX_POINTS = 2, 12
MAX_SPOTS = 5  # Bereiche je Licht: Hauptpunkt + Ersatz

# Pause zwischen zwei Titeln oder kurzes Anhalten soll die Lichter nicht zurücksetzen
GRACE_SECONDS = 30

# So lange liegen die Farben beim „Auf Lichtern testen“ im Editor auf den echten Lichtern
TEST_SECONDS = 10

# Alles, was der Editor ändert, samt Vorgabe für Räume, die es noch nicht gespeichert haben
DEFAULTS: dict[str, object] = {
    CONF_MODE: DEFAULT_MODE,
    CONF_SOURCE: SOURCE_PALETTE,
    CONF_POINTS: DEFAULT_POINTS,
    CONF_TURN_ON: True,
    CONF_BRIGHTNESS: DEFAULT_BRIGHTNESS,
    CONF_RESTORE: True,
    CONF_REGIONS: {},
    CONF_STYLE: DEFAULT_STYLE,
    CONF_MIN_SAT: DEFAULT_MIN_SAT,
    CONF_MIN_BRI: DEFAULT_MIN_BRI,
    CONF_BRI_MODE: BRI_KEEP,
    CONF_FADE: None,
    CONF_EVERY: None,
    CONF_ONLY_SOURCES: [],
    CONF_ONLY_WHILE: None,
    CONF_DEFAULT_COLOR: None,
    CONF_DRIFT_POINTS: False,
}
