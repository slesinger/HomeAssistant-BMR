# HomeAssistant-BMR
Custom component - climate platform - for BMR HC64 Heating Controller units for Home Assistant.

Producer's website: https://www.bmr.cz/menu-produkty/menu-regulace-vytapeni/webove-rozhrani-ovladani-hc64


## Manuel Installation:
Copy file custom_components/bmr/climate.py to custom_components/bmr/climate.py

## Usage:
Add this to configuration.yaml to respective sections:
```
climate:
  - platform: bmr
    host: [IP ADDRESS TO ATREA UNIT]
    username: [USER NAME FOR WEB UI TO ATREA UNIT]
    password: [PASSWORD FOR WEB UI TO ATREA UNIT]
    honza:
      - name: <name of room/circuit>
        schedule_mode_id: <Go to BMR web ui "Nastaveni rezimu" and count from top starting by 0>
        ai_mode_id: <Similar as above but this a mode dedicated by external script - out of scope>
        floor: <Go to BMR web ui "Nastaveni topeni okruhu" and count from top starting by 0. This circuit is supposed to fetch temperature from a floor sensor>
        room: <Go to BMR web ui "Nastaveni topeni okruhu" and count from top starting by 0. This circuit is supposed to fetch temperature from a room sensor>


# This is to display active overall mode read from the BMR
sensor:
  - platform: bmr
    host: 192.168.1.5
    username: hass
    password: !secret bmr

# HDO signal
binary_sensor:
  - platform: bmr
    host: 192.168.1.5
    username: hass
    password: !secret bmr

# This dropdown is used to set overall modes to BMR 
input_select:
  bmr_rezim:
    name: Režim topeni
    options:
      - auto
      - rozvrh
      - vypnuto
      - utlum
    icon: mdi:radiator
```

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
