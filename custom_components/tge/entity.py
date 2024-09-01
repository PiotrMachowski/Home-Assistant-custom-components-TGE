from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity, ExtraStoredData
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .connector import TgeData, TgeHourData
from .const import DEFAULT_NAME, DOMAIN, URL
from .update_coordinator import TgeUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class TgeEntityStoredData(ExtraStoredData):
    cache: dict[datetime.date, TgeData] | None = None

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
            value = TgeData.from_dict(v)
            parsed[date] = value
        return TgeEntityStoredData(parsed)


class TgeEntity(RestoreEntity, CoordinatorEntity):

    def __init__(self, coordinator: TgeUpdateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._stored_data: TgeEntityStoredData = TgeEntityStoredData({})

    def get_data(self) -> TgeEntityStoredData | None:
        return self._stored_data

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
        self._stored_data.cache[last_data.date] = last_data
        _LOGGER.debug("cleaning up: {}", self._stored_data.cache)
        for key in self._stored_data.cache.keys():
            if key < today:
                self._stored_data.cache.pop(key)

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
        await super().async_added_to_hass()
