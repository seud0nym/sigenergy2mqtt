# Home Assistant

## Install Mosquitto Broker

Follow [these instructions](https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md) to install the Mosquitto MQTT Broker app, if you have not already done so (unless you already have an MQTT broker available).

## Set up Repository

You need to add my Home Assistant Apps repository first, and then you will be able to add the `sigenergy2mqtt` app.

### Automatically Add Repository

[![Open your Home Assistant instance and show the add app repository dialogue with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fseud0nym%2Fhome-assistant-addons)

### Manually Add Repository

Follow these steps to get the app repository installed on your Home Assistant system:

1. Navigate in your Home Assistant frontend to **Settings** -> **Apps** -> **App store**.
1. Click the three vertical dots in the top-right corner and select **Repositories**.
1. Enter https://github.com/seud0nym/home-assistant-addons and click the **ADD** button.
1. Close the Repositories window and refresh.

## Installation

1. Select the `sigenergy2mqtt` app in the Home Assistant Apps Store
1. Enter the configuration details on the Configuration tab, and save.
1. Start the app from the Info tab.

## Post-Installation

You can set the current values for the daily accumulation sensors from the mySigen app through the MQTT device screen. The screen contains controls for inputting the values.

## Home Assistant Auto-Discovery

For each host defined in the `modbus` section of the configuration file, an MQTT device will be created in Home Assistant. The first device will be called `Sigenergy Plant` (plant is the terminology used in the "Sigenergy Modbus Protocol", and is in the context of a power plant). Each plant will have one or more related devices, such as `Sigenergy Plant Grid Sensor` and `Sigenergy Plant Statistics` and if applicable, `Sigenergy Plant Smart-Port`. Plants will also have associated inverters, and their names will include the model and serial number (e.g. `SigenStor CMUxxxxxxxxxx Energy Controller`). Each inverter will have an an Energy Storage System device (e.g. `SigenStor CMUxxxxxxxxxx ESS`) and as many PV String devices as the inverter supports. Chargers will be named `Sigenergy AC Charger` and `Sigenergy DC Charger`.

Example:
```
Sigenergy Plant
   ├─ Sigenergy Plant Grid Code
   ├─ Sigenergy Plant Grid Sensor
   ├─ Sigenergy Plant Smart-Port
   ├─ Sigenergy Plant Statistics
   ├─ Sigenergy AC Charger
   ├─ SigenStor CMUxxxxxxxxxx Energy Controller (ID 1)
   │    ├─ SigenStor CMUxxxxxxxxxx ESS
   │    ├─ SigenStor CMUxxxxxxxxxx PV String 1
   │    ├─ SigenStor CMUxxxxxxxxxx PV String 2
   │    ├─ SigenStor CMUxxxxxxxxxx PV String 3
   │    ├─ SigenStor CMUxxxxxxxxxx PV String 4
   │    └─ Sigenergy DC Charger
   └─ SigenStor CMUyyyyyyyyyy Energy Controller (ID 2)
        ├─ SigenStor CMUyyyyyyyyyy ESS
        ├─ SigenStor CMUyyyyyyyyyy PV String 1
        ├─ SigenStor CMUyyyyyyyyyy PV String 2
        └─ Sigenergy DC Charger
```


## Alternatives

For Sigenergy systems, with no requirement to integrate with PVOutput, the [Sigenergy Local Modbus HACS integration](https://github.com/TypQxQ/Sigenergy-Local-Modbus) may be a better alternative for integration with Home Assistant.

| Feature | Sigenergy Local Modbus | sigenergy2mqtt  (Linux) | sigenergy2mqtt  (HA App) | Comments |
|:--------|:----------------------:|:-----------------------:|:---------------------------:|:---------|
| Pre-requisites | None | Python, MQTT broker | MQTT broker | |
| Installation | GUI | Manual | GUI | |
| Configuration| GUI | Edit configuration file | GUI and/or config file | |
| Home Assistant | HACS Integration | Optional MQTT Auto-discovery | MQTT Auto-discovery |
| PVOutput | No | Optional | Optional | |

