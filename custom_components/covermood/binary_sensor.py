"""Statusanzeige je Raum: Covermood steuert gerade die Lichter."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory

from .controller import RoomController
from .entity import CoverMoodEntity, add_room_entities


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    add_room_entities(entry, async_add_entities, lambda room: [ActiveSensor(room)])


class ActiveSensor(CoverMoodEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, room: RoomController) -> None:
        super().__init__(room, "active")

    @property
    def is_on(self) -> bool:
        return self.room.active
