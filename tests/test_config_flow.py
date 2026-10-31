import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER, ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er

from custom_components.covermood.const import DOMAIN

LOOK = {"mode": "party", "source": "zones", "points": 5, "turn_on": True, "brightness": 50, "restore": True}


@pytest.fixture(autouse=True)
def _states(hass):
    hass.states.async_set("light.a", "on", {"supported_color_modes": ["hs"]})
    hass.states.async_set("light.b", "off", {"supported_color_modes": ["xy"]})
    hass.states.async_set("light.white", "on", {"supported_color_modes": ["brightness"]})
    hass.states.async_set("media_player.x", "idle")


async def test_first_room_wizard_then_second_room_and_edit(hass):
    flows = hass.config_entries.flow
    result = await flows.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["step_id"] == "user"
    result = await flows.async_configure(result["flow_id"], {})
    assert result["step_id"] == "room"
    result = await flows.async_configure(result["flow_id"], {"name": "Wohnzimmer"})
    assert result["step_id"] == "devices"

    with pytest.raises(InvalidData):  # ein Licht ohne Farbe wird nicht angenommen
        await flows.async_configure(result["flow_id"], {"players": ["media_player.x"], "lights": ["light.white"]})
    result = await flows.async_configure(
        result["flow_id"], {"players": ["media_player.x"], "lights": ["light.b", "light.a"]}
    )
    assert result["step_id"] == "look"
    result = await flows.async_configure(result["flow_id"], LOOK)
    assert result["type"] is FlowResultType.CREATE_ENTRY

    entry = result["result"]
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    (sub,) = entry.subentries.values()
    assert sub.title == "Wohnzimmer"
    assert sub.data["lights"] == ["light.b", "light.a"]  # Reihenfolge bleibt
    assert sub.data["points"] == 5 and sub.data["mode"] == "party"
    assert len(er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)) == 4

    # weiterer Raum: Name kommt aus dem Bereich
    area = ar.async_get(hass).async_create("Küche")
    subs = hass.config_entries.subentries
    result = await subs.async_init((entry.entry_id, "room"), context={"source": SOURCE_USER})
    result = await subs.async_configure(result["flow_id"], {"area": area.id})
    result = await subs.async_configure(
        result["flow_id"], {"players": ["media_player.x"], "lights": ["light.a"]}
    )
    result = await subs.async_configure(result["flow_id"], LOOK)
    assert result["type"] is FlowResultType.CREATE_ENTRY and result["title"] == "Küche"
    await hass.async_block_till_done()
    assert len(entry.subentries) == 2

    # Raum ändern
    sid = next(s.subentry_id for s in entry.subentries.values() if s.title == "Küche")
    result = await subs.async_init(
        (entry.entry_id, "room"), context={"source": SOURCE_RECONFIGURE, "subentry_id": sid}
    )
    result = await subs.async_configure(result["flow_id"], {"name": "Kochnische"})
    result = await subs.async_configure(
        result["flow_id"], {"players": ["media_player.x"], "lights": ["light.a"]}
    )
    result = await subs.async_configure(result["flow_id"], {**LOOK, "mode": "calm"})
    assert result["type"] is FlowResultType.ABORT
    await hass.async_block_till_done()
    assert entry.subentries[sid].title == "Kochnische" and entry.subentries[sid].data["mode"] == "calm"

    await hass.config_entries.async_unload(entry.entry_id)
