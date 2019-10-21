"""
Support for BMR HC64 Heating Regulation.

configuration.yaml

sensor:
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

from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_USERNAME, CONF_PASSWORD)
from homeassistant.components.climate.const import (HVAC_MODE_OFF, HVAC_MODE_AUTO, HVAC_MODE_COOL)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=60)
_LOGGER = logging.getLogger(__name__)
HVAC_MODES = [HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_AUTO]


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
    bmr_common = BmrCommon(bmr)
    sensors.append(bmr_common)
    add_entities(sensors)

    def handle_event(event):
        if event.data['entity_id']== 'input_select.bmr_rezim':
            state = event.data['new_state'].as_dict()['state']
            bmr_common.set_hvac_mode(state)

    hass.bus.listen('state_changed', handle_event)



class BmrCommon(Entity):

    def __init__(self, bmr):
        import pybmr
        self._bmr = bmr
        self._icon = "mdi:restart"
        self._current_hvac_mode = None
        self.update()

    @property
    def should_poll(self):
        return True

    @property
    def name(self):
        return 'Rezimy BMR Regulatoru'

    @property
    def icon(self):
        return self._icon


    @property
    def state(self):
        return self._current_hvac_mode

    @Throttle(MIN_TIME_BETWEEN_SCANS)
    def update(self):
        self.manualUpdate()

    def manualUpdate(self):
        is_summer = self._bmr.loadSummerMode()
        is_low = self._bmr.loadLows()
        if is_summer == True:
            self._current_hvac_mode = HVAC_MODE_OFF
            self._icon = "mdi:radiator-off"
            return
        elif is_summer == False and is_low == True:
            self._current_hvac_mode = HVAC_MODE_COOL
            self._icon = "mdi:snowflake"
            return
        elif is_summer == False and is_low == False:
            self._current_hvac_mode = HVAC_MODE_AUTO
            self._icon = "mdi:brightness-auto"
            return
        else:
            self._current_hvac_mode = None
            self._icon = "mdi:help"
            return

    def set_hvac_mode(self, hvac_mode):

        if hvac_mode == 'auto':
            hvac_mode = HVAC_MODE_AUTO
        if hvac_mode == 'rozvrh':
            hvac_mode = HVAC_MODE_AUTO
        if hvac_mode == 'utlum':
            hvac_mode = HVAC_MODE_COOL
        if hvac_mode == 'vypnuto':
            hvac_mode = HVAC_MODE_OFF

        if hvac_mode == HVAC_MODE_AUTO: # summer off, low off
            self._bmr.saveSummerMode(False)
            self._bmr.lowSave(False)
        elif hvac_mode == HVAC_MODE_OFF:
            self._bmr.saveSummerMode(True)
            self._bmr.lowSave(True)
        elif hvac_mode == HVAC_MODE_COOL:
            self._bmr.saveSummerMode(False)
            self._bmr.lowSave(True)
        else:
            _LOGGER.warn("Unsupported HVAC mode {}".format(hvac_mode))
        self.manualUpdate()

