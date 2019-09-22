# HomeAssistant-BMR
Custom component - climate platform - for BMR HC64 Heating Controller units for Home Assistant

## Installation:
Copy file custom_components/bmr/climate.py to custom_components/bmr/climate.py

## Usage:
Add to configuration.yaml:

```
climate:
  - platform: bmr
    host: [IP ADDRESS TO ATREA UNIT]
    username: [USER NAME FOR WEB UI TO ATREA UNIT]
    password: [PASSWORD FOR WEB UI TO ATREA UNIT]
```

## Track Updates
This custom component can be tracked with the help of [custom-lovelace](https://github.com/ciotlosm/custom-lovelace).

In your configuration.yaml

```
custom_updater:
  component_urls:
    - https://raw.githubusercontent.com/slesinger/HomeAssistant-BMR/master/custom_updater.json
```

