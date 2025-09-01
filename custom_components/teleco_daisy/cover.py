from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverEntity,
    CoverDeviceClass,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from teleco_daisy import DaisyAwningsCover, DaisySlatsCover, DaisyShadeCover

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([TelecoDaisyCover(cover) for cover in hub.covers])


class TelecoDaisyCover(CoverEntity):
    def __init__(
        self, cover: DaisyAwningsCover | DaisySlatsCover | DaisyShadeCover
    ) -> None:
        self._cover = cover

        self._attr_unique_id = str(cover.idInstallationDevice)
        self._attr_name = cover.label

        if isinstance(cover, DaisyAwningsCover):
            self._attr_device_class = CoverDeviceClass.AWNING
            self._attr_supported_features = (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.SET_POSITION
                | CoverEntityFeature.STOP
            )
        elif isinstance(cover, DaisySlatsCover):
            self._attr_device_class = CoverDeviceClass.BLIND
            self._attr_supported_features = (
                CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.SET_TILT_POSITION
                | CoverEntityFeature.STOP_TILT
            )
        elif isinstance(cover, DaisyShadeCover):
            self._attr_device_class = CoverDeviceClass.SHADE
            self._attr_supported_features = (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
            )

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Teleco Automation",
        )

    @property
    def is_closed(self) -> bool | None:
        return self._cover.is_closed

    @property
    def current_cover_position(self) -> int | None:
        return self._cover.position

    @property
    def current_cover_tilt_position(self) -> int | None:
        return self._cover.position

    def update(self) -> None:
        self._cover.update_state()
        self._attr_is_closed = self._cover.is_closed
        self._attr_current_cover_position = self._cover.position

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

    def set_cover_position(self, **kwargs: Any) -> None:
        position = kwargs[ATTR_POSITION]
        if position <= 15:
            self._cover.close_cover()
        elif 15 < position <= 48:
            self._cover.open_cover("33")
        elif 48 < position <= 81:
            self._cover.open_cover("66")
        else:
            self._cover.open_cover("100")
        self.update()

    def stop_cover(self, **kwargs: Any) -> None:
        self._cover.stop_cover()
        self.update()

    def open_cover_tilt(self, **kwargs: Any) -> None:
        self._cover.open_cover()
        self.update()

    def close_cover_tilt(self, **kwargs: Any) -> None:
        self._cover.close_cover()
        self.update()

    def set_cover_tilt_position(self, **kwargs: Any) -> None:
        position = kwargs[ATTR_TILT_POSITION]
        if position <= 15:
            self._cover.close_cover()
        elif 15 < position <= 48:
            self._cover.open_cover("33")
        elif 48 < position <= 81:
            self._cover.open_cover("66")
        else:
            self._cover.open_cover("100")
        self.update()

    def stop_cover_tilt(self, **kwargs: Any) -> None:
        self._cover.stop_cover()
        self.update()
