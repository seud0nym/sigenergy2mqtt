"""Stable exception taxonomy for every cloud-control backend."""


class CloudControlError(Exception):
    pass


class CloudControlAuthError(CloudControlError):
    pass


class CloudControlRateLimitedError(CloudControlError):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class CloudControlRejectedError(CloudControlError):
    def __init__(self, message: str, vendor_code: str | None = None) -> None:
        super().__init__(message)
        self.vendor_code = vendor_code


class CloudControlUnsupportedError(CloudControlError):
    pass


class CloudControlUnavailableError(CloudControlError):
    pass
