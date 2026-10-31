"""Einrichtung: Assistent für den ersten Raum, danach jeder weitere Raum als eigene Unterkonfiguration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.light import ATTR_SUPPORTED_COLOR_MODES, COLOR_MODES_COLOR
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    AreaSelector,
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)

from .const import (
    CONF_AREA,
    CONF_BRIGHTNESS,
    CONF_LIGHTS,
    CONF_MODE,
    CONF_PLAYERS,
    CONF_POINTS,
    CONF_RESTORE,
    CONF_SOURCE,
    CONF_TURN_ON,
    DEFAULT_BRIGHTNESS,
    DEFAULT_MODE,
    DEFAULT_POINTS,
    DOMAIN,
    MAX_POINTS,
    MIN_POINTS,
    SOURCE_PALETTE,
    SOURCES,
    SUBENTRY_ROOM,
)
from .modes import MODES


def _color_lights(hass: HomeAssistant) -> list[str]:
    """Lichter, die Farbe können – reine Weiß- oder Dimm-Lichter taugen für den Verlauf nicht."""
    return sorted(
        s.entity_id
        for s in hass.states.async_all("light")
        if COLOR_MODES_COLOR & set(s.attributes.get(ATTR_SUPPORTED_COLOR_MODES) or ())
    )


def _in_area(hass: HomeAssistant, area_id: str | None, domain: str) -> list[str]:
    """Entitäten eines Bereichs – direkt zugeordnet oder über ihr Gerät."""
    if not area_id:
        return []
    devices = dr.async_get(hass)
    found = []
    for e in er.async_get(hass).entities.values():
        if e.domain != domain or e.disabled:
            continue
        device = devices.async_get(e.device_id) if e.device_id else None
        if (e.area_id or (device.area_id if device else None)) == area_id:
            found.append(e.entity_id)
    return sorted(found)


class RoomWizard:
    """Die Schritte für einen Raum – gleich für die Ersteinrichtung und jeden weiteren Raum."""

    hass: HomeAssistant
    _room: dict[str, Any]

    def _defaults(self) -> dict[str, Any]:
        """Vorgaben für die Felder; beim Bearbeiten die bisherigen Werte."""
        return {}

    async def _async_finish(self, room: dict[str, Any]):
        raise NotImplementedError

    async def async_step_room(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        d = self._defaults()
        if user_input is not None:
            area_id = user_input.get(CONF_AREA)
            area = ar.async_get(self.hass).async_get_area(area_id) if area_id else None
            name = (user_input.get(CONF_NAME) or (area.name if area else "")).strip()
            if name:
                self._room = {CONF_NAME: name, CONF_AREA: area_id}
                return await self.async_step_devices()
            errors["base"] = "name_required"
        schema = vol.Schema(
            {
                vol.Optional(CONF_AREA, description={"suggested_value": d.get(CONF_AREA)}): AreaSelector(),
                vol.Optional(CONF_NAME, description={"suggested_value": d.get(CONF_NAME)}): TextSelector(),
            }
        )
        return self.async_show_form(step_id="room", data_schema=schema, errors=errors)

    async def async_step_devices(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        d = self._defaults()
        color_lights = _color_lights(self.hass)
        if user_input is not None:
            if not user_input[CONF_PLAYERS]:
                errors["base"] = "no_players"
            elif not user_input[CONF_LIGHTS]:
                errors["base"] = "no_lights"
            else:
                self._room.update(user_input)
                return await self.async_step_look()
        area = self._room.get(CONF_AREA)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PLAYERS,
                    description={"suggested_value": d.get(CONF_PLAYERS) or _in_area(self.hass, area, "media_player")},
                ): EntitySelector(EntitySelectorConfig(domain="media_player", multiple=True)),
                vol.Required(
                    CONF_LIGHTS,
                    description={
                        "suggested_value": d.get(CONF_LIGHTS)
                        or [e for e in _in_area(self.hass, area, "light") if e in color_lights]
                    },
                ): EntitySelector(
                    EntitySelectorConfig(
                        domain="light",
                        multiple=True,
                        include_entities=sorted(set(color_lights) | set(d.get(CONF_LIGHTS, []))),
                    )
                ),
            }
        )
        return self.async_show_form(step_id="devices", data_schema=schema, errors=errors)

    async def async_step_look(self, user_input: dict[str, Any] | None = None):
        d = self._defaults()
        if user_input is not None:
            room = {**self._room, **user_input}
            room[CONF_POINTS] = int(room[CONF_POINTS])
            room[CONF_BRIGHTNESS] = int(room[CONF_BRIGHTNESS])
            return await self._async_finish(room)
        schema = vol.Schema(
            {
                vol.Required(CONF_MODE, default=d.get(CONF_MODE, DEFAULT_MODE)): SelectSelector(
                    SelectSelectorConfig(options=list(MODES), translation_key="mode")
                ),
                vol.Required(CONF_SOURCE, default=d.get(CONF_SOURCE, SOURCE_PALETTE)): SelectSelector(
                    SelectSelectorConfig(options=SOURCES, translation_key="source")
                ),
                vol.Required(CONF_POINTS, default=d.get(CONF_POINTS, DEFAULT_POINTS)): NumberSelector(
                    NumberSelectorConfig(min=MIN_POINTS, max=MAX_POINTS, step=1, mode=NumberSelectorMode.BOX)
                ),
                vol.Required(CONF_TURN_ON, default=d.get(CONF_TURN_ON, True)): BooleanSelector(),
                vol.Required(CONF_BRIGHTNESS, default=d.get(CONF_BRIGHTNESS, DEFAULT_BRIGHTNESS)): NumberSelector(
                    NumberSelectorConfig(min=1, max=100, step=1, mode=NumberSelectorMode.SLIDER, unit_of_measurement="%")
                ),
                vol.Required(CONF_RESTORE, default=d.get(CONF_RESTORE, True)): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="look", data_schema=schema)


class CoverMoodConfigFlow(RoomWizard, ConfigFlow, domain=DOMAIN):
    """Ersteinrichtung: Willkommen, dann der erste Raum."""

    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_ROOM: RoomSubentryFlow}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user")
        return await self.async_step_room()

    async def _async_finish(self, room: dict[str, Any]) -> ConfigFlowResult:
        name = room.pop(CONF_NAME)
        return self.async_create_entry(
            title="Covermood",
            data={},
            subentries=[{"subentry_type": SUBENTRY_ROOM, "title": name, "data": room, "unique_id": None}],
        )


class RoomSubentryFlow(RoomWizard, ConfigSubentryFlow):
    """Jeder weitere Raum – und Raum ändern – durchläuft denselben Assistenten."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        return await self.async_step_room()

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        return await self.async_step_room()

    def _defaults(self) -> dict[str, Any]:
        if self.source != SOURCE_RECONFIGURE:
            return {}
        sub = self._get_reconfigure_subentry()
        return {**sub.data, CONF_NAME: sub.title}

    async def _async_finish(self, room: dict[str, Any]) -> SubentryFlowResult:
        name = room.pop(CONF_NAME)
        if self.source == SOURCE_RECONFIGURE:
            # data_updates: die im Editor gezeichneten Bereiche (regions) gehen dabei nicht verloren
            return self.async_update_and_abort(
                self._get_entry(), self._get_reconfigure_subentry(), title=name, data_updates=room
            )
        return self.async_create_entry(title=name, data=room)
