# HomeAssistant-BMR

Home Assistant integration plugin for [BMR HC64 heating
controller](https://bmr.cz/produkty/regulace-topeni/rnet). This controller has
many quirks but overall it is quite usable in Home Assistant.  The plugin
provides entities from these HA domains:

- `binary_sensor`
- `climate`
- `sensor`
- `switch`


## Installation

For normal use, use HACS to install the plugin.

Alternatively you can install the plugin manually: copy `custom_components/` to
your Home Assistant config directory.


## Usage

### Binary Sensor

Provided entities:

- `binary_sensor.bmr_hc64_hdo`: Binary sensor for indicating whether the state
  of HDO (low/high electricity tariff)

Example configuration:

```
binary_sensor:
  - platform: bmr_hc64
    base_url: "http://192.168.3.254/"
    username: !secret bmr_username
    password: !secret bmr_password
```


### Climate

This works as a thermostat. it supports setting HVAC mode, setting target
temperature, power off and away mode.

Provided entities:

-  `climate.bmr_hc64_<name>` (for every configured circuit)

Example configuration:

```
climate:
  - platform: bmr_hc64
    base_url: "http://192.168.3.254/"
    username: !secret bmr_username
    password: !secret bmr_password
    away_temperature: 18.0
    circuits:
      - name: "Living room"
        circuit: 8
        schedule:
          day_schedules: [0]
        schedule_override: 16

      - name: "Kitchen"
        circuit: 9
        schedule:
          day_schedules: [1]
        schedule_override: 17

      # etc.
```

The `circuits` key specifies circuits that will be handled by the plugin.
Usually the circuit will correspond to the room it is located in, but sometimes
the circuit can heat multiple rooms as well.

The HC64 controller usually has two circuits per room - the "room" circuit
(measuring air temperature) and "floor" circuit (measuring floor temperature).
The heating starts when both circuits "want" to heat (their current temperature
is lower than their target temperature). This is unneccesarily complicated and
sometimes results in unpredictable behaviour so it is recommended to configure
the floor circuit in such a way that it almost always "wants" to heat by
setting its target temperature to a high value (e.g. 32 C) and control the
temperature using the "room" sensor. *This plugin assumes that your heating
setup works like this and the specified circuit is the "room circuit, not the
floor circuit.*

Supported HVAC modes:

- Auto: Let the heating controller manage the temperature automatically using
  the configured schedules in `circuits.schedule`. The key `day_schedules`
  contains up to 21 schedules that are rotated daily, similarly it's in the
  HC64 Web UI.

- Heating: Set target temperature for the circuit manually. Internally this
  works by switching the circuit to schedule specified in `schedule_override`
  and setting the override schedule to the user-defined target temperature.
  Make sure the override schedule is not used for something else. The reason
  for using a special schedule for overriding temperature is to preserve the
  schedule used in automatic mode.

- Off: Turn off the circuit. Internally this works by assigning the circuit
  into "summer mode" and turning the summer mode on. *When running the plugin
  for the first time make sure there are no circuits assigned to summer mode,
  otherwise turning the circuit off using this HVAC mode will turn these
  additional circuits as well*.

There is 1 "preset mode" available as well:

- "Away" mode: Turn on the "away" mode which will set the target temperature of
  all specified circuits to `away_temperature`. Intenally this works by turning
  on the "low" mode of the HC64 controller assigning the circuits. *When
  running the plugin for the first time make sure your room circuits are
  assigned to "low" mode, this plugin will not change low mode circuit
  assignments (as opposed to the "summer" mode assignments, which it does change).*


### Sensor

Read-only sensor for reporting current and target temperature of circuits.

Provided entities:

- `sensor.bmr_hc64_<name>_temperature` (for every configured circuit)
- `sensor.bmr_hc64_<name>_target_temperature` (for every configured circuit)

Example configuration:

```
sensor:
  - platform: bmr_hc64
    base_url: "http://192.168.3.254/"
    username: !secret bmr_username
    password: !secret bmr_password
    circuits:
      - name: "Living room"
        circuit: 8

      - name: "Kitchen"
        circuit: 9
```

### Switch

Switches for controlling the "Away" mode and "Power".

Provided entities:

- `switch.bmr_hc64_away`
- `switch.bmr_hc64_power`

Example configuration:

```
switch:
  - platform: bmr_hc64
    base_url: "http://192.168.3.254/"
    username: !secret bmr_username
    password: !secret bmr_password
    circuits:
      - name: "Living room"
        circuit: 8

      - name: "Kitchen"
        circuit: 9
```

The `switch.bmr_hc64_away` switch will turn on/off the "Away" mode globally. As
described above, internally this works by turning on the "low" mode.

The `switch.bmr_hc64_power` switch controls power of all circuits globally. As
described above, internally this works by and assigning all the specified
circuits to "summer" mode and enabling the "summer" mode.


[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
