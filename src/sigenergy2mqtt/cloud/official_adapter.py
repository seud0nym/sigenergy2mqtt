"""Reserved integration point for Sigenergy's official OAuth API.

The public API does not yet document instant-control cancellation and status
semantics sufficiently to implement the :class:`CloudControlPort` contract.
"""


class OfficialCloudAdapter:
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "The official Sigenergy cloud adapter is not available yet"
        )
