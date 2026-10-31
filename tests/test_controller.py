from datetime import timedelta
from types import MappingProxyType
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed, async_mock_service

from custom_components.covermood.colors import Hs, Pick
from custom_components.covermood.const import GRACE_SECONDS, TEST_SECONDS
from custom_components.covermood.controller import RoomController

PLAYER = "media_player.sonos"
PALETTE = [Pick(Hs(0, 1), 0), Pick(Hs(120, 1), 0)]


def make_room(hass, **over):
    data = {
        "players": [PLAYER],
        "lights": ["light.a", "light.b"],
        "mode": "calm",
        "source": "palette",
        "points": 2,
        "turn_on": True,
        "brightness": 60,
        "restore": True,
    } | over
    sub = ConfigSubentry(data=MappingProxyType(data), subentry_type="room", title="Wohnzimmer", unique_id=None)
    return RoomController(hass, sub)


async def play(hass, room, palette=PALETTE):
    """Ein Raum mit zwei Lichtern (a an, b aus); der Player beginnt zu spielen. Liefert die gemockten Dienste."""
    calls = {
        "on": async_mock_service(hass, "light", "turn_on"),
        "create": async_mock_service(hass, "scene", "create"),
        "recall": async_mock_service(hass, "scene", "turn_on"),
        "delete": async_mock_service(hass, "scene", "delete"),
    }
    hass.states.async_set("light.a", "on")
    hass.states.async_set("light.b", "off")
    with patch.object(room, "_async_measure", AsyncMock(return_value=palette)):
        room.start()
        hass.states.async_set(PLAYER, "playing", {"entity_picture": "/c1", "media_title": "A"})
        await hass.async_block_till_done()
    return calls


async def test_colors_lights_then_restores_after_grace(hass):
    room = make_room(hass)
    calls = await play(hass, room)

    assert room.active
    assert calls["create"][0].data["snapshot_entities"] == ["light.a", "light.b"]
    a, b = calls["on"]
    assert a.data["hs_color"] == [0.0, 100.0] and "brightness_pct" not in a.data  # an: Helligkeit bleibt
    assert b.data["hs_color"] == [120.0, 100.0] and b.data["brightness_pct"] == 60  # aus: wird eingeschaltet

    hass.states.async_set(PLAYER, "paused")
    await hass.async_block_till_done()
    assert room.active and not calls["recall"]  # Pause ≠ Ende

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=GRACE_SECONDS + 1))
    await hass.async_block_till_done()
    assert not room.active
    assert len(calls["recall"]) == 1 and len(calls["delete"]) == 1
    await room.async_stop()


async def test_wander_tick_never_switches_lights_back_on(hass):
    room = make_room(hass)
    calls = await play(hass, room)
    calls["on"].clear()

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))  # ein Wanderschritt (calm: 30 s)
    await hass.async_block_till_done()
    assert {c.data["entity_id"] for c in calls["on"]} == {"light.a"}
    await room.async_stop()


async def test_unreadable_cover_leaves_lights_alone(hass):
    room = make_room(hass)
    calls = await play(hass, room, palette=[])
    assert not room.active and not calls["on"] and not calls["create"]
    await room.async_stop()


async def test_regions_color_each_light_from_its_area_and_stand_still(hass):
    # a im alten Format (ein Rechteck), b im neuen (Liste von Bereichen)
    room = make_room(hass, source="regions", regions={"light.a": [0, 0, 0.5, 1], "light.b": [[0.5, 0, 0.5, 1]]})
    row = [(230, 30, 30, 255)] * 32 + [(30, 30, 230, 255)] * 32  # links rot, rechts blau
    on = async_mock_service(hass, "light", "turn_on")
    for svc in ("create", "turn_on", "delete"):
        async_mock_service(hass, "scene", svc)
    hass.states.async_set("light.a", "on")
    hass.states.async_set("light.b", "on")

    async def load(entity_id):
        room.pixels, room.thumb = row * 64, b"jpg"
        return True

    with patch.object(room, "_async_load", AsyncMock(side_effect=load)):
        room.start()
        hass.states.async_set(PLAYER, "playing", {"entity_picture": "/c1", "media_title": "A"})
        await hass.async_block_till_done()
    a, b = on
    assert round(a.data["hs_color"][0]) == 0 and round(b.data["hs_color"][0]) == 240
    assert room._unsub_tick is None  # Bereiche wandern nicht, auch nicht in „Ruhig“
    await room.async_stop()


async def test_editor_test_paints_the_lights_then_restores(hass):
    room = make_room(hass)
    on = async_mock_service(hass, "light", "turn_on")
    create = async_mock_service(hass, "scene", "create")
    recall = async_mock_service(hass, "scene", "turn_on")
    async_mock_service(hass, "scene", "delete")
    hass.states.async_set("light.a", "on")
    hass.states.async_set("light.b", "off")
    room.pixels = ([(230, 30, 30, 255)] * 32 + [(30, 30, 230, 255)] * 32) * 64  # links rot, rechts blau

    await room.async_test({"source": "regions", "regions": {"light.a": [[0, 0, 0.5, 1]], "light.b": [[0.5, 0, 0.5, 1]]}})
    assert create[0].data["snapshot_entities"] == ["light.a", "light.b"]
    a, b = on
    assert round(a.data["hs_color"][0]) == 0 and round(b.data["hs_color"][0]) == 240
    assert b.data["brightness_pct"] == 60  # ein ausgeschaltetes Licht leuchtet für den Test auf
    assert not recall

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=TEST_SECONDS + 1))
    await hass.async_block_till_done()
    assert len(recall) == 1  # Zustand vor dem Test kommt zurück
    await room.async_stop()


