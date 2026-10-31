"""Sensor je Raum: die Farben, die gerade aus dem Cover gelesen wurden."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity

from .colors import to_hex as _hex
from .controller import RoomController
from .entity import CoverMoodEntity, add_room_entities


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    add_room_entities(entry, async_add_entities, lambda room: [PaletteSensor(room)])


class PaletteSensor(CoverMoodEntity, SensorEntity):
    def __init__(self, room: RoomController) -> None:
        super().__init__(room, "palette")

    @property
    def native_value(self) -> str | None:
        return _hex(self.room.palette[0]) if self.room.palette else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"colors": [_hex(c) for c in self.room.palette]}
