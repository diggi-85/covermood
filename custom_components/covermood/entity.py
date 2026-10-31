"""Gemeinsame Basis der Covermood-Entitäten: ein Gerät pro Raum."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .controller import RoomController

if TYPE_CHECKING:
    from . import CoverMoodConfigEntry


class CoverMoodEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, room: RoomController, key: str) -> None:
        self.room = room
        self._attr_unique_id = f"{room.id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room.id)},
            name=room.name,
            manufacturer="Covermood",
            model="Raum",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.room.add_listener(self.async_write_ha_state))


def add_room_entities(
    entry: CoverMoodConfigEntry,
    async_add_entities: AddEntitiesCallback,
    factory: Callable[[RoomController], list[CoverMoodEntity]],
) -> None:
    """Je Raum die Entitäten der Plattform anlegen, dem Raum (Unterkonfiguration) zugeordnet."""
    for sid, room in entry.runtime_data.items():
        async_add_entities(factory(room), config_subentry_id=sid)
