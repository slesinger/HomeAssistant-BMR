"""
Support for BMR HC64 Heating Regulation.

configuration.yaml

  climate:
    - platform: bmr
      base_url: http://192.168.1.254/
      username: !secret bmr_username
      password: !secret bmr_password
      away_temperature: 18
      min_temperature: 18
      max_temperature: 35
      circuits:
        - name: Kitchen
          circuit: 8
          schedule:
            day_schedules: [1]
            starting_day: 1
          schedule_override: 16
          min_temperature: 20
          max_temperature: 24
"""

__version__ = "0.7"

import logging
import socket
from datetime import timedelta

import voluptuous as vol


from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_PASSWORD,
    CONF_USERNAME,
    TEMP_CELSIUS,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle as throttle

PRESET_NORMAL = "Normal"
PRESET_AWAY = "Away"

_LOGGER = logging.getLogger(__name__)

TEMP_MIN = 7.0
TEMP_MAX = 35.0

CONF_BASE_URL = "base_url"
CONF_CIRCUITS = "circuits"
CONF_NAME = "name"
CONF_CIRCUIT_ID = "circuit"
CONF_SCHEDULE = "schedule"
CONF_DAY_SCHEDULES = "day_schedules"
CONF_STARTING_DAY = "starting_day"
CONF_SCHEDULE_OVERRIDE = "schedule_override"
CONF_AWAY_TEMPERATURE = "away_temperature"
CONF_CAN_COOL = "can_cool"
CONF_MIN_TEMPERATURE = "min_temperature"
CONF_MAX_TEMPERATURE = "max_temperature"

CONF_CIRCUIT = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_CIRCUIT_ID): vol.All(vol.Coerce(int), vol.Range(min=0, max=63)),
        vol.Required(CONF_SCHEDULE): vol.Schema(
            {
                vol.Required(CONF_DAY_SCHEDULES): vol.All(
                    cv.ensure_list, [vol.All(vol.Coerce(int), vol.Range(min=0, max=63))]
                ),
                vol.Optional(CONF_STARTING_DAY): vol.All(vol.Coerce(int), vol.Range(min=1, max=21)),
            }
        ),
        vol.Required(CONF_SCHEDULE_OVERRIDE): vol.All(vol.Coerce(int), vol.Range(min=0, max=63)),
        vol.Optional(CONF_MIN_TEMPERATURE): vol.All(vol.Coerce(int), vol.Range(min=TEMP_MIN, max=TEMP_MAX)),
        vol.Optional(CONF_MAX_TEMPERATURE): vol.All(vol.Coerce(int), vol.Range(min=TEMP_MIN, max=TEMP_MAX)),
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_BASE_URL): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_AWAY_TEMPERATURE): vol.All(vol.Coerce(int), vol.Range(min=TEMP_MIN, max=TEMP_MAX)),
        vol.Optional(CONF_CAN_COOL): vol.Coerce(bool),
        vol.Optional(CONF_MIN_TEMPERATURE): vol.All(vol.Coerce(int), vol.Range(min=TEMP_MIN, max=TEMP_MAX)),
        vol.Optional(CONF_MAX_TEMPERATURE): vol.All(vol.Coerce(int), vol.Range(min=TEMP_MIN, max=TEMP_MAX)),
        vol.Required(CONF_CIRCUITS): vol.All(cv.ensure_list, [CONF_CIRCUIT]),
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    import pybmr

    base_url = config.get(CONF_BASE_URL)
    user = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    bmr = pybmr.Bmr(base_url, user, password)
    entities = [
        BmrRoomClimate(
            bmr=bmr,
            config=circuit_config,
            away_temperature=config.get(CONF_AWAY_TEMPERATURE, TEMP_MIN),
            can_cool=config.get(CONF_CAN_COOL, False),
            min_temperature=config.get(CONF_MIN_TEMPERATURE),
            max_temperature=config.get(CONF_MAX_TEMPERATURE),
        )
        for circuit_config in config.get(CONF_CIRCUITS)
    ]
    add_entities(entities)


