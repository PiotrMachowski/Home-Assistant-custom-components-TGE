import datetime
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (DOMAIN, UNIT_CURRENCY_PLN, ATTRIBUTE_PRICES, ATTRIBUTE_PRICES_TODAY)
from .entity import TgeEntity
from .update_coordinator import TgeUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator: TgeUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        TgeFixing1RateSensor(coordinator, entry),
        TgeFixing1VolumeSensor(coordinator, entry),
        TgeFixing2RateSensor(coordinator, entry),
        TgeFixing2VolumeSensor(coordinator, entry)
    ]
    async_add_entities(entities)


class TgeSensor(SensorEntity, TgeEntity):
    def __init__(self, coordinator: TgeUpdateCoordinator, config_entry: ConfigEntry):
        super().__init__(coordinator, config_entry)

    @property
    def unique_id(self):
        return f"{super().unique_id}_sensor"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {}


class TgeFixing1RateSensor(TgeSensor):

    def __init__(self, coordinator: TgeUpdateCoordinator, config_entry: ConfigEntry):
        super().__init__(coordinator, config_entry)
        self._attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float | None:
        data = self.get_data()
        now_hour = datetime.datetime.now().hour
        hour_data = list(filter(lambda h: h.time.hour == now_hour, data.hours))
        if len(hour_data) > 0:
            return hour_data[0].fixing1_rate
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        output = super().extra_state_attributes
        data = self.get_data()
        if data is not None:
            prices_today = list(map(lambda d: {"time": d.time, "price": d.fixing1_rate}, data.hours))
            output[ATTRIBUTE_PRICES_TODAY] = prices_today
            output[ATTRIBUTE_PRICES] = prices_today
        return output

    @property
    def available(self) -> bool:
        return super().available and self.get_data() is not None

    @property
    def unique_id(self):
        return f"{super().unique_id}_fixing1_rate"

    @property
    def icon(self):
        return "mdi:cash"

    @property
    def name(self):
        return f"{self.base_name()} Fixing 1 Rate"

    @property
    def state_class(self) -> SensorStateClass:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return f"{UNIT_CURRENCY_PLN}/{UnitOfEnergy.MEGA_WATT_HOUR}"


class TgeFixing1VolumeSensor(TgeSensor):

    def __init__(self, coordinator: TgeUpdateCoordinator, config_entry: ConfigEntry):
        super().__init__(coordinator, config_entry)
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> float | None:
        data = self.get_data()
        now_hour = datetime.datetime.now().hour
        hour_data = list(filter(lambda h: h.time.hour == now_hour, data.hours))
        if len(hour_data) > 0:
            return hour_data[0].fixing1_volume
        return None

    @property
    def available(self) -> bool:
        return super().available and self.get_data() is not None

    @property
    def unique_id(self):
        return f"{super().unique_id}_fixing1_volume"

    @property
    def icon(self):
        return "mdi:meter-electric"

    @property
    def name(self):
        return f"{self.base_name()} Fixing 1 Volume"

    @property
    def state_class(self) -> SensorStateClass:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfEnergy.MEGA_WATT_HOUR


class TgeFixing2RateSensor(TgeSensor):

    def __init__(self, coordinator: TgeUpdateCoordinator, config_entry: ConfigEntry):
        super().__init__(coordinator, config_entry)
        self._attr_suggested_display_precision = 2
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> float | None:
        data = self.get_data()
        now_hour = datetime.datetime.now().hour
        hour_data = list(filter(lambda h: h.time.hour == now_hour, data.hours))
        if len(hour_data) > 0:
            return hour_data[0].fixing2_rate
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        output = super().extra_state_attributes
        data = self.get_data()
        if data is not None:
            prices_today = list(map(lambda d: {"time": d.time, "price": d.fixing2_rate}, data.hours))
            output[ATTRIBUTE_PRICES_TODAY] = prices_today
            output[ATTRIBUTE_PRICES] = prices_today
        return output

    @property
    def available(self) -> bool:
        return super().available and self.get_data() is not None

    @property
    def unique_id(self):
        return f"{super().unique_id}_fixing2_rate"

    @property
    def icon(self):
        return "mdi:cash"

    @property
    def name(self):
        return f"{self.base_name()} Fixing 2 Rate"

    @property
    def state_class(self) -> SensorStateClass:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return f"{UNIT_CURRENCY_PLN}/{UnitOfEnergy.MEGA_WATT_HOUR}"


class TgeFixing2VolumeSensor(TgeSensor):

    def __init__(self, coordinator: TgeUpdateCoordinator, config_entry: ConfigEntry):
        super().__init__(coordinator, config_entry)
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> float | None:
        data = self.get_data()
        now_hour = datetime.datetime.now().hour
        hour_data = list(filter(lambda h: h.time.hour == now_hour, data.hours))
        if len(hour_data) > 0:
            return hour_data[0].fixing2_volume
        return None

    @property
    def available(self) -> bool:
        return super().available and self.get_data() is not None

    @property
    def unique_id(self):
        return f"{super().unique_id}_fixing2_volume"

    @property
    def icon(self):
        return "mdi:meter-electric"

    @property
    def name(self):
        return f"{self.base_name()} Fixing 2 Volume"

    @property
    def state_class(self) -> SensorStateClass:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfEnergy.MEGA_WATT_HOUR
