import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Custom Integration in den HA-Testfixtures aktivieren."""
    yield
