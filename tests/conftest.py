import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Custom Integration in den HA-Testfixtures aktivieren."""
    yield


@pytest.fixture(autouse=True)
def no_real_school_api():
    """Tests dürfen nie die echte OpenHolidays-API anfragen."""
    from unittest.mock import patch

    from custom_components.tagestyp.school_provider import SchoolHolidays

    async def _empty(self, valid_from, valid_to):
        return []

    with patch.object(SchoolHolidays, "_async_fetch_raw", _empty):
        yield
