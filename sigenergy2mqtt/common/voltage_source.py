from enum import StrEnum


class VoltageSource(StrEnum):
    PHASE_A = "phase-a"
    PHASE_B = "phase-b"
    PHASE_C = "phase-c"
    L_N_AVG = "l/n-avg"  # line to neutral average
    L_L_AVG = "l/l-avg"  # line to line average
    PV = "pv"  # average across PV strings
