"""Root-level pytest configuration and shared fixtures."""

import sys
from pathlib import Path

# Add src to path for imports
root_dir = Path(__file__).parent.parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Markers are defined in pyproject.toml, but we can add runtime configuration here
