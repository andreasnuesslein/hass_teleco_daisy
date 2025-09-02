from __future__ import annotations

import logging
from typing import Literal

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from teleco_daisy import DaisyHeater4CH

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([TelecoDaisyClimateEntity(heater) for heater in hub.heaters])


class TelecoDaisyClimateEntity(ClimateEntity):
    def __init__(self, heater: DaisyHeater4CH) -> None:
        self._heater = heater

        self._attr_unique_id = str(heater.idInstallationDevice)
        self._attr_name = heater.label

        self._attr_supported_features = (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.PRESET_MODE
        )
        self.preset_modes = ["50", "75", "100"]
        # FIXME This is a workaround for the fact that teleco_daisy does not report the current preset mode
        self._preset_mode = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Teleco Automation",
        )

    def turn_on(self):
        self._heater.turn_on()

    def turn_off(self):
        self._heater.turn_off()

    def set_preset_mode(self, preset_mode: Literal["50", "75", "100"]):
        self._heater.set_level(preset_mode)
        self._preset_mode = preset_mode

    @property
    def preset_mode(self) -> str | None:
        # FIXME This is a workaround for the fact that teleco_daisy does not report the current preset mode
        return self._preset_mode
