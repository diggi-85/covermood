"""Covermood – Lichter im Raum passen sich dem Cover der laufenden Musik an."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import SUBENTRY_ROOM
from .controller import RoomController
from .panel import async_register_panel, async_unregister_panel
from .websocket import async_register_commands

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

type CoverMoodConfigEntry = ConfigEntry[dict[str, RoomController]]  # Unterkonfiguration-ID → Raum


async def async_setup_entry(hass: HomeAssistant, entry: CoverMoodConfigEntry) -> bool:
    entry.runtime_data = {
        sid: RoomController(hass, sub) for sid, sub in entry.subentries.items() if sub.subentry_type == SUBENTRY_ROOM
    }
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
