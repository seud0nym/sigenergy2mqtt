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

        # Extracting groups and converting to integers where applicable
        self.platform = int(match.group(1))
        self.release = int(match.group(2))
        self.variant = int(match.group(3))
        self.service_pack = int(match.group(4))

        # Build number and Special ID are optional
        self.build = int(match.group(5)) if match.group(5) else None
        self.special_id = match.group(6) if match.group(6) else None

    def __repr__(self):
        return (
            "FirmwareVersion("
            f"Platform={self.platform}, Release={self.release}, Variant={self.variant}, "
            f"SPC={self.service_pack}, Build={self.build}, SpecialID='{self.special_id}'"
            ")"
        )
