"""Pytest configuration."""

import pytest


# Enable asyncio for pytest-asyncio if needed
@pytest.fixture(autouse=True)
def reset_docker_client():
    """Reset any mock state between tests."""
    pass