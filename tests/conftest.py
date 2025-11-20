"""Root-level pytest configuration and shared fixtures."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers and settings."""
    # Markers are defined in pyproject.toml, but we can add runtime configuration here
