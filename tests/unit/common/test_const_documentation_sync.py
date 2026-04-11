import os
import re

import sigenergy2mqtt.config.const as const


def test_constants_in_documentation():
    """Verify that all defined constants appear in ENV.md and README.md."""
    # Get all constants defined in const.py
    # We filter by variables starting with "SIGENERGY2MQTT_"
    all_constants = [name for name in dir(const) if name.startswith("SIGENERGY2MQTT_") and isinstance(getattr(const, name), str)]

    # Define paths to documentation files
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    env_md_path = os.path.join(project_root, "resources", "configuration", "ENV.md")
    readme_md_path = os.path.join(project_root, "resources", "configuration", "README.md")

    # Read documentation files
    with open(env_md_path, "r", encoding="utf-8") as f:
        env_md_content = f.read()

    with open(readme_md_path, "r", encoding="utf-8") as f:
        readme_md_content = f.read()

    missing_in_env = []
    missing_in_readme = []

    for constant_name in all_constants:
        constant_value = getattr(const, constant_name)

        # Check against ENV.md
        if not re.search(r"\b" + re.escape(constant_value) + r"\b", env_md_content):
            missing_in_env.append(constant_value)

        # Check against README.md
        if not re.search(r"\b" + re.escape(constant_value) + r"\b", readme_md_content):
            missing_in_readme.append(constant_value)

    assert not missing_in_env, f"The following constants are missing from ENV.md: {missing_in_env}"
    assert not missing_in_readme, f"The following constants are missing from README.md: {missing_in_readme}"
