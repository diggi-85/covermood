"""Schalter je Raum: Covermood an/aus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF
from homeassistant.helpers.restore_state import RestoreEntity

from .controller import RoomController
from .entity import CoverMoodEntity, add_room_entities


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    add_room_entities(entry, async_add_entities, lambda room: [EnabledSwitch(room)])


class EnabledSwitch(CoverMoodEntity, SwitchEntity, RestoreEntity):
    def __init__(self, room: RoomController) -> None:
        super().__init__(room, "enabled")

    @property
    def is_on(self) -> bool:
        return self.room.enabled

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self.room.enabled = last.state != STATE_OFF

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.room.async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.room.async_set_enabled(False)
