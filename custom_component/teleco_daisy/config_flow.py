import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)


class TelecoDaisyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    data: Optional[Dict[str, Any]]

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data = user_input
            return self.async_create_entry(title="Teleco Daisy", data=self.data)
        return self.async_show_form(
            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
        )
