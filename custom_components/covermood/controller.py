"""Ein Raum: beobachtet seine Medienplayer und färbt seine Lichter passend zum Cover."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER
from homeassistant.components.media_player import MediaPlayerState
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON, STATE_UNAVAILABLE
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
    CONF_PLAYERS,
    CONF_POINTS,
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
    SOURCE_REGIONS,
    TEST_SECONDS,
)
from .modes import MODES, STYLES, Mode

_LOGGER = logging.getLogger(__name__)

# Ändert sich eines davon, müssen die Farben neu aus dem Cover gemessen werden
MEASURE_KEYS = (CONF_SOURCE, CONF_POINTS, CONF_REGIONS)
# Ändert sich eines davon, ist neu zu entscheiden, ob Covermood überhaupt färben soll
GATE_KEYS = (CONF_ONLY_SOURCES, CONF_ONLY_WHILE)

type Plan = list[tuple[Hs | None, int | None]]  # je Licht: Farbe (None = auslassen) und Helligkeit in % (None = lassen)


class RoomController:
    """Hört auf die Player eines Raums; spielt einer, färbt er die Lichter nach dem Cover und lässt die Farben wandern."""

    def __init__(self, hass: HomeAssistant, subentry: ConfigSubentry) -> None:
        self.hass = hass
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

    def rect_lists(self, cfg: dict[str, Any] | None = None) -> list[list[Rect]]:
        """Bereiche je Licht (Hauptpunkt zuerst); ohne eigene Wahl ein senkrechter Streifen in Lichter-Reihenfolge."""
        regions = (cfg or self.cfg)[CONF_REGIONS]
        n = len(self.lights)
        out: list[list[Rect]] = []
        for i, entity_id in enumerate(self.lights):
            spots = regions.get(entity_id)
            if not spots:
                out.append([(i / n, 0.0, 1 / n, 1.0)])
            elif isinstance(spots[0], int | float):  # Stand vor den Ersatzpunkten: ein einzelnes Rechteck
                out.append([tuple(spots)])
            else:
                out.append([tuple(r) for r in spots])
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
        old = self.cfg
        new = {**old, **patch}
        async with self._lock:
            self.cfg = new
            if self.pixels is not None and any(old[k] != new[k] for k in MEASURE_KEYS):
                self.picks = self._measure(new)
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
        async with self._lock:
            await self._async_end_test()
            await self._async_end()

    # --- Steuerung von außen (Entitäten) ---

    async def async_set_mode(self, key: str) -> None:
        # Die Stimmung bringt ihre eigene Überblend- und Wanderzeit mit
        await self.async_configure({CONF_MODE: key, CONF_FADE: None, CONF_EVERY: None}, persist=False)

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
        }

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
            if self._cover != sig[:2]:  # anderes Cover → neu auswerten; gleiches Cover bei neuem Titel nicht
                self._cover = sig[:2]
                picks = await self._async_measure(sig[0])
                if any(p.color for p in picks) and picks != self.picks:
                    self.picks, self._offset, changed = picks, 0.0, True
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

    def _measure(self, cfg: dict[str, Any]) -> list[Pick]:
        if self.pixels is None:
            return []
        return analyse(self.pixels, int(cfg[CONF_POINTS]), cfg[CONF_SOURCE], self.rect_lists(cfg))

    async def _async_measure(self, entity_id: str) -> list[Pick]:
        return self._measure(self.cfg) if await self._async_load(entity_id) else []

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
                if resp.status == 200:
                    return await resp.read()
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
        return [
            {"color": to_hex(c) if c else None, "bri": bri, "used": u}
            for (c, bri), u in zip(self._plan(cfg, picks), used, strict=True)
        ]

    async def _async_begin(self) -> None:
        await self._async_end_test()  # sonst würde der Schnappschuss die Testfarben festhalten
        if self.cfg[CONF_RESTORE]:
            self._snapshotted = await self._call(
                "scene", "create", {"scene_id": self._scene, "snapshot_entities": self.lights}
            )
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
        self._notify()

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

    async def _async_paint(self, plan: Plan, transition: float, switch_on: bool) -> None:
        for entity_id, (c, bri) in zip(self.lights, plan, strict=True):
            st = self.hass.states.get(entity_id)
            if c is None or st is None or st.state == STATE_UNAVAILABLE:
                continue
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

    def _schedule_tick(self) -> None:
        self._cancel_tick()
        if self.active and self._drifts(self.cfg):
            self._unsub_tick = async_track_time_interval(
                self.hass, self._on_tick, timedelta(seconds=self._every(self.cfg))
            )

    def _cancel_tick(self) -> None:
        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None

    async def _on_tick(self, _now: datetime) -> None:
        async with self._lock:
            if self.active and self.palette:
                self._offset = (self._offset + self._mode(self.cfg).shift) % 1.0
                await self._async_apply(fade=False)

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
            await self._async_paint(plan, 1.0, switch_on=not self.active)
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
