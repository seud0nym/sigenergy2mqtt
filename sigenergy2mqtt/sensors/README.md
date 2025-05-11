# Derived Sensors

In addition to the values read from the Modbus registers, `sigenergy2mqtt` calculates the following additional sensors:

## Plant

| Cacluated Sensor | Source/Calculation |
|------------------|--------|
| BatteryChargingPower | BatteryPower &gt; 0 |
| BatteryDischargingPower | BatteryPower &lt; 0 |
| GridSensorExportPower | GridSensorActivePower &lt; 0 &times; -1 |
| GridSensorLifetimeExportEnergy<sup>3</sup> | Riemann &sum; of GridSensorExportPower |
| GridSensorDailyExportEnergy<sup>3</sup> | GridSensorLifetimeExportEnergy &minus; GridSensorLifetimeExportEnergy at last midnight |
| GridSensorImportPower | GridSensorActivePower &gt; 0 |
| GridSensorLifetimeImportEnergy<sup>3</sup> | Riemann &sum; of GridSensorImportPower |
| GridSensorDailyImportEnergy<sup>3</sup> | GridSensorLifetimeImportEnergy &minus; GridSensorLifetimeImportEnergy at last midnight |
| SmartPort.PVPowerSensor | &sum; of all configured SmartPort MQTT sources and SmartPort modules | 
| TotalPVPower<sup>1</sup> | PlantPVPower &plus; SmartPort.PVPowerSensor |
| PlantConsumedPower | (either PlantPVPower _or_ TotalPVPower)<sup>2</sup> &plus; GridSensorActivePower &minus; BatteryPower |
| PlantLifetimeConsumedEnergy<sup>3</sup> | Riemann &sum; of PlantConsumedPower |
| PlantDailyConsumedEnergy<sup>3</sup> | PlantLifetimeConsumedEnergy &minus; PlantLifetimeConsumedEnergy at last midnight |
| PlantLifetimePVEnergy<sup>3</sup> | Riemann &sum; of (either PlantPVPower _or_ TotalPVPower)<sup>2</sup> |
| PlantDailyPVEnergy<sup>3</sup> | PlantLifetimePVEnergy &minus; PlantLifetimePVEnergy at last midnight |
| PlantDailyChargeEnergy<sup>3</sup> | &sum; of DailyChargeEnergy across all Inverters associated with the Plant |
| PlantDailyDischargeEnergy<sup>3</sup> | &sum; of DailyDischargeEnergy across all Inverters associated with the Plant |
| PlantAccumulatedChargeEnergy<sup>3</sup> | &sum; of AccumulatedChargeEnergy across all Inverters associated with the Plant |
| PlantAccumulatedDischargeEnergy<sup>3</sup> | &sum; of AccumulatedDischargeEnergy across all Inverters associated with the Plant |

Notes:
1. TotalPVPower is _only_ calculated when the SmartPort configuration is enabled and a module or MQTT source for the SmartPort PV production has been specified.
1. PlantPVPower is used unless TotalPVPower has been calculated
3. The Sigenergy Modbus Protocol does not define any daily or lifetime accumulation registers, except for charging and discharging at the inverter ESS (Energy Storage System) level.


## Inverters

| Cacluated Sensor | Source/Calculation |
|------------------|--------|
| InverterBatteryChargingPower | ChargeDischargePower &gt; 0 |
| InverterBatteryDischargingPower | ChargeDischargePower &lt; 0 &times; -1 |
| InverterDailyPVEnergy | InverterLifetimePVEnergy &minus; InverterLifetimePVEnergy at last midnight |
| InverterLifetimePVEnergy | Riemann &sum; of InverterPVPower |

## Inverter Strings

| Cacluated Sensor | Source/Calculation |
|------------------|--------|
| PVStringDailyEnergy | PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight |
| PVStringLifetimeEnergy | Riemann &sum; of PVStringPower |
| PVStringPower | PVVoltageSensor &times; PVCurrentSensor |
