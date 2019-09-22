"""
Support for BMR HC64 Heating Regulation.

configuration.yaml

climate:
  - platform: bmr
    host: ip
    user: user
    password: password
"""

__version__ = "1.0"

import logging
import json
import voluptuous as vol
import re

from datetime import timedelta

from homeassistant.components.climate import (ClimateDevice, PLATFORM_SCHEMA)
from homeassistant.components.climate.const import (ATTR_HVAC_MODE, SUPPORT_TARGET_TEMPERATURE, HVAC_MODE_OFF, HVAC_MODE_AUTO, HVAC_MODE_COOL)

from homeassistant.const import (STATE_ON, STATE_OFF, CONF_NAME, CONF_HOST, CONF_USER, CONF_PASSWORD, TEMP_CELSIUS, ATTR_TEMPERATURE)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=60)
SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE
_LOGGER = logging.getLogger(__name__)
DEFAULT_NAME = "BMR"
STATE_MANUAL = 'manual'
STATE_UNKNOWN = 'unknown'
BMR_WARN_CANNOTCONNECT = 9
HVAC_MODES = [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_AUTO]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USER): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    import pybmr
    host = config.get(CONF_HOST)
    user = config.get(CONF_USER)
    password = config.get(CONF_PASSWORD)
    sensor_name = config.get(CONF_NAME)

    bmr = pybmr.Bmr(host, user, password)
    cnt = bmr.getNumCircuits()
    if cnt == None:
        raise Exception("Cannot connect to BMR")

    devices = []
    for circuit_id in range(cnt):
        Bmr(bmr, circuit_id)
        devices.append(device)
    add_devices(devices)


class Bmr(ClimateDevice):

    def __init__(self, bmr, circuit_id):
        import pybmr
        self._circuit_id = circuit_id
        self._bmr = bmr
        self._warning = None
        self._name = None
        self._current_temperature = None
        self._target_temperature = None
        self._max_allowed_floor_temperature = None
        self._current_floor_temperature = None
        self._current_hvac_mode = None
        self._current_hvac_action = None
        self._unit = "Status"
        self._icon = "mdi:alert-decagram"

        self.update()

    @property
    def should_poll(self):
        return True

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        return self._current_hvac_mode

    @property
    def supported_features(self):
        return SUPPORT_FLAGS

    @property
    def name(self):
        return '{}'.format(self._prefixName)
    
    @property
    def device_state_attributes(self):
        attributes = {}
        attributes['current_floor_temp'] = self._current_floor_temperature
        attributes['max_allowed_floor_temperature'] = self._max_allowed_floor_temperature
        attributes['warning'] = self._warning
        return attributes

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def target_temperature(self):
        return float(self._requested_temp)

    @property
    def hvac_modes(self):
        return HVAC_MODES

    @property
    def hvac_mode(self):
        return self._current_hvac_mode
    
    @property
    def preset_mode(self):
        if self._current_preset in (0, 1, 2, 3, 4):
            return PRESET_LIST[self._current_preset]
        else:
            return STATE_UNKNOWN

    @property
    def preset_modes(self):
        return PRESET_LIST
    
    @property
    def current_temperature(self):
        return float(self._current_temperature)
        
    @property
    def min_temp(self):
        return 10
        
    @property
    def max_temp(self):
        return 27

     @Throttle(MIN_TIME_BETWEEN_SCANS)
    def update(self):
        self.manualUpdate()
            
    def manualUpdate(self):
        status = self.bmr.getStatus(self._circuit_id)
        if(status != None):
            self._name = status['name']
            self._current_hvac_action = CURRENT_HVAC_IDLE if status['summer'] == 0 and status['cooling'] == 0 and status['heating'] == 0
            self._current_hvac_action = CURRENT_HVAC_COOL if status['summer'] == 0 and status['cooling'] == 1 and status['heating'] == 0
            self._current_hvac_action = CURRENT_HVAC_OFF if status['summer'] == 1 and status['heating'] == 0
            self._current_hvac_action = CURRENT_HVAC_HEAT if status['heating'] == 1
            #self._? = status['enabled']
            self._current_temperature = status['current_temp']
            self._target_temperature = status['required_temp']
            self._max_allowed_floor_temperature = None
            self._current_floor_temperature = None
            self._warning = status['warning']
        else:
            self._warning = BMR_WARN_CANNOTCONNECT
            self._current_temperature = None
            self._target_temperature = None
            self._max_allowed_floor_temperature = None
            self._current_floor_temperature = None
            self._current_hvac_mode = None
            self._current_hvac_action = None

    def turn_on(self):
        #self._current_hvac_mode = HVAC_MODE_ON
        #self.bmr.setMode(2)
        #self.bmr.exec()
        self.manualUpdate()

    def turn_off(self):
        #self._current_hvac_mode = HVAC_MODE_OFF
        #self.bmr.setMode(0)
        #self.bmr.exec()
        self.manualUpdate()

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        elif(temperature >= 10 and temperature<= 27):
            #self.bmr.setTemperature(temperature)
            #self.bmr.exec()
            self.manualUpdate()
        else:
            _LOGGER.warn("Chosen temperature=%s is incorrect. It needs to be between 10 and 27.", str(temperature))
        
            
