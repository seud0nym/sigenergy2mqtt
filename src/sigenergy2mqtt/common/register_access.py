from dataclasses import dataclass


@dataclass
class RegisterAccess:
    no_remote_ems: bool = False
    read_only: bool = True
    read_write: bool = True
    write_only: bool = True
