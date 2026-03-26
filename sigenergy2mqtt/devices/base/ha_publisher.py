import abc
import asyncio
import json
import logging
from pathlib import Path
from random import uniform
from typing import TYPE_CHECKING, Any

import paho.mqtt.client as mqtt

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.mqtt import MqttHandler
from sigenergy2mqtt.sensors.base import Sensor

if TYPE_CHECKING:
    from .device import Device

# Constants for Home Assistant republish timing
HA_REPUBLISH_MIN_JITTER = 0.0
HA_REPUBLISH_MAX_JITTER = 3.0


class HaPublisherMixin(abc.ABC):
    """Mixin providing Home Assistant MQTT discovery and availability publishing.

    Encapsulates all HA-facing publish behaviour: discovery payloads, availability
    topics, sensor attributes, state republishing on HA restart, and the periodic
    discovery republish background task.

    Intended to be mixed into Device. The attributes and abstract method declared
    below are the contract that the concrete class must fulfil.
    """

    # Plain attributes provided by the concrete class.
    name: str
    log_identity: str
    children: list["Device"]
    _shutdown_event: asyncio.Event

    # Properties and methods that must be implemented by the concrete class.
    # Declared as abstract so Pyright sees them as properties throughout the mixin,
    # matching the @property implementations in Device.

    @property
    @abc.abstractmethod
    def online(self) -> bool:
        """Whether the device is currently considered online."""
        ...

    @property
    @abc.abstractmethod
    def sensors(self) -> dict[str, Sensor]:
        """All sensors directly owned by this device, keyed by unique_id."""
        ...

    @property
    @abc.abstractmethod
    def unique_id(self) -> str:
        """The primary unique identifier for this device."""
        ...

    @abc.abstractmethod
    def get_all_sensors(self, search_children: bool = True) -> dict[str, Sensor]:
        """Return all sensors owned by this device, optionally including child devices."""
        ...

    async def on_ha_state_change(
        self,
        modbus_client: ModbusClient | None,
        mqtt_client: mqtt.Client,
        ha_state: str,
        source: str,
        mqtt_handler: MqttHandler,
    ) -> bool:
        """Handle a Home Assistant availability state change notification.

        When HA comes online, waits a short random jitter period (to avoid thundering
        herd on broker restart) then republishes discovery and forces all sensors to
        republish their current state. This recovers HA's view of the device after
        an HA restart or MQTT broker reconnect.

        See: https://www.home-assistant.io/integrations/mqtt/#birth-and-last-will-messages

        Args:
            modbus_client: The Modbus client, if available, passed through to sensor
                           publish calls.
            mqtt_client:   The MQTT client used for publishing.
            ha_state:      The HA availability state string, typically "online" or
                           "offline".
            source:        Descriptive string identifying the source of the state
                           change, used for logging.
            mqtt_handler:  The MqttHandler used to coordinate discovery publication.

        Returns:
            True if the online handler completed successfully, False if it was
            cancelled (e.g. during device shutdown) or if ha_state is not "online".
        """
        if ha_state == "online":
            seconds = uniform(HA_REPUBLISH_MIN_JITTER, HA_REPUBLISH_MAX_JITTER)
            logging.info(f"{self.log_identity} received online state from Home Assistant ({source=}): Republishing discovery and forcing republish of all sensors in {seconds:.1f}s")
            try:
                await asyncio.sleep(seconds)  # https://www.home-assistant.io/integrations/mqtt/#birth-and-last-will-messages
                await mqtt_handler.wait_for(2, self.name, self.publish_discovery, mqtt_client, clean=False)
                for sensor in self.get_all_sensors(search_children=True).values():
                    await sensor.publish(mqtt_client, modbus_client=modbus_client, republish=True)
                return True
            except asyncio.CancelledError:
                logging.debug(f"{self.log_identity} on_ha_state_change sleep interrupted")
                return False
        else:
            return False

    def publish_attributes(self, mqtt_client: mqtt.Client, clean: bool = False, propagate: bool = True) -> None:
        """Publish MQTT attribute messages for all sensors on this device.

        Args:
            mqtt_client: The MQTT client used for publishing.
            clean:       If True, publishes empty/null payloads to clear retained
                         attribute messages.
            propagate:   If True (default), recursively publishes attributes for
                         all child devices.
        """
        for sensor in self.sensors.values():
            sensor.publish_attributes(mqtt_client, clean=clean)
        if propagate:
            for device in self.children:
                device.publish_attributes(mqtt_client, clean=clean, propagate=propagate)

    def publish_availability(self, mqtt_client: mqtt.Client, ha_state: str | None, qos: int = 2) -> None:
        """Publish this device's availability status to its HA availability topic.

        Publishes to "{discovery_prefix}/device/{unique_id}/availability" with
        retain=True. Recursively publishes availability for all child devices.

        Args:
            mqtt_client: The MQTT client used for publishing.
            ha_state:    The availability state string (e.g. "online", "offline",
                         or None to clear the retained message).
            qos:         MQTT QoS level. Defaults to 2.
        """
        logging.info(f"{self.log_identity} publishing {ha_state} availability")
        mqtt_client.publish(f"{active_config.home_assistant.discovery_prefix}/device/{self.unique_id}/availability", ha_state, qos, True)
        for device in self.children:
            device.publish_availability(mqtt_client, ha_state)

    def publish_discovery(self, mqtt_client: mqtt.Client, clean: bool = False) -> mqtt.MQTTMessageInfo | None:
        """Publish or clear the Home Assistant MQTT discovery payload for this device.

        In normal mode (clean=False), collects discovery components from all sensors,
        assembles the full device discovery JSON (including "dev", "o", and "cmps"
        keys), and publishes it with retain=True to the HA discovery topic. If no
        publishable components exist, publishes a null payload to clear any stale
        retained discovery message.

        In clean mode (clean=True), clears the availability topic first, then
        publishes a null payload to clear the discovery topic.

        If debug logging is enabled, the discovery JSON is also written to disk at
        active_config.persistent_state_path for inspection.

        Calls publish_attributes() for this device (without propagating to children,
        since children will publish their own attributes when their own discovery is
        published). Recursively calls publish_discovery() on all child devices.

        Args:
            mqtt_client: The MQTT client used for publishing.
            clean:       If True, clears retained discovery and availability messages
                         instead of publishing new ones.

        Returns:
            The MQTTMessageInfo from the final mqtt_client.publish() call, or None.
        """
        topic = f"{active_config.home_assistant.discovery_prefix}/device/{self.unique_id}/config"
        if clean:
            logging.debug(f"{self.log_identity} cleaning availability")
            self.publish_availability(mqtt_client, None, qos=0)  # Availability is always retained
            logging.debug(f"{self.log_identity} cleaning discovery")
            info = mqtt_client.publish(topic, None, qos=0, retain=True)  # Clear retained messages
        else:
            components: dict[str, Any] = {}
            for sensor in self.sensors.values():
                components.update(sensor.get_discovery(mqtt_client))
            if components:
                discovery: dict[str, Any] = {}
                discovery["dev"] = self
                discovery["o"] = active_config.origin
                discovery["cmps"] = components
                discovery_json = json.dumps(discovery, allow_nan=False, indent=2, sort_keys=False)
                logging.debug(f"{self.log_identity} publishing discovery")
                if active_config.log_level == logging.DEBUG:
                    discovery_dump = Path(active_config.persistent_state_path, f"{self.unique_id}.discovery.json")
                    with discovery_dump.open("w") as f:
                        f.write(discovery_json)
                    logging.debug(f"{self.log_identity} discovery JSON dumped to {discovery_dump.resolve()}")
                info = mqtt_client.publish(topic, discovery_json, qos=2, retain=True)
            else:
                logging.debug(f"{self.log_identity} publishing empty availability (No components found)")
                self.publish_availability(mqtt_client, None, qos=0)
                logging.debug(f"{self.log_identity} publishing empty discovery (No components found)")
                info = mqtt_client.publish(topic, None, qos=0, retain=True)  # Clear retained messages
        self.publish_attributes(mqtt_client, clean, propagate=False)  # Don't propagate to children because it will happen automatically when child discovery is published
        for device in self.children:
            device.publish_discovery(mqtt_client, clean=clean)
        return info

    async def republish_discovery(self, mqtt_client: mqtt.Client) -> None:
        """Periodically republish the HA discovery payload at the configured interval.

        Runs as a background coroutine alongside the sensor scan group tasks.
        Sleeps in 1-second increments and republishes when the configured interval
        has elapsed. Exits when the device goes offline, the shutdown event is set,
        or the task is cancelled.

        Args:
            mqtt_client: The MQTT client used for publishing discovery payloads.
        """
        wait = active_config.home_assistant.republish_discovery_interval
        while self.online and not self._shutdown_event.is_set() and active_config.home_assistant.republish_discovery_interval > 0:
            try:
                await asyncio.sleep(1)
                wait -= 1
                if wait <= 0:
                    logging.info(f"{self.log_identity} re-publishing discovery")
                    self.publish_discovery(mqtt_client, clean=False)
                    wait = active_config.home_assistant.republish_discovery_interval
            except asyncio.CancelledError:
                logging.debug(f"{self.log_identity} republish_discovery sleep interrupted")
                break
