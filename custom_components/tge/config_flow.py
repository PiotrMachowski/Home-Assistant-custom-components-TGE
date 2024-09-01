from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import DOMAIN, CONF_UNIT, UNIT_ZL_MWH, UNIT_GR_KWH


class TgeFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._async_abort_entries_match()
        if user_input is not None:
            return self.async_create_entry(title="TGE", data=user_input)
        return self.async_show_form(step_id="user")

    async_step_import = async_step_user

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TgeOptionsFlowHandler:
        return TgeOptionsFlowHandler(config_entry)


class TgeOptionsFlowHandler(config_entries.OptionsFlow):
    """TGE config flow options handler."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self.options.update(user_input)
            output = await self._update_options()
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return output

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_UNIT, default=self.get_option(CONF_UNIT, UNIT_ZL_MWH)): selector(
                    {"select": {"options": [
                        {"label": UNIT_ZL_MWH, "value": UNIT_ZL_MWH},
                        {"label": UNIT_GR_KWH, "value": UNIT_GR_KWH}
                    ]}}),
            })
        )


    def get_option(self, key: str, default: str) -> str:
        return self.options.get(key, default) if self.options.get(key, default) is not None else default

    async def _update_options(self) -> ConfigFlowResult:
        """Update config entry options."""
        return self.async_create_entry(
            title="TGE", data=self.options
        )
