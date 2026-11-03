from datetime import date

from custom_components.tagestyp.daytype import DayKind, classify
from custom_components.tagestyp.holidays_provider import build_lookup

LOOKUP = build_lookup("AT", "4", "de")


def test_werktag():
    info = classify(date(2026, 11, 3), LOOKUP)  # Dienstag
    assert info.kind is DayKind.WERKTAG and not info.is_bridge_day


def test_wochenende():
    assert classify(date(2026, 11, 7), LOOKUP).kind is DayKind.WOCHENENDE  # Sa


def test_feiertag():
    info = classify(date(2026, 12, 8), LOOKUP)  # Dienstag
    assert info.kind is DayKind.FEIERTAG
    assert info.holiday_name == "Mariä Empfängnis"
    assert not info.holiday_on_weekend


def test_feiertag_auf_wochenende_hat_vorrang():
    info = classify(date(2026, 11, 1), LOOKUP)  # Allerheiligen, Sonntag
    assert info.kind is DayKind.FEIERTAG
    assert info.holiday_on_weekend


def test_brueckentag_montag_vor_dienstag_feiertag():
    info = classify(date(2026, 12, 7), LOOKUP)  # Mo vor Di 8.12.
    assert info.kind is DayKind.WERKTAG and info.is_bridge_day


def test_brueckentag_freitag_nach_donnerstag_feiertag():
    info = classify(date(2026, 5, 15), LOOKUP)  # Fr nach Chr. Himmelfahrt 14.5.
    assert info.is_bridge_day


def test_kein_brueckentag_mitten_in_woche():
    assert not classify(date(2026, 12, 9), LOOKUP).is_bridge_day  # Mi nach Di-FT
