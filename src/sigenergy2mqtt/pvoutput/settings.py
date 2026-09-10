class PVOutputSettings:
    """PVOutput service settings."""

    donator: bool = False
    interval: int = 5  # Interval in minutes for PVOutput status updates
    interval_updated: float | None = None
