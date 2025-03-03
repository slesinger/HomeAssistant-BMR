"""
Support for BMR HC64 Heating Regulation.

configuration.yaml

sensor:
  - platform: bmr
    base_url: http://ip-address/
    user: user
    password: password
    circuits:
        - circuit: 0
          name: Kitchen
        - circuit: 1
          name: Living room
"""

__version__ = "0.7"

import logging
import socket
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, UnitOfTemperature
from homeassistant.helpers.entity import Entity
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

# Max difference between two subsequent temperature measurements.
MAX_TEMPERATURE_DELTA = 5.0


def setup_platform(hass, config, add_entities, discovery_info=None):
    import pybmr

    base_url = config.get(CONF_BASE_URL)
    user = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    bmr = pybmr.Bmr(base_url, user, password)
    sensors = []
    for circuit_config in config.get(CONF_CIRCUITS):
        sensors.append(BmrCircuitTemperature(bmr, circuit_config))
        sensors.append(BmrCircuitTargetTemperature(bmr, circuit_config))

    add_entities(sensors)


class BmrCircuitTemperatureBase(Entity):
    """ Base class for temperature reporting sensors.
    """

    def __init__(self, bmr, config):
        self._bmr = bmr
        self._config = config

        self._circuit = {}

    @property
    def unit_of_measurement(self):
        """ Return the unit of measurement.
        """
        return UnitOfTemperature.CELSIUS

    @property
    def device_state_attributes(self):
        return {
            "enabled": self._circuit.get("enabled"),
            "user_offset": self._circuit.get("user_offset"),
            "max_offset": self._circuit.get("max_offset"),
            "warning": self._circuit.get("warning"),
            "heating": self._circuit.get("heating"),
            "cooling": self._circuit.get("cooling"),
            "low_mode": self._circuit.get("low_mode"),
            "summer_mode": self._circuit.get("summer_mode"),
            "temperature": self._circuit.get("temperature"),
            "target_temperature": self._circuit.get("target_temperature"),
        }

    @throttle(timedelta(seconds=30))
    def update(self):
        """ Fetch new state data for the sensor.
            This is the only method that should fetch new data for Home Assistant.
        """
        try:
            circuit = self._bmr.getCircuit(self._config.get(CONF_CIRCUIT_ID))
            if circuit["temperature"] is None:
                _LOGGER.warn("BMR HC64 controller returned temperature as None, trying again later.")
            elif self._circuit and abs(circuit["temperature"] - self._circuit["temperature"]) >= MAX_TEMPERATURE_DELTA:
                _LOGGER.warn(
                    "BMR HC64 controller returned temperature which is too different from the previously seen value."
                )
            else:
                self._circuit = circuit
        except socket.timeout:
            _LOGGER.warn("Read from BMR HC64 controller timed out. Retrying later.")


class BmrCircuitTemperature(BmrCircuitTemperatureBase):
    """ Sensor for reporting the current temperature in BMR HC64 heating circuit.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._unique_id = f"{self._bmr.getUniqueId()}-sensor-{self._config.get(CONF_CIRCUIT_ID)}-temperature"

    @property
    def name(self):
        """ Return the name of the sensor.
        """
        return f"BMR HC64 {self._config.get(CONF_NAME)} temperature"

    @property
    def unique_id(self):
        """ Return unique ID of the entity.
        """
        return self._unique_id

    @property
    def state(self):
        """ Return the state of the sensor.
        """
        return self._circuit.get("temperature")


class BmrCircuitTargetTemperature(BmrCircuitTemperatureBase):
    """ Sensor for reporting the current temperature in BMR HC64 heating circuit.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._unique_id = f"{self._bmr.getUniqueId()}-sensor-{self._config.get(CONF_CIRCUIT_ID)}-target-temperature"

    @property
    def name(self):
        """ Return the name of the sensor.
        """
        return f"BMR HC64 {self._config.get(CONF_NAME)} target temperature"

    @property
    def unique_id(self):
        """ Return unique ID of the entity.
        """
        return self._unique_id

    @property
    def state(self):
        """ Return the state of the sensor.
        """
        return self._circuit.get("target_temperature")
