from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tagestyp.const import DOMAIN
from custom_components.tagestyp.rules import CalendarEvent

TZ = ZoneInfo("Europe/Vienna")
FETCH = "custom_components.tagestyp.coordinator.TagestypCoordinator._async_fetch_events"


def ent(hass, domain, key):
    """entity_id über die unique_id finden (unabhängig von der Übersetzungssprache)."""
    for e in er.async_get(hass).entities.values():
        if e.platform == DOMAIN and e.domain == domain and e.unique_id.endswith(f"_{key}"):
            return e.entity_id
    raise AssertionError(f"{domain}/{key} nicht gefunden")


def st(hass, domain, key):
    return hass.states.get(ent(hass, domain, key))


async def _setup(hass, events=None, calendar="calendar.dienst"):
    await hass.config.async_set_time_zone("Europe/Vienna")
    hass.states.async_set("person.lissy", "home", {"friendly_name": "Lissy"})
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"country": "AT"},
        options={"subdivision": "4", "language": "de", "extra_holidays": [], "school_holidays": False},
        subentries_data=[
            {
                "subentry_type": "person",
                "title": "Lissy",
                "unique_id": "person.lissy",
                "data": {
                    "person": "person.lissy",
                    "calendar": calendar,
                    "rules": [
                        {"search": "Lissy Arbeiten", "type": "arbeit", "mode": "contains"},
                        {"search": "Lissy Urlaub", "type": "urlaub", "mode": "contains"},
                    ],
                },
            }
        ],
    )
    entry.add_to_hass(hass)

    async def fake(self, entity_id, start, end):
        if events is None:
            raise ValueError("kaputt")
        return events

    with patch(FETCH, fake):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_entities_on_workday(hass, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))  # Dienstag
    await _setup(
        hass, events=[CalendarEvent("Lissy Arbeiten", date(2026, 11, 3), date(2026, 11, 4))]
    )
    assert st(hass, "sensor", "tagestyp").state == "werktag"
    assert st(hass, "binary_sensor", "free_today").state == "off"
    assert st(hass, "binary_sensor", "bridge_day").state == "off"
    nxt = st(hass, "sensor", "next_holiday")
    assert nxt is not None and nxt.state == "08.12.2026"
    assert nxt.attributes["date"] == "2026-12-08"
    assert nxt.attributes["holiday_name"] == "Mariä Empfängnis"
    assert st(hass, "calendar", "holidays") is not None
    assert st(hass, "sensor", "status").state == "arbeit"
    assert st(hass, "binary_sensor", "working").state == "on"


async def test_tomorrow_attributes_holiday(hass, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 12, 7, 8, 0, tzinfo=TZ))  # Mo vor Di-Feiertag
    await _setup(hass, events=[])
    state = st(hass, "sensor", "tagestyp")
    assert state.attributes["is_bridge_day"] is True
    assert state.attributes["tomorrow"] == "feiertag"
    assert state.attributes["tomorrow_holiday_name"] == "Mariä Empfängnis"
    assert st(hass, "binary_sensor", "bridge_day").state == "on"


async def test_vacation_event_wins(hass, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))
    events = [
        CalendarEvent("Lissy Arbeiten", date(2026, 11, 3), date(2026, 11, 4)),
        CalendarEvent("Lissy Urlaub", date(2026, 11, 3), date(2026, 11, 4)),
    ]
    await _setup(hass, events=events)
    status = st(hass, "sensor", "status")
    assert status.state == "urlaub"
    assert status.attributes["source"] == "regel"
    assert st(hass, "binary_sensor", "working").state == "off"


async def test_calendar_error_makes_person_unavailable(hass, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))
    await _setup(hass, events=None)
    assert st(hass, "sensor", "status").state == "unavailable"
    assert st(hass, "sensor", "tagestyp").state == "werktag"  # global bleibt


async def test_check_date_service(hass, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))
    await _setup(hass, events=[])
    with patch(FETCH, lambda *a, **k: _empty()):
        result = await hass.services.async_call(
            DOMAIN, "check_date", {"date": "2026-12-08"}, blocking=True, return_response=True
        )
    assert result["kind"] == "feiertag"
    assert result["holiday_name"] == "Mariä Empfängnis"
    assert result["persons"]["Lissy"]["state"] == "frei"


async def _empty():
    return []


async def test_holiday_calendar_events(hass, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))
    await _setup(hass, events=[])
    events = await hass.services.async_call(
        "calendar", "get_events",
        {"entity_id": ent(hass, "calendar", "holidays"), "start_date_time": "2026-12-01 00:00:00", "end_date_time": "2026-12-31 00:00:00"},
        blocking=True, return_response=True,
    )
    names = [e["summary"] for e in events[ent(hass, "calendar", "holidays")]["events"]]
    assert names == ["Mariä Empfängnis", "Christtag", "Stephanstag"]


async def test_missing_person_creates_issue(hass, freezer: FrozenDateTimeFactory):
    from homeassistant.helpers import issue_registry as ir

    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"country": "AT"},
        options={"subdivision": "4", "language": "de", "extra_holidays": [], "school_holidays": False},
        subentries_data=[{"subentry_type": "person", "title": "Weg", "unique_id": "gone",
                          "data": {"person": "person.weg", "calendar": None, "rules": []}}],
    )
    entry.add_to_hass(hass)
    await hass.config.async_set_time_zone("Europe/Vienna")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    issues = ir.async_get(hass).issues
    assert any(k[1].startswith("person_missing_") for k in issues)


async def test_no_event_means_off_for_schedule_person(hass, freezer: FrozenDateTimeFactory):
    """Regression: Dienstplan-Person ohne Termin heute ist frei, auch am Werktag."""
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))  # Dienstag
    await _setup(hass, events=[])
    status = st(hass, "sensor", "status")
    assert status.state == "frei"
    assert status.attributes["source"] == "kein_termin"
    assert status.attributes["configured_rules"] == [
        "arbeit: Lissy Arbeiten (contains)",
        "urlaub: Lissy Urlaub (contains)",
    ]
    assert st(hass, "binary_sensor", "working").state == "off"


async def test_status_tomorrow_sensor(hass, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))
    await _setup(
        hass,
        events=[
            CalendarEvent("Lissy Arbeiten", date(2026, 11, 3), date(2026, 11, 4)),
            CalendarEvent("Lissy Urlaub", date(2026, 11, 4), date(2026, 11, 5)),
        ],
    )
    assert st(hass, "sensor", "status").state == "arbeit"
    tomorrow = st(hass, "sensor", "status_tomorrow")
    assert tomorrow.state == "urlaub"
    assert tomorrow.attributes["source"] == "regel"
    assert tomorrow.attributes["date"] == "2026-11-04"
    assert "tomorrow" not in tomorrow.attributes


async def test_status_tomorrow_unavailable_when_calendar_fails(hass, freezer: FrozenDateTimeFactory):
    freezer.move_to(datetime(2026, 11, 3, 8, 0, tzinfo=TZ))
    await _setup(hass, events=None)
    assert st(hass, "sensor", "status_tomorrow").state == "unavailable"
