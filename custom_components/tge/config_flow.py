from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.selector import selector, TemplateSelectorConfig, TemplateSelector
from homeassistant.helpers.template import Template

from .const import DOMAIN, CONF_UNIT, UNIT_ZL_MWH, UNIT_GR_KWH, UNIT_ZL_KWH, CONF_STATE_TEMPLATE_FIXING_1_RATE, \
    CONF_STATE_TEMPLATE_FIXING_2_RATE, CONF_STATE_TEMPLATE_FIXING_1_VOLUME, CONF_STATE_TEMPLATE_FIXING_2_VOLUME, \
    PARAMETER_FIXING_1_RATE, PARAMETER_FIXING_1_VOLUME, PARAMETER_FIXING_2_RATE, PARAMETER_FIXING_2_VOLUME, \
    CONF_USE_STATE_TEMPLATES

_LOGGER = logging.getLogger(__name__)


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


# noinspection PyTypeChecker
class TgeOptionsFlowHandler(config_entries.OptionsFlow):
    """TGE config flow options handler."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(
            self,
            _: dict[str, Any] | None = None) -> ConfigFlowResult:  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_units()

    async def async_step_units(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self.options[CONF_UNIT] = user_input.get(CONF_UNIT, UNIT_ZL_MWH)
            return await self.async_step_templates()

        return self.async_show_form(
            step_id="units",
            data_schema=vol.Schema({
                vol.Required(CONF_UNIT, default=self.options.get(CONF_UNIT, UNIT_ZL_MWH)): selector(
                    {"select": {"options": [
                        {"label": UNIT_ZL_MWH, "value": UNIT_ZL_MWH},
                        {"label": UNIT_GR_KWH, "value": UNIT_GR_KWH},
                        {"label": UNIT_ZL_KWH, "value": UNIT_ZL_KWH}
                    ]}}),
            })
        )

    async def async_step_templates(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            for template_conf_key in [CONF_STATE_TEMPLATE_FIXING_1_RATE, CONF_STATE_TEMPLATE_FIXING_2_RATE,
                                      CONF_STATE_TEMPLATE_FIXING_1_VOLUME, CONF_STATE_TEMPLATE_FIXING_2_VOLUME]:
                template = user_input.get(template_conf_key)
                if not self._validate_template(template):
                    errors[template_conf_key] = "invalid_template"
            if len(errors) == 0:
                self.options[CONF_USE_STATE_TEMPLATES] = user_input.get(CONF_USE_STATE_TEMPLATES, False)
                if self.options[CONF_USE_STATE_TEMPLATES]:
                    self.options[CONF_STATE_TEMPLATE_FIXING_1_RATE] = user_input.get(CONF_STATE_TEMPLATE_FIXING_1_RATE,
                                                                                     "")
                    self.options[CONF_STATE_TEMPLATE_FIXING_2_RATE] = user_input.get(CONF_STATE_TEMPLATE_FIXING_2_RATE,
                                                                                     "")
                    self.options[CONF_STATE_TEMPLATE_FIXING_1_VOLUME] = user_input.get(
                        CONF_STATE_TEMPLATE_FIXING_1_VOLUME, "")
                    self.options[CONF_STATE_TEMPLATE_FIXING_2_VOLUME] = user_input.get(
                        CONF_STATE_TEMPLATE_FIXING_2_VOLUME, "")
                else:
                    self.options[CONF_STATE_TEMPLATE_FIXING_1_RATE] = ""
                    self.options[CONF_STATE_TEMPLATE_FIXING_2_RATE] = ""
                    self.options[CONF_STATE_TEMPLATE_FIXING_1_VOLUME] = ""
                    self.options[CONF_STATE_TEMPLATE_FIXING_2_VOLUME] = ""
                output = await self._update_options()
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return output

            return self.async_show_form(
                step_id="templates",
                errors=errors,
                data_schema=vol.Schema({
                    vol.Required(CONF_USE_STATE_TEMPLATES,
                                 default=user_input.get(CONF_USE_STATE_TEMPLATES, False)): bool,
                    vol.Optional(CONF_STATE_TEMPLATE_FIXING_1_RATE,
                                 default=user_input.get(CONF_STATE_TEMPLATE_FIXING_1_RATE, "")
                                 ): TemplateSelector(TemplateSelectorConfig()),
                    vol.Optional(CONF_STATE_TEMPLATE_FIXING_1_VOLUME,
                                 default=user_input.get(CONF_STATE_TEMPLATE_FIXING_1_VOLUME, "")
                                 ): TemplateSelector(TemplateSelectorConfig()),
                    vol.Optional(CONF_STATE_TEMPLATE_FIXING_2_RATE,
                                 default=user_input.get(CONF_STATE_TEMPLATE_FIXING_2_RATE, "")
                                 ): TemplateSelector(TemplateSelectorConfig()),
                    vol.Optional(CONF_STATE_TEMPLATE_FIXING_2_VOLUME,
                                 default=user_input.get(CONF_STATE_TEMPLATE_FIXING_2_VOLUME, "")
                                 ): TemplateSelector(TemplateSelectorConfig()),
                })
            )

        return self.async_show_form(
            step_id="templates",
            data_schema=vol.Schema({
                vol.Required(CONF_USE_STATE_TEMPLATES, default=self.options.get(CONF_USE_STATE_TEMPLATES, False)): bool,
                vol.Optional(CONF_STATE_TEMPLATE_FIXING_1_RATE,
                             default=self.options.get(CONF_STATE_TEMPLATE_FIXING_1_RATE, "")
                             ): TemplateSelector(TemplateSelectorConfig()),
                vol.Optional(CONF_STATE_TEMPLATE_FIXING_1_VOLUME,
                             default=self.options.get(CONF_STATE_TEMPLATE_FIXING_1_VOLUME, "")): TemplateSelector(
                    TemplateSelectorConfig()),
                vol.Optional(CONF_STATE_TEMPLATE_FIXING_2_RATE,
                             default=self.options.get(CONF_STATE_TEMPLATE_FIXING_2_RATE, "")): TemplateSelector(
                    TemplateSelectorConfig()),
                vol.Optional(CONF_STATE_TEMPLATE_FIXING_2_VOLUME,
                             default=self.options.get(CONF_STATE_TEMPLATE_FIXING_2_VOLUME, "")): TemplateSelector(
                    TemplateSelectorConfig()),
            })
        )

    def _validate_template(self, template: str) -> bool:
        if template == "":
            return True
        # noinspection PyBroadException
        try:
            ut = Template(template, self.hass).async_render(
                {
                    PARAMETER_FIXING_1_RATE: 1,
                    PARAMETER_FIXING_1_VOLUME: 0.5,
                    PARAMETER_FIXING_2_RATE: 0.5,
                    PARAMETER_FIXING_2_VOLUME: 0.5,
                }
            )

            return isinstance(ut, float) or isinstance(ut, int)
        except:
            return False

    def _get_option(self, key: str, default: str) -> str:
        return self.options.get(key, default) if self.options.get(key, default) is not None else default

    async def _update_options(self) -> ConfigFlowResult:
        """Update config entry options."""
        return self.async_create_entry(
            title="TGE", data=self.options
        )
