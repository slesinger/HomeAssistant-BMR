"""
Support for BMR HC64 Heating Regulation.

configuration.yaml

switch:
  - platform: bmr
    base_url: http://ip-address/
    user: user
    password: password
    circuits:
      - name: "Workshop"
        circuit: 8

      - name: "Storage"
        circuit: 9
"""

__version__ = "0.7"

import logging
import socket
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.util import Throttle as throttle

_LOGGER = logging.getLogger(__name__)

CONF_BASE_URL = "base_url"
CONF_CIRCUITS = "circuits"
CONF_NAME = "name"
CONF_CIRCUIT_ID = "circuit"
CONF_CIRCUIT = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_CIRCUIT_ID): vol.All(vol.Coerce(int), vol.Range(min=0, max=63)),
    }
)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_BASE_URL): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_CIRCUITS): vol.All(cv.ensure_list, [CONF_CIRCUIT]),
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    import pybmr

    base_url = config.get(CONF_BASE_URL)
    user = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    bmr = pybmr.Bmr(base_url, user, password)
    sensors = [
        BmrControllerAwayMode(bmr),
        BmrControllerPowerSwitch(bmr, config.get(CONF_CIRCUITS)),
    ]

    add_entities(sensors)


class BmrControllerAwayMode(SwitchEntity):
    """ Switch for the away mode (in HC64 called "low mode"). This is a global
        state of the controller, not specific to a particular circuit. When the
        controller is in "low mode" target temperature of all circuits is set to a
        predefined temperature and no schedules are taken into account.
    """

    def __init__(self, bmr):
        self._bmr = bmr
        self._low_mode = {}

    @property
    def name(self):
        """ Return the name of the entity.
        """
        return "BMR HC64 Away"

    @property
    def device_class(self):
        return "switch"

    @property
    def is_on(self):
        """ Return the state of the sensor.
        """
        return self._low_mode.get("start_date") is not None

    @property
    def device_state_attributes(self):
        return {
            "start_date": self._low_mode.get("user_offset"),
            "end_date": self._low_mode.get("max_offset"),
            "temperature": self._low_mode.get("temperature"),
        }

    def turn_on(self):
        """ Turn on the Away mode.
        """
        self._bmr.setLowMode(True)

    def turn_off(self):
        """ Turn off the Away mode.
        """
        self._bmr.setLowMode(False)

    @throttle(timedelta(seconds=30))
    def update(self):
        """ Fetch new state data for the sensor.
            This is the only method that should fetch new data for Home Assistant.
        """
        try:
            self._low_mode = self._bmr.getLowMode()
        except socket.timeout:
            _LOGGER.warn("Read from BMR HC64 controller timed out. Retrying later.")


class BmrControllerPowerSwitch(SwitchEntity):
    """ Turn heating on/off (in HC64 called "summer mode"). This is a global
        state of the controller, not specific to a particular circuit.
    """

    def __init__(self, bmr, circuits):
        self._bmr = bmr
        self._circuits = circuits

        self._summer_mode = None
        self._summer_mode_assignments = {}

    @property
    def name(self):
        """ Return the name of the entity.
        """
        return "BMR HC64 Power"

    @property
    def device_class(self):
        return "switch"

    @property
    def is_on(self):
        """ Return the state of the sensor.
        """
        return not (
            self._summer_mode and all(self._summer_mode_assignments[x.get(CONF_CIRCUIT_ID)] for x in self._circuits)
        )

    def turn_on(self):
        """ Turn the power on. Which means turn the summer mode off and remove
            circuits from summer mode assignments.
        """
        self._bmr.setSummerMode(False)
        self._bmr.setSummerModeAssignments([x.get(CONF_CIRCUIT_ID) for x in self._circuits], False)

    def turn_off(self):
        """ Turn the power off. Which means turn the summer mode on and add
            circuits to the summer mode assignments.
        """
        self._bmr.setSummerMode(True)
        self._bmr.setSummerModeAssignments([x.get(CONF_CIRCUIT_ID) for x in self._circuits], True)

    @throttle(timedelta(seconds=30))
    def update(self):
        """ Fetch new state data for the sensor.
            This is the only method that should fetch new data for Home Assistant.
        """
        self._summer_mode = self._bmr.getSummerMode()
        self._summer_mode_assignments = self._bmr.getSummerModeAssignments()
