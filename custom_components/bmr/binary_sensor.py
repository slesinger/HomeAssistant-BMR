"""
Support for BMR HC64 Heating Regulation.

configuration.yaml

binary_sensor:
  - platform: bmr
    base_url: http://ip-address/
    user: user
    password: password
"""

__version__ = "0.7"

import logging
import socket
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, BinarySensorEntity
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.util import Throttle as throttle

_LOGGER = logging.getLogger(__name__)

CONF_BASE_URL = "base_url"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_BASE_URL): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    import pybmr

    base_url = config.get(CONF_BASE_URL)
    user = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    bmr = pybmr.Bmr(base_url, user, password)
    sensors = [
        BmrControllerHDO(bmr),
    ]

    add_entities(sensors)


class BmrControllerHDO(BinarySensorEntity):
    """ Binary sensor for reporting HDO (low/high electricity tariff).
    """

    def __init__(self, bmr):
        self._bmr = bmr
        self._hdo = None

    @property
    def name(self):
        """ Return the name of the sensor.
        """
        return "BMR HC64 HDO"

    @property
    def is_on(self):
        """ Return the state of the sensor.
        """
        return bool(self._hdo)

    @throttle(timedelta(seconds=30))
    def update(self):
        """ Fetch new state data for the sensor.
            This is the only method that should fetch new data for Home Assistant.
        """
        try:
            self._hdo = self._bmr.getHDO()
        except socket.timeout:
            _LOGGER.warn("Read from BMR HC64 controller timed out. Retrying later.")
