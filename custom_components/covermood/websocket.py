"""WebSocket-API des Editors: Räume lesen, Cover live verfolgen, Farben vorab messen, Einstellungen ändern."""

from __future__ import annotations

import base64
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv

from .const import (
    BRI_MODES,
    CONF_BRI_MODE,
    CONF_BRIGHTNESS,
    CONF_DEFAULT_COLOR,
    CONF_DRIFT_POINTS,
    CONF_EVERY,
    CONF_FADE,
    CONF_MIN_BRI,
    CONF_MIN_SAT,
    CONF_MODE,
    CONF_ONLY_SOURCES,
    CONF_ONLY_WHILE,
    CONF_POINTS,
    CONF_REGIONS,
    CONF_RESTORE,
    CONF_SOURCE,
    CONF_STYLE,
    CONF_TURN_ON,
    DATA_REGISTERED,
    DEFAULTS,
    DOMAIN,
    MAX_POINTS,
    MAX_SPOTS,
    MIN_POINTS,
    SOURCES,
    TEST_SECONDS,
)
from .controller import RoomController
from .modes import MODES, STYLES

MIN_SIZE = 0.03  # kleinster Bereich: 3 % der Bildkante


def _unit(value: Any) -> float:
    return vol.All(vol.Coerce(float), vol.Range(min=0, max=1))(value)


def _rect(value: Any) -> list[float]:
    x, y, w, h = vol.ExactSequence([_unit] * 4)(value)
    if w < MIN_SIZE or h < MIN_SIZE or x + w > 1.0001 or y + h > 1.0001:
        raise vol.Invalid("Spot is not on the cover")
    return [x, y, w, h]


def _number(low: float, high: float) -> vol.All:
    return vol.All(vol.Coerce(float), vol.Range(min=low, max=high))


def _percent(low: int = 0) -> vol.All:
    return vol.All(vol.Coerce(int), vol.Range(min=low, max=100))


# Alles, was der Editor ändern darf – jedes Feld einzeln, ein Teil genügt
SETTINGS = vol.Schema(
    {
        vol.Optional(CONF_MODE): vol.In(list(MODES)),
        vol.Optional(CONF_STYLE): vol.In(list(STYLES)),
        vol.Optional(CONF_SOURCE): vol.In(SOURCES),
        vol.Optional(CONF_POINTS): vol.All(vol.Coerce(int), vol.Range(min=MIN_POINTS, max=MAX_POINTS)),
        vol.Optional(CONF_MIN_SAT): _percent(),
        vol.Optional(CONF_MIN_BRI): _percent(1),
        vol.Optional(CONF_BRIGHTNESS): _percent(1),
        vol.Optional(CONF_BRI_MODE): vol.In(BRI_MODES),
        vol.Optional(CONF_FADE): vol.Any(None, _number(0, 60)),
        vol.Optional(CONF_EVERY): vol.Any(None, _number(0, 600)),
        vol.Optional(CONF_TURN_ON): cv.boolean,
        vol.Optional(CONF_RESTORE): cv.boolean,
        vol.Optional(CONF_DRIFT_POINTS): cv.boolean,
        vol.Optional(CONF_ONLY_SOURCES): [cv.string],
        vol.Optional(CONF_ONLY_WHILE): vol.Any(None, "", cv.entity_id),
        vol.Optional(CONF_DEFAULT_COLOR): vol.Any(None, vol.ExactSequence([_number(0, 360), _number(0, 100)])),
        vol.Optional(CONF_REGIONS): {cv.entity_id: vol.All([_rect], vol.Length(min=1, max=MAX_SPOTS))},
    }
)


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    if hass.data.get(f"{DATA_REGISTERED}_ws"):
        return
    hass.data[f"{DATA_REGISTERED}_ws"] = True
    for command in (ws_rooms, ws_subscribe, ws_preview, ws_test, ws_update, ws_enable):
        websocket_api.async_register_command(hass, command)


