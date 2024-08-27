from typing import Final
from datetime import timedelta

from homeassistant.const import Platform

DOMAIN: Final = "tge"
DEFAULT_NAME: Final = "TGE"
DEFAULT_UPDATE_INTERVAL: Final = timedelta(minutes=1)
URL: Final = 'https://tge.pl/energia-elektryczna-rdn'

UNIT_CURRENCY_PLN: Final = "zł"

PLATFORMS = [
    Platform.SENSOR
]