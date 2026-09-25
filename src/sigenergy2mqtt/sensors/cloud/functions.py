"""Shared helper functions for cloud-backed sensors."""

from sigenergy2mqtt.config import active_config


def _identity(plant_index: int, station_id: str, suffix: str) -> tuple[str, str]:
    """Return the Home Assistant object and unique IDs for a cloud sensor.

    The object ID identifies the entity's cloud source, while the unique ID
    includes the cloud station ID so entities remain distinct between stations.
    """
    unique_prefix = active_config.home_assistant.unique_id_prefix
    return (
        f"{unique_prefix}_{plant_index}_cloud_{suffix}",
        f"{unique_prefix}_{plant_index}_{station_id}_{suffix}",
    )
