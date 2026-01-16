import os

import pytest


def pytest_runtest_setup(item):
    if os.environ.get("GITHUB_ACTIONS") == "true":
        pytest.skip("Skipping integration test in CI environment")
