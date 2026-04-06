"""sigenergy2mqtt persistence package.

Provides centralised state persistence with disk + MQTT retained message redundancy.
The module-level ``state_store`` singleton is the primary interface for all
persistence operations throughout the application.

Usage::

    from sigenergy2mqtt.persistence import state_store

    # During startup (after MQTT broker config is available):
    await state_store.initialise(
        active_config.mqtt,
        active_config.persistent_state_path,
        active_config.persistence,
    )

    # Save / load / delete:
    await state_store.save("sensor", "my_key.state", "123.45")
    value = await state_store.load("sensor", "my_key.state")
    await state_store.delete("sensor", "my_key.state")

    # During shutdown:
    state_store.shutdown()
"""

from .state_store import StateStore

state_store: StateStore = StateStore()

__all__ = ["StateStore", "state_store"]