class BmrRoomClimate(ClimateEntity):
    """ Entity representing a room heated by the BMR HC64 controller unit.

        Usually the room has two temperature sensors (circuits): floor and room
        sensor.  The controller will heat the room if BOTH sensors report lower
        current temperature then their target temperature.

        For simplicity it is recommended to set the floor sensor to a fixed
        temperature that is almost always higher than the actual floor
        temperature (e.g. 32 degrees) so that the floor sensor always "wants"
        to heat the room. This way the room temperature can be easily
        controlled just by the room sensor.

        This HA entity takes advantage of this approach. It will only modify
        settings related to the room cirtuit and will not touch settings of the
        floor circuit. It is up to the user to configure the floor circuit
        using the HC64 web UI.

        This class supports the following HVAC modes:

        - HVAC_MODE_AUTO - Automatic mode. HC64 controller will manage the
          temperature automatically according to its configuration.

        - HVAC_MODE_HEAT/HVAC_MODE_HEAT_COOL - Override the target temperature
          manually. Useful for temporarily increase/decrease the target
          temperature in the room.  Note that this will switch the circuit to a
          special "override" schedule and configure this schedule with the
          target temperature. HVAC_MODE_HEAT_COOL is for water-based circuits
          that can also cool.

        - HVAC_MODE_OFF - Turn off the heating circuit by assigning it to
          "summer mode" and turning the summer mode on.

          NOTE: Make sure to remove all circuits from summer mode when using
          the plugin for the first time. Otherwise any circuits assigned to the
          summer mode will be also turned off when the user switches a
          circuit into the HVAC_MODE_OFF mode.

          NOTE #2: The HC64 controller is slow AF so updates after changing
          something (such as HVAC mode) may take a while to show in Home
          Assistant UI. Even several minutes.
      """

    def __init__(
        self, bmr, config, away_temperature=18.0, can_cool=False, min_temperature=TEMP_MIN, max_temperature=TEMP_MAX
    ):
        self._bmr = bmr
        self._config = config
        self._away_temperature = away_temperature
        self._can_cool = can_cool
        self._min_temperature = min_temperature
        self._max_temperature = max_temperature

        self._unique_id = f"{self._bmr.getUniqueId()}-climate-{self._config.get(CONF_CIRCUIT_ID)}"

        # Initial state
        self._circuit = {}
        self._schedule = {}
        self._low_mode = {}
        self._summer_mode = None
        self._summer_mode_assignments = []

    @property
    def name(self):
        """ Return the name of the climate entity.
        """
        return f"BMR HC64 {self._config.get(CONF_NAME)}"

    @property
    def unique_id(self):
        """ Return unique ID of the entity.
        """
        return self._unique_id

    @property
    def temperature_unit(self):
        """ The unit of temperature measurement for the system.
        """
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """ Current temperature.
        """
        return self._circuit.get("temperature")

    @property
    def target_temperature(self):
        """ Currently set target temperature.
        """
        return self._circuit.get("target_temperature")

    @property
    def min_temp(self):
        return self._config.get(CONF_MIN_TEMPERATURE) or self._min_temperature or TEMP_MIN

    @property
    def max_temp(self):
        return self._config.get(CONF_MAX_TEMPERATURE) or self._max_temperature or TEMP_MAX

    @property
    def hvac_modes(self):
        """ Supported HVAC modes.

        See docs: https://developers.home-assistant.io/docs/core/entity/climate/#hvac-modes
        """
        if self._can_cool:
            return [HVAC_MODE_OFF, HVAC_MODE_AUTO, HVAC_MODE_HEAT_COOL]
        else:
            return [HVAC_MODE_OFF, HVAC_MODE_AUTO, HVAC_MODE_HEAT]

    @property
    def hvac_mode(self):
        """ Current HVAC mode.

            Return HVAC_MODE_OFF if the summer mode for the circuit is turned
            on. Summer mode essentially means the circuit is turned off.

            Return HVAC_MODE_HEAT/HVAC_MODE_HEAT_COOL if the user manually
            overrode the target temperature. The override works by reassigning
            the circuit to a special "override" schedule specified in the
            configuration. The target temperature for the "override" schedule
            is set by the set_temperature() method.

            Return HVAC_MODE_AUTO if the controller is managing everything
            automatically according to its configuration.
        """
        if (
            self._summer_mode
            and self._summer_mode_assignments
            and self._summer_mode_assignments[self._config.get(CONF_CIRCUIT_ID)]
        ):
            return HVAC_MODE_OFF
        elif [self._config.get(CONF_SCHEDULE_OVERRIDE)] == self._schedule.get("day_schedules"):
            if self._can_cool:
                return HVAC_MODE_HEAT_COOL
            else:
                return HVAC_MODE_HEAT
        else:
            # The controller is managing everything automatically according to
            # configured schedules.
            return HVAC_MODE_AUTO

    def set_hvac_mode(self, hvac_mode):
        """ Set HVAC mode.
        """
        if hvac_mode == HVAC_MODE_OFF:
            # Turn on the HVAC_MODE_OFF. This will turn off the heating/cooling
            # of the given circuit. This works by:
            #
            # - Adding the circuit to summer mode
            # - Turning the summer mode ON
            #
            # NOTE: Sometimes (usually) there are also other circuits assigned
            # to summer mode, especially if this plugin is used for the first
            # time. If there are also other circutis assigned to summer mode
            # and summer mode is turned on they will be turned off too. Make
            # sure to remove any circuits from the summer mode manually when
            # using the plugin for the first time.
            self._bmr.setSummerModeAssignments([self._config.get(CONF_CIRCUIT_ID)], True)
            self._bmr.setSummerMode(True)
        else:
            # Turn HVAC_MODE_OFF off and restore normal operation.
            #
            # - Remove the circuit from the summer mode assignments
            # - If there aren't any circuits assigned to summer mode anymore
            #   turn the summer mode OFF.
            self._bmr.setSummerModeAssignments([self._config.get(CONF_CIRCUIT_ID)], False)
            if not any(self._bmr.getSummerModeAssignments()):
                self._bmr.setSummerMode(False)

        if hvac_mode in (HVAC_MODE_HEAT, HVAC_MODE_HEAT_COOL):
            # Turn on the HVAC_MODE_HEAT. This will assign the "override"
            # schedule to the circuit. The "override" schedule is used for
            # setting the custom target temperature (see set_temperature()
            # below).
            self._bmr.setCircuitSchedules(
                self._config.get(CONF_CIRCUIT_ID), [self._config.get(CONF_SCHEDULE_OVERRIDE)],
            )
        else:
            # Turn off the HVAC_MODE_HEAT/HVAC_MODE_HEAT_COOL and restore
            # normal operation.
            #
            # - Assign normal schedules to the circuit
            self._bmr.setCircuitSchedules(
                self._config.get(CONF_CIRCUIT_ID),
                self._config.get(CONF_SCHEDULE)[CONF_DAY_SCHEDULES],
                self._config.get(CONF_SCHEDULE).get(CONF_STARTING_DAY, 1),
            )

        if hvac_mode == HVAC_MODE_AUTO:
            # Turn on the HVAC_MODE_AUTO. Currently this is no-op, as the
            # normal operation is restored in the else branches above.
            pass

    @property
    def hvac_action(self):
        """ What is the climate device currently doing (cooling, heating, idle).
        """
        if (
            self._summer_mode
            and self._summer_mode_assignments
            and self._summer_mode_assignments[self._config.get(CONF_CIRCUIT_ID)]
        ):
            return CURRENT_HVAC_OFF
        elif self._circuit.get("heating"):
            return CURRENT_HVAC_HEAT
        elif self._circuit.get("cooling"):
            return CURRENT_HVAC_COOL
        else:
            return CURRENT_HVAC_IDLE

    @property
    def preset_modes(self):
        """ Supported preset modes.
        """
        return [PRESET_NORMAL, PRESET_AWAY]

    @property
    def preset_mode(self):
        """ Current preset mode.
        """
        if self._low_mode.get("enabled"):
            return PRESET_AWAY
        else:
            return PRESET_NORMAL

    def set_preset_mode(self, preset_mode):
        """ Set preset mode.
        """
        if preset_mode == PRESET_AWAY:
            self._bmr.setLowMode(True, self._away_temperature)
        else:
            self._bmr.setLowMode(False)

    @property
    def supported_features(self):
        """ Supported features
        """
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

    def set_temperature(self, **kwargs):
        """ Set new target temperature for the circuit. This works by
            modifying the special "override" schedule and assigning the
            schedule to the circuit.

            This is being done to avoid overwriting the normal schedule used
            for HVAC_MODE_AUTO.
        """
        temperature = kwargs.get(ATTR_TEMPERATURE)
        self._bmr.setSchedule(
            self._config.get(CONF_SCHEDULE_OVERRIDE),
            f"{self._config.get(CONF_NAME)} override",
            [{"time": "00:00", "temperature": temperature}],
        )
        if self.hvac_mode not in (HVAC_MODE_HEAT, HVAC_MODE_HEAT_COOL):
            if self._can_cool:
                self.set_hvac_mode(HVAC_MODE_HEAT_COOL)
            else:
                self.set_hvac_mode(HVAC_MODE_HEAT)

    @throttle(timedelta(seconds=30))
    def update(self):
        """ Fetch new state data for the controller. This is the only method
            that should fetch new data for Home Assistant.
        """
        try:
            circuit = self._bmr.getCircuit(self._config.get(CONF_CIRCUIT_ID))
            if circuit["temperature"] is None:
                _LOGGER.warn("BMR HC64 controller returned temperature as None, trying again later.")
            else:
                self._circuit = circuit
            self._schedule = self._bmr.getCircuitSchedules(self._config.get(CONF_CIRCUIT_ID))
            self._low_mode = self._bmr.getLowMode()
            self._summer_mode = self._bmr.getSummerMode()
            self._summer_mode_assignments = self._bmr.getSummerModeAssignments()
        except socket.timeout:
            _LOGGER.warn("Read from BMR HC64 controller timed out. Retrying later.")
