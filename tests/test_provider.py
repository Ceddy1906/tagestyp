from datetime import date

import pytest

from custom_components.tagestyp.holidays_provider import (
    build_lookup,
    format_date,
    list_subdivisions,
    parse_extra_holidays,
)


def test_subdivisions_at_dach():
    assert "4" in list_subdivisions("AT")  # Oberösterreich
    assert "BY" in list_subdivisions("DE")
    assert "ZH" in list_subdivisions("CH")


def test_austria_national_holiday_german_name():
    lookup = build_lookup("AT", "4", "de")
    assert lookup.get(date(2026, 10, 26)) == "Nationalfeiertag"
    assert lookup.get(date(2026, 12, 25)) is not None


def test_regional_difference():
    # 19.03. (Josefstag) ist nur in einzelnen Bundesländern frei, nicht in OÖ
    assert build_lookup("AT", "4").get(date(2026, 3, 19)) is None


def test_works_for_future_years():
    assert build_lookup("AT", "4").get(date(2030, 1, 1)) is not None


def test_invalid_input():
    with pytest.raises(ValueError):
        build_lookup("US")
    with pytest.raises(ValueError):
        build_lookup("AT", "XX")


def test_extra_holidays_single_and_range():
    extra = parse_extra_holidays(["2026-12-24", "2026-12-28,2026-12-30", " "])
    assert set(extra) == {
        date(2026, 12, 24),
        date(2026, 12, 28),
        date(2026, 12, 29),
        date(2026, 12, 30),
    }
    lookup = build_lookup("AT", "4", extra_holidays=["2026-12-24"])
    assert lookup.get(date(2026, 12, 24)) == "Zusatzfeiertag"


def test_extra_holidays_german_format():
    extra = parse_extra_holidays(["24.12.2026", "28.12.2026,30.12.2026"])
    assert date(2026, 12, 24) in extra and date(2026, 12, 29) in extra
    assert format_date(date(2026, 12, 8)) == "08.12.2026"


@pytest.mark.parametrize("bad", ["24/12/2026", "30.12.2026,28.12.2026", "a,b,c", "31.02.2026"])
def test_extra_holidays_invalid(bad):
    with pytest.raises(ValueError):
        parse_extra_holidays([bad])


def test_next_holiday():
    lookup = build_lookup("AT", "4")
    assert lookup.next_holiday(date(2026, 11, 3)) == (date(2026, 12, 8), "Mariä Empfängnis")
