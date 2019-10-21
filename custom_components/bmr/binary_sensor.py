"""
Support for BMR HC64 Heating Regulation.

configuration.yaml

binary_sensor:
  - platform: bmr
    host: ip
    user: user
    password: password
"""

__version__ = "1.0"

import logging
import voluptuous as vol

from datetime import timedelta

from homeassistant.components.sensor import PLATFORM_SCHEMA

from homeassistant.const import (STATE_ON, STATE_OFF, CONF_NAME, CONF_HOST, CONF_USERNAME, CONF_PASSWORD)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=60)
_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    import pybmr
    host = config.get(CONF_HOST)
    user = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    bmr = pybmr.Bmr(host, user, password) # Test connectivity
    cnt = bmr.getNumCircuits()
    if cnt == None:
        raise Exception("Cannot connect to BMR")
    sensors = []
    sensors.append(Hdo(bmr))
    add_entities(sensors)


class Hdo(Entity):

    def __init__(self, bmr):
        import pybmr
        self._bmr = bmr
        self._icon = "mdi:restart"
        self._state = None
        self.update()

    @property
    def should_poll(self):
        return True

    @property
    def unit_of_measurement(self):
        return 'nizky tarif'

    @property
    def icon(self):
        return self._icon

    @property
    def is_on(self):
        return self._state

    @property
    def state(self):
        return STATE_ON if self._state else STATE_OFF

    @property
    def device_class(self):
        return 'plug'

    @Throttle(MIN_TIME_BETWEEN_SCANS)
    def update(self):
        self._state = self._bmr.loadHDO()
        self._icon = 'mdi:power-plug' if self._state else 'mdi:power-plug-off'


