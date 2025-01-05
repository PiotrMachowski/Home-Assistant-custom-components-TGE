from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity, ExtraStoredData
from homeassistant.helpers.template import Template
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .connector import TgeData, TgeHourData, TgeDayData
from .const import DEFAULT_NAME, DOMAIN, URL, CONF_STATE_TEMPLATE_FIXING_1_RATE, CONF_STATE_TEMPLATE_FIXING_1_VOLUME, \
    CONF_STATE_TEMPLATE_FIXING_2_RATE, CONF_STATE_TEMPLATE_FIXING_2_VOLUME, PARAMETER_FIXING_1_RATE, \
    PARAMETER_FIXING_1_VOLUME, PARAMETER_FIXING_2_RATE, PARAMETER_FIXING_2_VOLUME
from .update_coordinator import TgeUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class TgeEntityStoredData(ExtraStoredData):
    cache: dict[datetime.date, TgeDayData] | None = None

    def as_dict(self) -> dict[str, Any]:
        if self.cache is None:
            return {
                "cache": {}
            }
        return {
            "cache": {k.isoformat(): v.to_dict() for (k, v) in self.cache.items()}
        }

    def combined_hours(self) -> list[TgeHourData]:
        values = []
        for v in self.cache.values():
            values.extend(v.hours)
        values.sort(key=lambda x: x.time)
        return values

    @staticmethod
    def from_dict(data: dict[str, Any]) -> TgeEntityStoredData:
        _LOGGER.debug(f"TgeEntityStoredData.from_dict: {data}")
        cache = data["cache"]
        parsed = {}
        for k, v in cache.items():
            date = datetime.date.fromisoformat(k)
            value = TgeDayData.from_dict(v)
            parsed[date] = value
        return TgeEntityStoredData(parsed)


class TgeEntity(RestoreEntity, CoordinatorEntity):

    def __init__(self, coordinator: TgeUpdateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._stored_data: TgeEntityStoredData = TgeEntityStoredData({})
        self._calculated_data: TgeEntityStoredData = TgeEntityStoredData({})
        self.fixing_1_rate_template = config_entry.options.get(CONF_STATE_TEMPLATE_FIXING_1_RATE, "")
        self.fixing_1_volume_template = config_entry.options.get(CONF_STATE_TEMPLATE_FIXING_1_VOLUME, "")
        self.fixing_2_rate_template = config_entry.options.get(CONF_STATE_TEMPLATE_FIXING_2_RATE, "")
        self.fixing_2_volume_template = config_entry.options.get(CONF_STATE_TEMPLATE_FIXING_2_VOLUME, "")

    def get_data(self) -> TgeEntityStoredData | None:
        return self._calculated_data

    @property
    def name(self) -> str:
        return self.base_name()

    def base_name(self) -> str:
        return DEFAULT_NAME

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}"

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN,)},
            "name": self.base_name(),
            "configuration_url": URL,
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {}

    @callback
    def _handle_coordinator_update(self) -> None:
        today = datetime.date.today()
        last_data: TgeData | None = self.coordinator.data
        if last_data is None:
            return
        for day_data in last_data.data:
            self._stored_data.cache[day_data.date] = day_data
        _LOGGER.debug("cleaning up: {}", self._stored_data.cache)
        keys = [*self._stored_data.cache.keys()]
        for key in keys:
            if key < today:
                self._stored_data.cache.pop(key)

        self._calculated_data = self._calculate_stored_data(self._stored_data)
        self.async_write_ha_state()

    @property
    def extra_restore_state_data(self) -> TgeEntityStoredData:
        return TgeEntityStoredData.from_dict(self._stored_data.as_dict())

    async def async_added_to_hass(self) -> None:
        last_extra_data = await self.async_get_last_extra_data()
        _LOGGER.debug("Restored last data: {}", last_extra_data)
        if last_extra_data is None:
            self._stored_data = TgeEntityStoredData({})
        else:
            self._stored_data = TgeEntityStoredData.from_dict(last_extra_data.as_dict())
        self._calculated_data = self._calculate_stored_data(self._stored_data)
        await super().async_added_to_hass()

    def _calculate_stored_data(self, data: TgeEntityStoredData) -> TgeEntityStoredData:
        if data.cache is None:
            return TgeEntityStoredData({})
        new_data = {}
        for date, date_data in data.cache.items():
            new_data[date] = self._calculate_all_templates(date_data)
        return TgeEntityStoredData(new_data)

    def _calculate_all_templates(self, data: TgeDayData) -> TgeDayData:
        return TgeDayData(data.date, list(map(lambda h: self._calculate_templates(h), data.hours)))

    def _calculate_templates(self, data: TgeHourData) -> TgeHourData:
        templated_fixing1_rate = self._calculate_template(data, self.fixing_1_rate_template, data.fixing1_rate)
        templated_fixing1_volume = self._calculate_template(data, self.fixing_1_volume_template, data.fixing1_volume)
        templated_fixing2_rate = self._calculate_template(data, self.fixing_2_rate_template, data.fixing2_rate)
        templated_fixing2_volume = self._calculate_template(data, self.fixing_2_volume_template, data.fixing2_volume)
        return TgeHourData(data.time, templated_fixing1_rate, templated_fixing1_volume, templated_fixing2_rate,
                           templated_fixing2_volume)

    def _calculate_template(self, data: TgeHourData, template: str, default: float) -> float:
        if template == "":
            return default
        now_func = lambda: data.time
        return Template(template, self.hass).async_render(
            {
                PARAMETER_FIXING_1_RATE: data.fixing1_rate,
                PARAMETER_FIXING_1_VOLUME: data.fixing1_volume,
                PARAMETER_FIXING_2_RATE: data.fixing2_rate,
                PARAMETER_FIXING_2_VOLUME: data.fixing2_volume,
                "now": now_func
            }
        )
