import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .hub import TelecoDaisyHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["light", "cover", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    daisy_hub = TelecoDaisyHub(
        hass, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )

    if not await daisy_hub.async_setup():
        return False

    await daisy_hub.coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = daisy_hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
