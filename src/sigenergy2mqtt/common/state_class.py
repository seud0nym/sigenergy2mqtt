from enum import StrEnum

# Source: https://github.com/home-assistant/core/blob/dev/homeassistant/components/sensor/const.py#L527


class StateClass(StrEnum):
    """State class for sensors."""

    MEASUREMENT = "measurement"
    """The state represents a measurement in present time, not a historical aggregation such as statistics or a prediction of the future.

    Examples of what should be classified SensorStateClass.MEASUREMENT are:
        - current temperature
        - humidity
        - electric power

    Examples of what should not be classified as SensorStateClass.MEASUREMENT:
        - Forecasted temperature for tomorrow
        - yesterday's energy consumption
        - anything else that doesn't include the current measurement.

    For supported sensors, statistics of hourly min, max and average sensor readings is updated every 5 minutes.
    """

    MEASUREMENT_ANGLE = "measurement_angle"
    """Similar to the above SensorStateClass.MEASUREMENT, the state represents a measurement in present time for angles measured in degrees (°). 

    Examples of what should be classified SensorStateClass.MEASUREMENT_ANGLE are:
        - current wind direction
    """

    TOTAL = "total"
    """The state represents a total amount that can both increase and decrease, for example, a net energy meter.

    Statistics of the accumulated growth or decline of the sensor's value since it was first added is updated every 5 minutes. 
    
    This state class should not be used for sensors where the absolute value is interesting instead of the accumulated growth 
    or decline, for example remaining battery capacity or CPU load; in such cases state class SensorStateClass.MEASUREMENT 
    should be used instead.
    """

    TOTAL_INCREASING = "total_increasing"
    """Similar to SensorStateClass.TOTAL, with the restriction that the state represents a monotonically increasing positive total 
    which periodically restarts counting from 0, for example, a daily amount of consumed gas, weekly water consumption or lifetime 
    energy consumption. 
    
    Statistics of the accumulated growth of the sensor's value since it was first added is updated every 5 minutes. 
    
    A decreasing value is interpreted as the start of a new meter cycle or the replacement of the meter.
    """
