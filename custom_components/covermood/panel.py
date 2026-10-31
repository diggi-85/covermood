"""Der Editor in der Seitenleiste: je Licht den Bereich auf dem Cover festlegen."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .const import DATA_REGISTERED, PANEL_PATH, URL_BASE

FRONTEND_DIR = Path(__file__).parent / "frontend"
MODULE = "covermood-panel.js"


async def async_register_panel(hass: HomeAssistant) -> None:
    if not hass.data.get(DATA_REGISTERED):
        await hass.http.async_register_static_paths([StaticPathConfig(URL_BASE, str(FRONTEND_DIR), cache_headers=False)])
        hass.data[DATA_REGISTERED] = True
    # Änderungszeit als Cache-Schlüssel, damit eine neue Fassung sofort ankommt
    version = await hass.async_add_executor_job(lambda: int((FRONTEND_DIR / MODULE).stat().st_mtime))
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name="covermood-panel",
        sidebar_title="Covermood",
        sidebar_icon="mdi:palette",
        module_url=f"{URL_BASE}/{MODULE}?v={version}",
        require_admin=True,
    )


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:
    frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
