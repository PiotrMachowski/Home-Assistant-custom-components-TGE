"""Update coordinator for TGE integration."""
import datetime
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .connector import TgeConnector, TgeData
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class TgeUpdateCoordinator(DataUpdateCoordinator[TgeData]):

    def __init__(self, hass: HomeAssistant):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=DEFAULT_UPDATE_INTERVAL,
                         update_method=self.update_method)
        self.connector = TgeConnector()
        self._last_update_hour: datetime.date | None = None
        self._last_data: TgeData | None = None

    async def update_method(self) -> TgeData | None:
        return await self.hass.async_add_executor_job(self._update)

    def _update(self) -> TgeData:
        now = datetime.datetime.now()
        if self._should_update(now):
            self._last_update_hour = now.hour
            self._last_data = self.connector.get_data()
        return self._last_data

    def _should_update(self, now: datetime.datetime) -> bool:
        return (
                self._last_update_hour is None
                or now.hour != self._last_update_hour
                or self._last_data is None
        )
