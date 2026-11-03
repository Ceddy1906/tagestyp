from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import aiohttp
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tagestyp.const import DOMAIN
from custom_components.tagestyp.school_provider import (
    SchoolHolidays,
    parse_school_holidays,
)

from .test_integration import ent, st

TZ = ZoneInfo("Europe/Vienna")

PAYLOAD = [
    {  # regional, passt (AT-4)
        "type": "School", "startDate": "2026-11-02", "endDate": "2026-11-04",
        "name": [{"language": "EN", "text": "Autumn break"}, {"language": "DE", "text": "Herbstferien"}],
        "nationwide": False, "subdivisions": [{"code": "AT-4", "shortName": "4"}],
    },
    {  # anderes Bundesland
        "type": "School", "startDate": "2026-11-10", "endDate": "2026-11-12",
        "name": [{"language": "DE", "text": "Wien-Ferien"}],
        "nationwide": False, "subdivisions": [{"code": "AT-9", "shortName": "9"}],
    },
    {  # bundesweit
        "type": "School", "startDate": "2026-12-24", "endDate": "2027-01-06",
        "name": [{"language": "DE", "text": "Weihnachtsferien"}], "nationwide": True,
    },
    {"type": "School", "startDate": "kaputt", "endDate": "2026-12-01", "nationwide": True},
]


def test_parse_filters_region_and_language():
    res = parse_school_holidays(PAYLOAD, "AT", "4", "de")
    assert [h.name for h in res] == ["Herbstferien", "Weihnachtsferien"]
    assert res[0].covers(date(2026, 11, 4)) and not res[0].covers(date(2026, 11, 5))


def test_parse_without_subdivision_only_nationwide():
    assert [h.name for h in parse_school_holidays(PAYLOAD, "AT", None, "de")] == ["Weihnachtsferien"]


def test_language_fallback_to_english():
    res = parse_school_holidays(PAYLOAD, "AT", "4", "fr")
    assert res[0].name == "Autumn break"


async def _setup(hass, fetch):
    await hass.config.async_set_time_zone("Europe/Vienna")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"country": "AT"},
        options={"subdivision": "4", "language": "de", "extra_holidays": [], "school_holidays": True},
    )
    entry.add_to_hass(hass)
    with patch.object(SchoolHolidays, "_async_fetch_raw", fetch):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_school_sensor_on_during_break(hass, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))

    async def fetch(self, a, b):
        return PAYLOAD

    await _setup(hass, fetch)
    state = st(hass, "binary_sensor", "school_holiday")
    assert state.state == "on"
    assert state.attributes["name"] == "Herbstferien"
    assert state.attributes["end"] == "04.11.2026"
    assert state.attributes["next_name"] == "Weihnachtsferien"
    assert state.attributes["next_start"] == "24.12.2026"
    assert state.attributes["data_stale"] is False


async def test_school_api_down_without_cache_is_unavailable(hass, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))

    async def fetch(self, a, b):
        raise aiohttp.ClientError("offline")

    await _setup(hass, fetch)
    assert st(hass, "binary_sensor", "school_holiday").state == "unavailable"
    assert st(hass, "sensor", "tagestyp").state == "werktag"  # Rest läuft weiter


async def test_school_uses_cache_when_api_down(hass, hass_storage, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"country": "AT"},
        options={"subdivision": "4", "language": "de", "extra_holidays": [], "school_holidays": True},
    )
    hass_storage[f"{DOMAIN}.school_{entry.entry_id}"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.school_{entry.entry_id}",
        "data": {
            "country": "AT", "subdivision": "4", "language": "de",
            "fetched": "2026-11-01T10:00:00+00:00",
            "items": [{"start": "2026-11-02", "end": "2026-11-04", "name": "Herbstferien"}],
        },
    }
    await hass.config.async_set_time_zone("Europe/Vienna")
    entry.add_to_hass(hass)

    async def fetch(self, a, b):
        raise aiohttp.ClientError("offline")

    with patch.object(SchoolHolidays, "_async_fetch_raw", fetch):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    state = st(hass, "binary_sensor", "school_holiday")
    assert state.state == "on"
    assert state.attributes["data_stale"] is True


async def test_no_school_entity_when_disabled(hass, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))
    from .test_integration import _setup as base_setup

    await base_setup(hass, events=[])
    import pytest

    with pytest.raises(AssertionError):
        ent(hass, "binary_sensor", "school_holiday")
