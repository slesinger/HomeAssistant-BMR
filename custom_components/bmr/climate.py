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
from homeassistant.components.climate.const import (SUPPORT_TARGET_TEMPERATURE, ATTR_HVAC_MODE, HVAC_MODE_OFF, HVAC_MODE_AUTO, HVAC_MODE_COOL, CURRENT_HVAC_OFF, CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL, CURRENT_HVAC_IDLE)

from homeassistant.const import (STATE_ON, STATE_OFF, CONF_NAME, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, TEMP_CELSIUS, ATTR_TEMPERATURE)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=60)
SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE
_LOGGER = logging.getLogger(__name__)
DEFAULT_NAME = "BMR"
STATE_MANUAL = 'manual'
STATE_UNKNOWN = 'unknown'
BMR_WARN_CANNOTCONNECT = 9
HVAC_MODES = [HVAC_MODE_OFF, HVAC_MODE_AUTO, HVAC_MODE_COOL]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    import pybmr
    host = config.get(CONF_HOST)
    user = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    sensor_name = config.get(CONF_NAME)
    channels = [
        { "name": "Hala",      "floor": 0, "room": 14 },
        { "name": "Loznice",   "floor": 1, "room": 15 },
        { "name": "Technicka", "floor": 2, "room": 16 },
        { "name": "Chodba",    "floor": 3, "room": 17 },
        { "name": "Jidelna",   "floor": 4, "room": 18 },
        { "name": "Obyvak",    "floor": 5, "room": 19 },
        { "name": "Satna",     "floor": 6, "room": 20 },
        { "name": "Kuba",      "floor": 7, "room": 21 },
        { "name": "Chodba2",   "floor": 8, "room": 22 },
        { "name": "Maja",      "floor": 9, "room": 23 },
        { "name": "Koupelna",  "floor": 10},
        { "name": "Koupelna2", "floor": 11},
        { "name": "Zebrik1",   "room" : 12},
        { "name": "Zebrik2",   "room" : 13}
        ]

    bmr = pybmr.Bmr(host, user, password)
    cnt = bmr.getNumCircuits()
    if cnt == None:
        raise Exception("Cannot connect to BMR")

    devices = []
    if channels == None:
        for circuit_id in range(cnt):
            device = Bmr(bmr, circuit_id)
            devices.append(device)
    else:
        for channel in channels:
            device = Bmr(bmr, channel.get('room'), channel.get('floor'), channel['name'])
            devices.append(device)
    add_devices(devices)


class Bmr(ClimateDevice):

    def __init__(self, bmr, circuit_id, floor_circuit_id=None, channel_name=None):
        import pybmr
        self._circuit_id = circuit_id
        self._floor_circuit_id = floor_circuit_id
        self._bmr = bmr
        self._warning = None
        self._name = None
        self._channel_name = channel_name
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
        if self._channel_name != None:
            return '{}'.format(self._channel_name)
        else:
            return '{}'.format(self._name)

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
        return float(self._target_temperature)

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
        was_filled = False
        self._warning = None
        if self._floor_circuit_id != None:
            floor_status = self._bmr.getStatus(self._floor_circuit_id)
            if(floor_status != None):
                self.manualUpdateFill(floor_status, 'floor')
                was_filled = True

        if self._circuit_id != None:
            status = self._bmr.getStatus(self._circuit_id)
            if(status != None):
                self.manualUpdateFill(status, 'room')
                was_filled = True
        else: # Ensure required attributes are filled
            if self._current_temperature == None:
                self._current_temperature = floor_status['current_temp']
            if self._target_temperature == None:
                self._target_temperature = floor_status['required_temp']

        if was_filled == False:
            self._warning = BMR_WARN_CANNOTCONNECT
            self._current_temperature = None
            self._target_temperature = None
            self._max_allowed_floor_temperature = None
            self._current_floor_temperature = None
            self._current_hvac_mode = None
            self._current_hvac_action = None


    # It is assumed that for channels having both floor and room circuits the floor will get filled first and will get overwritten by room eventually
    def manualUpdateFill(self, status, type):
        self._name = status['name']
        if status['summer'] == 0 and status['cooling'] == 0 and status['heating'] == 0:
            self._current_hvac_action = CURRENT_HVAC_IDLE
        if status['summer'] == 0 and status['cooling'] == 1 and status['heating'] == 0:
            self._current_hvac_action = CURRENT_HVAC_COOL
        if status['summer'] == 1 and status['heating'] == 0:
            self._current_hvac_action = CURRENT_HVAC_OFF
        if status['heating'] == 1:
            self._current_hvac_action = CURRENT_HVAC_HEAT
        #self._? = status['enabled']
        if type == 'room':
            self._current_temperature = status['current_temp']
            self._target_temperature = status['required_temp']
        if type == 'floor':
            self._current_floor_temperature = status['current_temp']
            self._max_allowed_floor_temperature = status['required_temp']
        self._warning = status['warning'] #TODO room warning overwrites floor warning, needs condition here


    def set_hvac_mode(self, hvac_mode):
        #self._current_hvac_mode = HVAC_MODE_OFF
        #self.bmr.setMode(0)
        self.manualUpdate()

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        id = self._circuit_id
        if id == None:
            id = self._floor_circuit_id
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        elif(temperature >= 10 and temperature<= 27):
            self.bmr.setTemperature(temperature, id)
            self.manualUpdate()
        else:
            _LOGGER.warn("Chosen temperature=%s is incorrect. It needs to be between 10 and 27.", str(temperature))


