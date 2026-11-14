"""Merkt sich über einen Neustart hinweg, wie die Lichter vor der Musik standen."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN


class Memory:
    """Raum → Zustand seiner Lichter vor der Musik. Liegt nach einem Neustart noch etwas hier, hat Covermood nicht
    sauber aufgehört (Neustart mitten im Lied) und holt das Zurücksetzen nach."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, dict[str, Any]]] = Store(hass, 1, f"{DOMAIN}.restore")
        self._data: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        self._data = await self._store.async_load() or {}

    def get(self, room_id: str) -> dict[str, Any] | None:
        return self._data.get(room_id)

    def put(self, room_id: str, lights: dict[str, Any]) -> None:
        self._data[room_id] = lights
        self._store.async_delay_save(lambda: self._data, 1)

    def pop(self, room_id: str) -> None:
        if self._data.pop(room_id, None) is not None:
            self._store.async_delay_save(lambda: self._data, 1)
