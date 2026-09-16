"""Stable exception taxonomy for every battery-control backend."""


class BatteryControlError(Exception):
    pass


class BatteryControlAuthError(BatteryControlError):
    pass


class BatteryControlRateLimitedError(BatteryControlError):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class BatteryControlRejectedError(BatteryControlError):
    def __init__(self, message: str, vendor_code: str | None = None) -> None:
        super().__init__(message)
        self.vendor_code = vendor_code


class BatteryControlUnsupportedError(BatteryControlError):
    pass


class BatteryControlUnavailableError(BatteryControlError):
    pass
