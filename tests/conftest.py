"""Root conftest — shared fixtures and markers for all tests."""
from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir():
    """Path to the test input files directory."""
    return Path(__file__).parent / "input_content"


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests in e2e/ directory."""
    for item in items:
        if "/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
