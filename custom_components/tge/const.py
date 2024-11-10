from datetime import timedelta
from typing import Final

from homeassistant.const import Platform, UnitOfEnergy

DOMAIN: Final = "tge"
DEFAULT_NAME: Final = "TGE"
DEFAULT_UPDATE_INTERVAL: Final = timedelta(minutes=1)
URL: Final = 'https://tge.pl/energia-elektryczna-rdn'

ATTRIBUTE_TODAY_SUFFIX: Final = "_today"
ATTRIBUTE_TOMORROW_SUFFIX: Final = "_tomorrow"
ATTRIBUTE_PRICES: Final = "prices"
ATTRIBUTE_VOLUMES: Final = "volumes"
ATTRIBUTE_PARAMETER_PRICE: Final = "price"
ATTRIBUTE_PARAMETER_VOLUME: Final = "volume"

PARAMETER_FIXING_1_RATE = "fixing1_rate"
PARAMETER_FIXING_1_VOLUME = "fixing1_volume"
PARAMETER_FIXING_2_RATE = "fixing2_rate"
PARAMETER_FIXING_2_VOLUME = "fixing2_volume"

UNIT_CURRENCY_Zl: Final = "zł"
UNIT_CURRENCY_GR: Final = "gr"

UNIT_ZL_MWH = f"{UNIT_CURRENCY_Zl}/{UnitOfEnergy.MEGA_WATT_HOUR}"
UNIT_GR_KWH = f"{UNIT_CURRENCY_GR}/{UnitOfEnergy.KILO_WATT_HOUR}"
UNIT_ZL_KWH = f"{UNIT_CURRENCY_Zl}/{UnitOfEnergy.KILO_WATT_HOUR}"

PLATFORMS = [
    Platform.SENSOR
]

CONF_UNIT: Final = "unit"
CONF_USE_STATE_TEMPLATES: Final = "use_state_templates"
CONF_STATE_TEMPLATE_FIXING_1_RATE: Final = "state_template_" + PARAMETER_FIXING_1_RATE
CONF_STATE_TEMPLATE_FIXING_1_VOLUME: Final = "state_template_" + PARAMETER_FIXING_1_VOLUME
CONF_STATE_TEMPLATE_FIXING_2_RATE: Final = "state_template_" + PARAMETER_FIXING_2_RATE
CONF_STATE_TEMPLATE_FIXING_2_VOLUME: Final = "state_template_" + PARAMETER_FIXING_2_VOLUME
