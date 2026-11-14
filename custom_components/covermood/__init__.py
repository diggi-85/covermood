"""Covermood – Lichter im Raum passen sich dem Cover der laufenden Musik an."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import CONF_EVERY, CONF_FADE, CONF_MODE, CONF_STYLE, DATA_MEMORY, DOMAIN, SUBENTRY_ROOM
from .controller import RoomController
from .memory import Memory
from .modes import MODES, STYLES
from .panel import async_register_panel, async_unregister_panel
from .websocket import async_register_commands

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

type CoverMoodConfigEntry = ConfigEntry[dict[str, RoomController]]  # Unterkonfiguration-ID → Raum

SERVICE_APPLY = "apply"
APPLY_SCHEMA = vol.Schema(
    {
        vol.Optional("room"): cv.string,
        vol.Optional("preset"): cv.string,
        vol.Optional(CONF_STYLE): vol.In(list(STYLES)),
        vol.Optional(CONF_MODE): vol.In(list(MODES)),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: CoverMoodConfigEntry) -> bool:
    # Ein Gedächtnis je HA-Lauf: zwei würden beim Neuladen dieselbe Datei gegeneinander schreiben
    if (memory := hass.data.get(DATA_MEMORY)) is None:
        memory = hass.data[DATA_MEMORY] = Memory(hass)
        await memory.async_load()
    entry.runtime_data = {
        sid: RoomController(hass, sub, memory)
        for sid, sub in entry.subentries.items()
        if sub.subentry_type == SUBENTRY_ROOM
    }
    _register_services(hass)
    async_register_commands(hass)
    await async_register_panel(hass)
    # Erst die Entitäten (sie stellen Schalter-Zustand wieder her), dann loslegen
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    for room in entry.runtime_data.values():
        room.start()
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CoverMoodConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    async_unregister_panel(hass)
    for room in entry.runtime_data.values():
        await room.async_stop()  # Lichter in den Zustand vor der Musik zurück
    return True


async def _reload(hass: HomeAssistant, entry: CoverMoodConfigEntry) -> None:
    """Raum hinzugefügt, geändert oder entfernt. Änderungen aus dem Editor kennt der Raum schon – kein Neuladen."""
    rooms = entry.runtime_data
    subs = {sid: sub for sid, sub in entry.subentries.items() if sub.subentry_type == SUBENTRY_ROOM}
    if subs.keys() == rooms.keys() and all(rooms[sid].in_sync(sub) for sid, sub in subs.items()):
        return
    await hass.config_entries.async_reload(entry.entry_id)


def _register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_APPLY):
        return

    async def apply(call: ServiceCall) -> None:
        """Vorlage, Stil oder Stimmung setzen – für einen Raum (Name) oder, ohne Angabe, für alle."""
        wanted = call.data.get("room", "").casefold()
        rooms = [
            room
            for entry in hass.config_entries.async_entries(DOMAIN)
            for room in getattr(entry, "runtime_data", {}).values()
            if not wanted or wanted in (room.name.casefold(), room.id.casefold())
        ]
        if not rooms:
            raise ServiceValidationError(f"No Covermood room named {call.data.get('room')!r}")
        look = {key: call.data[key] for key in (CONF_STYLE, CONF_MODE) if key in call.data}
        if CONF_MODE in look:  # die Stimmung bringt ihre eigene Überblend- und Wanderzeit mit
            look |= {CONF_FADE: None, CONF_EVERY: None}
        found = False
        for room in rooms:
            if preset := call.data.get("preset"):
                found = await room.async_apply_preset(preset) or found
            if look:
                await room.async_configure(look)
        if "preset" in call.data and not found:
            raise ServiceValidationError(f"No preset named {call.data['preset']!r}")

    hass.services.async_register(DOMAIN, SERVICE_APPLY, apply, schema=APPLY_SCHEMA)
