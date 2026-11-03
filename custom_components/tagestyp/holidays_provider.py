"""Feiertage offline aus der `holidays`-Bibliothek (keine Netzwerkzugriffe)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable

import holidays

from .const import NEXT_HOLIDAY_LOOKAHEAD_DAYS, SUPPORTED_COUNTRIES

EXTRA_HOLIDAY_NAME = "Zusatzfeiertag"


def list_subdivisions(country: str) -> list[str]:
    """Gültige Unterteilungs-Codes (Bundesland/Kanton) laut `holidays`."""
    if country not in SUPPORTED_COUNTRIES:
        raise ValueError(f"Land nicht unterstützt: {country}")
    return sorted(holidays.country_holidays(country).subdivisions)


def format_date(day: date) -> str:
    """Anzeigeformat TT.MM.JJJJ."""
    return day.strftime("%d.%m.%Y")


def _parse_date(value: str) -> date:
    """Akzeptiert TT.MM.JJJJ (bevorzugt) und JJJJ-MM-TT."""
    text = value.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Ungültiges Datum: {value!r} (erwartet TT.MM.JJJJ)")


def parse_extra_holidays(items: Iterable[str]) -> dict[date, str]:
    """Zusatzfeiertage: 'TT.MM.JJJJ' oder Bereich 'TT.MM.JJJJ,TT.MM.JJJJ' (ISO geht auch)."""
    result: dict[date, str] = {}
    for item in items:
        item = item.strip()
        if not item:
            continue
        parts = item.split(",")
        if len(parts) == 1:
            result[_parse_date(parts[0])] = EXTRA_HOLIDAY_NAME
        elif len(parts) == 2:
            start, end = _parse_date(parts[0]), _parse_date(parts[1])
            if end < start:
                raise ValueError(f"Bereich endet vor Beginn: {item!r}")
            for offset in range((end - start).days + 1):
                result[start + timedelta(days=offset)] = EXTRA_HOLIDAY_NAME
        else:
            raise ValueError(f"Ungültiger Eintrag: {item!r}")
    return result


@dataclass
class HolidayLookup:
    """Feiertage für Land/Unterteilung plus Zusatzfeiertage."""

    base: holidays.HolidayBase
    extra: dict[date, str] = field(default_factory=dict)

    def get(self, day: date) -> str | None:
        """Name des Feiertags oder None. Zusatzfeiertage ergänzen die Bibliothek."""
        name = self.base.get(day)
        if name:
            return name
        return self.extra.get(day)

    def is_holiday(self, day: date) -> bool:
        return self.get(day) is not None

    def next_holiday(self, after: date) -> tuple[date, str] | None:
        """Nächster Feiertag ab `after` (inklusive)."""
        for offset in range(NEXT_HOLIDAY_LOOKAHEAD_DAYS + 1):
            day = after + timedelta(days=offset)
            name = self.get(day)
            if name:
                return day, name
        return None


def build_lookup(
    country: str,
    subdivision: str | None = None,
    language: str = "de",
    extra_holidays: Iterable[str] = (),
) -> HolidayLookup:
    """Erzeugt ein Lookup. Wirft ValueError bei ungültigem Land/Code/Datum."""
    if country not in SUPPORTED_COUNTRIES:
        raise ValueError(f"Land nicht unterstützt: {country}")
    if subdivision and subdivision not in list_subdivisions(country):
        raise ValueError(f"Unbekannte Unterteilung {subdivision!r} für {country}")
    base = holidays.country_holidays(
        country, subdiv=subdivision or None, language=language
    )
    return HolidayLookup(base=base, extra=parse_extra_holidays(extra_holidays))
