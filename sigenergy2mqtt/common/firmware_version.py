import re


class FirmwareVersion:
    """Parses and stores components of a Sigenergy firmware version string."""

    # Regex breakdown:
    # V(\d+)       -> 'V' followed by digits
    # R(\d+)       -> 'R' followed by digits
    # C(\d+)       -> 'C' followed by digits
    # SPC(\d+)     -> 'SPC' followed by digits
    # (?:B(\d+))?  -> Optional 'B' followed by digits
    # ([A-Z])?     -> Optional trailing single letter (Special Identifier)
    PATTERN = r"V(\d+)R(\d+)C(\d+)SPC(\d+)(?:B(\d+))?([A-Z])?"

    def __init__(self, version_string: str):
        match = re.search(self.PATTERN, version_string)

        if not match:
            raise ValueError(f"Invalid firmware format: {version_string}")

        self._version = version_string  # Store original version string for reference

        # Extracting groups and converting to integers where applicable
        self._platform = int(match.group(1))
        self._release = int(match.group(2))
        self._variant = int(match.group(3))
        self._service_pack = int(match.group(4))
        # Build number and Special ID are optional
        self._build = int(match.group(5)) if match.group(5) else None
        self._special_id = match.group(6) if match.group(6) else None

    @property
    def platform(self) -> int:
        """Major platform identifier (V component)."""
        return self._platform

    @property
    def release(self) -> int:
        """Release number (R component)."""
        return self._release

    @property
    def variant(self) -> int:
        """Variant/configuration code (C component)."""
        return self._variant

    @property
    def service_pack(self) -> int:
        """Service pack level (SPC component)."""
        return self._service_pack

    @property
    def build(self) -> int | None:
        """Optional build number (B component)."""
        return self._build

    @property
    def special_id(self) -> str | None:
        """Optional trailing special identifier letter."""
        return self._special_id

    def __repr__(self):
        return f"FirmwareVersion(Platform={self.platform}, Release={self.release}, Variant={self.variant}, SPC={self.service_pack}, Build={self.build}, SpecialID='{self.special_id}')"

    def __str__(self):
        return self._version