def _find(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]):
    """(Eintrag, Raum) zur room_id, sonst Fehler an den Editor."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if room := getattr(entry, "runtime_data", {}).get(msg["room_id"]):
            return entry, room
    connection.send_error(msg["id"], "not_found", "Room not found")
    return None


def _patch(connection: websocket_api.ActiveConnection, msg: dict[str, Any], room: RoomController) -> dict[str, Any] | None:
    """Die Einstellungen aus der Nachricht, auf diesen Raum zugeschnitten (nur seine Lichter, leere Entität = keine)."""
    patch = dict(msg["settings"])
    if not set(patch.get(CONF_REGIONS, {})) <= set(room.lights):
        connection.send_error(msg["id"], "invalid_format", "Spot for a light that is not part of this room")
        return None
    if CONF_ONLY_WHILE in patch:
        patch[CONF_ONLY_WHILE] = patch[CONF_ONLY_WHILE] or None
    return patch


def _needs_cover(connection: websocket_api.ActiveConnection, msg: dict[str, Any], room: RoomController) -> bool:
    if room.pixels is None:
        connection.send_error(msg["id"], "no_cover", "No cover yet")
        return False
    return True


def _settings(room: RoomController) -> dict[str, Any]:
    """Alle Editor-Einstellungen des Raums; Bereiche vollständig (auch die Streifen, die er noch nicht gespeichert hat)."""
    return {k: room.cfg[k] for k in DEFAULTS} | {CONF_REGIONS: dict(zip(room.lights, room.rect_lists(), strict=True))}


def _name(hass: HomeAssistant, entity_id: str) -> str:
    return st.name if (st := hass.states.get(entity_id)) else entity_id


def _sources(hass: HomeAssistant, room: RoomController) -> list[str]:
    """Quellen, die die Player des Raums anbieten oder gerade nutzen."""
    found: set[str] = set()
    for entity_id in room.players:
        if st := hass.states.get(entity_id):
            found.update(st.attributes.get("source_list") or ())
            if st.attributes.get("source"):
                found.add(st.attributes["source"])
    return sorted(found, key=str.casefold)


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "covermood/rooms"})
@callback
def ws_rooms(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    rooms = [
        {
            "id": room.id,
            "name": room.name,
            "enabled": room.enabled,
            "lights": [{"entity_id": e, "name": _name(hass, e)} for e in room.lights],
            "sources": _sources(hass, room),
            "settings": _settings(room),
        }
        for entry in hass.config_entries.async_entries(DOMAIN)
        for room in getattr(entry, "runtime_data", {}).values()
    ]
    # Die Vorgaben der Stimmungen, damit der Editor beim Wechsel die Regler passend stellt
    modes = {key: {"fade": m.fade, "every": m.every} for key, m in MODES.items()}
    connection.send_result(msg["id"], {"rooms": rooms, "modes": modes, "max_spots": MAX_SPOTS})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "covermood/subscribe", vol.Required("room_id"): str})
@websocket_api.async_response
async def ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Das Cover und der laufende Titel des Raums – sofort und bei jedem Wechsel."""
    if not (found := _find(hass, connection, msg)):
        return
    room = found[1]
    await room.async_cover()
    sent: list[bytes | None] = []  # das zuletzt geschickte Bild; ein Bild geht nur einmal über die Leitung

    @callback
    def push() -> None:
        event = room.now_playing() | {"active": room.active}
        if not sent or sent[0] is not room.thumb:
            sent[:] = [room.thumb]
            event["image"] = "data:image/jpeg;base64," + base64.b64encode(room.thumb).decode() if room.thumb else None
        connection.send_message(websocket_api.event_message(msg["id"], event))

    connection.subscriptions[msg["id"]] = room.add_listener(push)
    connection.send_result(msg["id"])
    push()


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "covermood/preview", vol.Required("room_id"): str, vol.Required("settings"): SETTINGS}
)
@callback
def ws_preview(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Die Farben, die die Lichter mit diesen Einstellungen bekämen."""
    if not (found := _find(hass, connection, msg)):
        return
    room = found[1]
    if _needs_cover(connection, msg, room) and (patch := _patch(connection, msg, room)) is not None:
        connection.send_result(msg["id"], room.preview(patch))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "covermood/test", vol.Required("room_id"): str, vol.Required("settings"): SETTINGS}
)
@websocket_api.async_response
async def ws_test(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Die Farben dieser Einstellungen kurz auf die echten Lichter legen – ohne etwas zu speichern."""
    if not (found := _find(hass, connection, msg)):
        return
    room = found[1]
    if _needs_cover(connection, msg, room) and (patch := _patch(connection, msg, room)) is not None:
        await room.async_test(patch)
        connection.send_result(msg["id"], {"seconds": TEST_SECONDS})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "covermood/update", vol.Required("room_id"): str, vol.Required("settings"): SETTINGS}
)
@websocket_api.async_response
async def ws_update(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Einstellungen übernehmen und speichern; die Lichter folgen sofort, ohne Neuladen."""
    if not (found := _find(hass, connection, msg)):
        return
    room = found[1]
    if (patch := _patch(connection, msg, room)) is not None:
        await room.async_configure(patch)
        connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "covermood/enable", vol.Required("room_id"): str, vol.Required("enabled"): cv.boolean}
)
@websocket_api.async_response
async def ws_enable(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Covermood für einen Raum an- oder ausschalten – dasselbe wie der Schalter des Raums."""
    if found := _find(hass, connection, msg):
        await found[1].async_set_enabled(msg["enabled"])
        connection.send_result(msg["id"])
