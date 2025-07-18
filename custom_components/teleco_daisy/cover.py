from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import CoverEntity, CoverDeviceClass, ATTR_POSITION
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from teleco_daisy import DaisyAwningsCover, DaisySlatsCover

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([TelecoDaisyCover(cover) for cover in hub.covers])


class TelecoDaisyCover(CoverEntity):
    def __init__(self, cover: DaisyAwningsCover | DaisySlatsCover) -> None:
        self._cover = cover
        self._attr_is_closed = self._cover.is_closed
        self._attr_current_cover_position = self._cover.position

        self._attr_unique_id = str(cover.idInstallationDevice)
        self._attr_name = cover.label
        self._attr_device_class = CoverDeviceClass.AWNING
        self._attr_available = True

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Teleco Automation",
        )

    # @property
    # def is_closing(self) -> bool:
    #     """Return if the cover is closing or not."""
    #     return self._roller.moving < 0
    #
    # @property
    # def is_opening(self) -> bool:
    #     """Return if the cover is opening or not."""
    #     return self._roller.moving > 0
    #
    def open_cover(self, **kwargs: Any) -> None:
        self._cover.open_cover()
        self.update()

    def close_cover(self, **kwargs: Any) -> None:
        self._cover.close_cover()
        self.update()

    def stop_cover(self, **kwargs: Any) -> None:
        self._cover.stop_cover()
        self.update()

    def update(self) -> None:
        self._cover.update_state()
        self._attr_is_closed = self._cover.is_closed
        self._attr_current_cover_position = self._cover.position

    def set_cover_position(self, **kwargs: Any) -> None:
        position = kwargs[ATTR_POSITION]
        if 0 < position < 15:
            self._cover.close_cover()
        elif 16 < position < 48:
            self._cover.open_cover("33")
        elif 49 < position < 81:
            self._cover.open_cover("66")
        else:
            self._cover.open_cover("100")
        self.update()
