from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries, core
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness

from teleco_daisy import DaisyRGBLight, DaisyWhiteLight

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

BRIGHTNESS_SCALE = (1, 100)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    hub = hass.data[DOMAIN][config_entry.entry_id]

    if config_entry.options:
        hub.update(config_entry.options)

    async_add_entities(TelecoDaisyLight(light) for light in hub.lights)


class TelecoDaisyLight(LightEntity):
    entity_description = LightEntityDescription(
        key="teleco_daisy_light", has_entity_name=True, name=None
    )

    def __init__(self, light: DaisyWhiteLight | DaisyRGBLight) -> None:
        self._light = light
        self._name = self._light.label

        self._attr_unique_id = str(self._light.idInstallationDevice)
        self._attr_name = self._light.label

        if isinstance(light, DaisyRGBLight):
            self._attr_color_mode = ColorMode.RGB
            self._attr_supported_color_modes = {ColorMode.RGB}

        elif isinstance(light, DaisyWhiteLight):
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Teleco Automation",
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_on(self) -> bool:
        return self._light.is_on

    @property
    def brightness(self) -> int | None:
        """Return the current brightness."""
        return (
            value_to_brightness(BRIGHTNESS_SCALE, self._light.brightness)
            if self._light.brightness
            else 50
        )

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        if isinstance(self._light, DaisyRGBLight):
            return self._light.rgb or (255, 255, 255)
        return None

    def turn_on(self, **kwargs: Any) -> None:
        if new_rgb := kwargs.get(ATTR_RGB_COLOR):
            rgb_col = (int(new_rgb[0]), int(new_rgb[1]), int(new_rgb[2]))
        else:
            rgb_col = self.rgb_color

        if new_bright := kwargs.get(ATTR_BRIGHTNESS):
            brightness = int(new_bright)
        else:
            brightness = self.brightness

        self._light.set_rgb_and_brightness(
            rgb=rgb_col,
            brightness=int(brightness_to_value(BRIGHTNESS_SCALE, brightness)),
        )
        self._light.update_state()

    def turn_off(self, **kwargs: Any) -> None:
        self._light.turn_off()
        self._light.update_state()

    def update(self) -> None:
        self._light.update_state()
