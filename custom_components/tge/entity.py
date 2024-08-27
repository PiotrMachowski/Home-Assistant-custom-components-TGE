from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .connector import TgeData
from .const import DEFAULT_NAME, DOMAIN, URL
from .update_coordinator import TgeUpdateCoordinator


class TgeEntity(CoordinatorEntity):

    def __init__(self, coordinator: TgeUpdateCoordinator, config_entry: ConfigEntry):
        super().__init__(coordinator)
        self.config_entry = config_entry

    def get_data(self) -> TgeData | None:
        return self.coordinator.data

    @property
    def name(self):
        return self.base_name()

    def base_name(self):
        return DEFAULT_NAME

    @property
    def unique_id(self):
        return f"{DOMAIN}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN,)},
            "name": self.base_name(),
            "configuration_url": URL,
        }
