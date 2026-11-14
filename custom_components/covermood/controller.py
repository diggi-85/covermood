"""Ein Raum: beobachtet seine Medienplayer und färbt seine Lichter passend zum Cover."""

from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER
from homeassistant.components.media_player import MediaPlayerState
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)

from .colors import Hs, Pick, Pixel, Rect, analyse, load_cover, spread, to_hex, tune
from .const import (
    BRI_FIXED,
    BRI_COVER,
    CONF_BRI_MODE,
    CONF_BRIGHTNESS,
    CONF_CALIBRATION,
    CONF_COVER_SPOTS,
    CONF_DEFAULT_COLOR,
    CONF_DRIFT_POINTS,
    CONF_EVERY,
    CONF_FADE,
    CONF_LIGHTS,
    CONF_MIN_BRI,
    CONF_MIN_SAT,
    CONF_MODE,
    CONF_ONLY_SOURCES,
    CONF_ONLY_WHILE,
    CONF_PATH_PERIOD,
    CONF_PATHS,
    CONF_PLAYERS,
    CONF_POINTS,
    CONF_PRESETS,
    CONF_REGIONS,
    CONF_RESTORE,
    CONF_SOURCE,
    CONF_STYLE,
    CONF_TURN_ON,
    DEFAULT_MODE,
    DEFAULT_STYLE,
    DEFAULTS,
    DOMAIN,
    GRACE_SECONDS,
    MAX_COVER_BYTES,
    MAX_COVER_SPOTS,
    PATH_FRAMES,
    PATH_STEP,
    RESTORE_DELAY,
    RESTORE_TRIES,
    SOURCE_REGIONS,
    TEST_SECONDS,
)
from .memory import Memory
from .modes import MODES, STYLES, Mode

_LOGGER = logging.getLogger(__name__)

# Ändert sich eines davon, müssen die Farben neu aus dem Cover gemessen werden
MEASURE_KEYS = (CONF_SOURCE, CONF_POINTS, CONF_REGIONS, CONF_PATHS, CONF_COVER_SPOTS)
# Ändert sich eines davon, ist neu zu entscheiden, ob Covermood überhaupt färben soll
GATE_KEYS = (CONF_ONLY_SOURCES, CONF_ONLY_WHILE)

type Plan = list[tuple[Hs | None, int | None]]  # je Licht: Farbe (None = auslassen) und Helligkeit in % (None = lassen)


