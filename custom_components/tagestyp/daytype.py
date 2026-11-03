"""Tagestyp: Werktag / Feiertag / Wochenende (reine Logik, ohne HA-Importe)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from .holidays_provider import HolidayLookup


class DayKind(StrEnum):
    WERKTAG = "werktag"
    FEIERTAG = "feiertag"
    WOCHENENDE = "wochenende"


@dataclass(frozen=True)
class DayInfo:
    day: date
    kind: DayKind
    holiday_name: str | None = None
    holiday_on_weekend: bool = False
    is_bridge_day: bool = False


def is_weekend(day: date) -> bool:
    """Wochenende ist fest Sa/So."""
    return day.weekday() >= 5


def _is_bridge_day(day: date, lookup: HolidayLookup) -> bool:
    """Brückentag: Werktag, der nur durch einen Feiertag vom Wochenende getrennt ist.

    Freitag nach Donnerstag-Feiertag, Montag vor Dienstag-Feiertag.
    """
    if is_weekend(day) or lookup.is_holiday(day):
        return False
    weekday = day.weekday()
    if weekday == 4:  # Freitag
        return lookup.is_holiday(day - timedelta(days=1))
    if weekday == 0:  # Montag
        return lookup.is_holiday(day + timedelta(days=1))
    return False


def classify(day: date, lookup: HolidayLookup) -> DayInfo:
    """Feiertag hat Vorrang vor Wochenende (mit Hinweis, wenn er auf Sa/So fällt)."""
    name = lookup.get(day)
    weekend = is_weekend(day)
    if name:
        return DayInfo(
            day=day,
            kind=DayKind.FEIERTAG,
            holiday_name=name,
            holiday_on_weekend=weekend,
        )
    if weekend:
        return DayInfo(day=day, kind=DayKind.WOCHENENDE)
    return DayInfo(
        day=day,
        kind=DayKind.WERKTAG,
        is_bridge_day=_is_bridge_day(day, lookup),
    )
