import pytest
from homeassistant.config_entries import ConfigSubentryData
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.covermood.const import DOMAIN

ROW = [(230, 30, 30, 255)] * 32 + [(30, 30, 230, 255)] * 32  # links rot, rechts blau
RECTS = [[0, 0, 0.5, 1], [0.5, 0, 0.5, 1]]


@pytest.fixture
async def room(hass):
    hass.states.async_set("light.a", "on", {"supported_color_modes": ["hs"]})
    hass.states.async_set("light.b", "on", {"supported_color_modes": ["hs"]})
    hass.states.async_set("media_player.x", "idle")
    data = {
        "players": ["media_player.x"],
        "lights": ["light.a", "light.b"],
        "mode": "calm",
        "source": "palette",
        "points": 3,
        "turn_on": True,
        "brightness": 60,
        "restore": True,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[ConfigSubentryData(subentry_type="room", title="Wohnzimmer", unique_id=None, data=data)],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    (controller,) = entry.runtime_data.values()
    controller.pixels, controller.thumb = ROW * 64, b"\xff\xd8jpg"
    yield entry, controller
    await hass.config_entries.async_unload(entry.entry_id)


async def test_editor_commands(hass, hass_ws_client, room):
    entry, controller = room
    ws = await hass_ws_client(hass)

    await ws.send_json_auto_id({"type": "covermood/rooms"})
    result = (await ws.receive_json())["result"]
    (info,) = result["rooms"]
    assert info["name"] == "Wohnzimmer"
    assert [light["entity_id"] for light in info["lights"]] == ["light.a", "light.b"]
    assert info["settings"]["regions"] == {"light.a": [RECTS[0]], "light.b": [RECTS[1]]}  # ohne eigene Wahl: Streifen
    assert info["settings"]["style"] == "vibrant" and result["modes"]["calm"]["every"] == 30

    # zu kleiner Bereich wird abgelehnt
    bad = {"regions": {"light.a": [[0, 0, 0.001, 1]]}}
    await ws.send_json_auto_id({"type": "covermood/preview", "room_id": controller.id, "settings": bad})
    assert not (await ws.receive_json())["success"]

    # Licht, das nicht zum Raum gehört
    other = {"regions": {"light.zzz": [[0, 0, 0.5, 0.5]]}}
    await ws.send_json_auto_id({"type": "covermood/preview", "room_id": controller.id, "settings": other})
    assert not (await ws.receive_json())["success"]

    # Vorschau mit den Einstellungen des Editors, auch mit fester Helligkeit
    mixed = {
        "source": "regions",
        "style": "faithful",
        "min_sat": 0,
        "regions": {"light.a": [[0, 0, 0.5, 1]], "light.b": [[0.5, 0, 0.5, 1]]},
    }
    await ws.send_json_auto_id({"type": "covermood/preview", "room_id": controller.id, "settings": mixed})
    left, right = (await ws.receive_json())["result"]
    assert left["color"] != right["color"] and left["used"] == right["used"] == 0
    await ws.send_json_auto_id(
        {
            "type": "covermood/preview",
            "room_id": controller.id,
            "settings": mixed | {"regions": {"light.a": [[0, 0, 0.5, 1]], "light.b": [[0.5, 0, 0.5, 1]]}, "bri_mode": "fixed", "brightness": 55},
        }
    )
    assert (await ws.receive_json())["result"][0]["bri"] == 55

    on = async_mock_service(hass, "light", "turn_on")
    for service in ("create", "turn_on", "delete"):
        async_mock_service(hass, "scene", service)
    await ws.send_json_auto_id({"type": "covermood/test", "room_id": controller.id, "settings": mixed})
    assert (await ws.receive_json())["result"] == {"seconds": 10}
    assert len(on) == 2  # beide Lichter bekommen ihre Testfarbe

    # Speichern: wirkt sofort, lädt die Integration aber nicht neu (der Raum bleibt dasselbe Objekt)
    await ws.send_json_auto_id(
        {"type": "covermood/update", "room_id": controller.id, "settings": mixed | {"fade": 12, "only_while": ""}}
    )
    assert (await ws.receive_json())["success"]
    await hass.async_block_till_done()
    (sub,) = entry.subentries.values()
    assert sub.data["source"] == "regions" and sub.data["fade"] == 12.0
    assert sub.data["regions"]["light.b"] == [RECTS[1]]
    assert sub.data["only_while"] is None
    assert next(iter(entry.runtime_data.values())) is controller
    assert controller.cfg["fade"] == 12.0


async def test_subscription_pushes_a_new_cover(hass, hass_ws_client, room):
    _, controller = room
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "covermood/subscribe", "room_id": controller.id})
    assert (await ws.receive_json())["success"]
    first = (await ws.receive_json())["event"]
    assert first["image"].startswith("data:image/jpeg;base64,") and first["playing"] is False

    controller.thumb = b"\xff\xd8other"
    controller._notify()  # dasselbe, was ein Titelwechsel auslöst
    second = (await ws.receive_json())["event"]
    assert second["image"] != first["image"]

    controller._notify()  # ohne neues Cover geht das Bild nicht noch einmal über die Leitung
    assert "image" not in (await ws.receive_json())["event"]


async def test_editor_can_switch_a_room_off_and_on(hass, hass_ws_client, room):
    _, controller = room
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "covermood/rooms"})
    assert (await ws.receive_json())["result"]["rooms"][0]["enabled"] is True

    await ws.send_json_auto_id({"type": "covermood/enable", "room_id": controller.id, "enabled": False})
    assert (await ws.receive_json())["success"]
    assert controller.enabled is False and controller.now_playing()["enabled"] is False

    await ws.send_json_auto_id({"type": "covermood/enable", "room_id": controller.id, "enabled": True})
    assert (await ws.receive_json())["success"]
    assert controller.enabled is True
