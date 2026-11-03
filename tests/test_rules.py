from datetime import date, datetime
from zoneinfo import ZoneInfo

from custom_components.tagestyp.daytype import classify
from custom_components.tagestyp.holidays_provider import build_lookup
from custom_components.tagestyp.rules import (
    CalendarEvent,
    MatchMode,
    PersonState,
    Rule,
    RuleType,
    evaluate,
)

TZ = ZoneInfo("Europe/Vienna")
LOOKUP = build_lookup("AT", "4", "de")
ARBEIT = Rule("Lissy Arbeiten", RuleType.ARBEIT)
URLAUB = Rule("Lissy Urlaub", RuleType.URLAUB)
FREI = Rule("Lissy Frei", RuleType.FREI, MatchMode.EXACT)


def run(day, events, rules):
    return evaluate(day, classify(day, LOOKUP), events, rules, TZ)


def test_arbeit_am_wochenende_per_termin():
    day = date(2026, 11, 7)  # Samstag
    ev = CalendarEvent("lissy arbeiten (Spät)", day, date(2026, 11, 8))
    res = run(day, [ev], [ARBEIT])
    assert res.state is PersonState.ARBEIT and res.source == "regel"
    assert res.matched_event is ev


def test_arbeitsregel_ohne_termin_ist_frei():
    """Dienstplan im Kalender: kein Termin heißt frei, auch an einem Werktag."""
    res = run(date(2026, 11, 3), [], [ARBEIT])  # Dienstag
    assert res.state is PersonState.FREI and res.source == "kein_termin"


def test_arbeitsregel_termin_am_feiertag_ist_arbeit():
    day = date(2026, 12, 8)  # Feiertag
    ev = CalendarEvent("Lissy Arbeiten", day, date(2026, 12, 9))
    assert run(day, [ev], [ARBEIT]).state is PersonState.ARBEIT


def test_ohne_arbeitsregel_gilt_tagestyp():
    res = run(date(2026, 11, 3), [], [URLAUB])
    assert res.state is PersonState.ARBEIT and res.source == "tagestyp"
    res = run(date(2026, 11, 7), [], [URLAUB])
    assert res.state is PersonState.FREI and res.source == "tagestyp"


def test_urlaub_hat_vorrang_vor_arbeit():
    day = date(2026, 11, 3)
    events = [
        CalendarEvent("Lissy Arbeiten", day, date(2026, 11, 4)),
        CalendarEvent("Lissy Urlaub", day, date(2026, 11, 4)),
    ]
    assert run(day, events, [ARBEIT, URLAUB]).state is PersonState.URLAUB


def test_frei_exakt_matcht_nicht_teilstring():
    day = date(2026, 11, 3)
    ev = CalendarEvent("Lissy Frei morgen", day, date(2026, 11, 4))
    assert run(day, [ev], [FREI]).source == "tagestyp"  # keine Arbeitsregel -> Tagestyp
    ev2 = CalendarEvent("Lissy Frei", day, date(2026, 11, 4))
    assert run(day, [ev2], [FREI]).state is PersonState.FREI


def test_mehrtaegiger_ganztagstermin_ende_exklusiv():
    ev = CalendarEvent("Lissy Urlaub", date(2026, 11, 2), date(2026, 11, 4))
    assert run(date(2026, 11, 3), [ev], [URLAUB]).state is PersonState.URLAUB
    assert run(date(2026, 11, 4), [ev], [URLAUB]).source == "tagestyp"


def test_termin_mit_uhrzeit_ueber_mitternacht():
    ev = CalendarEvent(
        "Lissy Arbeiten",
        datetime(2026, 11, 7, 22, 0, tzinfo=TZ),
        datetime(2026, 11, 8, 6, 0, tzinfo=TZ),
    )
    assert run(date(2026, 11, 8), [ev], [ARBEIT]).state is PersonState.ARBEIT
    assert run(date(2026, 11, 9), [ev], [ARBEIT]).source == "kein_termin"


def test_urlaub_am_feiertag_bleibt_urlaub():
    day = date(2026, 12, 8)
    ev = CalendarEvent("Lissy Urlaub", day, date(2026, 12, 9))
    assert run(day, [ev], [URLAUB]).state is PersonState.URLAUB


def test_leerer_suchstring_matcht_nie():
    day = date(2026, 11, 3)
    ev = CalendarEvent("irgendwas", day, date(2026, 11, 4))
    assert run(day, [ev], [Rule("  ", RuleType.ARBEIT)]).source == "kein_termin"
