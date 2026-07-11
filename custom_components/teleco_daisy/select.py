from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .lib import DaisyRetractableSlatsCover

ANGLE_TO_LEVEL = {"0°": "0", "45°": "33", "90°": "66", "135°": "100"}
LEVEL_TO_ANGLE = {int(level): angle for angle, level in ANGLE_TO_LEVEL.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        TelecoDaisySlatAngle(hub.coordinator, device)
        for device in hub.devices
        if isinstance(device, DaisyRetractableSlatsCover)
    )


class TelecoDaisySlatAngle(CoordinatorEntity, SelectEntity):
    _attr_options = list(ANGLE_TO_LEVEL)
    _attr_icon = "mdi:angle-acute"

    def __init__(self, coordinator, cover: DaisyRetractableSlatsCover) -> None:
        super().__init__(coordinator)
        self._cover = cover
        self._attr_unique_id = f"{cover.idInstallationDevice}_slat_angle"
        self._attr_name = "Slat angle"
        self._attr_has_entity_name = True

    @property
    def current_option(self) -> str | None:
        if self._cover.tilt_position is None:
            return None
        return LEVEL_TO_ANGLE.get(self._cover.tilt_position)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._cover.idInstallationDevice))},
            name=self._cover.label,
            manufacturer="Teleco Automation",
        )

    async def async_select_option(self, option: str) -> None:
        await self._cover.open_cover_tilt(ANGLE_TO_LEVEL[option])
        await self._cover.update_state()
        self.async_write_ha_state()
