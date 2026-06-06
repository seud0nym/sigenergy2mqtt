"""Tests for PSS sensor class instantiation.

Each PSS sensor is a data class with a constructor. Instantiating them covers
the constructor code which is the main source of missing coverage in pss_read_only.py.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import Sensor


@pytest.fixture(autouse=True)
def pss_config():
    """Configure active_config for PSS sensor construction."""
    cfg = Config()
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.enabled = False
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.home_assistant.device_name_prefix = ""
    cfg.home_assistant.use_simplified_topics = False
    cfg.home_assistant.edit_percentage_with_box = False
    cfg.home_assistant.enabled_by_default = True
    cfg.home_assistant.sigenergy_local_modbus_naming = False
    cfg.persistent_state_path = Path(".")
    cfg.modbus = []

    with _swap_active_config(cfg):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            yield cfg

    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


PLANT_INDEX = 0
DEVICE_ADDRESS = 200  # Use a device address valid for PSS (NonInverter range)


class TestPSSBasicSensors:
    """Tests for basic PSS sensor instantiation."""

    def test_pss_model_type(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSModelType
        s = PSSModelType(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32500
        assert s.count == 15

    def test_pss_serial_number(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSSerialNumber
        s = PSSSerialNumber(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32515
        assert s.count == 10

    def test_pss_communication_status(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSCommunicationStatus
        s = PSSCommunicationStatus(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32525
        assert s.sanity_check.min_raw == 0
        assert s.sanity_check.max_raw == 2


class TestPSSTeleindication:
    """Tests for PSS teleindication alarm sensors."""

    def test_pss_teleindication1(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication1
        s = PSSTeleindication1(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32526
        # Test alarm bit decoding
        assert s.decode_alarm_bit(0) == "Measurement & control unit general trip"
        assert s.decode_alarm_bit(15) == "LA low voltage cabinet over-temperature trip"
        assert s.decode_alarm_bit(16) is None  # Out of range

    def test_pss_teleindication2(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication2
        s = PSSTeleindication2(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32527
        assert s.decode_alarm_bit(0) == "LB low voltage cabinet over-temperature trip"
        assert s.decode_alarm_bit(15) == "Medium voltage room over-temperature alarm"
        assert s.decode_alarm_bit(16) is None

    def test_pss_teleindication3(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication3
        s = PSSTeleindication3(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32528
        assert s.decode_alarm_bit(0) == "LA low voltage cabinet IMD pre-alarm"
        assert s.decode_alarm_bit(15) == "Medium voltage cabinet G3 disconnector switch switch-on"
        assert s.decode_alarm_bit(16) is None

    def test_pss_teleindication4(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication4
        s = PSSTeleindication4(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32529
        assert s.decode_alarm_bit(0) == "Medium voltage cabinet G3 disconnector switch switch-off"
        assert s.decode_alarm_bit(15) == "Medium voltage room door open"
        assert s.decode_alarm_bit(16) is None

    def test_pss_teleindication5(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication5
        s = PSSTeleindication5(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32530
        assert s.decode_alarm_bit(0) == "Medium voltage cabinet G1 cable L1 phase over-temperature"
        assert s.decode_alarm_bit(10) == "Medium voltage protection general alarm"
        assert s.decode_alarm_bit(11) is None  # Out of range


class TestPSSMVElectrical:
    """Tests for PSS medium voltage electrical measurement sensors."""

    def test_pss_mv_phase_a_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVPhaseACurrent
        s = PSSMVPhaseACurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32531
        assert s.gain == 100

    def test_pss_mv_phase_b_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVPhaseBCurrent
        s = PSSMVPhaseBCurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32533

    def test_pss_mv_phase_c_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVPhaseCCurrent
        s = PSSMVPhaseCCurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32535

    def test_pss_mv_zero_sequence_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVZeroSequenceCurrent
        s = PSSMVZeroSequenceCurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32537

    def test_pss_mv_frequency(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVFrequency
        s = PSSMVFrequency(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32539

    def test_pss_mv_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVTemperature
        s = PSSMVTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32540

    def test_pss_mv_humidity(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVHumidity
        s = PSSMVHumidity(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32541


class TestPSSMVCableTemperatures:
    """Tests for PSS cable temperature sensors."""

    def test_pss_mv_g1_cable_l1_phase_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVG1CableL1PhaseTemperature
        s = PSSMVG1CableL1PhaseTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32542

    def test_pss_mv_g1_cable_l2_phase_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVG1CableL2PhaseTemperature
        s = PSSMVG1CableL2PhaseTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32543

    def test_pss_mv_g1_cable_l3_phase_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVG1CableL3PhaseTemperature
        s = PSSMVG1CableL3PhaseTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32544

    def test_pss_mv_g2_cable_l1_phase_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVG2CableL1PhaseTemperature
        s = PSSMVG2CableL1PhaseTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32545

    def test_pss_mv_g2_cable_l2_phase_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVG2CableL2PhaseTemperature
        s = PSSMVG2CableL2PhaseTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32546

    def test_pss_mv_g2_cable_l3_phase_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVG2CableL3PhaseTemperature
        s = PSSMVG2CableL3PhaseTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32547

    def test_pss_mv_g3_cable_l1_phase_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVG3CableL1PhaseTemperature
        s = PSSMVG3CableL1PhaseTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32548

    def test_pss_mv_g3_cable_l2_phase_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVG3CableL2PhaseTemperature
        s = PSSMVG3CableL2PhaseTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32549

    def test_pss_mv_g3_cable_l3_phase_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSMVG3CableL3PhaseTemperature
        s = PSSMVG3CableL3PhaseTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32550


class TestPSSLALBCabinet:
    """Tests for PSS LA and LB cabinet sensors."""

    def test_pss_la_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLATemperature
        s = PSSLATemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32551

    def test_pss_la_humidity(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAHumidity
        s = PSSLAHumidity(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32552

    def test_pss_lb_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBTemperature
        s = PSSLBTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32616

    def test_pss_lb_humidity(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBHumidity
        s = PSSLBHumidity(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32617
class TestPSSRemainingSensors:
    """Tests for remaining PSS sensors."""

    def test_pss_l_a_phase_a_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseAVoltage
        s = PSSLAPhaseAVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32553

    def test_pss_l_a_phase_b_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseBVoltage
        s = PSSLAPhaseBVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32555

    def test_pss_l_a_phase_c_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseCVoltage
        s = PSSLAPhaseCVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32557

    def test_pss_l_a_a_b_line_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAABLineVoltage
        s = PSSLAABLineVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32559

    def test_pss_l_a_b_c_line_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLABCLineVoltage
        s = PSSLABCLineVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32561

    def test_pss_l_a_c_a_line_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLACALineVoltage
        s = PSSLACALineVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32563

    def test_pss_l_a_phase_a_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseACurrent
        s = PSSLAPhaseACurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32565

    def test_pss_l_a_phase_b_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseBCurrent
        s = PSSLAPhaseBCurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32567

    def test_pss_l_a_phase_c_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseCCurrent
        s = PSSLAPhaseCCurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32569

    def test_pss_l_a_phase_a_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseAActivePower
        s = PSSLAPhaseAActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32571

    def test_pss_l_a_phase_b_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseBActivePower
        s = PSSLAPhaseBActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32573

    def test_pss_l_a_phase_c_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseCActivePower
        s = PSSLAPhaseCActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32575

    def test_pss_l_a_total_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLATotalActivePower
        s = PSSLATotalActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32577

    def test_pss_l_a_phase_a_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseAReactivePower
        s = PSSLAPhaseAReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32579

    def test_pss_l_a_phase_b_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseBReactivePower
        s = PSSLAPhaseBReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32581

    def test_pss_l_a_phase_c_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseCReactivePower
        s = PSSLAPhaseCReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32583

    def test_pss_l_a_total_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLATotalReactivePower
        s = PSSLATotalReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32585

    def test_pss_l_a_phase_a_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseAApparentPower
        s = PSSLAPhaseAApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32587

    def test_pss_l_a_phase_b_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseBApparentPower
        s = PSSLAPhaseBApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32589

    def test_pss_l_a_phase_c_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseCApparentPower
        s = PSSLAPhaseCApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32591

    def test_pss_l_a_total_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLATotalApparentPower
        s = PSSLATotalApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32593

    def test_pss_l_a_phase_a_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseAPowerFactor
        s = PSSLAPhaseAPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32595

    def test_pss_l_a_phase_b_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseBPowerFactor
        s = PSSLAPhaseBPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32596

    def test_pss_l_a_phase_c_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAPhaseCPowerFactor
        s = PSSLAPhaseCPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32597

    def test_pss_l_a_total_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLATotalPowerFactor
        s = PSSLATotalPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32598

    def test_pss_l_a_frequency(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAFrequency
        s = PSSLAFrequency(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32599

    def test_pss_l_a_forward_active_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAForwardActiveEnergy
        s = PSSLAForwardActiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32600

    def test_pss_l_a_reverse_active_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAReverseActiveEnergy
        s = PSSLAReverseActiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32604

    def test_pss_l_a_forward_reactive_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAForwardReactiveEnergy
        s = PSSLAForwardReactiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32608

    def test_pss_l_a_reverse_reactive_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLAReverseReactiveEnergy
        s = PSSLAReverseReactiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32612

    def test_pss_l_b_phase_a_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseAVoltage
        s = PSSLBPhaseAVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32618

    def test_pss_l_b_phase_b_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseBVoltage
        s = PSSLBPhaseBVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32620

    def test_pss_l_b_phase_c_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseCVoltage
        s = PSSLBPhaseCVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32622

    def test_pss_l_b_a_b_line_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBABLineVoltage
        s = PSSLBABLineVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32624

    def test_pss_l_b_b_c_line_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBBCLineVoltage
        s = PSSLBBCLineVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32626

    def test_pss_l_b_c_a_line_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBCALineVoltage
        s = PSSLBCALineVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32628

    def test_pss_l_b_phase_a_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseACurrent
        s = PSSLBPhaseACurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32630

    def test_pss_l_b_phase_b_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseBCurrent
        s = PSSLBPhaseBCurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32632

    def test_pss_l_b_phase_c_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseCCurrent
        s = PSSLBPhaseCCurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32634

    def test_pss_l_b_phase_a_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseAActivePower
        s = PSSLBPhaseAActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32636

    def test_pss_l_b_phase_b_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseBActivePower
        s = PSSLBPhaseBActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32638

    def test_pss_l_b_phase_c_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseCActivePower
        s = PSSLBPhaseCActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32640

    def test_pss_l_b_total_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBTotalActivePower
        s = PSSLBTotalActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32642

    def test_pss_l_b_phase_a_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseAReactivePower
        s = PSSLBPhaseAReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32644

    def test_pss_l_b_phase_b_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseBReactivePower
        s = PSSLBPhaseBReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32646

    def test_pss_l_b_phase_c_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseCReactivePower
        s = PSSLBPhaseCReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32648

    def test_pss_l_b_total_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBTotalReactivePower
        s = PSSLBTotalReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32650

    def test_pss_l_b_phase_a_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseAApparentPower
        s = PSSLBPhaseAApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32652

    def test_pss_l_b_phase_b_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseBApparentPower
        s = PSSLBPhaseBApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32654

    def test_pss_l_b_phase_c_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseCApparentPower
        s = PSSLBPhaseCApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32656

    def test_pss_l_b_total_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBTotalApparentPower
        s = PSSLBTotalApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32658

    def test_pss_l_b_phase_a_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseAPowerFactor
        s = PSSLBPhaseAPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32660

    def test_pss_l_b_phase_b_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseBPowerFactor
        s = PSSLBPhaseBPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32661

    def test_pss_l_b_phase_c_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBPhaseCPowerFactor
        s = PSSLBPhaseCPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32662

    def test_pss_l_b_total_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBTotalPowerFactor
        s = PSSLBTotalPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32663

    def test_pss_l_b_frequency(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBFrequency
        s = PSSLBFrequency(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32664

    def test_pss_l_b_forward_active_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBForwardActiveEnergy
        s = PSSLBForwardActiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32665

    def test_pss_l_b_reverse_active_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBReverseActiveEnergy
        s = PSSLBReverseActiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32669

    def test_pss_l_b_forward_reactive_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBForwardReactiveEnergy
        s = PSSLBForwardReactiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32673

    def test_pss_l_b_reverse_reactive_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSLBReverseReactiveEnergy
        s = PSSLBReverseReactiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32677

    def test_pss_transformer_oil_surface_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTransformerOilSurfaceTemperature
        s = PSSTransformerOilSurfaceTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32681

    def test_pss_transformer_winding_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTransformerWindingTemperature
        s = PSSTransformerWindingTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32682

    def test_pss_distribution_cabinet_temperature(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetTemperature
        s = PSSDistributionCabinetTemperature(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32683

    def test_pss_distribution_cabinet_humidity(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetHumidity
        s = PSSDistributionCabinetHumidity(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32684

    def test_pss_distribution_cabinet_phase_a_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseAVoltage
        s = PSSDistributionCabinetPhaseAVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32685

    def test_pss_distribution_cabinet_phase_b_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseBVoltage
        s = PSSDistributionCabinetPhaseBVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32687

    def test_pss_distribution_cabinet_phase_c_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseCVoltage
        s = PSSDistributionCabinetPhaseCVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32689

    def test_pss_distribution_cabinet_a_b_line_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetABLineVoltage
        s = PSSDistributionCabinetABLineVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32691

    def test_pss_distribution_cabinet_b_c_line_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetBCLineVoltage
        s = PSSDistributionCabinetBCLineVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32693

    def test_pss_distribution_cabinet_c_a_line_voltage(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetCALineVoltage
        s = PSSDistributionCabinetCALineVoltage(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32695

    def test_pss_distribution_cabinet_phase_a_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseACurrent
        s = PSSDistributionCabinetPhaseACurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32697

    def test_pss_distribution_cabinet_phase_b_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseBCurrent
        s = PSSDistributionCabinetPhaseBCurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32699

    def test_pss_distribution_cabinet_phase_c_current(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseCCurrent
        s = PSSDistributionCabinetPhaseCCurrent(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32701

    def test_pss_distribution_cabinet_phase_a_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseAActivePower
        s = PSSDistributionCabinetPhaseAActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32703

    def test_pss_distribution_cabinet_phase_b_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseBActivePower
        s = PSSDistributionCabinetPhaseBActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32705

    def test_pss_distribution_cabinet_phase_c_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseCActivePower
        s = PSSDistributionCabinetPhaseCActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32707

    def test_pss_distribution_cabinet_total_active_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetTotalActivePower
        s = PSSDistributionCabinetTotalActivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32709

    def test_pss_distribution_cabinet_phase_a_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseAReactivePower
        s = PSSDistributionCabinetPhaseAReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32711

    def test_pss_distribution_cabinet_phase_b_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseBReactivePower
        s = PSSDistributionCabinetPhaseBReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32713

    def test_pss_distribution_cabinet_phase_c_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseCReactivePower
        s = PSSDistributionCabinetPhaseCReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32715

    def test_pss_distribution_cabinet_total_reactive_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetTotalReactivePower
        s = PSSDistributionCabinetTotalReactivePower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32717

    def test_pss_distribution_cabinet_phase_a_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseAApparentPower
        s = PSSDistributionCabinetPhaseAApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32719

    def test_pss_distribution_cabinet_phase_b_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseBApparentPower
        s = PSSDistributionCabinetPhaseBApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32721

    def test_pss_distribution_cabinet_phase_c_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseCApparentPower
        s = PSSDistributionCabinetPhaseCApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32723

    def test_pss_distribution_cabinet_total_apparent_power(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetTotalApparentPower
        s = PSSDistributionCabinetTotalApparentPower(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32725

    def test_pss_distribution_cabinet_phase_a_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseAPowerFactor
        s = PSSDistributionCabinetPhaseAPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32727

    def test_pss_distribution_cabinet_phase_b_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseBPowerFactor
        s = PSSDistributionCabinetPhaseBPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32728

    def test_pss_distribution_cabinet_phase_c_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetPhaseCPowerFactor
        s = PSSDistributionCabinetPhaseCPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32729

    def test_pss_distribution_cabinet_total_power_factor(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetTotalPowerFactor
        s = PSSDistributionCabinetTotalPowerFactor(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32730

    def test_pss_distribution_cabinet_frequency(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetFrequency
        s = PSSDistributionCabinetFrequency(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32731

    def test_pss_distribution_cabinet_forward_active_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetForwardActiveEnergy
        s = PSSDistributionCabinetForwardActiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32732

    def test_pss_distribution_cabinet_reverse_active_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetReverseActiveEnergy
        s = PSSDistributionCabinetReverseActiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32736

    def test_pss_distribution_cabinet_forward_reactive_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetForwardReactiveEnergy
        s = PSSDistributionCabinetForwardReactiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32740

    def test_pss_distribution_cabinet_reverse_reactive_energy(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSDistributionCabinetReverseReactiveEnergy
        s = PSSDistributionCabinetReverseReactiveEnergy(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.address == 32744