async def test_editor_cover_comes_from_idle_player(hass):
    room = make_room(hass)
    hass.states.async_set(PLAYER, "idle", {"entity_picture": "/c1"})

    async def load(entity_id):
        room.thumb = b"jpg"
        return True

    with patch.object(room, "_async_load", AsyncMock(side_effect=load)):
        assert await room.async_cover() == b"jpg"


async def test_disable_restores_immediately(hass):
    room = make_room(hass)
    calls = await play(hass, room)
    await room.async_set_enabled(False)
    assert not room.active and len(calls["recall"]) == 1
    await room.async_stop()


async def test_style_and_brightness_apply_instantly_to_the_playing_title(hass):
    room = make_room(hass)
    calls = await play(hass, room)
    calls["on"].clear()

    await room.async_configure({"style": "pastel", "min_sat": 0, "bri_mode": "fixed", "brightness": 40}, persist=False)
    (a,) = calls["on"]  # nur das eingeschaltete Licht; b ist aus und bleibt es
    assert a.data["hs_color"][1] <= 45 and a.data["brightness_pct"] == 40  # Pastell: nie über 45 % gesättigt
    await room.async_stop()


async def test_brightness_follows_cover_but_never_below_the_floor(hass):
    room = make_room(hass, bri_mode="cover", min_bri=30, brightness=90)
    dark = [Pick(Hs(0, 1, 0.0), 0), Pick(Hs(120, 1, 1.0), 0)]
    calls = await play(hass, room, palette=dark)
    a, b = calls["on"]
    assert a.data["brightness_pct"] == 30 and b.data["brightness_pct"] == 90
    await room.async_stop()


async def test_default_colour_replaces_restoring(hass):
    room = make_room(hass, default_color=[30, 80])
    calls = await play(hass, room)
    calls["on"].clear()
    await room.async_set_enabled(False)
    assert [c.data["hs_color"] for c in calls["on"]] == [[30.0, 80.0]]  # nur das eingeschaltete Licht a
    assert not calls["recall"] and len(calls["delete"]) == 1  # Schnappschuss wird verworfen
    await room.async_stop()


async def test_only_while_entity_is_on(hass):
    room = make_room(hass, only_while="input_boolean.party")
    hass.states.async_set("input_boolean.party", "off")
    with patch.object(room, "_async_measure", AsyncMock(return_value=PALETTE)):
        calls = await play(hass, room)  # play() legt seinen eigenen Patch darüber – derselbe Rückgabewert
        assert not room.active and not calls["on"]

        hass.states.async_set("input_boolean.party", "on")
        await hass.async_block_till_done()
        assert room.active

        hass.states.async_set("input_boolean.party", "off")
        await hass.async_block_till_done()
        assert not room.active and len(calls["recall"]) == 1  # sofort, ohne Schonfrist
    await room.async_stop()


async def test_only_certain_sources(hass):
    room = make_room(hass, only_sources=["Spotify"])
    hass.states.async_set("light.a", "on")
    hass.states.async_set("light.b", "on")
    for domain, service in (("light", "turn_on"), ("scene", "create"), ("scene", "turn_on"), ("scene", "delete")):
        async_mock_service(hass, domain, service)
    with patch.object(room, "_async_measure", AsyncMock(return_value=PALETTE)):
        room.start()
        hass.states.async_set(PLAYER, "playing", {"entity_picture": "/c1", "media_title": "A", "source": "TV"})
        await hass.async_block_till_done()
        assert not room.active
        hass.states.async_set(PLAYER, "playing", {"entity_picture": "/c1", "media_title": "A", "source": "spotify"})
        await hass.async_block_till_done()
        assert room.active
    await room.async_stop()


async def test_editor_settings_reach_a_running_room_without_reload(hass):
    room = make_room(hass)
    calls = await play(hass, room)
    calls["on"].clear()
    await room.async_configure({"only_sources": ["Radio"]}, persist=False)  # Quelle passt nicht mehr
    assert room.active and room._unsub_grace  # der Titel passt nicht mehr: Schonfrist läuft, Lichter bleiben so lange
    await room.async_stop()


async def test_own_points_can_drift_round_the_lamps(hass):
    regions = {"light.a": [[0, 0, 0.5, 1]], "light.b": [[0.5, 0, 0.5, 1]]}
    row = [(230, 30, 30, 255)] * 32 + [(30, 30, 230, 255)] * 32  # links rot, rechts blau
    on = async_mock_service(hass, "light", "turn_on")
    for svc in ("create", "turn_on", "delete"):
        async_mock_service(hass, "scene", svc)
    hass.states.async_set("light.a", "on")
    hass.states.async_set("light.b", "on")
    room = make_room(hass, source="regions", regions=regions, drift_points=True, style="faithful", min_sat=0)

    async def load(entity_id):
        room.pixels, room.thumb = row * 64, b"jpg"
        return True

    with patch.object(room, "_async_load", AsyncMock(side_effect=load)):
        room.start()
        hass.states.async_set(PLAYER, "playing", {"entity_picture": "/c1", "media_title": "A"})
        await hass.async_block_till_done()
    assert room._unsub_tick is not None  # eigene Punkte wandern jetzt
    on.clear()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))  # ein Wanderschritt (calm: 30 s, 6 % des Rings)
    await hass.async_block_till_done()
    a, b = on
    assert 0 < a.data["hs_color"][0] < 120 or a.data["hs_color"][0] > 240  # a ist von Rot Richtung Blau gewandert
    assert round(a.data["hs_color"][0]) != 0 and round(b.data["hs_color"][0]) != 240
    await room.async_stop()
