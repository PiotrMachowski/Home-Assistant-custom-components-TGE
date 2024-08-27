from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "tge"
DEFAULT_NAME: Final = "TGE"
DEFAULT_UPDATE_INTERVAL: Final = timedelta(minutes=1)
URL: Final = 'https://tge.pl/energia-elektryczna-rdn'

ATTRIBUTE_PRICES_TODAY: Final = "prices_today"
ATTRIBUTE_PRICES: Final = "prices"

UNIT_CURRENCY_PLN: Final = "zł"

PLATFORMS = [
    Platform.SENSOR
]
