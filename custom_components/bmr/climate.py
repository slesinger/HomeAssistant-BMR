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

from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.components.climate import (ClimateDevice, PLATFORM_SCHEMA)
from homeassistant.components.climate.const import (SUPPORT_TARGET_TEMPERATURE, ATTR_HVAC_MODE, HVAC_MODE_OFF, HVAC_MODE_AUTO, HVAC_MODE_COOL, HVAC_MODE_HEAT_COOL, CURRENT_HVAC_OFF, CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL, CURRENT_HVAC_IDLE)

from homeassistant.const import (STATE_ON, STATE_OFF, CONF_NAME, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, TEMP_CELSIUS, ATTR_TEMPERATURE)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=60)
SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE
_LOGGER = logging.getLogger(__name__)
#DEFAULT_NAME = "BMR"
#STATE_MANUAL = 'manual'
#STATE_UNKNOWN = 'unknown'
#BMR_WARN_CANNOTCONNECT = 9
HVAC_MODES = [HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_AUTO, HVAC_MODE_HEAT_COOL]

CHANNELS = "honza"
NAME = "name"
SCH_MODE_ID = "schedule_mode_id"
AI_MODE_ID = "ai_mode_id"
FLOOR = "floor"
ROOM = "room"

CHANNEL_SCHEMA = vol.Schema(
    {
        vol.Required(NAME): cv.string,
        vol.Optional(SCH_MODE_ID): vol.All(vol.Coerce(int), vol.Range(min=0, max=31)),
        vol.Optional(AI_MODE_ID): vol.All(vol.Coerce(int), vol.Range(min=0, max=31)),
        vol.Optional(FLOOR): vol.All(vol.Coerce(int), vol.Range(min=0, max=31)),
        vol.Optional(ROOM): vol.All(vol.Coerce(int), vol.Range(min=0, max=31))
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CHANNELS): vol.All(cv.ensure_list, [CHANNEL_SCHEMA])
})
#    vol.Required(CHANNELS): vol.All(cv.ensure_list, [CHANNEL_SCHEMA])


def setup_platform(hass, config, add_devices, discovery_info=None):
    import pybmr
    host = config.get(CONF_HOST)
    user = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    bmr = pybmr.Bmr(host, user, password) # Test connectivity
    cnt = bmr.getNumCircuits()
    if cnt == None:
        raise Exception("Cannot connect to BMR")

    devices = []
    for channel in config.get(CHANNELS):
        devices.append(Bmr(bmr, CHANNEL_SCHEMA(channel)))
    add_devices(devices)


class Bmr(ClimateDevice):

    def __init__(self, bmr, config):
        import pybmr
        self._circuit_id = config.get(ROOM)
        self._floor_circuit_id = config.get(FLOOR)
        self._schedule_mode_id = config.get(SCH_MODE_ID)
        self._ai_mode_id = config.get(AI_MODE_ID)
        self._bmr = bmr
        self._warning = None
        self._name = None
        self._channel_name = config.get(NAME)
        self._current_temperature = None
        self._target_temperature = None
        self._max_allowed_floor_temperature = None
        self._current_floor_temperature = None
        self._current_hvac_mode = None
        self._current_hvac_action = None
        self._unit = "Status"
        self._icon = "mdi:restart"
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
    def hvac_action(self):
        return self._current_hvac_action
    
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
            self._icon = "mdi:null"



    # It is assumed that for channels having both floor and room circuits the floor will get filled first and will get overwritten by room eventually
    def manualUpdateFill(self, status, type):
        self._name = status['name']
        #_LOGGER.debug("BMR status in manual update {}".format(status))
        if status['summer'] == 0 and status['cooling'] == 0 and status['heating'] == 0:
            self._current_hvac_action = CURRENT_HVAC_IDLE
            self._current_hvac_mode = self.resolve_auto_mode()
            self._icon = "mdi:sleep"
        if status['summer'] == 0 and status['cooling'] == 1 and status['heating'] == 0:
            self._current_hvac_action = CURRENT_HVAC_COOL
            self._current_hvac_mode = HVAC_MODE_COOL
            self._icon = "mdi:snowflake"
        if status['summer'] == 1 and status['heating'] == 0:
            self._current_hvac_action = CURRENT_HVAC_OFF
            self._current_hvac_mode = HVAC_MODE_OFF
            self._icon = "mdi:white-balance-sunny"
        if status['heating'] == 1:
            self._current_hvac_action = CURRENT_HVAC_HEAT
            self._current_hvac_mode = self.resolve_auto_mode()
            self._icon = "mdi:radiator"
        if type == 'room':
            self._current_temperature = status['current_temp']
            self._target_temperature = status['required_temp']
        if type == 'floor':
            self._current_floor_temperature = status['current_temp']
            self._max_allowed_floor_temperature = status['required_temp']
        self._warning = status['warning'] #TODO room warning overwrites floor warning, needs condition here

    def resolve_auto_mode(self):
        mode = self._bmr.get_mode_id(self._circuit_id)
        #_LOGGER.debug("BMR resolve mode for {} is {} (ai {} / sch {})".format(self._circuit_id, mode, self._ai_mode_id, self._schedule_mode_id))
        if mode == self._ai_mode_id:
             return HVAC_MODE_AUTO
        elif mode == self._schedule_mode_id:
             return HVAC_MODE_HEAT_COOL
        else:
            return None


    def set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVAC_MODE_AUTO: # ai script
            self._bmr.set_mode_id(self._circuit_id, self._ai_mode_id)
            self._bmr.exclude_from_summer([self._floor_circuit_id, self._circuit_id])
            self._bmr.exclude_from_low([self._floor_circuit_id, self._circuit_id])
        elif hvac_mode == HVAC_MODE_HEAT_COOL: # schedule
            self._bmr.set_mode_id(self._circuit_id, self._schedule_mode_id)
            self._bmr.exclude_from_summer([self._floor_circuit_id, self._circuit_id])
            self._bmr.exclude_from_low([self._floor_circuit_id, self._circuit_id])
        elif hvac_mode == HVAC_MODE_OFF:
            self._bmr.include_to_summer([self._floor_circuit_id, self._circuit_id])
        elif hvac_mode == HVAC_MODE_COOL:
            self._bmr.exclude_from_summer([self._floor_circuit_id, self._circuit_id])
            self._bmr.include_to_low([self._floor_circuit_id, self._circuit_id])
        else:
            _LOGGER.warn("Unsupported HVAC mode {} for {}".format(hvac_mode, self._channel_name))
        self.manualUpdate()

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        # check if room is set to auto mode
        if self._ai_mode_id == None or self._current_hvac_mode != HVAC_MODE_AUTO:
            _LOGGER.warn("Temperature cannot be set if BMR room is not set to AUTO")
            pass

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        elif(temperature >= 10 and temperature<= 27):
            self._bmr.setTargetTemperature(temperature, self._ai_mode_id, self.name)
            self.manualUpdate()
        else:
            _LOGGER.warn("Chosen temperature=%s is incorrect. It needs to be between 10 and 27.", str(temperature))


