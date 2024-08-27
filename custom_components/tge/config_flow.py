from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from .const import DOMAIN


class TgeFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._async_abort_entries_match()
        if user_input is not None:
            return self.async_create_entry(title="TGE", data=user_input)
        return self.async_show_form(step_id="user")

    async_step_import = async_step_user
