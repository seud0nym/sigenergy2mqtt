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

## Minimum Requirements

- A Sigenergy ESS or PV Inverter, with the Modbus-TCP server enabled by your installer
- The Home Assistant [Mosquitto broker app](https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md) or an existing MQTT broker that you have already integrated with Home Assistant.

## Installation

1. Select the `sigenergy2mqtt` app in the Home Assistant Apps Store
1. Enter the configuration details on the Configuration tab, and save.
1. Start the app from the Info tab.

## Post-Installation

You can set the current values for daily accumulation sensors from the mySigen app through the MQTT device screen. The screen contains controls for inputting the values.

## MQTT Devices

For each Sigenergy host, an MQTT device will be created in Home Assistant. A host can be configured in the app Configuration tab, or it can be discovered automatically.

The first host will be called `Sigenergy Plant` (plant is the terminology used in the "Sigenergy Modbus Protocol", and is in the context of a power plant). Each plant will have one or more related MQTT devices, such as `Sigenergy Plant Grid Sensor` and `Sigenergy Plant Statistics`. Plants will also have associated inverters, and their names will include the model and serial number (e.g. `SigenStor CMUxxxxxxxxxx Energy Controller`). Each inverter will have an an Energy Storage System device (e.g. `SigenStor CMUxxxxxxxxxx ESS`) and as many PV String devices as the inverter supports. Chargers will be named `Sigenergy AC Charger` and `Sigenergy DC Charger`.

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

## Beta Channel

A beta channel is available for testing new features and bug fixes before stable releases. Beta apps require **Advanced Mode** enabled in your Home Assistant profile.

> [!WARNING]
> Running both stable and beta versions simultaneously is not recommended. The app can _not_ detect or prevent this.
> It is up to _you_ to ensure that you do not run both the stable and beta releases simultaneously!


### Automatic

[![Open your Home Assistant instance and show the add app repository dialogue with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fseud0nym%2Fhome-assistant-addons%23beta)

### Manual

1. Navigate in your Home Assistant frontend to **Settings** -> **Apps** -> **App store**.
1. Click the three vertical dots in the top-right corner and select **Repositories**.
1. Enter https://github.com/seud0nym/home-assistant-addons#beta and click the **ADD** button.
1. Close the Repositories window and refresh.
