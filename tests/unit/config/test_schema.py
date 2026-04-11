import os
import pytest
from ruamel.yaml import YAML
from sigenergy2mqtt.config.settings import Settings

# jsonschema is a test dependency
try:
    import jsonschema
except ImportError:
    pytest.skip("jsonschema not installed", allow_module_level=True)

# Find paths relative to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "resources/configuration/sigenergy2mqtt.schema.yaml")
SAMPLE_CONFIG_PATH = os.path.join(PROJECT_ROOT, "resources/configuration/sigenergy2mqtt.yaml")

def load_yaml(path):
    with open(path, "r") as f:
        return YAML(typ="safe").load(f)

def to_json_safe(obj):
    """Convert non-serializable objects (dates, times, enums) to a JSON-safe format or strings."""
    import datetime
    from enum import Enum
    if isinstance(obj, (datetime.date, datetime.time, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_json_safe(i) for i in obj]
    return obj

@pytest.fixture
def schema():
    return load_yaml(SCHEMA_PATH)

@pytest.fixture
def sample_config():
    return load_yaml(SAMPLE_CONFIG_PATH)

def test_schema_validates_sample_config(schema, sample_config):
    """Ensure the sample configuration file matches the schema."""
    # Convert sample_config to json-safe (handles date objects found in YAML)
    instance = to_json_safe(sample_config)
    jsonschema.validate(instance=instance, schema=schema)

def test_schema_validates_pydantic_defaults(schema):
    """Ensure the default settings produced by Pydantic match the schema."""
    from sigenergy2mqtt.config.settings import ModbusConfig
    settings = Settings(modbus=[ModbusConfig(host="localhost")])
    
    # Dump to dict, using aliases to match the YAML structure (e.g. log-level)
    config_dict = settings.model_dump(by_alias=True)
    
    # Convert to json-safe for validation (handles Enums, etc.)
    instance = to_json_safe(config_dict)
    jsonschema.validate(instance=instance, schema=schema)

def test_sensor_overrides_schema(schema):
    """Test that the sensor-overrides pattern properties are working."""
    test_config = {
        "modbus": [{"host": "localhost"}],
        "sensor-overrides": {
            "PlantPVPower": {
                "scan-interval": 5,
                "precision": 2,
                "publishable": True
            },
            "Inverter.*": {
                "debug-logging": True
            }
        }
    }
    jsonschema.validate(instance=test_config, schema=schema)

def test_pvoutput_time_periods_24h(schema):
    """Ensure 24:00 is accepted in PVOutput time periods as per user request."""
    test_config = {
        "modbus": [{"host": "localhost"}],
        "pvoutput": {
            "enabled": True,
            "time-periods": [
                {
                    "plan": "Test",
                    "periods": [
                        {
                            "type": "peak",
                            "start": "10:00",
                            "end": "24:00"
                        }
                    ]
                }
            ]
        }
    }
    jsonschema.validate(instance=test_config, schema=schema)

def test_invalid_log_level_fails(schema):
    """Ensure invalid enum values for log-level fail validation."""
    test_config = {
        "modbus": [{"host": "localhost"}],
        "log-level": "INVALID"
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=test_config, schema=schema)

def test_invalid_modbus_missing_host(schema):
    """Ensure modbus entries require a host."""
    test_config = {
        "modbus": [{"port": 502}]
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=test_config, schema=schema)
