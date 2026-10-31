"""Auswahl je Raum: die Stimmung. Nach einem Neustart gilt wieder die im Assistenten gewählte."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .controller import RoomController
from .entity import CoverMoodEntity, add_room_entities
from .modes import MODES


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    add_room_entities(entry, async_add_entities, lambda room: [ModeSelect(room)])


class ModeSelect(CoverMoodEntity, SelectEntity):
    _attr_options = list(MODES)

    def __init__(self, room: RoomController) -> None:
        super().__init__(room, "mode")

    @property
    def current_option(self) -> str:
        return self.room.mode_key

    async def async_select_option(self, option: str) -> None:
        await self.room.async_set_mode(option)
