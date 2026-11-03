from datetime import date
from zoneinfo import ZoneInfo

from custom_components.tagestyp.engine import PersonConfig, compute_day, rules_from_data
from custom_components.tagestyp.holidays_provider import build_lookup
from custom_components.tagestyp.rules import CalendarEvent, PersonState

TZ = ZoneInfo("Europe/Vienna")
LOOKUP = build_lookup("AT", "4", "de")
RULES = rules_from_data([{"search": "Lissy Arbeiten", "type": "arbeit", "mode": "contains"}])


def test_person_ohne_kalender_nutzt_tagestyp():
    p = PersonConfig("a", "Lissy", None, RULES)
    snap = compute_day(date(2026, 11, 3), LOOKUP, [p], {}, TZ)
    assert snap.persons["a"].state is PersonState.ARBEIT


def test_kalender_nicht_lesbar_ist_unbekannt():
    p = PersonConfig("a", "Lissy", "calendar.x", RULES)
    snap = compute_day(date(2026, 11, 3), LOOKUP, [p], {"a": None}, TZ)
    assert snap.persons["a"] is None


def test_kalendertermin_am_wochenende():
    p = PersonConfig("a", "Lissy", "calendar.x", RULES)
    ev = CalendarEvent("Lissy Arbeiten", date(2026, 11, 7), date(2026, 11, 8))
    snap = compute_day(date(2026, 11, 7), LOOKUP, [p], {"a": [ev]}, TZ)
    assert snap.persons["a"].state is PersonState.ARBEIT


def test_arbeitsregel_ohne_kalender_wirkt_nicht():
    p = PersonConfig("a", "Lissy", None, RULES)
    snap = compute_day(date(2026, 11, 7), LOOKUP, [p], {}, TZ)  # Samstag
    assert snap.persons["a"].state is PersonState.FREI and snap.persons["a"].source == "tagestyp"


def test_dienstplan_ohne_termin_ist_frei_am_werktag():
    p = PersonConfig("a", "Lissy", "calendar.x", RULES)
    snap = compute_day(date(2026, 11, 3), LOOKUP, [p], {"a": []}, TZ)
    assert snap.persons["a"].state is PersonState.FREI and snap.persons["a"].source == "kein_termin"