class RoomController:
    """Hört auf die Player eines Raums; spielt einer, färbt er die Lichter nach dem Cover und lässt die Farben wandern."""

    def __init__(self, hass: HomeAssistant, subentry: ConfigSubentry, memory: Memory | None = None) -> None:
        self.hass = hass
        self._memory = memory
        self.id = subentry.subentry_id
        self.name = subentry.title
        self.players: list[str] = list(subentry.data[CONF_PLAYERS])
        self.lights: list[str] = list(subentry.data[CONF_LIGHTS])
        self._saved: dict[str, Any] = dict(subentry.data)  # so liegt der Raum in der Konfiguration (siehe in_sync)
        self.cfg: dict[str, Any] = {**DEFAULTS, **subentry.data}  # alles, was der Editor ändern kann
        if self.cfg[CONF_MODE] not in MODES:
            self.cfg[CONF_MODE] = DEFAULT_MODE
        if self.cfg[CONF_STYLE] not in STYLES:
            self.cfg[CONF_STYLE] = DEFAULT_STYLE
        self.enabled = True
        self.active = False  # Covermood steuert gerade die Lichter dieses Raums
        self.picks: list[Pick] = []
        self.pixels: list[Pixel] | None = None  # zuletzt gelesenes Cover (für Vorschau im Editor)
        self.thumb: bytes | None = None  # dasselbe als kleines JPEG

        self._scene = f"covermood_{self.id.lower()}"  # Schnappschuss der Lichter vor dem Start
        self._snapshotted = False
        self._test_scene = f"covermood_test_{self.id.lower()}"  # Schnappschuss vor einem Test im Editor
        self._test_snapshot = False
        self._unsub_test: CALLBACK_TYPE | None = None
        self._listeners: list[CALLBACK_TYPE] = []
        self._sig: tuple[str, Any, Any] | tuple[()] | None = None  # (Player, Cover, Titel) des laufenden Players
        self._cover: tuple[str, Any] | None = None  # zuletzt ausgewertetes (Player, Cover)
        self._offset = 0.0
        self._phase = 0.0  # wo die pendelnden Punkte gerade stehen: 0 = Start, 0,5 = Ziel, 1 = wieder Start
        self.album: str | None = None  # Schlüssel des laufenden Albums (für eigene Punkte je Album)
        self.album_label: str | None = None
        self._unsub_leftover: CALLBACK_TYPE | None = None
        self._leftover_tries = 0
        self.stopped = False  # dieser Raum ist abgelöst (Neuladen); der Editor soll sich den neuen holen
        self._lock = asyncio.Lock()
        self._unsub_players: CALLBACK_TYPE | None = None
        self._unsub_tick: CALLBACK_TYPE | None = None
        self._unsub_grace: CALLBACK_TYPE | None = None

    # --- Einstellungen ---

    @property
    def mode_key(self) -> str:
        return self.cfg[CONF_MODE]

    @property
    def palette(self) -> list[Hs]:
        """Die gemessenen Farben (ohne Lichter, die nichts bekamen)."""
        return [p.color for p in self.picks if p.color]

    @staticmethod
    def _mode(cfg: dict[str, Any]) -> Mode:
        return MODES[cfg[CONF_MODE]]

    def _fade(self, cfg: dict[str, Any]) -> float:
        return self._mode(cfg).fade if cfg[CONF_FADE] is None else cfg[CONF_FADE]

    def _every(self, cfg: dict[str, Any]) -> float:
        return self._mode(cfg).every if cfg[CONF_EVERY] is None else cfg[CONF_EVERY]

    def _drifts(self, cfg: dict[str, Any]) -> bool:
        """Wandern die Farben? Eigene Punkte gehören fest zu ihrem Licht – außer der Benutzer lässt sie wandern."""
        return self._every(cfg) > 0 and (cfg[CONF_SOURCE] != SOURCE_REGIONS or cfg[CONF_DRIFT_POINTS])

    def spot_cfg(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """Die Einstellungen, wie sie für das laufende Album gelten: hat es eigene Punkte, ersetzen sie die des Raums."""
        own = cfg[CONF_COVER_SPOTS].get(self.album) if self.album else None
        return {**cfg, **own} if own else cfg

    def _moving(self, cfg: dict[str, Any]) -> bool:
        """Pendelt mindestens ein Punkt über das Cover?"""
        return cfg[CONF_SOURCE] == SOURCE_REGIONS and any(cfg[CONF_PATHS].get(e) for e in self.lights)

    def rect_lists(self, cfg: dict[str, Any] | None = None, phase: float = 0.0) -> list[list[Rect]]:
        """Bereiche je Licht (Hauptpunkt zuerst); ohne eigene Wahl ein senkrechter Streifen in Lichter-Reihenfolge.
        Hat ein Licht eine Bahn, steht sein Hauptpunkt je nach phase zwischen Start und Ziel (sanft an- und auslaufend)."""
        cfg = cfg or self.cfg
        regions, paths = cfg[CONF_REGIONS], cfg[CONF_PATHS]
        t = (1 - math.cos(math.tau * phase)) / 2
        n = len(self.lights)
        out: list[list[Rect]] = []
        for i, entity_id in enumerate(self.lights):
            spots = regions.get(entity_id)
            if not spots:
                rects = [(i / n, 0.0, 1 / n, 1.0)]
            elif isinstance(spots[0], int | float):  # Stand vor den Ersatzpunkten: ein einzelnes Rechteck
                rects = [tuple(spots)]
            else:
                rects = [tuple(r) for r in spots]
            if target := paths.get(entity_id):
                rects[0] = tuple(a + (b - a) * t for a, b in zip(rects[0], target, strict=True))
            out.append(rects)
        return out

    def in_sync(self, sub: ConfigSubentry) -> bool:
        """Entspricht die gespeicherte Konfiguration dem, was dieser Raum schon weiß? Dann braucht es kein Neuladen."""
        return sub.title == self.name and dict(sub.data) == self._saved

    def _persist(self, patch: dict[str, Any]) -> None:
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if sub := entry.subentries.get(self.id):
                self._saved = {**sub.data, **patch}
                self.hass.config_entries.async_update_subentry(entry, sub, data=self._saved)
                return

    async def async_configure(self, patch: dict[str, Any], persist: bool = True) -> None:
        """Einstellungen ändern – wirkt sofort auf den laufenden Titel, ohne Neuladen."""
        async with self._lock:
            # Erst unter der Sperre lesen: zwei gleichzeitige Änderungen bauen sonst beide auf dem alten Stand auf
            old = self.cfg
            new = self.cfg = {**old, **patch}
            if self.pixels is not None and any(old[k] != new[k] for k in MEASURE_KEYS):
                self.picks = self._measure_own()
            if self.active and self.palette:
                await self._async_apply(fade=True)
                self._schedule_tick()
        if persist:
            self._persist(patch)
        if any(old[k] != new[k] for k in GATE_KEYS):
            self._track()
            self._sig = ()  # ≠ jede Signatur: Lage neu beurteilen
            await self.async_refresh()
        self._notify()

    @callback
    def add_listener(self, cb: Callable[[], None]) -> CALLBACK_TYPE:
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb)

    def _notify(self) -> None:
        for cb in list(self._listeners):
            cb()

    # --- Lebenszyklus ---

    @callback
    def start(self) -> None:
        self._track()
        self.hass.async_create_task(self.async_refresh())  # es könnte schon etwas laufen
        if self._memory and self._memory.get(self.id):  # Neustart mitten im Lied: Zurücksetzen nachholen
            self._unsub_leftover = async_call_later(self.hass, RESTORE_DELAY, self._restore_leftover)

    async def _restore_leftover(self, _now: datetime) -> None:
        """Läuft nach dem Neustart keine Musik mehr, bekommen die Lichter ihren Zustand von vor der Musik zurück."""
        self._unsub_leftover = None
        async with self._lock:
            if self.active or not (saved := self._memory.get(self.id)):
                return  # spielt wieder: _async_begin hat den gemerkten Zustand übernommen
            missing = [e for e in saved if (st := self.hass.states.get(e)) is None or st.state == STATE_UNAVAILABLE]
            self._leftover_tries += 1
            if missing and self._leftover_tries < RESTORE_TRIES:  # z. B. Matter ist noch nicht verbunden: später wieder
                self._unsub_leftover = async_call_later(self.hass, RESTORE_DELAY, self._restore_leftover)
                return
            if default := self.cfg[CONF_DEFAULT_COLOR]:
                await self._async_paint([(Hs(default[0], default[1] / 100), None)] * len(self.lights), 3, False)
            elif self.cfg[CONF_RESTORE]:
                if await self._call("scene", "create", {"scene_id": self._scene, "entities": saved}):
                    await self._async_restore(self._scene)
            self._memory.pop(self.id)

    def _track(self) -> None:
        if self._unsub_players:
            self._unsub_players()
        watched = [*self.players, *([gate] if (gate := self.cfg[CONF_ONLY_WHILE]) else [])]
        self._unsub_players = async_track_state_change_event(self.hass, watched, self._on_player)

    async def async_stop(self) -> None:
        if self._unsub_players:
            self._unsub_players()
            self._unsub_players = None
        self._cancel_grace()
        if self._unsub_leftover:
            self._unsub_leftover()
            self._unsub_leftover = None
        async with self._lock:
            await self._async_end_test()
            if self.hass.is_stopping:
                # Beim Herunterfahren sind die Lichter oft schon nicht mehr erreichbar. Der Zustand vor der Musik
                # bleibt gemerkt und kommt nach dem Start zurück (siehe _restore_leftover).
                self._cancel_tick()
                return
            await self._async_end()
        self.stopped = True
        self._notify()

    # --- Steuerung von außen (Entitäten) ---

    async def async_set_mode(self, key: str) -> None:
        # Die Stimmung bringt ihre eigene Überblend- und Wanderzeit mit
        await self.async_configure({CONF_MODE: key, CONF_FADE: None, CONF_EVERY: None}, persist=False)

    async def async_apply_preset(self, name: str) -> bool:
        """Eine gespeicherte Vorlage übernehmen; False, wenn der Raum keine dieses Namens hat."""
        if (preset := self.cfg[CONF_PRESETS].get(name)) is None:
            return False
        await self.async_configure(dict(preset))
        return True

    async def async_set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self._cancel_grace()
        if enabled:
            self._sig = None
            await self.async_refresh()
        else:
            async with self._lock:
                self._sig = None
                await self._async_end()
        self._notify()

    # --- Beobachten ---

    def _playing(self) -> State | None:
        only = {s.casefold() for s in self.cfg[CONF_ONLY_SOURCES]}
        for entity_id in self.players:
            st = self.hass.states.get(entity_id)
            if st and st.state == MediaPlayerState.PLAYING:
                if not only or str(st.attributes.get("source", "")).casefold() in only:
                    return st
        return None

    def _gate_open(self) -> bool:
        """Läuft Covermood nur, solange eine Entität an ist – und ist sie es?"""
        gate = self.cfg[CONF_ONLY_WHILE]
        return not gate or ((st := self.hass.states.get(gate)) is not None and st.state == STATE_ON)

    def _signature(self) -> tuple[str, Any, Any] | None:
        st = self._playing() if self.enabled and self._gate_open() else None
        if st is None:
            return None
        return (st.entity_id, st.attributes.get("entity_picture"), st.attributes.get("media_title"))

    def now_playing(self) -> dict[str, Any]:
        """Was der Editor als „läuft gerade“ zeigt."""
        st = self._playing()
        return {
            "enabled": self.enabled,
            "playing": st is not None,
            "player": st.entity_id if st else None,
            "title": st.attributes.get("media_title") if st else None,
            "artist": st.attributes.get("media_artist") if st else None,
            "album": self.album_label,
            "album_spots": self.cfg[CONF_COVER_SPOTS].get(self.album) if self.album else None,
        }

    def _note_album(self, st: State) -> None:
        """Das laufende Album merken – eigene Punkte können an ihm hängen."""
        album = st.attributes.get("media_album_name")
        artist = st.attributes.get("media_album_artist") or st.attributes.get("media_artist") or ""
        self.album = f"{artist}|{album}".casefold() if album else None
        self.album_label = album or None

    def set_album_spots(self, spots: dict[str, Any] | None) -> dict[str, Any]:
        """Eigene Punkte für das laufende Album setzen (None = wieder die des Raums); liefert die neue Sammlung."""
        store = {k: v for k, v in self.cfg[CONF_COVER_SPOTS].items() if k != self.album}
        if spots is not None and self.album:
            store[self.album] = spots
            while len(store) > MAX_COVER_SPOTS:
                store.pop(next(iter(store)))
        return store

    @callback
    def _on_player(self, event: Event[EventStateChangedData]) -> None:
        # Position und Lautstärke ändern ständig Attribute – nur echte Wechsel lösen etwas aus
        if self._signature() != self._sig:
            self.hass.async_create_task(self.async_refresh())

    async def async_refresh(self) -> None:
        async with self._lock:
            sig = self._signature()
            if sig == self._sig:
                return
            self._sig = sig
            self._notify()
            if sig is None:
                if self.active:
                    if not self._gate_open():  # Schalter aus: sofort Schluss, keine Schonfrist
                        self._cancel_grace()
                        await self._async_end()
                    elif self._unsub_grace is None:
                        self._unsub_grace = async_call_later(self.hass, GRACE_SECONDS, self._grace_expired)
                return
            self._cancel_grace()
            changed = False
            had = self.album
            if st := self.hass.states.get(sig[0]):
                self._note_album(st)
            if self.album != had and self.pixels is not None and self._cover == sig[:2]:
                self.picks, changed = self._measure_own(), True  # gleiches Bild, anderes Album: dessen Punkte gelten
            if self._cover != sig[:2]:  # anderes Cover → neu auswerten; gleiches Cover bei neuem Titel nicht
                self._cover = sig[:2]
                picks = await self._async_measure(sig[0])
                if any(p.color for p in picks) and picks != self.picks:
                    self.picks, self._offset, self._phase, changed = picks, 0.0, 0.0, True
                    self._notify()
            if not self.palette:  # noch nie ein lesbares Cover: Lichter in Ruhe lassen
                return
            if not self.active:
                await self._async_begin()
                await self._async_apply(fade=True, switch_on=True)
            elif changed:
                await self._async_apply(fade=True)
            self._schedule_tick()

    async def _grace_expired(self, _now: datetime) -> None:
        self._unsub_grace = None
        async with self._lock:
            if self._sig is None:
                await self._async_end()

    def _cancel_grace(self) -> None:
        if self._unsub_grace:
            self._unsub_grace()
            self._unsub_grace = None

    # --- Cover → Farben ---

    async def _async_load(self, entity_id: str) -> bool:
        """Cover des Players holen und merken (Pixel zum Messen, JPEG für den Editor)."""
        try:
            if data := await self._async_cover_bytes(entity_id):
                self.pixels, self.thumb = await self.hass.async_add_executor_job(load_cover, data)
                self._notify()  # der Editor zeigt das neue Cover sofort
                return True
        except Exception:  # noqa: BLE001 – unlesbares Bild oder Netzwerkfehler: Cover auslassen
            _LOGGER.debug("Cover of %s is not readable", entity_id, exc_info=True)
        return False

    def _measure(self, cfg: dict[str, Any], phase: float = 0.0) -> list[Pick]:
        if self.pixels is None:
            return []
        return analyse(self.pixels, int(cfg[CONF_POINTS]), cfg[CONF_SOURCE], self.rect_lists(cfg, phase))

    def _measure_own(self) -> list[Pick]:
        """Messen, wie es für den laufenden Titel gilt: Punkte des Albums, Stand der pendelnden Punkte."""
        return self._measure(self.spot_cfg(self.cfg), self._phase)

    async def _async_measure(self, entity_id: str) -> list[Pick]:
        return self._measure_own() if await self._async_load(entity_id) else []

    async def async_cover(self) -> bytes | None:
        """Cover für den Editor. Liegt noch keins vor, kommt es vom ersten Player des Raums, der eines hat –
        auch wenn er gerade pausiert oder im Leerlauf ist."""
        if self.thumb is None:
            async with self._lock:
                for entity_id in self.players:
                    st = self.hass.states.get(entity_id)
                    if st and st.attributes.get("entity_picture") and await self._async_load(entity_id):
                        break
        return self.thumb

    async def _async_cover_bytes(self, entity_id: str) -> bytes | None:
        # Der Player selbst holt das Bild so, wie er es auch seiner Oberfläche gibt – das gilt für jeden Musikdienst
        if player := self.hass.data[MEDIA_PLAYER].get_entity(entity_id):
            if data := (await player.async_get_media_image())[0]:
                return data
        url = (self.hass.states.get(entity_id) or State(entity_id, "")).attributes.get("entity_picture")
        if url and url.startswith("http"):
            async with async_get_clientsession(self.hass).get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200 and (resp.content_length or 0) <= MAX_COVER_BYTES:
                    data = await resp.content.read(MAX_COVER_BYTES + 1)
                    return data if len(data) <= MAX_COVER_BYTES else None
        return None

    # --- Farben → Lichter ---

    def _plan(self, cfg: dict[str, Any], picks: list[Pick], offset: float = 0.0) -> Plan:
        """Endfarbe und Helligkeit je Licht: Stil, Mindestsättigung, Verlauf."""
        style = STYLES[cfg[CONF_STYLE]]
        min_sat = cfg[CONF_MIN_SAT] / 100

        def finish(c: Hs) -> Hs:
            return tune(tune(c, style.boost, style.floor, style.cap), 1.0, min_sat)

        if cfg[CONF_SOURCE] == SOURCE_REGIONS:
            colors = [finish(p.color) if p.color else None for p in picks]
            if self._drifts(cfg) and (ring := [c for c in colors if c]):  # jede Lampe läuft reihum über alle Farben
                colors = spread(ring, len(self.lights), offset, cyclic=True)
        elif picks:
            colors = spread([finish(p.color) for p in picks if p.color], len(self.lights), offset, self._drifts(cfg))
        else:
            colors = [None] * len(self.lights)
        return [(c, self._brightness(cfg, c) if c else None) for c in colors]

    @staticmethod
    def _brightness(cfg: dict[str, Any], c: Hs) -> int | None:
        top = cfg[CONF_BRIGHTNESS]
        if cfg[CONF_BRI_MODE] == BRI_FIXED:
            return top
        if cfg[CONF_BRI_MODE] == BRI_COVER:
            low = min(cfg[CONF_MIN_BRI], top)  # nie dunkler als die Untergrenze
            return round(low + (top - low) * c.v)
        return None

    def preview(self, patch: dict[str, Any]) -> list[dict[str, Any]]:
        """Was die Lichter mit diesen (noch ungespeicherten) Einstellungen bekämen – für den Editor."""
        cfg = {**self.cfg, **patch}
        picks = self._measure(cfg)
        used = [p.used for p in picks] if cfg[CONF_SOURCE] == SOURCE_REGIONS else [0] * len(self.lights)
        out = [
            {"color": to_hex(c) if c else None, "bri": bri, "used": u}
            for (c, bri), u in zip(self._plan(cfg, picks), used, strict=True)
        ]
        if self._moving(cfg):  # Farben entlang der Bahn (Start → Ziel), damit der Editor die Bewegung abspielen kann
            still = {**cfg, CONF_DRIFT_POINTS: False}
            frames = [self._plan(still, self._measure(still, k / (2 * (PATH_FRAMES - 1)))) for k in range(PATH_FRAMES)]
            for i, entity_id in enumerate(self.lights):
                if cfg[CONF_PATHS].get(entity_id):
                    out[i]["track"] = [to_hex(f[i][0]) if f[i][0] else None for f in frames]
        return out

    async def _async_begin(self) -> None:
        await self._async_end_test()  # sonst würde der Schnappschuss die Testfarben festhalten
        saved = self._memory.get(self.id) if self._memory else None
        if saved is None and self._memory:
            self._memory.put(self.id, self._light_states())
        if self.cfg[CONF_RESTORE]:
            # Nach einem Neustart mitten im Lied stehen die Lichter schon in Cover-Farben – dann zählt der gemerkte Zustand
            what = {"entities": saved} if saved else {"snapshot_entities": self.lights}
            self._snapshotted = await self._call("scene", "create", {"scene_id": self._scene, **what})
        self.active = True
        self._notify()

    async def _async_end(self) -> None:
        self._cancel_tick()
        if not self.active:
            return
        self.active = False
        if default := self.cfg[CONF_DEFAULT_COLOR]:  # eine Standardfarbe ersetzt das Wiederherstellen
            await self._async_paint([(Hs(default[0], default[1] / 100), None)] * len(self.lights), 3, False)
        if self._snapshotted:
            self._snapshotted = False
            await self._async_restore(self._scene, recall=not default)
        if self._memory:
            self._memory.pop(self.id)
        self._notify()

    def _light_states(self) -> dict[str, dict[str, Any]]:
        """Zustand der Lichter in der Form, die scene.create versteht – übersteht einen Neustart."""
        out: dict[str, dict[str, Any]] = {}
        for entity_id in self.lights:
            st = self.hass.states.get(entity_id)
            if st is None or st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                continue
            light: dict[str, Any] = {"state": st.state}
            if st.state == STATE_ON:
                if (brightness := st.attributes.get("brightness")) is not None:
                    light["brightness"] = brightness
                if st.attributes.get("color_mode") == "color_temp" and st.attributes.get("color_temp_kelvin"):
                    light["color_temp_kelvin"] = st.attributes["color_temp_kelvin"]
                elif hs := st.attributes.get("hs_color"):
                    light["hs_color"] = list(hs)
            out[entity_id] = light
        return out

    async def _async_restore(self, scene_id: str, recall: bool = True) -> None:
        scene = {ATTR_ENTITY_ID: f"scene.{scene_id}"}
        if recall:
            await self._call("scene", "turn_on", {**scene, "transition": 3})
        await self._call("scene", "delete", scene)

    async def _async_apply(self, fade: bool, switch_on: bool = False) -> None:
        """Verlauf auf die Lichter legen. Aus-Lichter nur beim Start einschalten – wer sie danach ausmacht, behält recht."""
        cfg = self.cfg
        plan = self._plan(cfg, self.picks, self._offset)
        await self._async_paint(plan, self._fade(cfg) if fade else self._every(cfg), switch_on)

    async def _async_paint(
        self, plan: Plan, transition: float, switch_on: bool, cfg: dict[str, Any] | None = None
    ) -> None:
        calibration = (cfg or self.cfg)[CONF_CALIBRATION]
        for entity_id, (c, bri) in zip(self.lights, plan, strict=True):
            st = self.hass.states.get(entity_id)
            if c is None or st is None or st.state == STATE_UNAVAILABLE:
                continue
            if shift := calibration.get(entity_id):  # dieses Leuchtmittel zeigt Farben anders als die anderen
                c = c._replace(h=(c.h + shift[0]) % 360, s=min(1.0, c.s * shift[1] / 100))
            data: dict[str, Any] = {
                ATTR_ENTITY_ID: entity_id,
                "hs_color": [round(c.h, 1), round(c.s * 100, 1)],
                "transition": transition,
            }
            if bri is not None:
                data["brightness_pct"] = bri
            if st.state != STATE_ON:
                if not (switch_on and self.cfg[CONF_TURN_ON]):
                    continue
                data.setdefault("brightness_pct", self.cfg[CONF_BRIGHTNESS])
            await self._call("light", "turn_on", data, blocking=False)

    def _tick_seconds(self, cfg: dict[str, Any]) -> float:
        """Abstand der Schritte: pendelnde Punkte brauchen einen engen Takt, wandernde Farben den des Benutzers."""
        if self._moving(self.spot_cfg(cfg)):
            return PATH_STEP
        return self._every(cfg) if self._drifts(cfg) else 0

    def _schedule_tick(self) -> None:
        self._cancel_tick()
        if self.active and (seconds := self._tick_seconds(self.cfg)):
            self._unsub_tick = async_track_time_interval(self.hass, self._on_tick, timedelta(seconds=seconds))

    def _cancel_tick(self) -> None:
        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None

    async def _on_tick(self, _now: datetime) -> None:
        async with self._lock:
            if not (self.active and self.palette):
                return
            cfg = self.cfg
            step = self._tick_seconds(cfg)
            if self._moving(self.spot_cfg(cfg)):
                self._phase = (self._phase + step / cfg[CONF_PATH_PERIOD]) % 1.0
                # Läuft ein Punkt durch eine schwarze Stelle, behält das Licht seine letzte Farbe
                self.picks = [
                    old if new.used == -1 and old.color else new
                    for old, new in zip(self.picks, self._measure_own(), strict=True)
                ]
            if self._drifts(cfg):
                self._offset = (self._offset + self._mode(cfg).shift * step / self._every(cfg)) % 1.0
            await self._async_paint(self._plan(cfg, self.picks, self._offset), step, False)

    async def async_test(self, patch: dict[str, Any]) -> None:
        """Die Farben dieser (ungespeicherten) Einstellungen kurz auf die echten Lichter legen (Editor); danach kehren
        sie zurück. Läuft gerade Musik, gehen sie zu deren Farben zurück, sonst in ihren früheren Zustand."""
        cfg = {**self.cfg, **patch}
        plan = self._plan(cfg, self._measure(cfg))
        async with self._lock:
            if self._unsub_test:  # läuft schon: Schnappschuss behalten, nur Frist verlängern
                self._unsub_test()
            elif not self.active:
                self._test_snapshot = await self._call(
                    "scene", "create", {"scene_id": self._test_scene, "snapshot_entities": self.lights}
                )
            await self._async_paint(plan, 1.0, switch_on=not self.active, cfg=cfg)
            self._unsub_test = async_call_later(self.hass, TEST_SECONDS, self._test_over)

    async def _test_over(self, _now: datetime) -> None:
        self._unsub_test = None
        async with self._lock:
            if self.active and self.palette:
                await self._async_apply(fade=True)
            await self._async_end_test()

    async def _async_end_test(self) -> None:
        if self._unsub_test:
            self._unsub_test()
            self._unsub_test = None
        if self._test_snapshot:
            self._test_snapshot = False
            await self._async_restore(self._test_scene)

    async def _call(self, domain: str, service: str, data: dict[str, Any], blocking: bool = True) -> bool:
        try:
            await self.hass.services.async_call(domain, service, data, blocking=blocking)
        except Exception:  # noqa: BLE001 – ein defektes Licht darf die anderen nicht aufhalten
            _LOGGER.warning("%s.%s failed: %s", domain, service, data, exc_info=True)
            return False
        return True
